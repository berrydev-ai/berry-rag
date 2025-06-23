#!/usr/bin/env python3
"""
BerryRAG Status Check
Quick system health and configuration check
"""

import os
import json
from pathlib import Path

def check_project_structure():
    """Check if all required files and directories exist"""
    required_files = [
        'package.json',
        'requirements.txt',
        'README.md',
        'src/rag_system.py',
        'src/playwright_integration.py',
        'mcp_servers/vector_db_server.ts',
        'setup.sh',
        'test_system.py'
    ]
    
    required_dirs = [
        'src',
        'mcp_servers',
        'storage',
        'scraped_content'
    ]
    
    print("📁 Project Structure:")
    
    all_good = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path}")
            all_good = False
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"   ✅ {dir_path}/")
        else:
            print(f"   ❌ {dir_path}/")
            all_good = False
    
    return all_good

def check_dependencies():
    """Check if dependencies are available"""
    print("\n📦 Dependencies:")
    
    # Check Node.js files
    if Path('node_modules').exists():
        print("   ✅ Node.js dependencies installed")
    else:
        print("   ❌ Node.js dependencies missing (run: npm install)")
    
    # Check TypeScript compilation
    if Path('dist').exists():
        print("   ✅ TypeScript compiled")
    else:
        print("   ⚠️  TypeScript not compiled (run: npm run build)")
    
    # Check Python dependencies
    try:
        import numpy, sqlite3
        print("   ✅ Core Python dependencies available")
    except ImportError:
        print("   ❌ Core Python dependencies missing")
    
    try:
        from sentence_transformers import SentenceTransformer
        print("   ✅ sentence-transformers available")
    except ImportError:
        print("   ⚠️  sentence-transformers not available (optional)")

def check_configuration():
    """Check configuration files"""
    print("\n⚙️  Configuration:")
    
    if Path('.env').exists():
        print("   ✅ .env file exists")
    else:
        print("   ⚠️  .env file missing (copy from .env.example)")
    
    if Path('claude_desktop_config.json').exists():
        print("   ✅ Claude Desktop config generated")
        try:
            with open('claude_desktop_config.json') as f:
                config = json.load(f)
            if 'berry-rag' in config.get('mcpServers', {}):
                print("   ✅ BerryRAG MCP server configured")
            if 'playwright' in config.get('mcpServers', {}):
                print("   ✅ Playwright MCP server configured")
        except:
            print("   ⚠️  Config file exists but may be invalid")
    else:
        print("   ⚠️  Claude Desktop config not generated (run: ./setup.sh)")

def check_storage():
    """Check storage and data status"""
    print("\n💾 Storage:")
    
    storage_path = Path('storage')
    if storage_path.exists():
        db_path = storage_path / 'documents.db'
        vectors_path = storage_path / 'vectors'
        
        if db_path.exists():
            print(f"   ✅ Database exists ({db_path.stat().st_size} bytes)")
        else:
            print("   📭 No database yet (will be created on first use)")
        
        if vectors_path.exists():
            vector_count = len(list(vectors_path.glob('*.npy')))
            print(f"   📊 {vector_count} vectors stored")
        else:
            print("   📭 No vectors yet")
    
    scraped_path = Path('scraped_content')
    if scraped_path.exists():
        md_files = list(scraped_path.glob('*.md'))
        non_system_files = [f for f in md_files if not f.name.startswith(('PLAYWRIGHT_', 'sample_'))]
        print(f"   📄 {len(non_system_files)} scraped files ready for processing")

def print_next_steps():
    """Print recommended next steps"""
    print("\n🚀 Next Steps:")
    
    if not Path('dist').exists():
        print("   1. Build the system: npm run build")
    
    if not Path('.env').exists():
        print("   2. Create .env file: cp .env.example .env")
    
    print("   3. Test the system: npm run test")
    print("   4. Configure Claude Desktop with the generated config")
    print("   5. Start scraping with Playwright MCP")
    print("   6. Process content: npm run process-scraped")
    print("   7. Search: python src/rag_system.py search 'your query'")

def main():
    print("🍓 BerryRAG System Status\n")
    print(f"📍 Location: {Path.cwd()}")
    
    # Run all checks
    structure_ok = check_project_structure()
    check_dependencies()
    check_configuration()
    check_storage()
    
    print("\n" + "="*50)
    
    if structure_ok:
        print("✅ System structure is complete!")
    else:
        print("❌ System structure has issues")
    
    print_next_steps()
    
    print(f"\n📖 For detailed instructions, see: README.md")
    print(f"🔧 For setup help, run: ./setup.sh")

if __name__ == "__main__":
    main()
