"""
UCSD HDH Dining Services Scraper
Extracts nutrition facts, allergens, and menu structure for all dining halls.
Outputs JSON with hierarchy: dining_hall -> restaurant/station -> meal_period -> food_item -> nutrition
"""

import json
import re
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://hdh-web.ucsd.edu/dining/apps/diningservices"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

MAX_WORKERS = 10  # concurrent nutrition page fetches


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "UCSD-Dining-Scraper/1.0 (Student Project)"})
    return s


def fetch(url: str, session: requests.Session = None) -> BeautifulSoup:
    session = session or make_session()
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def scrape_restaurants() -> list[dict]:
    """Scrape the restaurant listing page for all dining halls."""
    url = f"{BASE_URL}/Restaurants/Restaurants"
    log.info("Fetching restaurant list")
    soup = fetch(url)

    restaurants = []
    accordion = soup.find("div", id="accordion")
    if not accordion:
        return restaurants

    headers = accordion.find_all("h2")
    for h2 in headers:
        name_tag = h2.find("a")
        if not name_tag:
            continue
        name = name_tag.get_text(strip=True)

        content_div = h2.find_next_sibling("div")
        if not content_div:
            continue

        menu_link = content_div.find("a", href=re.compile(r"Venue_V3"))
        if not menu_link:
            continue

        menu_url = urljoin(BASE_URL + "/", menu_link["href"])
        params = parse_qs(urlparse(menu_url).query)
        loc_id = params.get("locId", [""])[0]

        address = ""
        addr_section = content_div.find("section", class_="contact-module")
        if addr_section:
            addr_text = addr_section.get_text(" ", strip=True)
            match = re.search(r"(9500 Gilman[^\n,]*(?:,\s*\S+)?)", addr_text)
            if match:
                address = match.group(1).strip()

        restaurants.append({
            "name": name,
            "loc_id": loc_id,
            "menu_url": menu_url,
            "address": address or "9500 Gilman Dr, La Jolla, CA 92093",
        })

    log.info("Found %d restaurants", len(restaurants))
    return restaurants


def scrape_menu(menu_url: str, restaurant_name: str) -> list[dict]:
    """Scrape all 7 days of menus for a restaurant, deduplicate items."""
    log.info("Fetching menu for %s", restaurant_name)

    base_params = parse_qs(urlparse(menu_url).query)
    loc_id = base_params.get("locId", [""])[0]
    loc_det_id = base_params.get("locDetID", [""])[0]

    all_items = []
    seen_ids = set()

    for day_num in range(7):
        day_url = f"{BASE_URL}/Restaurants/Venue_V3?locId={loc_id}&locDetID={loc_det_id}&dayNum={day_num}"
        try:
            soup = fetch(day_url)
        except requests.RequestException as e:
            log.warning("  Failed day %d for %s: %s", day_num, restaurant_name, e)
            continue

        items = parse_menu_page(soup, day_num)
        for item in items:
            key = (item["item_id"], item["recipe_id"])
            if key not in seen_ids:
                all_items.append(item)
                seen_ids.add(key)

    log.info("  %d unique items for %s", len(all_items), restaurant_name)
    return all_items


def parse_menu_page(soup: BeautifulSoup, day_num: int) -> list[dict]:
    """Parse a single day's menu page into food items."""
    items = []
    meal_divs = soup.find_all("div", class_="meal-category")

    for meal_div in meal_divs:
        meal_period = meal_div.get("id", "Unknown").replace("_", " ")
        station_sections = meal_div.find_all("div", class_=re.compile(r"menu-category-section"))

        for station_section in station_sections:
            classes = station_section.get("class", [])
            station_name = " ".join(
                cls for cls in classes
                if cls != "menu-category-section" and not cls.startswith("stationID")
            ).strip()

            if not station_name:
                h3 = station_section.find("h3")
                if h3:
                    station_name = h3.get_text(strip=True)

            category_headers = station_section.find_all(
                "div", class_=re.compile(r"panel-heading menu-cat-secondary")
            )

            for cat_header in category_headers:
                current_category = ""
                cat_link = cat_header.find(["a", "h4"])
                if cat_link:
                    current_category = cat_link.get_text(strip=True)

                item_container = cat_header.find_next_sibling("div", class_=re.compile(r"station-list"))
                if not item_container:
                    continue

                large_blocks = item_container.find_all("div", class_=re.compile(r"d-none d-lg-block"))
                if not large_blocks:
                    large_blocks = [item_container]

                seen_in_cat = set()
                for block in large_blocks:
                    for link in block.find_all("a", class_="sublocsitem"):
                        item_name = link.get_text(strip=True)
                        href = link.get("href", "")

                        match = re.search(r"id=(\d+)&recId=(\w+)", href)
                        if not match:
                            continue

                        item_id = match.group(1)
                        recipe_id = match.group(2)

                        if (item_id, recipe_id) in seen_in_cat:
                            continue
                        seen_in_cat.add((item_id, recipe_id))

                        row = link.find_parent("div", class_=re.compile(r"menU-item-row"))
                        calories_inline = None
                        price = None
                        allergens_inline = []

                        if row:
                            cal_span = row.find("span", class_="cals")
                            if cal_span:
                                cal_match = re.search(r"(\d+)", cal_span.get_text(strip=True))
                                if cal_match:
                                    calories_inline = int(cal_match.group(1))

                            price_span = row.find("span", class_="item-price")
                            if price_span:
                                price = price_span.get_text(strip=True)

                            for img in row.find_all("img", title=True):
                                title = img.get("title", "").strip()
                                if title:
                                    allergens_inline.append(title)

                        nutrition_url = urljoin(BASE_URL + "/", href)

                        items.append({
                            "name": item_name,
                            "item_id": item_id,
                            "recipe_id": recipe_id,
                            "meal_period": meal_period,
                            "station": station_name,
                            "category": current_category,
                            "calories_inline": calories_inline,
                            "price": price,
                            "allergens_inline": allergens_inline,
                            "nutrition_url": nutrition_url,
                        })

    return items


