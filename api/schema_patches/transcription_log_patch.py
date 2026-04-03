"""
Schema patch: create transcription_logs table.
Tracks voice message transcriptions from Telegram bot (Whisper API).
Idempotent — safe to run on every startup.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def apply(conn):
    """Create transcription_logs table if not exists."""
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS transcription_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            telegram_user_id BIGINT,
            telegram_chat_id BIGINT,
            audio_duration_sec INTEGER,
            transcribed_text TEXT,
            ai_response_summary VARCHAR(500),
            language_detected VARCHAR(10),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))

    # Index: filter by user
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_transcription_logs_user_id
        ON transcription_logs (user_id)
    """))

    # Index: chronological listing
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_transcription_logs_created
        ON transcription_logs (created_at DESC)
    """))

    # Index: filter by telegram user
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_transcription_logs_tg_user
        ON transcription_logs (telegram_user_id) WHERE telegram_user_id IS NOT NULL
    """))

    logger.info("Schema patch applied: transcription_logs table")
