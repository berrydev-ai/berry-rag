#!/usr/bin/env python3
"""
BerryRAG Streamlit Interface
Web interface for the local RAG system
"""

import streamlit as st
import sys
import os
from pathlib import Path
import json
import tempfile
from datetime import datetime
import pandas as pd

# Add src directory to path to import rag_system
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from rag_system import BerryRAGSystem
except ImportError as e:
    st.error(f"Failed to import RAG system: {e}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="🍓 BerryRAG - Local Vector Database",
    page_icon="🍓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'rag_system' not in st.session_state:
    try:
        st.session_state.rag_system = BerryRAGSystem()
    except Exception as e:
        st.error(f"Failed to initialize RAG system: {e}")
        st.stop()

def main():
    st.title("🍓 BerryRAG - Local Vector Database")
    st.markdown("*Local RAG System with Vector Storage*")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a function:",
        ["🔍 Search", "📄 Context", "➕ Add Document", "📚 List Documents", "📊 Statistics"]
    )
    
    # Display system stats in sidebar
    with st.sidebar:
        st.markdown("---")
        st.subheader("System Status")
        try:
            stats = st.session_state.rag_system.get_stats()
            st.metric("Documents", stats['document_count'])
            st.metric("Chunks", stats['chunk_count'])
            st.metric("Storage (MB)", stats['total_storage_mb'])
            st.caption(f"Provider: {stats['embedding_provider']}")
            st.caption(f"Dimensions: {stats['embedding_dimension']}")
        except Exception as e:
            st.error(f"Failed to load stats: {e}")
    
    # Main content based on selected page
    if page == "🔍 Search":
        search_page()
    elif page == "📄 Context":
        context_page()
    elif page == "➕ Add Document":
        add_document_page()
    elif page == "📚 List Documents":
        list_documents_page()
    elif page == "📊 Statistics":
        statistics_page()

