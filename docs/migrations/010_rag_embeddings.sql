-- Migration 010: RAG embeddings table (pgvector-free)
-- Stores text + OpenAI embeddings as float[] + full-text search via tsvector
-- Works on any PostgreSQL (Railway, Supabase, local, etc.)

CREATE TABLE IF NOT EXISTS rag_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_table    VARCHAR(100) NOT NULL,
    source_id       UUID NOT NULL,
    content_text    TEXT NOT NULL,
    content_tsvector TSVECTOR,
    embedding       FLOAT[] DEFAULT NULL,          -- OpenAI text-embedding-3-small (1536 floats)
    metadata_json   JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for source lookup
CREATE INDEX IF NOT EXISTS idx_rag_source
    ON rag_embeddings(source_table, source_id);

-- GIN index for full-text search
CREATE INDEX IF NOT EXISTS idx_rag_tsvector
    ON rag_embeddings USING GIN (content_tsvector);

-- Auto-populate tsvector on INSERT/UPDATE
CREATE OR REPLACE FUNCTION rag_tsvector_trigger() RETURNS trigger AS $$
BEGIN
    NEW.content_tsvector := to_tsvector('simple', COALESCE(NEW.content_text, ''));
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_rag_tsvector ON rag_embeddings;
CREATE TRIGGER trg_rag_tsvector
    BEFORE INSERT OR UPDATE OF content_text ON rag_embeddings
    FOR EACH ROW EXECUTE FUNCTION rag_tsvector_trigger();
