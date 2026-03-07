-- Migration: Finished Goods Stock + Stock Shortage System
-- Date: 2026-03-07
-- Description: Add finished goods stock table, metadata_json to tasks, and stock-related enum values

-- 1. New enum values for TaskType
ALTER TYPE task_type ADD VALUE IF NOT EXISTS 'stock_shortage';
ALTER TYPE task_type ADD VALUE IF NOT EXISTS 'stock_transfer';

-- 2. New enum value for NotificationType
ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'stock_shortage';

-- 3. Add metadata_json column to tasks table
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS metadata_json JSONB;

-- 4. Create finished_goods_stock table
CREATE TABLE IF NOT EXISTS finished_goods_stock (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id UUID NOT NULL REFERENCES factories(id),
    color VARCHAR(100) NOT NULL,
    size VARCHAR(50) NOT NULL,
    collection VARCHAR(100),
    product_type product_type DEFAULT 'tile',
    quantity INTEGER NOT NULL DEFAULT 0,
    reserved_quantity INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_finished_goods_stock UNIQUE (factory_id, color, size, collection, product_type)
);

-- 5. Index for efficient availability lookups
CREATE INDEX IF NOT EXISTS idx_finished_goods_color_size
    ON finished_goods_stock (color, size);

CREATE INDEX IF NOT EXISTS idx_finished_goods_factory
    ON finished_goods_stock (factory_id);
