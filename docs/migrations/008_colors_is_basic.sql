-- Migration: Add is_basic flag to colors table
-- Date: 2026-03-07
-- Description: Replace base_colors join table with is_basic column directly on colors.
--              Used for surplus routing: 10x10 + basic → showroom, 10x10 + non-basic → casters.

-- 1. Add is_basic column to colors
ALTER TABLE colors ADD COLUMN IF NOT EXISTS is_basic BOOLEAN NOT NULL DEFAULT false;

-- 2. Mark existing 25 catalog colors as basic
UPDATE colors SET is_basic = true;

-- 3. base_colors table remains but is deprecated (empty).
--    Surplus routing now reads colors.is_basic directly.
