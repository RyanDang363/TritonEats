"""
Apply dining hall coordinates after running migrate_supabase.sql in the Supabase dashboard.
Also verifies the user_profiles table exists.
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
SUPABASE_KEY = os.environ["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

DINING_HALL_COORDS = {
    "64 Degrees": (32.8747361891314, -117.24203767174787),
    "Bistro": (32.887956067919724, -117.24206241257659),
    "Canyon Vista Marketplace": (32.88403633357428, -117.23325809538268),
    "Club Med": (32.87536044758696, -117.23494381718517),
    "Foodworx": (32.878896028759875, -117.2304497515708),
    "OceanView": (32.883301890248696, -117.24265415125186),
    "Restaurants at Sixth College": (32.87991281921435, -117.24157902483346),
    "Ventanas": (32.88607466442636, -117.24257422659045),
}


def update_coordinates():
    halls = supabase.table("dining_halls").select("id, name, latitude, longitude").execute()
    print(f"Found {len(halls.data)} dining halls\n")

    for hall in halls.data:
        for pattern, (lat, lng) in DINING_HALL_COORDS.items():
            if pattern.lower() in hall["name"].lower():
                supabase.table("dining_halls").update({
                    "latitude": lat,
                    "longitude": lng,
                }).eq("id", hall["id"]).execute()
                print(f"  Updated {hall['name']}: ({lat}, {lng})")
                break
        else:
            if hall.get("latitude") is None:
                print(f"  WARNING: No coordinates for {hall['name']}")


def verify():
    halls = supabase.table("dining_halls").select("name, latitude, longitude").not_.is_("latitude", "null").execute()
    print(f"\nDining halls with coordinates: {len(halls.data)}")
    for h in halls.data:
        print(f"  {h['name']}: ({h['latitude']}, {h['longitude']})")

    try:
        supabase.table("user_profiles").select("id", count="exact").limit(0).execute()
        print("\nuser_profiles table: EXISTS")
    except Exception as e:
        print(f"\nuser_profiles table: NOT FOUND - run migrate_supabase.sql first!\n  {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("Updating dining hall coordinates...")
    print("=" * 50)
    update_coordinates()
    print("\n" + "=" * 50)
    print("Verifying migration...")
    print("=" * 50)
    verify()