def search_page():
    st.header("🔍 Search Documents")
    st.markdown("Search through your document collection using semantic similarity.")
    
    # Search form
    with st.form("search_form"):
        query = st.text_input(
            "Enter your search query:",
            placeholder="e.g., 'React hooks', 'machine learning', 'API documentation'"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            top_k = st.slider("Number of results", min_value=1, max_value=20, value=5)
        with col2:
            similarity_threshold = st.slider(
                "Similarity threshold", 
                min_value=0.0, 
                max_value=1.0, 
                value=0.1, 
                step=0.05
            )
        
        submitted = st.form_submit_button("🔍 Search")
    
    if submitted and query:
        with st.spinner("Searching documents..."):
            try:
                results = st.session_state.rag_system.search(
                    query, top_k=top_k, similarity_threshold=similarity_threshold
                )
                
                if not results:
                    st.warning(f"No results found for: '{query}'")
                    st.info("Try adjusting the similarity threshold or using different search terms.")
                else:
                    st.success(f"Found {len(results)} results for: '{query}'")
                    
                    for i, result in enumerate(results, 1):
                        with st.expander(
                            f"📄 Result {i}: {result.document.title} (Similarity: {result.similarity:.3f})",
                            expanded=(i <= 3)  # Expand first 3 results
                        ):
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.markdown(f"**URL:** {result.document.url}")
                                st.markdown(f"**Chunk:** {result.document.chunk_id + 1}")
                                st.markdown(f"**Timestamp:** {result.document.timestamp}")
                            
                            with col2:
                                st.metric("Similarity", f"{result.similarity:.3f}")
                            
                            st.markdown("**Content:**")
                            st.text_area(
                                "Content",
                                value=result.chunk_text,
                                height=150,
                                key=f"content_{i}",
                                label_visibility="collapsed"
                            )
                            
                            # Show metadata if available
                            if result.document.metadata:
                                with st.expander("📋 Metadata"):
                                    st.json(result.document.metadata)
                            
            except Exception as e:
                st.error(f"Search failed: {e}")

def context_page():
    st.header("📄 Context Generation")
    st.markdown("Generate formatted context for queries, optimized for AI assistants.")
    
    with st.form("context_form"):
        query = st.text_input(
            "Enter your query:",
            placeholder="e.g., 'How to implement authentication in React'"
        )
        
        max_chars = st.slider(
            "Maximum characters in context",
            min_value=1000,
            max_value=10000,
            value=4000,
            step=500
        )
        
        submitted = st.form_submit_button("📄 Generate Context")
    
    if submitted and query:
        with st.spinner("Generating context..."):
            try:
                context = st.session_state.rag_system.get_context_for_query(
                    query, max_chars=max_chars
                )
                
                st.success("Context generated successfully!")
                
                # Display context in a text area for easy copying
                st.text_area(
                    "Generated Context:",
                    value=context,
                    height=400,
                    help="Copy this context to use with AI assistants"
                )
                
                # Show context stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Characters", len(context))
                with col2:
                    st.metric("Words", len(context.split()))
                with col3:
                    st.metric("Lines", len(context.split('\n')))
                
            except Exception as e:
                st.error(f"Context generation failed: {e}")

def add_document_page():
    st.header("➕ Add Document")
    st.markdown("Add new documents to your vector database.")
    
    # Input method selection
    input_method = st.radio(
        "Choose input method:",
        ["📝 Text Input", "📁 File Upload", "🔗 URL (Manual)"]
    )
    
    with st.form("add_document_form"):
        if input_method == "📝 Text Input":
            url = st.text_input("Document URL:", placeholder="https://example.com/doc")
            title = st.text_input("Document Title:", placeholder="My Document")
            content = st.text_area(
                "Document Content:",
                height=300,
                placeholder="Paste your document content here..."
            )
            
        elif input_method == "📁 File Upload":
            url = st.text_input("Document URL:", placeholder="https://example.com/doc")
            title = st.text_input("Document Title:", placeholder="My Document")
            uploaded_file = st.file_uploader(
                "Choose a text file",
                type=['txt', 'md', 'py', 'js', 'html', 'css', 'json', 'xml']
            )
            content = ""
            if uploaded_file is not None:
                try:
                    content = uploaded_file.read().decode('utf-8')
                    st.success(f"File loaded: {len(content)} characters")
                except Exception as e:
                    st.error(f"Failed to read file: {e}")
                    
        else:  # URL Manual
            url = st.text_input("Document URL:", placeholder="https://example.com/doc")
            title = st.text_input("Document Title:", placeholder="My Document")
            content = st.text_area(
                "Document Content:",
                height=300,
                placeholder="Manually paste content from the URL..."
            )
        
        # Metadata
        with st.expander("📋 Optional Metadata"):
            source = st.text_input("Source:", placeholder="e.g., documentation, blog, tutorial")
            author = st.text_input("Author:", placeholder="e.g., John Doe")
            tags = st.text_input("Tags:", placeholder="e.g., react, javascript, tutorial (comma-separated)")
            
        submitted = st.form_submit_button("➕ Add Document")
    
    if submitted:
        if not all([url, title, content]):
            st.error("Please fill in URL, Title, and Content fields.")
        else:
            # Prepare metadata
            metadata = {}
            if source:
                metadata['source'] = source
            if author:
                metadata['author'] = author
            if tags:
                metadata['tags'] = [tag.strip() for tag in tags.split(',') if tag.strip()]
            
            with st.spinner("Adding document to database..."):
                try:
                    doc_id = st.session_state.rag_system.add_document(
                        url=url,
                        title=title,
                        content=content,
                        metadata=metadata
                    )
                    
                    st.success(f"✅ Document added successfully!")
                    st.info(f"Document ID: {doc_id}")
                    
                    # Show document stats
                    chunks = st.session_state.rag_system.chunk_text(content)
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Characters", len(content))
                    with col2:
                        st.metric("Words", len(content.split()))
                    with col3:
                        st.metric("Chunks", len(chunks))
                        
                except Exception as e:
                    st.error(f"Failed to add document: {e}")

def list_documents_page():
    st.header("📚 Document Library")
    st.markdown("Browse and manage your document collection.")
    
    try:
        documents = st.session_state.rag_system.list_documents()
        
        if not documents:
            st.info("📭 No documents in the database yet.")
            st.markdown("Use the **Add Document** page to add your first document!")
            return
        
        st.success(f"📚 Found {len(documents)} documents in your library")
        
        # Create DataFrame for better display
        df_data = []
        for doc in documents:
            df_data.append({
                "Title": doc['title'],
                "URL": doc['url'],
                "Chunks": doc['chunk_count'],
                "Size (chars)": f"{doc['content_length']:,}",
                "Added": doc['timestamp'][:19].replace('T', ' '),  # Format timestamp
                "Source": doc.get('source', 'Unknown')
            })
        
        df = pd.DataFrame(df_data)
        
        # Display as interactive table
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "URL": st.column_config.LinkColumn("URL"),
                "Chunks": st.column_config.NumberColumn("Chunks", format="%d"),
                "Size (chars)": st.column_config.TextColumn("Size (chars)"),
            }
        )
        
        # Detailed view
        st.subheader("📋 Detailed View")
        for i, doc in enumerate(documents):
            with st.expander(f"📄 {doc['title']}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**URL:** {doc['url']}")
                    st.markdown(f"**Chunks:** {doc['chunk_count']}")
                    st.markdown(f"**Size:** {doc['content_length']:,} characters")
                
                with col2:
                    st.markdown(f"**Added:** {doc['timestamp']}")
                    st.markdown(f"**Source:** {doc.get('source', 'Unknown')}")
                
                # Quick search button
                if st.button(f"🔍 Search similar to '{doc['title']}'", key=f"search_{i}"):
                    st.session_state.quick_search_query = doc['title']
                    st.rerun()
        
        # Handle quick search
        if hasattr(st.session_state, 'quick_search_query'):
            query = st.session_state.quick_search_query
            del st.session_state.quick_search_query
            
            st.markdown("---")
            st.subheader(f"🔍 Quick Search Results for: '{query}'")
            
            with st.spinner("Searching..."):
                results = st.session_state.rag_system.search(query, top_k=3)
                
                for i, result in enumerate(results, 1):
                    with st.expander(f"Result {i}: {result.document.title} (Similarity: {result.similarity:.3f})"):
                        st.markdown(f"**URL:** {result.document.url}")
                        st.text_area(
                            "Content",
                            value=result.chunk_text[:500] + "..." if len(result.chunk_text) > 500 else result.chunk_text,
                            height=100,
                            key=f"quick_search_{i}",
                            label_visibility="collapsed"
                        )
        
    except Exception as e:
        st.error(f"Failed to load documents: {e}")

