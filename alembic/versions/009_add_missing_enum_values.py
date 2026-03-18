"""Add missing enum values to all PostgreSQL enum types.

Uses ADD VALUE IF NOT EXISTS — safe to run multiple times.
Values that already exist in the DB will be silently skipped.

Revision ID: 009_add_missing_enums
Revises: 008_add_position_schedule_fields
Create Date: 2026-03-16
"""
from alembic import op
from sqlalchemy import text

revision = "009_add_missing_enums"
down_revision = "008_add_position_schedule_fields"
branch_labels = None
depends_on = None


# All enum types → full list of values from api/enums.py
ENUM_VALUES = {
    "position_status": [
        "planned", "insufficient_materials", "awaiting_recipe",
        "awaiting_stencil_silkscreen", "awaiting_color_matching",
        "awaiting_size_confirmation", "engobe_applied", "engobe_check",
        "glazed", "pre_kiln_check", "sent_to_glazing", "loaded_in_kiln",
        "fired", "transferred_to_sorting", "refire", "awaiting_reglaze",
        "packed", "sent_to_quality_check", "quality_check_done",
        "ready_for_shipment", "blocked_by_qm", "shipped", "cancelled",
    ],
    "order_status": [
        "new", "in_production", "partially_ready",
        "ready_for_shipment", "shipped", "cancelled",
    ],
    "task_type": [
        "stencil_order", "silk_screen_order", "color_matching",
        "material_order", "quality_check", "kiln_maintenance",
        "showroom_transfer", "photographing", "mana_confirmation",
        "packing_photo", "recipe_configuration", "repair_sla_alert",
        "reconciliation_alert", "stock_shortage", "stock_transfer",
        "size_resolution",
    ],
    "task_status": [
        "pending", "in_progress", "done", "cancelled",
    ],
    "batch_status": [
        "suggested", "planned", "in_progress", "done",
    ],
    "resource_status": [
        "active", "maintenance_planned", "maintenance_emergency", "inactive",
    ],
    "resource_type": [
        "kiln", "glazing_station", "sorting_station",
    ],
    "purchase_status": [
        "pending", "approved", "sent", "partially_received", "received",
    ],
    "transaction_type": [
        "reserve", "consume", "receive", "order",
        "unreserve", "manual_write_off", "inventory",
    ],
    "user_role": [
        "owner", "administrator", "ceo", "production_manager",
        "quality_manager", "warehouse", "sorter_packer", "purchaser",
        "master", "senior_master",
    ],
    "order_source": [
        "sales_webhook", "pdf_upload", "manual",
    ],
    "change_request_status": [
        "pending", "approved", "rejected",
    ],
    "product_type": [
        "tile", "countertop", "sink", "3d",
    ],
    "shape_type": [
        "rectangle", "square", "round", "freeform", "triangle", "octagon",
    ],
    "split_category": [
        "repair", "refire", "color_mismatch", "reglaze",
    ],
    "defect_stage": [
        "incoming_inspection", "pre_glazing", "after_engobe",
        "before_kiln", "after_firing", "sorting",
    ],
    "defect_outcome": [
        "return_to_work", "write_off", "grinding", "repair",
        "refire", "reglaze", "to_stock", "to_mana",
    ],
    "qc_result": ["ok", "defect"],
    "qc_stage": ["glazing", "firing", "sorting"],
    "batch_mode": ["hybrid", "auto"],
    "batch_creator": ["auto", "manual"],
    "schedule_slot_status": ["planned", "in_progress", "done", "cancelled"],
    "maintenance_status": ["planned", "in_progress", "done"],
    "notification_type": [
        "alert", "task_assigned", "status_change", "material_received",
        "repair_sla", "reconciliation_discrepancy", "order_cancelled",
        "kiln_breakdown", "reference_changed", "ready_for_shipment",
        "stock_shortage", "cancellation_request",
    ],
    "notification_channel": ["in_app", "telegram", "both"],
    "reconciliation_status": ["in_progress", "completed", "cancelled", "scheduled"],
    "grinding_status": ["in_stock", "sent_to_mana", "used_in_production"],
    "repair_status": ["in_repair", "repaired", "returned_to_production", "written_off"],
    "mana_shipment_status": ["pending", "confirmed", "shipped"],
    "write_off_reason": ["breakage", "loss", "damage", "expired", "adjustment", "other"],
    "media_type": ["photo", "video", "audio", "document"],
    "dashboard_type": ["owner", "ceo", "manager", "quality", "warehouse", "packing", "purchaser"],
    "expense_type": ["opex", "capex"],
    "expense_category": ["materials", "labor", "utilities", "maintenance", "equipment", "logistics", "other"],
    "kiln_constants_mode": ["manual", "production"],
    "language_preference": ["en", "ru", "id"],
    "audit_action_type": [
        "login_success", "login_failed", "logout", "token_refresh",
        "password_change", "role_change", "user_create", "user_deactivate",
        "permission_grant", "permission_revoke", "data_export",
        "file_upload", "file_download", "settings_change", "webhook_received",
        "totp_setup", "totp_disable", "session_revoke",
        "ip_allowlist_change", "factory_create", "factory_delete",
        "anomaly_detected",
    ],
    "ip_scope": ["admin_panel", "webhook", "all"],
    "qm_block_type": ["position", "batch"],
    "surplus_disposition_type": ["showroom", "casters", "mana"],
    "casters_removed_reason": ["used", "shipped_to_mana", "other"],
    "tps_deviation_type": ["positive", "negative"],
    "tps_status": ["normal", "warning", "critical"],
    "buffer_health": ["green", "yellow", "red"],
    "related_entity_type": ["order", "position", "task", "material", "kiln"],
    "reference_action": ["create", "update", "delete"],
    "problem_card_mode": ["simple", "full_8d"],
    "problem_card_status": ["open", "in_progress", "closed"],
    "backup_status": ["in_progress", "success", "failed"],
    "backup_type": ["scheduled", "manual"],
    "engobe_type": ["standard", "shelf_coating", "hole_filler"],
    "night_alert_level": ["morning", "repeat", "call"],
}


def upgrade() -> None:
    conn = op.get_bind()

    for enum_name, values in ENUM_VALUES.items():
        # First check if the enum type exists
        exists = conn.execute(text(
            "SELECT 1 FROM pg_type WHERE typname = :name"
        ), {"name": enum_name}).fetchone()

        if not exists:
            # Create the enum type if it doesn't exist at all
            vals_str = ", ".join(f"'{v}'" for v in values)
            conn.execute(text(f"CREATE TYPE {enum_name} AS ENUM ({vals_str});"))
        else:
            # Add missing values
            for val in values:
                conn.execute(text(
                    f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{val}';"
                ))


def downgrade() -> None:
    # PostgreSQL doesn't support removing values from enums
    pass
