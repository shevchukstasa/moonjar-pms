-- Migration: Add SHIPPED status and shipped_at
-- Date: 2026-03-07
-- Description: Complete order lifecycle with shipped status for orders and positions

-- 1. Add shipped status to enums
ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'shipped';
ALTER TYPE position_status ADD VALUE IF NOT EXISTS 'shipped';

-- 2. Add shipped_at column to production_orders
ALTER TABLE production_orders ADD COLUMN IF NOT EXISTS shipped_at TIMESTAMPTZ;