def statistics_page():
    st.header("📊 System Statistics")
    st.markdown("Overview of your RAG system performance and storage.")
    
    try:
        stats = st.session_state.rag_system.get_stats()
        
        # Main metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📚 Documents",
                stats['document_count'],
                help="Total number of unique documents"
            )
        
        with col2:
            st.metric(
                "🧩 Chunks",
                stats['chunk_count'],
                help="Total number of text chunks"
            )
        
        with col3:
            st.metric(
                "💾 Storage",
                f"{stats['total_storage_mb']} MB",
                help="Total storage used"
            )
        
        with col4:
            avg_chunks = stats['chunk_count'] / max(stats['document_count'], 1)
            st.metric(
                "📊 Avg Chunks/Doc",
                f"{avg_chunks:.1f}",
                help="Average chunks per document"
            )
        
        # Detailed breakdown
        st.subheader("🔧 System Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Embedding Provider:**")
            st.code(stats['embedding_provider'])
            
            st.markdown("**Embedding Dimensions:**")
            st.code(stats['embedding_dimension'])
            
            st.markdown("**Storage Path:**")
            st.code(stats['storage_path'])
        
        with col2:
            st.markdown("**Storage Breakdown:**")
            storage_data = {
                "Component": ["Database", "Vectors", "Total"],
                "Size (MB)": [
                    stats['database_size_mb'],
                    stats['vector_storage_mb'],
                    stats['total_storage_mb']
                ]
            }
            st.dataframe(pd.DataFrame(storage_data), hide_index=True)
        
        # Performance recommendations
        st.subheader("💡 Recommendations")
        
        if stats['document_count'] == 0:
            st.info("🚀 **Get Started:** Add your first document using the 'Add Document' page!")
        
        elif stats['document_count'] < 10:
            st.info("📈 **Growing Collection:** Consider adding more documents to improve search quality.")
        
        elif stats['embedding_provider'] == 'simple':
            st.warning("⚠️ **Upgrade Embeddings:** You're using simple hash-based embeddings. Install sentence-transformers or configure OpenAI for better results.")
        
        else:
            st.success("✅ **System Healthy:** Your RAG system is properly configured!")
        
        # System health check
        st.subheader("🏥 System Health")
        
        health_checks = []
        
        # Check embedding provider
        if stats['embedding_provider'] in ['sentence-transformers', 'openai']:
            health_checks.append(("✅", "Embedding Provider", "Advanced embeddings available"))
        else:
            health_checks.append(("⚠️", "Embedding Provider", "Using fallback embeddings"))
        
        # Check document count
        if stats['document_count'] > 0:
            health_checks.append(("✅", "Document Collection", f"{stats['document_count']} documents indexed"))
        else:
            health_checks.append(("❌", "Document Collection", "No documents added yet"))
        
        # Check storage
        if stats['total_storage_mb'] < 100:
            health_checks.append(("✅", "Storage Usage", "Storage usage is reasonable"))
        else:
            health_checks.append(("⚠️", "Storage Usage", "Consider cleaning up old documents"))
        
        for status, component, message in health_checks:
            st.markdown(f"{status} **{component}:** {message}")
        
    except Exception as e:
        st.error(f"Failed to load statistics: {e}")

if __name__ == "__main__":
    main()
