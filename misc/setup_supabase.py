"""
Load UCSD dining data into Supabase.
Creates tables via SQL, then bulk-inserts from ucsd_dining_data.json.
"""

import json
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
SUPABASE_KEY = os.environ["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Step 1: Create tables via SQL ---
# Run this in the Supabase SQL Editor (Dashboard > SQL Editor > New Query)
SCHEMA_SQL = """
-- Dining halls (e.g. "64 Degrees", "OceanView")
CREATE TABLE IF NOT EXISTS dining_halls (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    location TEXT,
    menu_url TEXT
);

-- Stations within a dining hall (e.g. "Garden Bar", "Taqueria")
CREATE TABLE IF NOT EXISTS stations (
    id SERIAL PRIMARY KEY,
    dining_hall_id INTEGER REFERENCES dining_halls(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    UNIQUE(dining_hall_id, name)
);

-- Food items with full nutrition
CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,
    station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,
    meal_period TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    price TEXT,
    -- Nutrition
    serving_size TEXT,
    calories INTEGER,
    calories_from_fat INTEGER,
    total_fat_g REAL,
    total_fat_g_dv INTEGER,
    saturated_fat_g REAL,
    saturated_fat_g_dv INTEGER,
    trans_fat_g REAL,
    cholesterol_mg REAL,
    cholesterol_mg_dv INTEGER,
    sodium_mg REAL,
    sodium_mg_dv INTEGER,
    total_carbs_g REAL,
    total_carbs_g_dv INTEGER,
    dietary_fiber_g REAL,
    dietary_fiber_g_dv INTEGER,
    sugars_g REAL,
    sugars_g_dv INTEGER,
    protein_g REAL,
    protein_g_dv INTEGER,
    -- Allergens & ingredients
    allergens TEXT[],
    ingredients TEXT,
    UNIQUE(station_id, meal_period, name)
);
"""


def create_tables():
    """Print the SQL so the user can run it in the Supabase SQL Editor."""
    print("=" * 60)
    print("STEP 1: Run this SQL in your Supabase SQL Editor")
    print("  (Dashboard > SQL Editor > New Query > paste & Run)")
    print("=" * 60)
    print(SCHEMA_SQL)
    print("=" * 60)
    input("Press Enter after you've run the SQL above...")


def load_data():
    """Load dining data from JSON into Supabase tables."""
    with open("ucsd_dining_data.json") as f:
        data = json.load(f)

    print(f"\nLoading {len(data['dining_halls'])} dining halls...")

    for hall in data["dining_halls"]:
        # Insert dining hall
        result = supabase.table("dining_halls").upsert({
            "name": hall["name"],
            "location": hall["location"],
            "menu_url": hall["menu_url"],
        }, on_conflict="name").execute()

        hall_id = result.data[0]["id"]
        print(f"  {hall['name']} (id={hall_id})")

        for station_data in hall["stations"]:
            # Insert station
            result = supabase.table("stations").upsert({
                "dining_hall_id": hall_id,
                "name": station_data["station"],
            }, on_conflict="dining_hall_id,name").execute()

            station_id = result.data[0]["id"]
            print(f"    {station_data['station']} (id={station_id})")

            for meal in station_data["meal_periods"]:
                # Batch insert menu items (Supabase handles up to 1000 per call)
                rows = []
                for item in meal["items"]:
                    n = item["nutrition"]
                    rows.append({
                        "station_id": station_id,
                        "meal_period": meal["meal_period"],
                        "name": item["name"],
                        "category": item.get("category"),
                        "price": item.get("price"),
                        "serving_size": n.get("serving_size"),
                        "calories": n.get("calories"),
                        "calories_from_fat": n.get("calories_from_fat"),
                        "total_fat_g": n.get("total_fat_g"),
                        "total_fat_g_dv": n.get("total_fat_g_dv"),
                        "saturated_fat_g": n.get("saturated_fat_g"),
                        "saturated_fat_g_dv": n.get("saturated_fat_g_dv"),
                        "trans_fat_g": n.get("trans_fat_g"),
                        "cholesterol_mg": n.get("cholesterol_mg"),
                        "cholesterol_mg_dv": n.get("cholesterol_mg_dv"),
                        "sodium_mg": n.get("sodium_mg"),
                        "sodium_mg_dv": n.get("sodium_mg_dv"),
                        "total_carbs_g": n.get("total_carbs_g"),
                        "total_carbs_g_dv": n.get("total_carbs_g_dv"),
                        "dietary_fiber_g": n.get("dietary_fiber_g"),
                        "dietary_fiber_g_dv": n.get("dietary_fiber_g_dv"),
                        "sugars_g": n.get("sugars_g"),
                        "sugars_g_dv": n.get("sugars_g_dv"),
                        "protein_g": n.get("protein_g"),
                        "protein_g_dv": n.get("protein_g_dv"),
                        "allergens": item.get("allergens", []),
                        "ingredients": item.get("ingredients"),
                    })

                if rows:
                    supabase.table("menu_items").upsert(
                        rows,
                        on_conflict="station_id,meal_period,name"
                    ).execute()
                    print(f"      {meal['meal_period']}: {len(rows)} items")

    # Final count
    count = supabase.table("menu_items").select("id", count="exact").execute()
    print(f"\nDone! {count.count} total menu items in Supabase.")


if __name__ == "__main__":
    create_tables()
    load_data()
