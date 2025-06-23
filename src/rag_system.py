#!/usr/bin/env python3
"""
BerryRAG: Local RAG System with Vector Storage
Optimized for Playwright MCP integration with Claude
"""

import os
import json
import hashlib
import sqlite3
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
    def __init__(self, storage_path: str = "./storage"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Database and vector storage paths
        self.db_path = self.storage_path / "documents.db"
        self.vectors_path = self.storage_path / "vectors"
        self.vectors_path.mkdir(exist_ok=True)
        
        # Initialize embedding provider
        self.embedder = EmbeddingProvider()
        
        # Initialize database
        self._init_database()
        
        logger.info(f"🚀 BerryRAG initialized at {self.storage_path}")
        logger.info(f"📊 Embedding provider: {self.embedder.provider}")
        logger.info(f"📐 Embedding dimension: {self.embedder.embedding_dim}")
    
    def _init_database(self):
        """Initialize SQLite database for metadata"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    chunk_id INTEGER,
                    timestamp TEXT,
                    metadata TEXT,
                    content_hash TEXT
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_url ON documents(url)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON documents(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_content_hash ON documents(content_hash)')
            conn.commit()
    
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
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                'SELECT id FROM documents WHERE url = ? AND content_hash = ? LIMIT 1',
                (url, content_hash)
            ).fetchone()
            
            if existing:
                logger.info(f"📄 Document already exists: {title}")
                return existing[0].split('_')[0]  # Return base doc ID
        
        # Generate document ID
        doc_id = hashlib.md5(f"{url}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        timestamp = datetime.now().isoformat()
        
        # Chunk the content
        chunks = self.chunk_text(content)
        logger.info(f"📝 Processing document: {title} ({len(chunks)} chunks)")
        
        # Store chunks and generate embeddings
        with sqlite3.connect(self.db_path) as conn:
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_{i}"
                
                document = Document(
                    id=chunk_id,
                    url=url,
                    title=title,
                    content=chunk,
                    chunk_id=i,
                    timestamp=timestamp,
                    metadata={
                        **metadata,
                        'total_chunks': len(chunks),
                        'content_hash': content_hash,
                        'original_length': len(content)
                    }
                )
                
                # Store metadata in SQLite
                conn.execute('''
                    INSERT OR REPLACE INTO documents 
                    (id, url, title, content, chunk_id, timestamp, metadata, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    document.id, document.url, document.title, 
                    document.content, document.chunk_id, 
                    document.timestamp, json.dumps(document.metadata),
                    content_hash
                ))
                
                # Generate and store embedding
                try:
                    embedding = self.embedder.encode(chunk)
                    np.save(self.vectors_path / f"{document.id}.npy", embedding)
                except Exception as e:
                    logger.error(f"Failed to generate embedding for chunk {i}: {e}")
                    continue
        
        logger.info(f"✅ Added document: {title} (ID: {doc_id})")
        self._update_query_interface()
        return doc_id
    
    def search(self, query: str, top_k: int = 5, similarity_threshold: float = 0.1) -> List[QueryResult]:
        """Search for similar documents"""
        try:
            query_embedding = self.embedder.encode(query)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return []
        
        results = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT * FROM documents ORDER BY timestamp DESC')
            
            for row in cursor:
                doc_id, url, title, content, chunk_id, timestamp, metadata_str, content_hash = row
                
                # Load embedding
                embedding_path = self.vectors_path / f"{doc_id}.npy"
                if not embedding_path.exists():
                    continue
                
                try:
                    embedding = np.load(embedding_path)
                    
                    # Compute cosine similarity
                    dot_product = np.dot(query_embedding, embedding)
                    norms = np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
                    
                    if norms == 0:
                        similarity = 0.0
                    else:
                        similarity = dot_product / norms
                    
                    if similarity >= similarity_threshold:
                        document = Document(
                            id=doc_id, url=url, title=title, content=content,
                            chunk_id=chunk_id, timestamp=timestamp,
                            metadata=json.loads(metadata_str)
                        )
                        
                        results.append(QueryResult(
                            document=document,
                            similarity=float(similarity),
                            chunk_text=content
                        ))
                
                except Exception as e:
                    logger.error(f"Error processing embedding for {doc_id}: {e}")
                    continue
        
        # Sort by similarity and return top_k
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]
    
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT url, title, MAX(timestamp) as latest_timestamp, 
                       COUNT(*) as chunk_count, MAX(metadata) as metadata
                FROM documents 
                GROUP BY url, title
                ORDER BY latest_timestamp DESC
            ''')
            
            documents = []
            for row in cursor:
                url, title, timestamp, chunk_count, metadata_str = row
                try:
                    metadata = json.loads(metadata_str) if metadata_str else {}
                except:
                    metadata = {}
                
                documents.append({
                    "url": url,
                    "title": title,
                    "timestamp": timestamp,
                    "chunk_count": chunk_count,
                    "content_length": metadata.get('original_length', 0),
                    "source": metadata.get('source', 'unknown')
                })
            
            return documents
    
    def get_stats(self) -> Dict:
        """Get system statistics"""
        with sqlite3.connect(self.db_path) as conn:
            doc_count = conn.execute('SELECT COUNT(DISTINCT url) FROM documents').fetchone()[0]
            chunk_count = conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
            
            # Get storage size
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            vector_files = list(self.vectors_path.glob("*.npy"))
            vector_size = sum(f.stat().st_size for f in vector_files)
            
            return {
                "document_count": doc_count,
                "chunk_count": chunk_count,
                "embedding_provider": self.embedder.provider,
                "embedding_dimension": self.embedder.embedding_dim,
                "database_size_mb": round(db_size / 1024 / 1024, 2),
                "vector_storage_mb": round(vector_size / 1024 / 1024, 2),
                "total_storage_mb": round((db_size + vector_size) / 1024 / 1024, 2),
                "storage_path": str(self.storage_path.absolute())
            }
    
    def _update_query_interface(self):
        """Update the query interface file for external access"""
        interface_path = self.storage_path / "query_interface.json"
        
        interface = {
            "system": "BerryRAG Local Vector Database",
            "last_updated": datetime.now().isoformat(),
            "stats": self.get_stats(),
            "usage": {
                "search": "python src/rag_system.py search 'your query'",
                "context": "python src/rag_system.py context 'your query'",
                "list": "python src/rag_system.py list",
                "add": "python src/rag_system.py add <url> <title> <content_file>"
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
🍓 BerryRAG - Local Vector Database System

Usage: python src/rag_system.py <command> [args...]

Commands:
  search <query>              - Search for documents
  context <query>             - Get formatted context for query
  add <url> <title> <file>    - Add document from file
  list                        - List all documents
  stats                       - Show system statistics
  
Examples:
  python src/rag_system.py search "React hooks"
  python src/rag_system.py context "How to use useState"
  python src/rag_system.py add "https://react.dev" "React Docs" content.txt
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
            print(f"   💾 Storage: {stats['total_storage_mb']} MB")
            print(f"   📁 Path: {stats['storage_path']}")
        
        else:
            print(f"❌ Unknown command: {command}")
            
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
