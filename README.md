# 🍓 BerryRAG: Local Vector Database with Playwright MCP Integration

A complete local RAG (Retrieval-Augmented Generation) system that integrates Playwright MCP web scraping with vector database storage for Claude.

## ✨ Features

- **Zero-cost self-hosted** vector database
- **Playwright MCP integration** for automated web scraping
- **Multiple embedding providers** (sentence-transformers, OpenAI, fallback)
- **Smart content processing** with quality filters
- **Claude-optimized** context formatting
- **MCP server** for direct Claude integration
- **Command-line tools** for manual operation

## 🚀 Quick Start

### 1. Installation
```bash
cd /Users/eberry/BerryDev/berry-rag

# Install dependencies
npm run install-deps

# Setup directories and instructions
npm run setup
```

### 2. Configure Claude Desktop
Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    },
    "berry-rag": {
      "command": "node",
      "args": ["mcp_servers/vector_db_server.js"],
      "cwd": "/Users/eberry/BerryDev/berry-rag"
    }
  }
}
```

### 3. Start Using
```bash
# Example workflow:
# 1. Scrape with Playwright MCP through Claude
# 2. Process into vector DB
npm run process-scraped

# 3. Search your knowledge base
npm run search "React hooks"
```

## 📁 Project Structure

```
berry-rag/
├── src/                          # Python source code
│   ├── rag_system.py            # Core vector database system
│   └── playwright_integration.py # Playwright MCP integration
├── mcp_servers/                  # MCP server implementations
│   └── vector_db_server.ts      # TypeScript MCP server
├── storage/                      # Vector database storage
│   ├── documents.db             # SQLite metadata
│   └── vectors/                 # NumPy embedding files
├── scraped_content/             # Playwright saves content here
└── dist/                        # Compiled TypeScript
```

## 🔧 Commands

### NPM Scripts
| Command | Description |
|---------|-------------|
| `npm run install-deps` | Install all dependencies |
| `npm run setup` | Initialize directories and instructions |
| `npm run build` | Compile TypeScript MCP server |
| `npm run process-scraped` | Process scraped files into vector DB |
| `npm run search` | Search the knowledge base |
| `npm run list-docs` | List all documents |

### Python CLI
```bash
# RAG System Operations
python src/rag_system.py search "query"
python src/rag_system.py context "query"  # Claude-formatted
python src/rag_system.py add <url> <title> <file>
python src/rag_system.py list
python src/rag_system.py stats

# Playwright Integration
python src/playwright_integration.py process
python src/playwright_integration.py setup
python src/playwright_integration.py stats
```

## 🤖 Usage with Claude

### 1. Scraping Documentation
```
"Use Playwright to scrape the React hooks documentation from https://react.dev/reference/react and save it to the scraped_content directory"
```

### 2. Processing into Vector Database
```
"Process all new scraped files and add them to the BerryRAG vector database"
```

### 3. Querying Knowledge Base
```
"Search the BerryRAG database for information about React useState best practices"

"Get context from the vector database about implementing custom hooks"
```

## 🔌 MCP Tools Available to Claude

- `add_document` - Add content directly to vector DB
- `search_documents` - Search for similar content
- `get_context` - Get formatted context for queries
- `list_documents` - List all stored documents
- `get_stats` - Vector database statistics
- `process_scraped_files` - Process Playwright scraped content
- `save_scraped_content` - Save content for later processing

## 🧠 Embedding Providers

The system supports multiple embedding providers with automatic fallback:

1. **sentence-transformers** (recommended, free, local)
2. **OpenAI embeddings** (requires API key, set `OPENAI_API_KEY`)
3. **Simple hash-based** (fallback, not recommended for production)

## ⚙️ Configuration

### Environment Variables
```bash
# Optional: for OpenAI embeddings
export OPENAI_API_KEY=your_key_here
```

### Content Quality Filters
The system automatically filters out:
- Content shorter than 100 characters
- Navigation-only content
- Repetitive/duplicate content
- Files larger than 500KB

### Chunking Strategy
- Default chunk size: 500 characters
- Overlap: 50 characters
- Smart boundary detection (sentences, paragraphs)

## 📊 Monitoring

### Check System Status
```bash
# Vector database statistics
python src/rag_system.py stats

# Processing status
python src/playwright_integration.py stats

# View recent documents
python src/rag_system.py list
```

### Storage Information
- **Database**: `storage/documents.db` (SQLite metadata)
- **Vectors**: `storage/vectors/` (NumPy arrays)
- **Scraped Content**: `scraped_content/` (Markdown files)

## 🔍 Example Workflows

### Academic Research
1. Scrape research papers with Playwright
2. Process into vector database
3. Query for specific concepts across all papers

### Documentation Management
1. Scrape API documentation from multiple sources
2. Build unified searchable knowledge base
3. Get contextual answers about implementation details

### Content Aggregation
1. Scrape blog posts and articles
2. Create topic-based knowledge clusters
3. Find related content across sources

## 🛠️ Development

### Building the MCP Server
```bash
npm run build
```

### Running in Development Mode
```bash
npm run dev  # TypeScript watch mode
```

### Testing
```bash
# Test RAG system
python src/rag_system.py stats

# Test integration
python src/playwright_integration.py setup

# Test MCP server
node mcp_servers/vector_db_server.js
```

## 🚨 Troubleshooting

### Common Issues

**Python dependencies missing:**
```bash
pip install -r requirements.txt
```

**TypeScript compilation errors:**
```bash
npm install
npm run build
```

**Embedding model download slow:**
The first run downloads sentence-transformers model (~90MB). This is normal.

**No results from search:**
- Check if documents were processed: `python src/rag_system.py list`
- Verify content quality filters aren't too strict
- Try broader search terms

### Logs and Debugging
- Python logs: Check console output
- MCP server logs: Stderr output
- Processing status: `scraped_content/.processed_files.json`

## 📝 License

MIT License - feel free to modify and extend for your needs.

## 🤝 Contributing

This is a personal project for Eric Berry, but feel free to fork and adapt for your own use cases.

---

**Happy scraping and searching!** 🕷️🔍✨
