"""Add right_triangle shape; auto-classify existing triangles whose sides
satisfy a²+b²=c² (within tolerance) as right_triangle.

See docs/BUSINESS_LOGIC_FULL.md §29 — right-angle triangle is a distinct shape
because its loading on shelves and pairing in kiln differs from a general
triangle, and operators input only the two legs (hypotenuse is derived).

Revision ID: 031
Revises: 030
Create Date: 2026-04-26
"""
from __future__ import annotations

import math

import sqlalchemy as sa
from alembic import op


revision = '031'
down_revision = '030'
branch_labels = None
depends_on = None


_RIGHT_ANGLE_TOLERANCE_PCT = 0.03  # 3% — covers 10/10/14 rounded to integers


def _is_right_triangle(a: float, b: float, c: float) -> bool:
    sides = sorted([float(a), float(b), float(c)])
    legs_sq = sides[0] ** 2 + sides[1] ** 2
    hyp_sq = sides[2] ** 2
    if hyp_sq == 0:
        return False
    return abs(legs_sq - hyp_sq) / hyp_sq <= _RIGHT_ANGLE_TOLERANCE_PCT


def upgrade() -> None:
    # 1. Add the new enum value (PG enum is append-only).
    op.execute("ALTER TYPE shapetype ADD VALUE IF NOT EXISTS 'right_triangle'")

    # The new value is not visible inside the same transaction in some PG
    # configurations — commit before issuing UPDATE statements that reference it.
    bind = op.get_bind()
    bind.execute(sa.text("COMMIT"))
    bind.execute(sa.text("BEGIN"))

    # 2. Auto-classify existing triangles whose sides satisfy the
    #    Pythagorean theorem (within tolerance) as right_triangle.
    for table, dim_col in (
        ("order_positions", "shape_dimensions"),
        ("production_order_items", "shape_dimensions"),
        ("sizes", "shape_dimensions"),
    ):
        rows = bind.execute(sa.text(
            f"SELECT id, {dim_col} FROM {table} WHERE shape = 'triangle' "
            f"AND {dim_col} IS NOT NULL"
        )).mappings().all()
        for row in rows:
            dims = row[dim_col] or {}
            a = dims.get("side_a_cm") or dims.get("side_a") or dims.get("a")
            b = dims.get("side_b_cm") or dims.get("side_b") or dims.get("b")
            c = dims.get("side_c_cm") or dims.get("side_c") or dims.get("c")
            if a is None or b is None or c is None:
                continue
            try:
                if _is_right_triangle(a, b, c):
                    bind.execute(
                        sa.text(f"UPDATE {table} SET shape = 'right_triangle' WHERE id = :id"),
                        {"id": row["id"]},
                    )
            except (TypeError, ValueError):
                continue

    # 3. Seed shape consumption coefficient for right_triangle (same as triangle).
    bind.execute(sa.text("""
        INSERT INTO shape_consumption_coefficients (id, shape, product_type, coefficient, description)
        SELECT gen_random_uuid(), 'right_triangle', 'tile', 0.5,
               'Right triangle: half of bounding box (a*b/2)'
        WHERE NOT EXISTS (
            SELECT 1 FROM shape_consumption_coefficients
            WHERE shape = 'right_triangle' AND product_type = 'tile'
        )
    """))


def downgrade() -> None:
    # Revert right_triangle rows back to triangle so the enum value can
    # technically become unused. (We can't DROP a single PG enum value
    # safely without recreating the type — leave the value in place.)
    bind = op.get_bind()
    for table in ("order_positions", "production_order_items", "sizes"):
        bind.execute(sa.text(
            f"UPDATE {table} SET shape = 'triangle' WHERE shape = 'right_triangle'"
        ))
    bind.execute(sa.text(
        "DELETE FROM shape_consumption_coefficients "
        "WHERE shape = 'right_triangle' AND product_type = 'tile'"
    ))
