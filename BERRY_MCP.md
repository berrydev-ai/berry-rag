# 🍓 BerryRAG MCP Servers Guide

This document provides comprehensive information about the Model Context Protocol (MCP) servers available in the BerryRAG ecosystem, how to run them, configure them with Claude Desktop, and use them effectively.

## 📋 Table of Contents

- [Overview](#overview)
- [Available MCP Servers](#available-mcp-servers)
- [Docker Setup](#docker-setup)
- [Claude Desktop Configuration](#claude-desktop-configuration)
- [Usage Examples](#usage-examples)
- [Port Configuration](#port-configuration)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## 🔍 Overview

BerryRAG provides two powerful MCP servers that extend Claude's capabilities with local vector database operations and advanced web content extraction:

1. **Vector DB Server** - Direct integration with your local vector database
2. **BerryExa Server** - Advanced web crawling and content extraction

Both servers run as Docker services and communicate with Claude Desktop via the Model Context Protocol, providing seamless integration for knowledge management workflows.

## 🛠️ Available MCP Servers

### 1. Vector DB Server (`mcp-server`)

**Purpose**: Direct vector database operations for document storage, search, and retrieval.

**Technologies**: TypeScript, Node.js, PostgreSQL with pgvector

**Key Features**:

- Add documents directly to vector database
- Search for similar content with configurable similarity thresholds
- Get formatted context for AI conversations
- List and manage stored documents
- Process scraped content from Playwright
- Database statistics and health monitoring

**Available Tools**:

- `add_document` - Add content directly to vector DB
- `search_documents` - Search for similar content
- `get_context` - Get formatted context for queries
- `list_documents` - List all stored documents
- `get_stats` - Vector database statistics
- `process_scraped_files` - Process Playwright scraped content
- `save_scraped_content` - Save content for later processing

### 2. BerryExa Server (`berry-exa-server`)

**Purpose**: Advanced web content extraction with Mozilla Readability and AI enhancement.

**Technologies**: Python, Playwright, Mozilla Readability, OpenAI

**Key Features**:

- JavaScript-enabled web crawling with Playwright
- Mozilla Readability integration for clean content extraction
- AI-powered summaries and highlights (with OpenAI)
- Subpage discovery and crawling
- Link extraction and analysis
- Content preview without full processing

**Available Tools**:

- `crawl_content` - Full content extraction with optional subpage crawling
- `extract_links` - Extract internal links for subpage discovery
- `get_content_preview` - Quick content preview without full processing

## 🐳 Docker Setup

### Prerequisites

1. **Docker and Docker Compose** installed
2. **Environment Configuration** - Copy `.env.example` to `.env` and customize
3. **OpenAI API Key** (optional, for enhanced AI features)

### Starting the Services

```bash
# Start all services including MCP servers
docker-compose up -d

# Start specific services
docker-compose up -d postgres mcp-server berry-exa-server

# View logs
docker-compose logs -f mcp-server
docker-compose logs -f berry-exa-server
```

### Service Architecture

```
BerryRAG Docker Services
├── postgres (pgvector database)
├── app (main application)
├── mcp-server (Vector DB MCP Server)
├── berry-exa-server (BerryExa MCP Server)
└── playwright-service (content processing)
```

### Default Ports

| Service       | Default Port | Environment Variable |
| ------------- | ------------ | -------------------- |
| PostgreSQL    | 5432         | `POSTGRES_PORT`      |
| Main App      | 8000         | `APP_PORT`           |
| Vector DB MCP | 3000         | `BERRY_RAG_PORT`     |
| BerryExa MCP  | 3001         | `BERRY_EXA_PORT`     |

## ⚙️ Claude Desktop Configuration

### Configuration File Location

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### Complete Configuration

```json
{
  "mcpServers": {
    "berry-rag-vector": {
      "command": "node",
      "args": ["dist/vector_db_server.js"],
      "cwd": "/path/to/your/berry-rag",
      "env": {
        "DATABASE_URL": "postgresql://berryrag:berryrag_password@localhost:5432/berryrag"
      }
    },
    "berry-exa": {
      "command": "python",
      "args": ["mcp_servers/berry_exa_server.py"],
      "cwd": "/path/to/your/berry-rag",
      "env": {
        "OPENAI_API_KEY": "your_openai_key_here",
        "DATABASE_URL": "postgresql://berryrag:berryrag_password@localhost:5432/berryrag"
      }
    }
  }
}
```

### Docker-based Configuration

If running via Docker, you can also connect to the containerized servers:

```json
{
  "mcpServers": {
    "berry-rag-vector": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "berry-rag-mcp-server-1",
        "node",
        "dist/vector_db_server.js"
      ]
    },
    "berry-exa": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "berry-rag-berry-exa-server-1",
        "python",
        "mcp_servers/berry_exa_server.py"
      ]
    }
  }
}
```

### Restart Claude Desktop

After updating the configuration:

1. Quit Claude Desktop completely
2. Restart Claude Desktop
3. Verify MCP servers are connected (look for tool availability)

## 🚀 Usage Examples

### Vector Database Operations

#### Adding Documents

```
"Add this research paper to the vector database: [paste content]"

"Save this documentation to BerryRAG with title 'React Hooks Guide'"
```

#### Searching Content

```
"Search the vector database for information about React useState"

"Find documents related to machine learning algorithms"

"Get context about Python async programming from the knowledge base"
```

#### Database Management

```
"List all documents in the vector database"

"Show me database statistics and health information"

"Process any new scraped files into the vector database"
```

### Web Content Extraction

#### Basic Content Crawling

```
"Use BerryExa to extract content from https://docs.python.org/3/tutorial/"

"Crawl the React documentation homepage and get a summary"
```

#### Advanced Crawling with Subpages

```
"Crawl https://docs.python.org/3/tutorial/ and also extract 5 related subpages"

"Extract content from the main page and find subpages related to 'hooks' and 'state'"
```

#### Link Discovery

```
"Extract all internal links from https://react.dev for potential crawling"

"Find links on the Python docs homepage that contain 'tutorial' or 'guide'"
```

#### Content Preview

```
"Get a quick preview of https://example.com/article without full processing"
```

### Combined Workflows

#### Research Workflow

```
1. "Use BerryExa to crawl this research paper: [URL]"
2. "Add the extracted content to the vector database"
3. "Search for related concepts in the knowledge base"
```

#### Documentation Aggregation

```
1. "Crawl the main API documentation page and 10 subpages"
2. "Process all extracted content into the vector database"
3. "Search for implementation examples across all documentation"
```

## 🔧 Port Configuration

### Environment Variables

Configure custom ports in your `.env` file:

```bash
# Database
POSTGRES_PORT=5432

# Main application
APP_PORT=8000

# MCP Servers
BERRY_RAG_PORT=3000           # Vector DB MCP Server
BERRY_EXA_PORT=3001           # BerryExa MCP Server
```

### Port Conflicts

If you encounter port conflicts:

1. **Check running services**: `lsof -i :3000`
2. **Update .env file** with available ports
3. **Restart services**: `docker-compose down && docker-compose up -d`
4. **Update Claude config** if using direct connection

### Firewall Configuration

For remote access (not recommended for security):

```bash
# Allow specific ports (example for Ubuntu/Debian)
sudo ufw allow 3000/tcp  # Vector DB MCP
sudo ufw allow 3001/tcp  # BerryExa MCP
```

## 🔍 Troubleshooting

### Common Issues

#### MCP Server Not Connecting

**Symptoms**: Tools not available in Claude, connection errors

**Solutions**:

1. Check Docker services: `docker-compose ps`
2. View logs: `docker-compose logs mcp-server berry-exa-server`
3. Verify Claude Desktop config path and syntax
4. Restart Claude Desktop completely

#### Database Connection Errors

**Symptoms**: "Database connection failed" errors

**Solutions**:

1. Ensure PostgreSQL is running: `docker-compose ps postgres`
2. Check database health: `docker-compose exec postgres pg_isready -U berryrag`
3. Verify DATABASE_URL in environment variables
4. Check network connectivity between containers

#### Content Extraction Failures

**Symptoms**: BerryExa returns empty content or errors

**Solutions**:

1. Check Playwright browser installation: `docker-compose logs berry-exa-server`
2. Verify target website accessibility
3. Check OpenAI API key if using AI features
4. Review content filtering settings

#### Port Binding Errors

**Symptoms**: "Port already in use" errors during startup

**Solutions**:

1. Check for conflicting services: `lsof -i :3000 -i :3001`
2. Update port configuration in `.env`
3. Stop conflicting services or use different ports

### Debug Mode

Enable detailed logging:

```bash
# Set in .env file
LOG_LEVEL=DEBUG

# Restart services
docker-compose down && docker-compose up -d
```

### Health Checks

```bash
# Check all services
docker-compose ps

# Test database connection
docker-compose exec postgres psql -U berryrag -d berryrag -c "SELECT version();"

# Test MCP server responsiveness
docker-compose logs --tail=50 mcp-server
docker-compose logs --tail=50 berry-exa-server
```

## 🛠️ Development

### Local Development Setup

For development without Docker:

```bash
# Install dependencies
npm install
pip install -r requirements.txt

# Build TypeScript MCP server
npm run build

# Start PostgreSQL (via Docker)
docker-compose up -d postgres

# Run MCP servers locally
node dist/vector_db_server.js
python mcp_servers/berry_exa_server.py
```

### Testing MCP Servers

```bash
# Test Vector DB server
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | node dist/vector_db_server.js

# Test BerryExa server
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python mcp_servers/berry_exa_server.py
```

### Custom Configuration

#### Environment Variables

Both servers support extensive configuration via environment variables:

```bash
# Content processing
MIN_CONTENT_LENGTH=100
MAX_CONTENT_LENGTH=500000
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# Search behavior
DEFAULT_TOP_K=5
SIMILARITY_THRESHOLD=0.1
MAX_CONTEXT_CHARS=4000

# AI features
OPENAI_API_KEY=your_key_here
EMBEDDING_PROVIDER=auto  # auto, sentence-transformers, openai, simple
```

#### Database Schema

The system uses PostgreSQL with pgvector extension:

```sql
-- Documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Vectors table
CREATE TABLE vectors (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    chunk_index INTEGER,
    content TEXT,
    embedding vector(384),  -- Dimension depends on embedding model
    metadata JSONB
);
```

### Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-mcp-tool`
3. **Add tests** for new functionality
4. **Update documentation** in this file
5. **Submit pull request**

### Adding New Tools

To add new tools to either MCP server:

1. **Define tool schema** in `get_tools()` method
2. **Implement handler** in `handle_tool_call()` method
3. **Add error handling** and validation
4. **Update documentation** with usage examples
5. **Test with Claude Desktop**

## 📚 Additional Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Guide](https://docs.anthropic.com/claude/docs/mcp)
- [BerryRAG Main Documentation](README.md)
- [BerryExa Documentation](README_BERRY_EXA.md)
- [Docker Setup Guide](README_DOCKER.md)

## 🔐 Security Considerations

- **Local Network Only**: MCP servers should only be accessible locally
- **API Key Security**: Store OpenAI API keys securely, never commit to version control
- **Database Access**: Use strong passwords and limit database access
- **Content Filtering**: Review extracted content before adding to knowledge base
- **Resource Limits**: Monitor memory and CPU usage during large crawling operations

## 📄 License

MIT License - Part of the BerryRAG project.

---

**The BerryRAG MCP servers provide powerful local AI capabilities while maintaining privacy and control over your data. Happy knowledge building!** 🍓🤖✨
