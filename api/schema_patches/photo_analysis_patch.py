"""Add analysis_result JSONB column to position_photos.

Persists Vision API results (OCR readings, confidence, issues) so they
survive server restarts and can be queried later.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

STATEMENTS = [
    """
    ALTER TABLE position_photos
    ADD COLUMN IF NOT EXISTS analysis_result JSONB;
    """,
    """
    COMMENT ON COLUMN position_photos.analysis_result IS
    'Vision API result: {analysis_type, readings, confidence, issues, raw_description}';
    """,
]


def run(conn):
    for stmt in STATEMENTS:
        try:
            conn.execute(text(stmt))
        except Exception as e:
            logger.warning("photo_analysis_patch statement skipped: %s", e)
