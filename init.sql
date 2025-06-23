-- Initialize PostgreSQL database for BerryRAG with pgvector extension

-- Create the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create documents table with vector support
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    content TEXT,
    chunk_id INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    content_hash TEXT,
    embedding vector(1536)  -- Default to OpenAI embedding size, will be adjusted based on provider
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_url ON documents(url);
CREATE INDEX IF NOT EXISTS idx_documents_timestamp ON documents(timestamp);
CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create a function to search similar documents
CREATE OR REPLACE FUNCTION search_similar_documents(
    query_embedding vector,
    similarity_threshold float DEFAULT 0.1,
    max_results integer DEFAULT 5
)
RETURNS TABLE (
    id TEXT,
    url TEXT,
    title TEXT,
    content TEXT,
    chunk_id INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    content_hash TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id,
        d.url,
        d.title,
        d.content,
        d.chunk_id,
        d.timestamp,
        d.metadata,
        d.content_hash,
        1 - (d.embedding <=> query_embedding) as similarity
    FROM documents d
    WHERE d.embedding IS NOT NULL
        AND 1 - (d.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY d.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Create a table to store system configuration
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value JSONB,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default configuration
INSERT INTO system_config (key, value) VALUES 
    ('embedding_dimension', '1536'),
    ('embedding_provider', '"openai"'),
    ('version', '"1.0.0"')
ON CONFLICT (key) DO NOTHING;