def scrape_nutrition(nutrition_url: str, session: requests.Session = None) -> dict:
    """Scrape a single nutrition facts page."""
    try:
        soup = fetch(nutrition_url, session)
    except requests.RequestException as e:
        log.warning("Failed nutrition fetch: %s", e)
        return {}

    result = {}

    h1 = soup.find("h1")
    if h1:
        result["name"] = h1.get_text(strip=True)

    serving_p = soup.find("p", string=re.compile(r"Serving Size"))
    if serving_p:
        result["serving_size"] = serving_p.get_text(strip=True).replace("Serving Size ", "")

    tables = soup.find_all("table")

    for table in tables:
        caption = table.find("caption")
        if caption and "Amount per serving" in caption.get_text():
            for row in table.find_all("tr"):
                th = row.find("th", scope="row")
                td = row.find("td")
                if th and td:
                    key = th.get_text(strip=True)
                    val = td.get_text(strip=True)
                    if key == "Calories":
                        result["calories"] = parse_number(val)
                    elif key == "Calories from Fat":
                        result["calories_from_fat"] = parse_number(val)
            break

    for table in tables:
        caption = table.find("caption")
        if caption and "Nutrition Values" in caption.get_text():
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 4:
                    parse_nutrient(result, cells[0].get_text(strip=True), cells[1].get_text(strip=True))
                    parse_nutrient(result, cells[2].get_text(strip=True), cells[3].get_text(strip=True))
            break

    ing_header = soup.find("h2", string=re.compile(r"Ingredients"))
    if ing_header:
        ing_p = ing_header.find_next_sibling("p")
        if ing_p:
            result["ingredients"] = ing_p.get_text(strip=True)

    allergen_div = soup.find("div", id="allergens")
    if allergen_div:
        allergens = []
        for card in allergen_div.find_all("div", class_="card"):
            footer = card.find("div", class_="card-footer")
            if footer:
                text = footer.get_text(strip=True)
                if text:
                    allergens.append(text)
        result["allergens"] = allergens

    return result


def parse_number(text: str):
    match = re.search(r"([\d.]+)", text)
    if match:
        val = match.group(1)
        return float(val) if "." in val else int(val)
    return None


def parse_nutrient(result: dict, text: str, dv: str):
    text = text.strip()
    if not text or text == "\xa0":
        return

    patterns = [
        (r"Total Fat\s*([\d.]+)\s*g", "total_fat_g"),
        (r"Sat\.?\s*Fat\s*([\d.]+)\s*g", "saturated_fat_g"),
        (r"Trans Fat\s*([\d.]+)\s*g", "trans_fat_g"),
        (r"Cholesterol\s*([\d.]+)\s*mg", "cholesterol_mg"),
        (r"Sodium\s*([\d.]+)\s*mg", "sodium_mg"),
        (r"Tot\.?\s*Carb\.?\s*([\d.]+)\s*g", "total_carbs_g"),
        (r"Dietary Fiber\s*([\d.]+)\s*g", "dietary_fiber_g"),
        (r"Sugars?\s*([\d.]+)\s*g", "sugars_g"),
        (r"Protein\s*([\d.]+)\s*g", "protein_g"),
    ]

    for pattern, key in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1)
            result[key] = float(val) if "." in val else int(val)
            dv_match = re.search(r"(\d+)", dv)
            if dv_match:
                result[f"{key}_dv"] = int(dv_match.group(1))
            return


