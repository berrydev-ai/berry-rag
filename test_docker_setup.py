#!/usr/bin/env python3
"""
Test script to verify Docker setup with pgvector
"""

import os
import sys
import time
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test PostgreSQL connection"""
    database_url = os.getenv('DATABASE_URL', 'postgresql://berryrag:berryrag_password@postgres:5432/berryrag')
    
    max_retries = 30
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to database (attempt {attempt + 1}/{max_retries})")
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            
            with conn.cursor() as cur:
                # Test basic connection
                cur.execute("SELECT version()")
                version = cur.fetchone()
                logger.info(f"✅ Connected to PostgreSQL: {version['version']}")
                
                # Test pgvector extension
                cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector'")
                vector_ext = cur.fetchone()
                if vector_ext:
                    logger.info("✅ pgvector extension is installed")
                else:
                    logger.error("❌ pgvector extension not found")
                    return False
                
                # Test tables exist
                cur.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'documents'
                """)
                tables = cur.fetchall()
                if tables:
                    logger.info("✅ Documents table exists")
                else:
                    logger.error("❌ Documents table not found")
                    return False
                
                # Test system_config table
                cur.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'system_config'
                """)
                config_tables = cur.fetchall()
                if config_tables:
                    logger.info("✅ System config table exists")
                else:
                    logger.error("❌ System config table not found")
                    return False
                
                # Test search function
                cur.execute("""
                    SELECT routine_name FROM information_schema.routines 
                    WHERE routine_schema = 'public' AND routine_name = 'search_similar_documents'
                """)
                functions = cur.fetchall()
                if functions:
                    logger.info("✅ Search function exists")
                else:
                    logger.error("❌ Search function not found")
                    return False
            
            conn.close()
            return True
            
        except psycopg2.OperationalError as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("❌ Failed to connect to database after all retries")
                return False
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return False

def test_rag_system():
    """Test RAG system functionality"""
    try:
        from src.rag_system_pgvector import BerryRAGSystem
        
        logger.info("Testing RAG system initialization...")
        rag = BerryRAGSystem()
        
        # Test stats
        stats = rag.get_stats()
        logger.info(f"✅ RAG system initialized successfully")
        logger.info(f"   📊 Embedding provider: {stats['embedding_provider']}")
        logger.info(f"   📐 Embedding dimension: {stats['embedding_dimension']}")
        logger.info(f"   📚 Document count: {stats['document_count']}")
        logger.info(f"   🧩 Chunk count: {stats['chunk_count']}")
        
        # Test adding a simple document
        logger.info("Testing document addition...")
        doc_id = rag.add_document(
            url="https://test.example.com",
            title="Test Document",
            content="This is a test document for verifying the Docker setup with pgvector. It contains some sample text to test the embedding and search functionality."
        )
        logger.info(f"✅ Document added successfully with ID: {doc_id}")
        
        # Test search
        logger.info("Testing search functionality...")
        results = rag.search("test document", top_k=1)
        if results:
            logger.info(f"✅ Search successful, found {len(results)} results")
            logger.info(f"   📄 Top result: {results[0].document.title}")
            logger.info(f"   📊 Similarity: {results[0].similarity:.3f}")
        else:
            logger.warning("⚠️  Search returned no results")
        
        # Test context generation
        logger.info("Testing context generation...")
        context = rag.get_context_for_query("test document")
        if context and len(context) > 50:
            logger.info("✅ Context generation successful")
            logger.info(f"   📝 Context length: {len(context)} characters")
        else:
            logger.warning("⚠️  Context generation returned minimal content")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ RAG system test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting Docker setup tests...")
    
    # Test database connection
    if not test_database_connection():
        logger.error("❌ Database tests failed")
        sys.exit(1)
    
    # Test RAG system
    if not test_rag_system():
        logger.error("❌ RAG system tests failed")
        sys.exit(1)
    
    logger.info("🎉 All tests passed! Docker setup is working correctly.")

if __name__ == "__main__":
    main()
