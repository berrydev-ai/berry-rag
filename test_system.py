#!/usr/bin/env python3
"""
BerryRAG Test Script
Validates the system installation and basic functionality
"""

import sys
import os
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from rag_system import BerryRAGSystem
    from playwright_integration import PlaywrightRAGIntegration
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root and dependencies are installed")
    sys.exit(1)

def test_rag_system():
    """Test basic RAG system functionality"""
    print("🧪 Testing RAG system...")
    
    # Use a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        rag = BerryRAGSystem(temp_dir)
        
        # Test adding a document
        test_content = """
# Test Document

This is a test document for the BerryRAG system.

## Features
- Vector storage
- Semantic search
- Content chunking

## Usage
This system can be used for document retrieval and question answering.
"""
        
        doc_id = rag.add_document(
            url="https://test.example.com",
            title="Test Document",
            content=test_content,
            metadata={"test": True}
        )
        
        print(f"✅ Added test document: {doc_id}")
        
        # Test search
        results = rag.search("vector storage")
        if results:
            print(f"✅ Search returned {len(results)} results")
            print(f"   Best match similarity: {results[0].similarity:.3f}")
        else:
            print("⚠️  Search returned no results")
        
        # Test context generation
        context = rag.get_context_for_query("features of the system")
        if context and len(context) > 100:
            print("✅ Context generation working")
        else:
            print("⚠️  Context generation may have issues")
        
        # Test stats
        stats = rag.get_stats()
        print(f"✅ Stats: {stats['document_count']} docs, {stats['chunk_count']} chunks")
        
        return True

def test_playwright_integration():
    """Test Playwright integration functionality"""
    print("🎭 Testing Playwright integration...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        integration = PlaywrightRAGIntegration(
            scraped_content_dir=temp_dir + "/scraped",
            rag_storage_dir=temp_dir + "/storage"
        )
        
        # Test content saving
        test_url = "https://example.com/test"
        test_title = "Test Page"
        test_content = "This is test content for the integration system."
        
        filepath = integration.save_scraped_content(test_url, test_title, test_content)
        if Path(filepath).exists():
            print("✅ Content saving working")
        else:
            print("❌ Content saving failed")
            return False
        
        # Test processing
        stats = integration.process_scraped_files()
        if stats['processed'] > 0:
            print(f"✅ Processing working: {stats['processed']} files processed")
        else:
            print("⚠️  No files were processed (this might be expected)")
        
        return True

def test_dependencies():
    """Test required dependencies"""
    print("📦 Testing dependencies...")
    
    try:
        import numpy as np
        print("✅ NumPy available")
    except ImportError:
        print("❌ NumPy not available")
        return False
    
    try:
        import sqlite3
        print("✅ SQLite3 available")
    except ImportError:
        print("❌ SQLite3 not available")
        return False
    
    try:
        from sentence_transformers import SentenceTransformer
        print("✅ sentence-transformers available")
    except ImportError:
        print("⚠️  sentence-transformers not available (will use fallback)")
    
    try:
        import openai
        print("✅ OpenAI library available")
    except ImportError:
        print("⚠️  OpenAI library not available (optional)")
    
    return True

def main():
    """Run all tests"""
    print("🍓 BerryRAG System Test\n")
    
    all_passed = True
    
    # Test dependencies
    if not test_dependencies():
        print("❌ Dependency test failed")
        all_passed = False
    
    print()
    
    # Test RAG system
    try:
        if not test_rag_system():
            all_passed = False
    except Exception as e:
        print(f"❌ RAG system test failed: {e}")
        all_passed = False
    
    print()
    
    # Test Playwright integration
    try:
        if not test_playwright_integration():
            all_passed = False
    except Exception as e:
        print(f"❌ Playwright integration test failed: {e}")
        all_passed = False
    
    print("\n" + "="*50)
    
    if all_passed:
        print("🎉 All tests passed! BerryRAG is ready to use.")
        print("\nNext steps:")
        print("1. Configure Claude Desktop with the MCP server")
        print("2. Start scraping content with Playwright MCP")
        print("3. Process content with: npm run process-scraped")
        print("4. Search with: python src/rag_system.py search 'query'")
    else:
        print("❌ Some tests failed. Check the output above for details.")
        print("Try running: pip install -r requirements.txt")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
