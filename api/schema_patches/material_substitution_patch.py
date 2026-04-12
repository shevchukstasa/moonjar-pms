"""Create material_substitutions table + seed CMC ↔ Bentonite pair.

Interchangeable materials with conversion ratio.
Example: 0.2g CMC = 1g Bentonite → ratio = 5.0  (1 unit CMC → 5 units Bentonite)
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS material_substitutions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        material_a_id UUID NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
        material_b_id UUID NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
        ratio NUMERIC(10, 4) NOT NULL,
        notes TEXT,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT uq_material_substitution_pair UNIQUE (material_a_id, material_b_id)
    )
    """,
    # Seed CMC ↔ Bentonite substitution (0.2g CMC = 1g Bentonite)
    # material_a = CMC, material_b = Bentonite, ratio = 5.0
    # Meaning: 1 unit of CMC can be replaced by 5 units of Bentonite
    """
    INSERT INTO material_substitutions (material_a_id, material_b_id, ratio, notes)
    SELECT
        cmc.id,
        ben.id,
        5.0,
        '0.2g CMC = 1g Bentonite. For all glazes.'
    FROM materials cmc, materials ben
    WHERE lower(cmc.name) LIKE '%cmc%'
      AND lower(ben.name) LIKE '%bentonite%'
      AND NOT EXISTS (
          SELECT 1 FROM material_substitutions ms
          WHERE ms.material_a_id = cmc.id AND ms.material_b_id = ben.id
      )
    LIMIT 1
    """,
]


def run(engine):
    with engine.begin() as conn:
        for stmt in STATEMENTS:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                logger.warning("material_substitution_patch: %s — %s", stmt[:60], e)
