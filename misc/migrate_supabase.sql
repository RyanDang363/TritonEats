-- =============================================================================
-- TritonEats: Supabase migration (run once in SQL Editor)
-- =============================================================================
-- Prerequisites:
--   1. Base schema already exists: dining_halls, stations, menu_items
--      (from setup_supabase.py SCHEMA_SQL or your prior load).
--   2. After this migration, set FastAPI to use SUPABASE_SERVICE_ROLE_KEY
--      (not the anon key) so /recommend can read user_profiles. The anon key
--      has no auth.uid(), so RLS would block profile reads from the server.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. fitness_goal enum (matches Expo survey: cut | bulk | maintain)
-- -----------------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE fitness_goal AS ENUM ('cut', 'bulk', 'maintain');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- -----------------------------------------------------------------------------
-- 2. user_profiles (linked to Supabase Auth)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    fitness_goal fitness_goal NOT NULL DEFAULT 'maintain',
    allergies TEXT[] NOT NULL DEFAULT '{}',
    diet_restrictions TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE user_profiles IS 'TritonEats onboarding: allergies, diet tags, fitness goal per auth user.';

-- -----------------------------------------------------------------------------
-- 3. RLS: users only see/edit their own row (mobile app uses user JWT)
-- -----------------------------------------------------------------------------
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;

CREATE POLICY "Users can view own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON user_profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- -----------------------------------------------------------------------------
-- 4. Dining hall coordinates (for Google Routes walking times)
-- -----------------------------------------------------------------------------
ALTER TABLE dining_halls
    ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;

-- Exact names must match rows in dining_halls.name (case-sensitive).
UPDATE dining_halls SET latitude = 32.8747361891314,   longitude = -117.24203767174787 WHERE name = '64 Degrees';
UPDATE dining_halls SET latitude = 32.887956067919724,  longitude = -117.24206241257659 WHERE name = 'Bistro';
UPDATE dining_halls SET latitude = 32.88403633357428,   longitude = -117.23325809538268 WHERE name = 'Canyon Vista Marketplace';
UPDATE dining_halls SET latitude = 32.87536044758696,   longitude = -117.23494381718517 WHERE name = 'Club Med';
UPDATE dining_halls SET latitude = 32.878896028759875,  longitude = -117.2304497515708  WHERE name = 'Foodworx';
UPDATE dining_halls SET latitude = 32.883301890248696,  longitude = -117.24265415125186 WHERE name = 'OceanView';
UPDATE dining_halls SET latitude = 32.87991281921435,   longitude = -117.24157902483346 WHERE name = 'Restaurants at Sixth College';
UPDATE dining_halls SET latitude = 32.88607466442636,   longitude = -117.24257422659045 WHERE name = 'Ventanas';

-- -----------------------------------------------------------------------------
-- 5. RLS: public read on menu data (FastAPI + anon key read menu + halls)
-- -----------------------------------------------------------------------------
ALTER TABLE dining_halls ENABLE ROW LEVEL SECURITY;
ALTER TABLE stations ENABLE ROW LEVEL SECURITY;
ALTER TABLE menu_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read dining_halls" ON dining_halls;
DROP POLICY IF EXISTS "Public read stations" ON stations;
DROP POLICY IF EXISTS "Public read menu_items" ON menu_items;

CREATE POLICY "Public read dining_halls"
    ON dining_halls FOR SELECT
    USING (true);

CREATE POLICY "Public read stations"
    ON stations FOR SELECT
    USING (true);

CREATE POLICY "Public read menu_items"
    ON menu_items FOR SELECT
    USING (true);

-- -----------------------------------------------------------------------------
-- 6. Optional: verify all halls got coordinates (should return 8 rows)
-- -----------------------------------------------------------------------------
-- SELECT id, name, latitude, longitude FROM dining_halls ORDER BY id;
