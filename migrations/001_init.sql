-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Transcript documents table
CREATE TABLE IF NOT EXISTS transcripts (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT NOT NULL UNIQUE,
    session_date DATE,
    title TEXT,
    themes TEXT[],
    participants TEXT[],
    duration TEXT,
    raw_content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transcript chunks with embeddings
CREATE TABLE IF NOT EXISTS transcript_chunks (
    id BIGSERIAL PRIMARY KEY,
    transcript_id BIGINT REFERENCES transcripts(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    section_header TEXT,          -- e.g. "Key Teachings", "Full Transcript"
    embedding VECTOR(1536),      -- text-embedding-3-small dimension
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat conversations
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat messages
CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sources JSONB,               -- cited transcript chunks
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_embedding
    ON transcript_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- Index for filtering by transcript
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_transcript_id
    ON transcript_chunks(transcript_id);

-- Index for conversation messages
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
    ON messages(conversation_id);

-- RPC function for semantic search
CREATE OR REPLACE FUNCTION match_transcript_chunks(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5
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
        1 - (tc.embedding <=> query_embedding) AS similarity,
        t.filename,
        t.session_date,
        t.title
    FROM transcript_chunks tc
    JOIN transcripts t ON t.id = tc.transcript_id
    WHERE 1 - (tc.embedding <=> query_embedding) > match_threshold
    ORDER BY tc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
