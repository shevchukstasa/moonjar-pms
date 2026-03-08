-- Migration 014: Add served_locations to factories for delivery location → factory routing
-- Each factory serves specific delivery locations from Sales app

ALTER TABLE factories ADD COLUMN IF NOT EXISTS served_locations JSONB;

-- Seed: Bali factory serves Bali + Lombok
UPDATE factories
SET served_locations = '["Bali", "Lombok"]'::jsonb
WHERE name = 'Bali';

-- Seed: Java factory serves Java + Sumatra + Kalimantan + Sulawesi + Papua + International
UPDATE factories
SET served_locations = '["Java", "Sumatra", "Kalimantan", "Sulawesi", "Papua", "International"]'::jsonb
WHERE name = 'Java';
