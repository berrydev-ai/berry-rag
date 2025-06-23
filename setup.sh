#!/bin/bash

# BerryRAG Setup Script
# Sets up the complete RAG system with dependencies

set -e

echo "🍓 Setting up BerryRAG..."

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Please run this script from the berry-rag project root"
    exit 1
fi

# Check dependencies
echo "🔍 Checking dependencies..."

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required. Please install Node.js first."
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Please install Python 3 first."
    exit 1
fi

# Check npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm is required. Please install npm first."
    exit 1
fi

# Check pip
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo "❌ pip is required. Please install pip first."
    exit 1
fi

echo "✅ Dependencies check passed"

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
npm install

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt
else
    pip install -r requirements.txt
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📋 Creating .env file..."
    cp .env.example .env
    echo "✅ Created .env file (customize as needed)"
fi

# Build TypeScript
echo "🔨 Building TypeScript MCP server..."
npm run build

# Setup directories and instructions
echo "📁 Setting up directories..."
python3 src/playwright_integration.py setup

# Create Claude Desktop config suggestion
echo "🤖 Creating Claude Desktop configuration..."
cat > claude_desktop_config.json << EOF
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    },
    "berry-rag": {
      "command": "node",
      "args": ["mcp_servers/vector_db_server.js"],
      "cwd": "$(pwd)"
    }
  }
}
EOF

echo "📋 Created claude_desktop_config.json"

# Test the system
echo "🧪 Testing the system..."
python3 src/rag_system.py stats

echo ""
echo "🎉 BerryRAG setup complete!"
echo ""
echo "Next steps:"
echo "1. Add the contents of claude_desktop_config.json to your Claude Desktop config"
echo "2. Restart Claude Desktop"
echo "3. Start scraping with Playwright MCP:"
echo "   'Use Playwright to scrape documentation and save to scraped_content'"
echo "4. Process scraped content:"
echo "   'Process scraped files into the BerryRAG vector database'"
echo "5. Search your knowledge base:"
echo "   'Search BerryRAG for information about [topic]'"
echo ""
echo "📚 See README.md for detailed usage instructions"
echo "📁 Project location: $(pwd)"