def fetch_nutrition_batch(items: list[dict]) -> dict:
    """Fetch nutrition for all unique items concurrently. Returns {(item_id, recipe_id): nutrition_dict}."""
    unique = {}
    for item in items:
        key = (item["item_id"], item["recipe_id"])
        if key not in unique:
            unique[key] = item["nutrition_url"]

    log.info("  Fetching nutrition for %d unique items (%d workers)", len(unique), MAX_WORKERS)
    cache = {}
    count = [0]

    def _fetch(key_url):
        key, url = key_url
        session = make_session()
        return key, scrape_nutrition(url, session)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_fetch, (k, u)): k for k, u in unique.items()}
        for future in as_completed(futures):
            key, nutrition = future.result()
            cache[key] = nutrition
            count[0] += 1
            if count[0] % 50 == 0:
                log.info("    Nutrition progress: %d/%d", count[0], len(unique))

    return cache


def build_station_hierarchy(food_items: list[dict]) -> list[dict]:
    """Group flat food items into station -> meal_period -> items hierarchy, deduplicating by name."""
    stations = {}
    seen = {}  # (station, meal_period, name) -> True
    for item in food_items:
        station_name = item.pop("station") or "General"
        meal_period = item.pop("meal_period")

        dedup_key = (station_name, meal_period, item["name"])
        if dedup_key in seen:
            continue
        seen[dedup_key] = True

        if station_name not in stations:
            stations[station_name] = {}
        if meal_period not in stations[station_name]:
            stations[station_name][meal_period] = []

        stations[station_name][meal_period].append(item)

    result = []
    for station_name, meals in stations.items():
        meal_list = [{"meal_period": m, "items": i} for m, i in meals.items()]
        result.append({"station": station_name, "meal_periods": meal_list})
    return result


def main():
    log.info("Starting UCSD Dining scraper")

    restaurants = scrape_restaurants()
    if not restaurants:
        log.error("No restaurants found")
        return

    output = {
        "source": "https://hdh-web.ucsd.edu/dining/apps/diningservices",
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "dining_halls": []
    }

    for rest in restaurants:
        log.info("=" * 60)
        log.info("Processing: %s", rest["name"])

        menu_items = scrape_menu(rest["menu_url"], rest["name"])
        if not menu_items:
            log.warning("  No menu items found, skipping")
            output["dining_halls"].append({
                "name": rest["name"],
                "location": rest["address"],
                "menu_url": rest["menu_url"],
                "stations": [],
            })
            continue

        nutrition_cache = fetch_nutrition_batch(menu_items)

        food_items = []
        for item in menu_items:
            cache_key = (item["item_id"], item["recipe_id"])
            nutrition = nutrition_cache.get(cache_key, {})

            food_items.append({
                "name": item["name"],
                "item_id": item["item_id"],
                "recipe_id": item["recipe_id"],
                "station": item["station"],
                "category": item["category"],
                "meal_period": item["meal_period"],
                "price": item["price"],
                "nutrition": {
                    "serving_size": nutrition.get("serving_size"),
                    "calories": nutrition.get("calories"),
                    "calories_from_fat": nutrition.get("calories_from_fat"),
                    "total_fat_g": nutrition.get("total_fat_g"),
                    "total_fat_g_dv": nutrition.get("total_fat_g_dv"),
                    "saturated_fat_g": nutrition.get("saturated_fat_g"),
                    "saturated_fat_g_dv": nutrition.get("saturated_fat_g_dv"),
                    "trans_fat_g": nutrition.get("trans_fat_g"),
                    "cholesterol_mg": nutrition.get("cholesterol_mg"),
                    "cholesterol_mg_dv": nutrition.get("cholesterol_mg_dv"),
                    "sodium_mg": nutrition.get("sodium_mg"),
                    "sodium_mg_dv": nutrition.get("sodium_mg_dv"),
                    "total_carbs_g": nutrition.get("total_carbs_g"),
                    "total_carbs_g_dv": nutrition.get("total_carbs_g_dv"),
                    "dietary_fiber_g": nutrition.get("dietary_fiber_g"),
                    "dietary_fiber_g_dv": nutrition.get("dietary_fiber_g_dv"),
                    "sugars_g": nutrition.get("sugars_g"),
                    "sugars_g_dv": nutrition.get("sugars_g_dv"),
                    "protein_g": nutrition.get("protein_g"),
                    "protein_g_dv": nutrition.get("protein_g_dv"),
                },
                "allergens": nutrition.get("allergens", item.get("allergens_inline", [])),
                "ingredients": nutrition.get("ingredients"),
            })

        output["dining_halls"].append({
            "name": rest["name"],
            "location": rest["address"],
            "menu_url": rest["menu_url"],
            "stations": build_station_hierarchy(food_items),
        })

    out_path = "ucsd_dining_data.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    total_items = sum(
        len(meal["items"])
        for hall in output["dining_halls"]
        for station in hall["stations"]
        for meal in station["meal_periods"]
    )
    log.info("Done! %d items across %d dining halls -> %s", total_items, len(output["dining_halls"]), out_path)


if __name__ == "__main__":
    main()
