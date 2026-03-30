"""
Schema patch — widen NUMERIC(5,x) columns to prevent overflow.

Several columns with precision 5 can overflow when:
- Material consumption calculations produce large values
- Coefficients exceed single-digit range
- Defect percentages exceed 10%

This patch widens all known narrow NUMERIC columns to safe ranges.
Called from startup patches in main.py.
"""

import logging
import sqlalchemy as sa

logger = logging.getLogger("moonjar.schema_patches.numeric_precision")

# Each tuple: (table, column, new_type)
ALTERATIONS = [
    # thickness columns: NUMERIC(5,1) -> NUMERIC(8,2) — supports up to 99999.99mm
    ("production_order_items", "thickness", "NUMERIC(8,2)"),
    ("order_positions", "thickness_mm", "NUMERIC(8,2)"),

    # duration columns: NUMERIC(5,1) -> NUMERIC(8,2)
    ("batches", "firing_duration_hours", "NUMERIC(8,2)"),
    ("schedule_slots", "estimated_duration_hours", "NUMERIC(8,2)"),
    ("process_step_templates", "duration_hours", "NUMERIC(8,2)"),

    # firing profile thickness: NUMERIC(5,1) -> NUMERIC(8,2)
    ("firing_profiles", "thickness_min_mm", "NUMERIC(8,2)"),
    ("firing_profiles", "thickness_max_mm", "NUMERIC(8,2)"),
    ("firing_profiles", "total_duration_hours", "NUMERIC(8,2)"),

    # consumption rule thickness: NUMERIC(5,1) -> NUMERIC(8,2)
    ("consumption_rules", "thickness_mm_min", "NUMERIC(8,2)"),
    ("consumption_rules", "thickness_mm_max", "NUMERIC(8,2)"),

    # coefficient columns: NUMERIC(5,3) -> NUMERIC(10,4) — supports coefficients up to 99999.9999
    ("consumption_adjustments", "suggested_coefficient", "NUMERIC(10,4)"),
    ("defect_coefficients", "coefficient", "NUMERIC(10,4)"),

    # specific_gravity: NUMERIC(5,3) -> NUMERIC(8,4)
    ("recipes", "specific_gravity", "NUMERIC(8,4)"),
    ("consumption_rules", "specific_gravity_override", "NUMERIC(8,4)"),

    # lead time avg: NUMERIC(5,1) -> NUMERIC(8,2)
    ("supplier_lead_times", "avg_actual_lead_time_days", "NUMERIC(8,2)"),

    # defect_pct columns: NUMERIC(5,4) -> NUMERIC(8,4)
    ("production_defects", "defect_pct", "NUMERIC(8,4)"),
    ("stone_defect_coefficients", "stone_defect_pct", "NUMERIC(8,4)"),
    ("defect_coefficient_history", "defect_pct", "NUMERIC(8,4)"),

    # percentage columns: NUMERIC(5,2) -> NUMERIC(8,2)
    ("defect_coefficient_settings", "base_percentage", "NUMERIC(8,2)"),
    ("defect_coefficient_settings", "increase_on_defect_percentage", "NUMERIC(8,2)"),
    ("defect_coefficient_settings", "current_percentage", "NUMERIC(8,2)"),
    ("tps_metrics", "defect_percentage", "NUMERIC(8,2)"),
    ("tps_daily_stats", "defect_rate", "NUMERIC(8,2)"),
    ("tps_daily_stats", "oee_percent", "NUMERIC(8,2)"),
    ("tps_bottleneck_snapshots", "current_bottleneck_utilization", "NUMERIC(8,2)"),
    ("material_transactions", "defect_percent", "NUMERIC(8,2)"),
    ("consumption_adjustments", "variance_pct", "NUMERIC(10,2)"),
    ("kpi_targets", "tolerance_percent", "NUMERIC(8,2)"),
    ("finished_goods_stock", "margin_percent", "NUMERIC(8,2)"),
    ("sales_employees", "commission_rate", "NUMERIC(8,2)"),
    ("quality_alert_thresholds", "max_defect_percent", "NUMERIC(8,2)"),
]


def apply_patch(connection):
    """Widen NUMERIC columns to prevent overflow (idempotent)."""
    applied = 0
    for table, column, new_type in ALTERATIONS:
        try:
            # Check if table and column exist first
            check = connection.execute(sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :table AND column_name = :column"
            ), {"table": table, "column": column})
            if not check.fetchone():
                continue

            # Check current type — skip if already wider
            type_check = connection.execute(sa.text(
                "SELECT numeric_precision, numeric_scale "
                "FROM information_schema.columns "
                "WHERE table_name = :table AND column_name = :column"
            ), {"table": table, "column": column})
            row = type_check.fetchone()
            if row and row[0] and row[0] >= 8:
                # Already wide enough
                continue

            sql = f'ALTER TABLE {table} ALTER COLUMN "{column}" TYPE {new_type}'
            connection.execute(sa.text(sql))
            connection.commit()
            applied += 1
            logger.info("NUMERIC_WIDEN | %s.%s -> %s", table, column, new_type)
        except Exception as e:
            try:
                connection.rollback()
            except Exception:
                pass
            # Ignore errors for non-existent tables/columns
            logger.debug("NUMERIC_WIDEN_SKIP | %s.%s: %s", table, column, e)

    if applied:
        logger.info("NUMERIC_PRECISION_PATCH | widened %d columns", applied)
    else:
        logger.info("NUMERIC_PRECISION_PATCH | all columns already at target precision")
