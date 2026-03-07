-- Migration 011: Add quantity_sqm to order_positions
-- Stores square-meter quantity alongside piece count (quantity)
-- Sales app sends both quantity (pcs) and quantity_sqm (m²)

ALTER TABLE order_positions
    ADD COLUMN IF NOT EXISTS quantity_sqm NUMERIC(10, 3);

COMMENT ON COLUMN order_positions.quantity_sqm IS 'Quantity in square meters (m²)';
