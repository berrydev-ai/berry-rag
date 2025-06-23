#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to pgvector
"""

import os
import json
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_data():
    """Migrate data from SQLite to PostgreSQL with pgvector"""
    
    # Paths
    sqlite_db_path = "./storage/documents.db"
    vectors_path = Path("./storage/vectors")
    
    # Database URLs
    postgres_url = os.getenv('DATABASE_URL', 'postgresql://berryrag:berryrag_password@localhost:5432/berryrag')
    
    if not Path(sqlite_db_path).exists():
        logger.info("No SQLite database found. Nothing to migrate.")
        return
    
    logger.info("Starting migration from SQLite to pgvector...")
    
    # Connect to databases
    sqlite_conn = sqlite3.connect(sqlite_db_path)
    sqlite_conn.row_factory = sqlite3.Row
    
    try:
        postgres_conn = psycopg2.connect(postgres_url, cursor_factory=RealDictCursor)
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        logger.info("Make sure PostgreSQL is running and accessible")
        return
    
    try:
        # Get all documents from SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT * FROM documents ORDER BY timestamp")
        documents = sqlite_cursor.fetchall()
        
        logger.info(f"Found {len(documents)} documents to migrate")
        
        # Migrate each document
        with postgres_conn:
            with postgres_conn.cursor() as pg_cursor:
                migrated_count = 0
                
                for doc in documents:
                    try:
                        # Load embedding from file
                        embedding_file = vectors_path / f"{doc['id']}.npy"
                        if embedding_file.exists():
                            embedding = np.load(embedding_file)
                            embedding_list = embedding.tolist()
                        else:
                            logger.warning(f"No embedding found for document {doc['id']}")
                            embedding_list = None
                        
                        # Parse metadata
                        try:
                            metadata = json.loads(doc['metadata']) if doc['metadata'] else {}
                        except:
                            metadata = {}
                        
                        # Convert timestamp
                        timestamp = datetime.fromisoformat(doc['timestamp'])
                        
                        # Insert into PostgreSQL
                        pg_cursor.execute('''
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
                            doc['id'], doc['url'], doc['title'], doc['content'],
                            doc['chunk_id'], timestamp, json.dumps(metadata),
                            doc['content_hash'], embedding_list
                        ))
                        
                        migrated_count += 1
                        
                        if migrated_count % 10 == 0:
                            logger.info(f"Migrated {migrated_count}/{len(documents)} documents...")
                    
                    except Exception as e:
                        logger.error(f"Failed to migrate document {doc['id']}: {e}")
                        continue
                
                postgres_conn.commit()
                logger.info(f"✅ Migration completed! Migrated {migrated_count} documents")
                
                # Verify migration
                pg_cursor.execute("SELECT COUNT(*) FROM documents")
                pg_count = pg_cursor.fetchone()[0]
                logger.info(f"PostgreSQL now contains {pg_count} documents")
    
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        postgres_conn.rollback()
    
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def backup_sqlite_data():
    """Create a backup of SQLite data before migration"""
    sqlite_db_path = "./storage/documents.db"
    backup_path = f"./storage/documents_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    if Path(sqlite_db_path).exists():
        import shutil
        shutil.copy2(sqlite_db_path, backup_path)
        logger.info(f"SQLite database backed up to: {backup_path}")
    else:
        logger.info("No SQLite database found to backup")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "backup":
        backup_sqlite_data()
    else:
        backup_sqlite_data()
        migrate_data()
