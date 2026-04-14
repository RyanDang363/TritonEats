"""
TritonEats FastAPI Backend
- POST /recommend: returns top 5 food recommendations based on user preferences, nutrition, and proximity, giving a reason for each recommendation
"""

import json
import os
import time
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
from supabase import create_client

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SUPABASE_URL = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
# Service role bypasses RLS so /recommend can read any user_profiles row by id.
# Anon key cannot read user_profiles (RLS requires auth.uid() = id). Never expose service role in the Expo app.
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GOOGLE_ROUTES_API_KEY = os.environ["GOOGLE_ROUTES_API_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="TritonEats API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Walking time cache: (dining_hall_id, rounded_lat, rounded_lng) -> (walk_seconds, cached_at)
# ---------------------------------------------------------------------------
_walk_cache: dict[tuple, tuple[int, float]] = {}
WALK_CACHE_TTL = 300  # 5 minutes

PACIFIC = ZoneInfo("America/Los_Angeles")

# Hours per dining hall: day index 0=Mon..6=Sun -> (open_hour, open_min, close_hour, close_min) or None if closed
DINING_HALL_HOURS: dict[str, list[tuple[int, int, int, int] | None]] = {
    "64 degrees": [
        (7, 0, 23, 0), (7, 0, 23, 0), (7, 0, 23, 0), (7, 0, 23, 0),  # Mon-Thu
        (7, 0, 20, 0),   # Fri
        (10, 0, 20, 0),  # Sat
        (10, 0, 23, 0),  # Sun
    ],
    "bistro": [
        (11, 0, 21, 0), (11, 0, 21, 0), (11, 0, 21, 0), (11, 0, 21, 0),
        (11, 0, 20, 0),
        None, None,
    ],
    "canyon vista": [
        (7, 0, 21, 0), (7, 0, 21, 0), (7, 0, 21, 0), (7, 0, 21, 0),
        (7, 0, 20, 0),
        (10, 0, 20, 0),
        (10, 0, 20, 0),
    ],
    "club med": [
        (7, 0, 14, 0), (7, 0, 14, 0), (7, 0, 14, 0), (7, 0, 14, 0),
        (7, 0, 14, 0),
        None, None,
    ],
    "foodworx": [
        (9, 0, 20, 0), (9, 0, 20, 0), (9, 0, 20, 0), (9, 0, 20, 0),
        (9, 0, 20, 0),
        None, None,
    ],
    "oceanview": [
        (8, 0, 21, 0), (8, 0, 21, 0), (8, 0, 21, 0), (8, 0, 21, 0),
        (8, 0, 16, 0),
        None, None,
    ],
    "sixth": [
        (8, 0, 23, 0), (8, 0, 23, 0), (8, 0, 23, 0), (8, 0, 23, 0),
        (8, 0, 20, 0),
        (10, 0, 20, 0),
        (10, 0, 23, 0),
    ],
    "ventanas": [
        (7, 0, 23, 0), (7, 0, 23, 0), (7, 0, 23, 0), (7, 0, 23, 0),
        (7, 0, 20, 0),
        (10, 0, 20, 0),
        (10, 0, 23, 0),
    ],
}


def is_hall_open(hall_name: str) -> bool:
    now = datetime.now(PACIFIC)
    day = now.weekday()  # 0=Mon
    name_lower = hall_name.lower()

    for pattern, schedule in DINING_HALL_HOURS.items():
        if pattern in name_lower:
            hours = schedule[day]
            if hours is None:
                return False
            open_h, open_m, close_h, close_m = hours
            current_minutes = now.hour * 60 + now.minute
            open_minutes = open_h * 60 + open_m
            close_minutes = close_h * 60 + close_m
            return open_minutes <= current_minutes < close_minutes
    return True  # default to open if not found


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class RecommendRequest(BaseModel):
    user_id: str
    latitude: float
    longitude: float
    craving: Optional[str] = None


class FoodRecommendation(BaseModel):
    name: str
    dining_hall: str
    station: str
    meal_period: str
    calories: Optional[int] = None
    protein_g: Optional[float] = None
    total_carbs_g: Optional[float] = None
    total_fat_g: Optional[float] = None
    price: Optional[str] = None
    walking_minutes: Optional[int] = None
    scooter_minutes: Optional[int] = None
    is_open: bool = True
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reason: str = ""


class RecommendResponse(BaseModel):
    recommendations: list[FoodRecommendation]


# ---------------------------------------------------------------------------
# Google Routes API
# ---------------------------------------------------------------------------
async def get_walking_time(origin_lat: float, origin_lng: float,
                           dest_lat: float, dest_lng: float) -> Optional[int]:
    """Returns walking time in seconds using Google Routes API."""
    cache_key = (round(dest_lat, 4), round(dest_lng, 4),
                 round(origin_lat, 3), round(origin_lng, 3))
    now = time.time()
    if cache_key in _walk_cache:
        seconds, cached_at = _walk_cache[cache_key]
        if now - cached_at < WALK_CACHE_TTL:
            return seconds

    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_ROUTES_API_KEY,
        "X-Goog-FieldMask": "routes.duration",
    }
    body = {
        "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}},
        "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}},
        "travelMode": "WALK",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=body, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            duration_str = data["routes"][0]["duration"]
            seconds = int(duration_str.rstrip("s"))
            _walk_cache[cache_key] = (seconds, now)
            return seconds
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Data fetching helpers
# ---------------------------------------------------------------------------
def get_user_profile(user_id: str) -> dict:
    result = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User profile not found. Complete the survey first.")
    return result.data[0]


def get_dining_halls_with_coords() -> list[dict]:
    result = (supabase.table("dining_halls")
              .select("id, name, latitude, longitude")
              .not_.is_("latitude", "null")
              .execute())
    return result.data


def get_menu_items_for_halls(hall_ids: list[int]) -> list[dict]:
    result = (supabase.table("stations")
              .select("id, name, dining_hall_id")
              .in_("dining_hall_id", hall_ids)
              .execute())
    stations = result.data
    if not stations:
        return []

    station_map = {s["id"]: s for s in stations}
    station_ids = list(station_map.keys())

    result = (supabase.table("menu_items")
              .select("*")
              .in_("station_id", station_ids)
              .execute())

    for item in result.data:
        station = station_map.get(item["station_id"], {})
        item["_station_name"] = station.get("name", "")
        item["_dining_hall_id"] = station.get("dining_hall_id")

    return result.data


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------
ALLERGEN_MAP = {
    "dairy": "Contains Dairy",
    "eggs": "Contains Eggs",
    "fish": "Contains Fish",
    "shellfish": "Contains Shellfish",
    "tree nuts": "Contains TreeNuts",
    "treenuts": "Contains TreeNuts",
    "peanuts": "Contains Peanuts",
    "wheat": "Contains Wheat",
    "soy": "Contains Soy",
    "gluten": "Contains Gluten",
    "sesame": "Contains Sesame",
}

DIET_TAGS = {
    "vegan": "Vegan",
    "vegetarian": "Vegetarian",
    "halal": "Halal",
}


def filter_items(items: list[dict], profile: dict) -> list[dict]:
    user_allergies = [a.lower().strip() for a in (profile.get("allergies") or [])]
    user_diets = [d.lower().strip() for d in (profile.get("diet_restrictions") or [])]

    blocked_allergen_tags = set()
    for allergy in user_allergies:
        tag = ALLERGEN_MAP.get(allergy)
        if tag:
            blocked_allergen_tags.add(tag)

    filtered = []
    for item in items:
        allergens = item.get("allergens") or []

        if blocked_allergen_tags & set(allergens):
            continue

        if "halal" in user_diets:
            hall_id = item.get("_dining_hall_id")
            hall_name = _hall_name_cache.get(hall_id, "").lower()
            is_halal = "Halal" in allergens or "halal" in hall_name or "canyon vista" in hall_name
            if not is_halal:
                continue

        if "vegan" in user_diets and "Vegan" not in allergens:
            continue

        if "vegetarian" in user_diets:
            is_veg = "Vegetarian" in allergens or "Vegan" in allergens
            if not is_veg:
                continue

        if item.get("calories") is None:
            continue

        filtered.append(item)

    return filtered


_hall_name_cache: dict[int, str] = {}


# ---------------------------------------------------------------------------
# OpenAI ranking
# ---------------------------------------------------------------------------
def rank_with_openai(items: list[dict], profile: dict, hall_walk_times: dict[int, int], craving: Optional[str] = None) -> list[dict]:
    goal = profile.get("fitness_goal", "maintain")
    allergies = profile.get("allergies") or []
    diet_restrictions = profile.get("diet_restrictions") or []

    items_for_prompt = []
    for item in items[:80]:
        hall_id = item.get("_dining_hall_id")
        walk_sec = hall_walk_times.get(hall_id)
        walk_min = round(walk_sec / 60) if walk_sec else None

        items_for_prompt.append({
            "name": item["name"],
            "dining_hall_id": hall_id,
            "station": item.get("_station_name", ""),
            "meal_period": item.get("meal_period", ""),
            "calories": item.get("calories"),
            "protein_g": item.get("protein_g"),
            "total_carbs_g": item.get("total_carbs_g"),
            "total_fat_g": item.get("total_fat_g"),
            "price": item.get("price"),
            "walking_minutes": walk_min,
        })

    restriction_lines = ""
    if allergies:
        restriction_lines += f"\nThe student has these food allergies: {', '.join(allergies)}. NEVER recommend items that likely contain these allergens."
    if diet_restrictions:
        restriction_lines += f"\nThe student follows these dietary restrictions: {', '.join(diet_restrictions)}. Only recommend items compatible with ALL of these."
    if craving:
        restriction_lines += f"\nThe student is currently craving: {craving}. Strongly prioritize items that match or relate to this craving, but still respect all dietary restrictions and allergies."

    craving_priority = ""
    if craving:
        craving_priority = f"\n2. Craving match — the student wants \"{craving}\", so strongly prefer items matching this cuisine or food type"
        priority_nums = """
3. Nutritional fit for their goal ({goal}): cutting = low calorie + high protein, bulking = high calorie + high protein, maintain = balanced macros
4. Proximity (shorter walk is better)
5. Value (reasonable price)"""
    else:
        priority_nums = f"""
2. Nutritional fit for their goal ({goal}): cutting = low calorie + high protein, bulking = high calorie + high protein, maintain = balanced macros
3. Proximity (shorter walk is better)
4. Value (reasonable price)"""

    system_prompt = f"""You are a campus dining advisor for UC San Diego students.
The student's fitness goal is: {goal}.{restriction_lines}

Given the list of available food items with nutrition facts and walking times, pick the 5 best options.
Prioritize:
1. Compatibility with the student's allergies and dietary restrictions (this is mandatory — do not recommend anything that violates them){craving_priority}{priority_nums}

Return ONLY valid JSON — an array of exactly 5 objects with these fields:
- "name": exact item name from the input
- "dining_hall_id": the dining_hall_id from the input
- "reason": one sentence explaining why this is a good pick

No markdown, no extra text. Just the JSON array."""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(items_for_prompt)},
        ],
        temperature=0.3,
        max_tokens=1000,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        picks = json.loads(raw)
    except json.JSONDecodeError:
        return items_for_prompt[:5]

    return picks


# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------
@app.post("/recommend", response_model=RecommendResponse)
async def recommend(req: RecommendRequest):
    profile = get_user_profile(req.user_id)

    halls = get_dining_halls_with_coords()
    if not halls:
        raise HTTPException(status_code=500, detail="No dining halls with coordinates found.")

    open_halls = [h for h in halls if is_hall_open(h["name"])]
    if not open_halls:
        return RecommendResponse(recommendations=[])

    global _hall_name_cache
    _hall_name_cache = {h["id"]: h["name"] for h in open_halls}

    hall_walk_times: dict[int, int] = {}
    for hall in open_halls:
        seconds = await get_walking_time(req.latitude, req.longitude,
                                         hall["latitude"], hall["longitude"])
        if seconds is not None:
            hall_walk_times[hall["id"]] = seconds

    hall_ids = [h["id"] for h in open_halls]
    all_items = get_menu_items_for_halls(hall_ids)

    filtered = filter_items(all_items, profile)
    if not filtered:
        return RecommendResponse(recommendations=[])

    filtered.sort(key=lambda x: hall_walk_times.get(x.get("_dining_hall_id"), 9999))

    picks = rank_with_openai(filtered, profile, hall_walk_times, craving=req.craving)

    item_lookup = {item["name"]: item for item in filtered}
    hall_lookup = {h["id"]: h["name"] for h in open_halls}
    hall_coords = {h["id"]: (h["latitude"], h["longitude"]) for h in open_halls}

    recommendations = []
    for pick in picks[:5]:
        name = pick.get("name", "")
        hall_id = pick.get("dining_hall_id")
        item_data = item_lookup.get(name, {})

        walk_sec = hall_walk_times.get(hall_id)
        walk_min = round(walk_sec / 60) if walk_sec else None
        scooter_min = max(1, round(walk_min / 3)) if walk_min else None

        coords = hall_coords.get(hall_id, (None, None))

        recommendations.append(FoodRecommendation(
            name=name,
            dining_hall=hall_lookup.get(hall_id, "Unknown"),
            station=item_data.get("_station_name", ""),
            meal_period=item_data.get("meal_period", ""),
            calories=item_data.get("calories"),
            protein_g=item_data.get("protein_g"),
            total_carbs_g=item_data.get("total_carbs_g"),
            total_fat_g=item_data.get("total_fat_g"),
            price=item_data.get("price"),
            walking_minutes=walk_min,
            scooter_minutes=scooter_min,
            latitude=coords[0],
            longitude=coords[1],
            reason=pick.get("reason", ""),
        ))

    return RecommendResponse(recommendations=recommendations)


@app.get("/dining-hours")
async def dining_hours():
    """Returns open/closed status for all dining halls."""
    halls = get_dining_halls_with_coords()
    return [
        {"name": h["name"], "is_open": is_hall_open(h["name"])}
        for h in halls
    ]


@app.get("/health")
async def health():
    return {"status": "ok"}
