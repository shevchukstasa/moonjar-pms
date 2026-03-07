-- Migration 012: Add sales_manager_contact to production_orders
-- Sales sends manager contact info (phone/email) alongside name

ALTER TABLE production_orders
    ADD COLUMN IF NOT EXISTS sales_manager_contact VARCHAR(300);

COMMENT ON COLUMN production_orders.sales_manager_contact IS 'Sales manager contact (phone/email/WhatsApp)';
