-- Migration 015: Universal Firing Profiles + Multi-Firing Support
-- Creates firing_profiles (universal temperature curves) and recipe_firing_stages (multi-round definitions)
-- Adds firing_round to order_positions, firing_profile_id to batches

-- 1. Universal firing profiles (10-20 rows, not per-kiln)
CREATE TABLE IF NOT EXISTS firing_profiles (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                 VARCHAR(200) NOT NULL,
    product_type         product_type,                    -- nullable = matches all types
    collection           VARCHAR(100),                    -- nullable = matches all; "Gold" for Gold-specific
    thickness_min_mm     DECIMAL(5,1),                    -- nullable = no lower bound
    thickness_max_mm     DECIMAL(5,1),                    -- nullable = no upper bound
    target_temperature   INTEGER NOT NULL,                -- max firing temp in °C
    total_duration_hours DECIMAL(5,1) NOT NULL,           -- total cycle time
    stages               JSONB NOT NULL DEFAULT '[]',     -- temperature curve stages
    match_priority       INTEGER NOT NULL DEFAULT 0,      -- higher = more specific, wins
    is_default           BOOLEAN NOT NULL DEFAULT FALSE,
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- stages JSONB structure:
-- [
--   {"stage_num": 1, "name": "Ramp up", "target_temp": 600, "ramp_rate": 100, "hold_minutes": 0, "duration_hours": 2.0},
--   {"stage_num": 2, "name": "Main firing", "target_temp": 1100, "ramp_rate": 125, "hold_minutes": 0, "duration_hours": 4.0},
--   {"stage_num": 3, "name": "Soak", "target_temp": 1100, "ramp_rate": 0, "hold_minutes": 180, "duration_hours": 3.0},
--   {"stage_num": 4, "name": "Cooling", "target_temp": 50, "ramp_rate": -131, "hold_minutes": 0, "duration_hours": 8.0}
-- ]

CREATE INDEX IF NOT EXISTS idx_firing_profiles_product_type ON firing_profiles(product_type);
CREATE INDEX IF NOT EXISTS idx_firing_profiles_collection ON firing_profiles(collection);
CREATE INDEX IF NOT EXISTS idx_firing_profiles_active ON firing_profiles(is_active) WHERE is_active = TRUE;

-- 2. Multi-firing sequence per recipe (Gold = 2 rows, regular = 0 rows → auto 1 round)
CREATE TABLE IF NOT EXISTS recipe_firing_stages (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipe_id               UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    stage_number            INTEGER NOT NULL DEFAULT 1,
    firing_profile_id       UUID REFERENCES firing_profiles(id),
    requires_glazing_before BOOLEAN NOT NULL DEFAULT TRUE,
    description             VARCHAR(200),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(recipe_id, stage_number)
);

CREATE INDEX IF NOT EXISTS idx_recipe_firing_stages_recipe ON recipe_firing_stages(recipe_id);

-- 3. Track firing round on positions
ALTER TABLE order_positions ADD COLUMN IF NOT EXISTS firing_round INTEGER NOT NULL DEFAULT 1;

-- 4. Record which profile was used for a batch
ALTER TABLE batches ADD COLUMN IF NOT EXISTS firing_profile_id UUID REFERENCES firing_profiles(id);
ALTER TABLE batches ADD COLUMN IF NOT EXISTS target_temperature INTEGER;
