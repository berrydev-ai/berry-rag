#!/usr/bin/env python3
"""
BerryRAG Quick Start Guide
Run this after installation to get started
"""

import os
import json
from pathlib import Path

def main():
    print("🍓 BerryRAG Quick Start Guide")
    print("=" * 50)
    
    print(f"📍 Project Location: {Path.cwd()}")
    print()
    
    print("🚀 To get started:")
    print("1. Install dependencies:")
    print("   npm install")
    print("   pip3 install -r requirements.txt")
    print()
    
    print("2. Build the system:")
    print("   npm run build")
    print()
    
    print("3. Test the installation:")
    print("   npm run test")
    print()
    
    print("4. Configure Claude Desktop:")
    print("   - Run: npm run full-setup")
    print("   - Copy contents of claude_desktop_config.json to your Claude Desktop config")
    print("   - Restart Claude Desktop")
    print()
    
    print("🎭 Using with Playwright MCP:")
    print()
    print("1. Scrape content:")
    print('   "Use Playwright to scrape documentation from https://react.dev"')
    print()
    
    print("2. Process into vector database:")
    print('   "Process scraped files into BerryRAG"')
    print("   or: npm run process-scraped")
    print()
    
    print("3. Search your knowledge base:")
    print('   "Search BerryRAG for React hooks information"')
    print("   or: python src/rag_system.py search 'React hooks'")
    print()
    
    print("📊 Monitor your system:")
    print("   npm run status        # Check system health")
    print("   npm run list-docs     # List all documents")
    print("   npm run search        # Search via CLI")
    print()
    
    print("🔧 Available Commands:")
    commands = [
        ("npm run full-setup", "Complete automated setup"),
        ("npm run status", "Check system status"),
        ("npm run test", "Run system tests"),
        ("npm run build", "Compile TypeScript"),
        ("npm run process-scraped", "Process new scraped files"),
        ("npm run search", "Search the knowledge base"),
        ("npm run list-docs", "List all documents"),
        ("./setup.sh", "Interactive setup script"),
    ]
    
    for cmd, desc in commands:
        print(f"   {cmd:<25} # {desc}")
    
    print()
    print("📚 For detailed documentation, see README.md")
    print("🐛 For troubleshooting, run: npm run status")
    print()
    print("Happy scraping and searching! 🕷️🔍✨")

if __name__ == "__main__":
    main()
