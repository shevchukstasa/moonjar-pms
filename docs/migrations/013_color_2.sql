-- Migration 013: Add color_2 to production_order_items and order_positions
-- Second color for Stencil/Silkscreen collections and custom items

ALTER TABLE production_order_items
    ADD COLUMN IF NOT EXISTS color_2 VARCHAR(100);

ALTER TABLE order_positions
    ADD COLUMN IF NOT EXISTS color_2 VARCHAR(100);

COMMENT ON COLUMN production_order_items.color_2 IS 'Second color for Stencil/Silkscreen/Custom';
COMMENT ON COLUMN order_positions.color_2 IS 'Second color for Stencil/Silkscreen/Custom';
