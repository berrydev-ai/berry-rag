# BerryRAG Docker Setup with pgvector

This guide explains how to run BerryRAG with Docker and PostgreSQL with pgvector extension.

## Quick Start

1. **Clone and setup environment**:

   ```bash
   # Copy environment file
   cp .env.example .env

   # Edit .env with your OpenAI API key (optional)
   # OPENAI_API_KEY=your_key_here
   ```

2. **Start the services**:
   ```bash
   # Build and start PostgreSQL + Application
   docker-compose up --build
   ```

## Architecture

- **PostgreSQL with pgvector**: Vector database for embeddings
- **Python Application**: RAG system with multiple embedding providers
- **Docker Compose**: Orchestrates both services

## Services

### PostgreSQL (pgvector)

- **Image**: `pgvector/pgvector:pg16`
- **Port**: `5432`
- **Database**: `berryrag`
- **User**: `berryrag`
- **Password**: `berryrag_password`

### Application

- **Build**: Local Dockerfile
- **Port**: `8000`
- **Depends on**: PostgreSQL service

## Usage

### CLI Commands

```bash
# Search documents
docker-compose exec app python src/rag_system_pgvector.py search "your query"

# Get context for query
docker-compose exec app python src/rag_system_pgvector.py context "your query"

# Add document
docker-compose exec app python src/rag_system_pgvector.py add "https://example.com" "Title" /path/to/content.txt

# List documents
docker-compose exec app python src/rag_system_pgvector.py list

# Show statistics
docker-compose exec app python src/rag_system_pgvector.py stats
```

### Python API

```python
from src.rag_system_pgvector import BerryRAGSystem

# Initialize with Docker database
rag = BerryRAGSystem(
    database_url="postgresql://berryrag:berryrag_password@postgres:5432/berryrag"
)

# Add document
doc_id = rag.add_document(
    url="https://example.com",
    title="Example Document",
    content="Your document content here..."
)

# Search
results = rag.search("your query", top_k=5)

# Get formatted context
context = rag.get_context_for_query("your query")
```

## Environment Variables

| Variable               | Default                                                          | Description                                         |
| ---------------------- | ---------------------------------------------------------------- | --------------------------------------------------- |
| `DATABASE_URL`         | `postgresql://berryrag:berryrag_password@postgres:5432/berryrag` | PostgreSQL connection string                        |
| `OPENAI_API_KEY`       | -                                                                | OpenAI API key for embeddings                       |
| `EMBEDDING_PROVIDER`   | `auto`                                                           | `auto`, `sentence-transformers`, `openai`, `simple` |
| `CHUNK_SIZE`           | `500`                                                            | Text chunk size for processing                      |
| `CHUNK_OVERLAP`        | `50`                                                             | Overlap between chunks                              |
| `DEFAULT_TOP_K`        | `5`                                                              | Default number of search results                    |
| `SIMILARITY_THRESHOLD` | `0.1`                                                            | Minimum similarity for search results               |

## Development

### Local Development

```bash
# Start only PostgreSQL
docker-compose up postgres

# Run application locally
export DATABASE_URL="postgresql://berryrag:berryrag_password@localhost:5432/berryrag"
python src/rag_system_pgvector.py stats
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U berryrag -d berryrag

# View documents
SELECT id, title, url, chunk_id FROM documents LIMIT 5;

# Check vector dimensions
SELECT id, array_length(embedding, 1) as dimensions FROM documents LIMIT 1;

# Search similar documents
SELECT * FROM search_similar_documents('[0.1, 0.2, ...]'::vector, 0.5, 5);
```

## Embedding Providers

### OpenAI (Recommended)

- **Dimensions**: 1536
- **Model**: `text-embedding-3-small`
- **Requires**: `OPENAI_API_KEY`

### Sentence Transformers

- **Dimensions**: 384
- **Model**: `all-MiniLM-L6-v2`
- **Requires**: No API key (local model)

### Simple Hash (Fallback)

- **Dimensions**: 128
- **Quality**: Low (for testing only)

## Performance

### pgvector Configuration

The system uses IVFFlat index for fast similarity search:

```sql
CREATE INDEX idx_documents_embedding
ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### Scaling

- **Memory**: Increase for larger embedding models
- **Storage**: PostgreSQL handles large vector datasets efficiently
- **Compute**: Consider GPU for sentence-transformers

## Troubleshooting

### Common Issues

1. **Database Connection Failed**

   ```bash
   # Check if PostgreSQL is running
   docker-compose ps

   # View PostgreSQL logs
   docker-compose logs postgres
   ```

2. **Embedding Dimension Mismatch**

   - The system automatically adjusts vector dimensions
   - Check logs for dimension updates

3. **Out of Memory**

   - Reduce batch size for large documents
   - Use lighter embedding models

4. **Slow Search Performance**
   - Ensure pgvector index is created
   - Adjust `lists` parameter for IVFFlat index

### Logs

```bash
# View application logs
docker-compose logs app

# View PostgreSQL logs
docker-compose logs postgres

# Follow logs in real-time
docker-compose logs -f app
```

## Production Deployment

### Security

1. **Change default passwords**:

   ```yaml
   environment:
     POSTGRES_PASSWORD: your_secure_password
   ```

2. **Use environment files**:

   ```bash
   # Create .env.production
   DATABASE_URL=postgresql://user:pass@host:5432/db
   OPENAI_API_KEY=your_key
   ```

3. **Network security**:
   ```yaml
   # Remove port exposure for production
   # ports:
   #   - "5432:5432"
   ```

### Backup

```bash
# Backup database
docker-compose exec postgres pg_dump -U berryrag berryrag > backup.sql

# Restore database
docker-compose exec -T postgres psql -U berryrag berryrag < backup.sql
```

### Monitoring

```bash
# Check database size
docker-compose exec postgres psql -U berryrag -d berryrag -c "
SELECT
    pg_size_pretty(pg_database_size('berryrag')) as db_size,
    COUNT(*) as document_count
FROM documents;"
```

## API Integration

The system can be extended with a REST API:

```python
# Example Flask integration
from flask import Flask, request, jsonify
from src.rag_system_pgvector import BerryRAGSystem

app = Flask(__name__)
rag = BerryRAGSystem()

@app.route('/search', methods=['POST'])
def search():
    query = request.json['query']
    results = rag.search(query)
    return jsonify([{
        'title': r.document.title,
        'url': r.document.url,
        'similarity': r.similarity,
        'content': r.chunk_text
    } for r in results])

@app.route('/add', methods=['POST'])
def add_document():
    data = request.json
    doc_id = rag.add_document(
        url=data['url'],
        title=data['title'],
        content=data['content']
    )
    return jsonify({'document_id': doc_id})
```

## Next Steps

1. **Add more documents** to your vector database
2. **Experiment with different embedding providers**
3. **Tune similarity thresholds** for your use case
4. **Scale horizontally** with multiple application instances
5. **Add monitoring and alerting** for production use
