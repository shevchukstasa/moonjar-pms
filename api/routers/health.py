"""Health check router."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "moonjar-pms"}


@router.get("/debug/triggers")
async def debug_triggers(db: Session = Depends(get_db)):
    """Temporary endpoint to inspect DB triggers. Remove after debugging."""
    result = db.execute(text("""
        SELECT pg_get_functiondef(oid)
        FROM pg_proc
        WHERE proname = 'compute_order_status'
    """))
    compute_fn = [row[0] for row in result]

    result2 = db.execute(text("""
        SELECT pg_get_functiondef(oid)
        FROM pg_proc
        WHERE proname = 'trigger_update_order_status'
    """))
    trigger_fn = [row[0] for row in result2]

    result3 = db.execute(text("""
        SELECT tgname, tgtype, pg_get_triggerdef(oid)
        FROM pg_trigger
        WHERE tgrelid = 'order_positions'::regclass
        AND NOT tgisinternal
    """))
    triggers = [{"name": row[0], "type": row[1], "definition": row[2]} for row in result3]

    return {
        "compute_order_status": compute_fn,
        "trigger_update_order_status": trigger_fn,
        "triggers_on_order_positions": triggers,
    }


@router.post("/debug/fix-trigger")
async def fix_trigger(db: Session = Depends(get_db)):
    """Temporary endpoint to fix the compute_order_status trigger. Remove after fix."""
    db.execute(text("""
        CREATE OR REPLACE FUNCTION public.compute_order_status(p_order_id uuid)
         RETURNS order_status
         LANGUAGE plpgsql
        AS $function$
        DECLARE
            min_status_num INTEGER;
            result order_status;
            is_override BOOLEAN;
        BEGIN
            SELECT status_override INTO is_override
            FROM production_orders WHERE id = p_order_id;

            IF is_override THEN
                SELECT status INTO result FROM production_orders WHERE id = p_order_id;
                RETURN result;
            END IF;

            SELECT MIN(
                CASE status
                    WHEN 'planned' THEN 1
                    WHEN 'insufficient_materials' THEN 2
                    WHEN 'awaiting_recipe' THEN 3
                    WHEN 'awaiting_stencil_silkscreen' THEN 4
                    WHEN 'awaiting_color_matching' THEN 5
                    WHEN 'engobe_applied' THEN 6
                    WHEN 'engobe_check' THEN 7
                    WHEN 'glazed' THEN 8
                    WHEN 'pre_kiln_check' THEN 9
                    WHEN 'sent_to_glazing' THEN 10
                    WHEN 'loaded_in_kiln' THEN 11
                    WHEN 'fired' THEN 12
                    WHEN 'transferred_to_sorting' THEN 13
                    WHEN 'refire' THEN 14
                    WHEN 'awaiting_reglaze' THEN 15
                    WHEN 'packed' THEN 16
                    WHEN 'sent_to_quality_check' THEN 17
                    WHEN 'quality_check_done' THEN 18
                    WHEN 'ready_for_shipment' THEN 19
                    WHEN 'blocked_by_qm' THEN 5
                    ELSE 20
                END
            ) INTO min_status_num
            FROM order_positions
            WHERE order_id = p_order_id
              AND status != 'cancelled'
              AND is_merged = FALSE;

            CASE
                WHEN min_status_num IS NULL THEN result := 'new';
                WHEN min_status_num <= 1 THEN result := 'new';
                WHEN min_status_num >= 19 THEN result := 'ready_for_shipment';
                ELSE result := 'in_production';
            END CASE;

            RETURN result;
        END;
        $function$;
    """))
    db.commit()
    return {"status": "ok", "message": "Trigger function fixed: min_status changed from position_status to INTEGER"}
