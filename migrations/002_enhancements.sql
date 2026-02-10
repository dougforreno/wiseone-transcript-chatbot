-- Enhancement migration: theme search + full-text search support
-- Run after 001_init.sql

-- Add GIN index on themes for array search
CREATE INDEX IF NOT EXISTS idx_transcripts_themes
    ON transcripts USING GIN (themes);

-- Add full-text search column and index on transcript chunks
ALTER TABLE transcript_chunks
    ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;

-- Populate search vectors for existing data
UPDATE transcript_chunks
SET search_vector = to_tsvector('english', content)
WHERE search_vector IS NULL;

-- Auto-update search vector on insert/update
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', NEW.content);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_search_vector ON transcript_chunks;
CREATE TRIGGER trg_update_search_vector
    BEFORE INSERT OR UPDATE OF content ON transcript_chunks
    FOR EACH ROW EXECUTE FUNCTION update_search_vector();

-- GIN index for full-text search
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_search
    ON transcript_chunks USING GIN (search_vector);

-- Enhanced search function: hybrid vector + keyword
CREATE OR REPLACE FUNCTION match_transcript_chunks_hybrid(
    query_embedding VECTOR(1536),
    query_text TEXT DEFAULT '',
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 8
)
RETURNS TABLE (
    id BIGINT,
    transcript_id BIGINT,
    chunk_index INTEGER,
    content TEXT,
    section_header TEXT,
    similarity FLOAT,
    filename TEXT,
    session_date DATE,
    title TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        tc.id,
        tc.transcript_id,
        tc.chunk_index,
        tc.content,
        tc.section_header,
        GREATEST(
            1 - (tc.embedding <=> query_embedding),
            CASE
                WHEN query_text != '' AND tc.search_vector @@ plainto_tsquery('english', query_text)
                THEN ts_rank(tc.search_vector, plainto_tsquery('english', query_text))::FLOAT * 0.5 + 0.5
                ELSE 0
            END
        ) AS similarity,
        t.filename,
        t.session_date,
        t.title
    FROM transcript_chunks tc
    JOIN transcripts t ON t.id = tc.transcript_id
    WHERE 1 - (tc.embedding <=> query_embedding) > match_threshold
       OR (query_text != '' AND tc.search_vector @@ plainto_tsquery('english', query_text))
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- Function to get themes across all transcripts
CREATE OR REPLACE FUNCTION get_all_themes()
RETURNS TABLE (theme TEXT, count BIGINT)
LANGUAGE SQL
AS $$
    SELECT unnest(themes) as theme, count(*) as count
    FROM transcripts
    GROUP BY theme
    ORDER BY count DESC;
$$;
