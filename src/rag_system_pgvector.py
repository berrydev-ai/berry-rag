#!/usr/bin/env python3
"""
BerryRAG: Local RAG System with pgvector Storage
Optimized for Playwright MCP integration with Claude
"""

import os
import json
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from dataclasses import dataclass, asdict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available. Install with: pip install sentence-transformers")

try:
    import openai
    from dotenv import load_dotenv
    load_dotenv()
    OPENAI_AVAILABLE = bool(os.getenv('OPENAI_API_KEY'))
except ImportError:
    OPENAI_AVAILABLE = False

@dataclass
class Document:
    id: str
    url: str
    title: str
    content: str
    chunk_id: int
    timestamp: str
    metadata: Dict[str, Any]

@dataclass
class QueryResult:
    document: Document
    similarity: float
    chunk_text: str

class EmbeddingProvider:
    """Handles different embedding providers with fallbacks"""
    
    def __init__(self, provider: str = "auto"):
        self.provider = provider
        self.model = None
        self._init_provider()
    
    def _init_provider(self):
        if self.provider == "auto":
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.provider = "sentence-transformers"
            elif OPENAI_AVAILABLE:
                self.provider = "openai"
            else:
                self.provider = "simple"
        
        if self.provider == "sentence-transformers" and SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.info("Loading sentence-transformers model...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.embedding_dim = 384
            logger.info("✅ Sentence-transformers model loaded")
        
        elif self.provider == "openai" and OPENAI_AVAILABLE:
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.embedding_dim = 1536  # text-embedding-3-small
            logger.info("✅ OpenAI embeddings configured")
        
        else:
            self.provider = "simple"
            self.embedding_dim = 128
            logger.info("⚠️  Using simple hash-based embeddings (not recommended for production)")
    
    def encode(self, text: str) -> np.ndarray:
        """Generate embedding for text"""
        if self.provider == "sentence-transformers":
            return self.model.encode(text)
        
        elif self.provider == "openai":
            try:
                response = openai.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                return np.array(response.data[0].embedding)
            except Exception as e:
                logger.error(f"OpenAI embedding failed: {e}")
                return self._simple_embedding(text)
        
        else:
            return self._simple_embedding(text)
    
    def _simple_embedding(self, text: str) -> np.ndarray:
        """Simple hash-based embedding as fallback"""
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        # Convert to float array normalized to [-1, 1]
        embedding = np.array([
            (b - 128) / 128 for b in hash_bytes[:self.embedding_dim]
        ])
        return embedding

class BerryRAGSystem:
    def __init__(self, database_url: str = None, storage_path: str = "./storage"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Database connection
        self.database_url = database_url or os.getenv('DATABASE_URL', 
            'postgresql://berryrag:berryrag_password@localhost:5432/berryrag')
        
        # Initialize embedding provider
        self.embedder = EmbeddingProvider(os.getenv('EMBEDDING_PROVIDER', 'auto'))
        
        # Initialize database
        self._init_database()
        
        logger.info(f"🚀 BerryRAG initialized with pgvector")
        logger.info(f"📊 Embedding provider: {self.embedder.provider}")
        logger.info(f"📐 Embedding dimension: {self.embedder.embedding_dim}")
    
    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)
    
    def _init_database(self):
        """Initialize PostgreSQL database and update embedding dimension if needed"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if we need to update the embedding dimension
                    cur.execute("SELECT value FROM system_config WHERE key = 'embedding_dimension'")
                    result = cur.fetchone()
                    
                    stored_dim = int(result['value']) if result else 1536
                    
                    if stored_dim != self.embedder.embedding_dim:
                        logger.info(f"Updating embedding dimension from {stored_dim} to {self.embedder.embedding_dim}")
                        
                        # Drop the existing index and column
                        cur.execute("DROP INDEX IF EXISTS idx_documents_embedding")
                        cur.execute("ALTER TABLE documents DROP COLUMN IF EXISTS embedding")
                        
                        # Add new column with correct dimension
                        cur.execute(f"ALTER TABLE documents ADD COLUMN embedding vector({self.embedder.embedding_dim})")
                        
                        # Recreate index
                        cur.execute(f"""
                            CREATE INDEX idx_documents_embedding 
                            ON documents USING ivfflat (embedding vector_cosine_ops) 
                            WITH (lists = 100)
                        """)
                        
                        # Update configuration
                        cur.execute("""
                            INSERT INTO system_config (key, value, updated_at) 
                            VALUES ('embedding_dimension', %s, NOW())
                            ON CONFLICT (key) DO UPDATE SET 
                                value = EXCLUDED.value, 
                                updated_at = EXCLUDED.updated_at
                        """, (str(self.embedder.embedding_dim),))
                        
                        cur.execute("""
                            INSERT INTO system_config (key, value, updated_at) 
                            VALUES ('embedding_provider', %s, NOW())
                            ON CONFLICT (key) DO UPDATE SET 
                                value = EXCLUDED.value, 
                                updated_at = EXCLUDED.updated_at
                        """, (json.dumps(self.embedder.provider),))
                        
                        conn.commit()
                        logger.info("✅ Database schema updated")
                    
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks with smart boundaries"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            if end >= len(text):
                chunk = text[start:].strip()
                if chunk:
                    chunks.append(chunk)
                break
            
            # Try to break at natural boundaries
            chunk_text = text[start:end]
            
            # Look for sentence boundaries
            sentence_breaks = [chunk_text.rfind('. '), chunk_text.rfind('.\n'), 
                             chunk_text.rfind('? '), chunk_text.rfind('! ')]
            sentence_break = max([b for b in sentence_breaks if b > start + chunk_size // 2] or [-1])
            
            if sentence_break > 0:
                end = start + sentence_break + 1
            else:
                # Look for paragraph boundaries
                para_break = chunk_text.rfind('\n\n')
                if para_break > start + chunk_size // 3:
                    end = start + para_break + 2
                else:
                    # Look for line boundaries
                    line_break = chunk_text.rfind('\n')
                    if line_break > start + chunk_size // 2:
                        end = start + line_break + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def add_document(self, url: str, title: str, content: str, metadata: Dict = None) -> str:
        """Add document to the vector database"""
        metadata = metadata or {}
        
        # Generate content hash for deduplication
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Check if document already exists
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT id FROM documents WHERE url = %s AND content_hash = %s LIMIT 1',
                    (url, content_hash)
                )
                existing = cur.fetchone()
                
                if existing:
                    logger.info(f"📄 Document already exists: {title}")
                    return existing['id'].split('_')[0]  # Return base doc ID
        
        # Generate document ID
        doc_id = hashlib.md5(f"{url}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        timestamp = datetime.now()
        
        # Chunk the content
        chunks = self.chunk_text(content)
        logger.info(f"📝 Processing document: {title} ({len(chunks)} chunks)")
        
        # Store chunks and generate embeddings
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{doc_id}_{i}"
                    
                    document_metadata = {
                        **metadata,
                        'total_chunks': len(chunks),
                        'content_hash': content_hash,
                        'original_length': len(content)
                    }
                    
                    # Generate embedding
                    try:
                        embedding = self.embedder.encode(chunk)
                        embedding_list = embedding.tolist()
                    except Exception as e:
                        logger.error(f"Failed to generate embedding for chunk {i}: {e}")
                        continue
                    
                    # Store in PostgreSQL
                    cur.execute('''
                        INSERT INTO documents 
                        (id, url, title, content, chunk_id, timestamp, metadata, content_hash, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            url = EXCLUDED.url,
                            title = EXCLUDED.title,
                            content = EXCLUDED.content,
                            chunk_id = EXCLUDED.chunk_id,
                            timestamp = EXCLUDED.timestamp,
                            metadata = EXCLUDED.metadata,
                            content_hash = EXCLUDED.content_hash,
                            embedding = EXCLUDED.embedding
                    ''', (
                        chunk_id, url, title, chunk, i, timestamp, 
                        json.dumps(document_metadata), content_hash, embedding_list
                    ))
                
                conn.commit()
        
        logger.info(f"✅ Added document: {title} (ID: {doc_id})")
        self._update_query_interface()
        return doc_id
    
    def search(self, query: str, top_k: int = 5, similarity_threshold: float = 0.1) -> List[QueryResult]:
        """Search for similar documents using pgvector"""
        try:
            query_embedding = self.embedder.encode(query)
            query_embedding_list = query_embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return []
        
        results = []
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Use the PostgreSQL function for similarity search
                    cur.execute("""
                        SELECT * FROM search_similar_documents(%s, %s, %s)
                    """, (query_embedding_list, similarity_threshold, top_k))
                    
                    rows = cur.fetchall()
                    
                    for row in rows:
                        try:
                            metadata = json.loads(row['metadata']) if row['metadata'] else {}
                        except:
                            metadata = {}
                        
                        document = Document(
                            id=row['id'],
                            url=row['url'],
                            title=row['title'],
                            content=row['content'],
                            chunk_id=row['chunk_id'],
                            timestamp=row['timestamp'].isoformat(),
                            metadata=metadata
                        )
                        
                        results.append(QueryResult(
                            document=document,
                            similarity=float(row['similarity']),
                            chunk_text=row['content']
                        ))
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
        
        return results
    
    def get_context_for_query(self, query: str, max_chars: int = 4000) -> str:
        """Get relevant context for a query, formatted for Claude"""
        results = self.search(query, top_k=10)
        
        if not results:
            return f"No relevant context found for query: {query}"
        
        context_parts = [f"🔍 Context for query: '{query}'\n"]
        total_chars = len(context_parts[0])
        
        for i, result in enumerate(results, 1):
            context_part = f"""
📄 Source {i}: {result.document.title}
🔗 URL: {result.document.url}
📊 Similarity: {result.similarity:.3f}
📝 Content:
{result.chunk_text}

---
"""
            
            if total_chars + len(context_part) <= max_chars:
                context_parts.append(context_part)
                total_chars += len(context_part)
            else:
                remaining_chars = max_chars - total_chars
                if remaining_chars > 200:  # Only add if meaningful content fits
                    truncated = context_part[:remaining_chars-50] + "\n[Content truncated...]\n---\n"
                    context_parts.append(truncated)
                break
        
        if len(results) == 0:
            context_parts.append("ℹ️ No relevant documents found. Try different search terms.")
        
        return "".join(context_parts)
    
    def list_documents(self) -> List[Dict]:
        """List all stored documents"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT url, title, MAX(timestamp) as latest_timestamp, 
                           COUNT(*) as chunk_count, 
                           (array_agg(metadata ORDER BY timestamp DESC))[1] as metadata
                    FROM documents 
                    GROUP BY url, title
                    ORDER BY latest_timestamp DESC
                ''')
                
                documents = []
                for row in cur.fetchall():
                    try:
                        metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    except:
                        metadata = {}
                    
                    documents.append({
                        "url": row['url'],
                        "title": row['title'],
                        "timestamp": row['latest_timestamp'].isoformat(),
                        "chunk_count": row['chunk_count'],
                        "content_length": metadata.get('original_length', 0),
                        "source": metadata.get('source', 'unknown')
                    })
                
                return documents
    
    def get_stats(self) -> Dict:
        """Get system statistics"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(DISTINCT url) FROM documents')
                doc_count = cur.fetchone()[0]
                
                cur.execute('SELECT COUNT(*) FROM documents')
                chunk_count = cur.fetchone()[0]
                
                # Get database size
                cur.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size,
                           pg_database_size(current_database()) as db_size_bytes
                """)
                db_info = cur.fetchone()
                
                return {
                    "document_count": doc_count,
                    "chunk_count": chunk_count,
                    "embedding_provider": self.embedder.provider,
                    "embedding_dimension": self.embedder.embedding_dim,
                    "database_size": db_info['db_size'],
                    "database_size_bytes": db_info['db_size_bytes'],
                    "storage_path": str(self.storage_path.absolute()),
                    "database_url": self.database_url.split('@')[1] if '@' in self.database_url else "localhost"
                }
    
    def _update_query_interface(self):
        """Update the query interface file for external access"""
        interface_path = self.storage_path / "query_interface.json"
        
        interface = {
            "system": "BerryRAG pgvector Database",
            "last_updated": datetime.now().isoformat(),
            "stats": self.get_stats(),
            "usage": {
                "search": "python src/rag_system_pgvector.py search 'your query'",
                "context": "python src/rag_system_pgvector.py context 'your query'",
                "list": "python src/rag_system_pgvector.py list",
                "add": "python src/rag_system_pgvector.py add <url> <title> <content_file>"
            },
            "recent_documents": self.list_documents()[:10]  # Latest 10 docs
        }
        
        with open(interface_path, 'w') as f:
            json.dump(interface, f, indent=2)

def main():
    """CLI interface for the RAG system"""
    import sys
    
    if len(sys.argv) < 2:
        print("""
🍓 BerryRAG - pgvector Database System

Usage: python src/rag_system_pgvector.py <command> [args...]

Commands:
  search <query>              - Search for documents
  context <query>             - Get formatted context for query
  add <url> <title> <file>    - Add document from file
  list                        - List all documents
  stats                       - Show system statistics
  
Examples:
  python src/rag_system_pgvector.py search "React hooks"
  python src/rag_system_pgvector.py context "How to use useState"
  python src/rag_system_pgvector.py add "https://react.dev" "React Docs" content.txt
        """)
        return
    
    rag = BerryRAGSystem()
    command = sys.argv[1]
    
    try:
        if command == "search" and len(sys.argv) >= 3:
            query = " ".join(sys.argv[2:])
            results = rag.search(query)
            
            if not results:
                print(f"❌ No results found for: {query}")
                return
                
            print(f"🔍 Found {len(results)} results for: {query}\n")
            for i, result in enumerate(results, 1):
                print(f"📄 Result {i} (Similarity: {result.similarity:.3f})")
                print(f"📋 Title: {result.document.title}")
                print(f"🔗 URL: {result.document.url}")
                print(f"📝 Content: {result.chunk_text[:200]}...")
                print("─" * 60)
        
        elif command == "context" and len(sys.argv) >= 3:
            query = " ".join(sys.argv[2:])
            context = rag.get_context_for_query(query)
            print(context)
        
        elif command == "add" and len(sys.argv) >= 5:
            url, title, content_file = sys.argv[2], sys.argv[3], sys.argv[4]
            
            if not Path(content_file).exists():
                print(f"❌ File not found: {content_file}")
                return
                
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            doc_id = rag.add_document(url, title, content)
            print(f"✅ Document added with ID: {doc_id}")
        
        elif command == "list":
            docs = rag.list_documents()
            if not docs:
                print("📭 No documents in the database")
                return
                
            print(f"📚 {len(docs)} documents in database:\n")
            for doc in docs:
                print(f"📄 {doc['title']}")
                print(f"   🔗 {doc['url']}")
                print(f"   📊 {doc['chunk_count']} chunks, {doc['content_length']:,} chars")
                print(f"   🕐 {doc['timestamp']}")
                print()
        
        elif command == "stats":
            stats = rag.get_stats()
            print("📊 BerryRAG Statistics:")
            print(f"   📚 Documents: {stats['document_count']}")
            print(f"   🧩 Chunks: {stats['chunk_count']}")
            print(f"   🤖 Embeddings: {stats['embedding_provider']}")
            print(f"   📐 Dimensions: {stats['embedding_dimension']}")
            print(f"   💾 Database: {stats['database_size']}")
            print(f"   🔗 Host: {stats['database_url']}")
        
        else:
            print(f"❌ Unknown command: {command}")
            
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
