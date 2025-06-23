#!/usr/bin/env python3
"""
Playwright MCP Integration for BerryRAG
Processes scraped content and integrates with the vector database
"""

import os
import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
from urllib.parse import urlparse

# Import our RAG system
from rag_system import BerryRAGSystem

logger = logging.getLogger(__name__)

class PlaywrightRAGIntegration:
    def __init__(self, 
                 scraped_content_dir: str = "./scraped_content",
                 rag_storage_dir: str = "./storage"):
        
        self.scraped_dir = Path(scraped_content_dir)
        self.scraped_dir.mkdir(exist_ok=True)
        
        # Initialize RAG system
        self.rag = BerryRAGSystem(rag_storage_dir)
        
        # Track processed files
        self.processed_files = self._load_processed_files()
        
        # Content quality filters
        self.min_content_length = 100
        self.max_content_length = 500000  # 500KB max
        
        logger.info(f"🤖 Playwright integration initialized")
        logger.info(f"📁 Scraped content: {self.scraped_dir.absolute()}")
    
    def _load_processed_files(self) -> set:
        """Load list of already processed files"""
        processed_file = self.scraped_dir / ".processed_files.json"
        if processed_file.exists():
            try:
                with open(processed_file, 'r') as f:
                    return set(json.load(f))
            except Exception as e:
                logger.warning(f"Could not load processed files list: {e}")
        return set()
    
    def _save_processed_files(self):
        """Save list of processed files"""
        processed_file = self.scraped_dir / ".processed_files.json"
        try:
            with open(processed_file, 'w') as f:
                json.dump(list(self.processed_files), f, indent=2)
        except Exception as e:
            logger.error(f"Could not save processed files list: {e}")
    
    def extract_metadata_from_content(self, content: str, filename: str) -> Dict:
        """Extract metadata from scraped content"""
        metadata = {
            "source": "playwright_mcp",
            "filename": filename,
            "scraped_at": datetime.now().isoformat()
        }
        
        lines = content.split('\n')[:10]  # Check first 10 lines
        
        # Look for metadata patterns
        for line in lines:
            line = line.strip()
            
            # URL patterns
            if re.match(r'(?:Source|URL|Original|Scraped from):\s*https?://', line, re.IGNORECASE):
                url_match = re.search(r'https?://[^\s\n]+', line)
                if url_match:
                    metadata['url'] = url_match.group()
            
            # Title patterns
            if line.startswith('#') and not metadata.get('title'):
                metadata['title'] = line.lstrip('#').strip()
            
            # Date patterns
            if re.search(r'(?:Scraped|Date|Updated):\s*\d{4}-\d{2}-\d{2}', line, re.IGNORECASE):
                date_match = re.search(r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}', line)
                if date_match:
                    metadata['original_date'] = date_match.group()
        
        # Extract domain from URL if available
        if 'url' in metadata:
            try:
                parsed = urlparse(metadata['url'])
                metadata['domain'] = parsed.netloc
                metadata['path'] = parsed.path
            except:
                pass
        
        # Fallback title from filename
        if 'title' not in metadata:
            # Remove timestamp and extension from filename
            clean_name = re.sub(r'scraped_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_', '', filename)
            clean_name = re.sub(r'\.[^.]+$', '', clean_name)
            metadata['title'] = clean_name.replace('_', ' ').replace('-', ' ').title()
        
        return metadata
    
    def clean_content(self, content: str) -> str:
        """Clean and normalize scraped content"""
        # Remove metadata header if present
        lines = content.split('\n')
        content_start = 0
        
        # Skip metadata lines at the beginning
        for i, line in enumerate(lines[:20]):  # Check first 20 lines
            if line.strip().startswith('Source:') or line.strip().startswith('Scraped:') or line.strip().startswith('URL:'):
                content_start = i + 1
            elif line.strip().startswith('#'):
                break
        
        if content_start > 0:
            content = '\n'.join(lines[content_start:])
        
        # Clean up whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        # Remove common navigation and UI elements
        navigation_patterns = [
            r'^(Home|Back|Next|Previous|Menu|Navigation|Skip to|Jump to)$',
            r'^\s*[\|\-\+\=]{3,}\s*$',  # ASCII dividers
            r'^\s*[•·▪▫→←↑↓]\s*$',      # Standalone bullets/arrows
            r'^\s*(Cookie|Privacy|Terms).{0,50}(Policy|Notice|Settings)\s*$',
            r'^\s*(Accept|Decline|OK|Cancel|Close|×|✕)\s*$',
            r'^\s*\d+\s*$',  # Standalone numbers (often pagination)
        ]
        
        cleaned_lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not any(re.match(pattern, line, re.IGNORECASE) for pattern in navigation_patterns):
                cleaned_lines.append(line)
        
        cleaned_content = '\n'.join(cleaned_lines)
        
        # Remove excessive empty lines again
        cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
        
        return cleaned_content.strip()
    
    def validate_content(self, content: str, metadata: Dict) -> Tuple[bool, str]:
        """Validate content quality"""
        if len(content) < self.min_content_length:
            return False, f"Content too short ({len(content)} chars)"
        
        if len(content) > self.max_content_length:
            return False, f"Content too long ({len(content)} chars)"
        
        # Check for minimum word count
        word_count = len(content.split())
        if word_count < 20:
            return False, f"Too few words ({word_count})"
        
        # Check for meaningful content (not just navigation)
        sentences = re.split(r'[.!?]+', content)
        meaningful_sentences = [s for s in sentences if len(s.strip()) > 10]
        
        if len(meaningful_sentences) < 3:
            return False, "Not enough meaningful sentences"
        
        # Check for excessive repetition
        lines = content.split('\n')
        unique_lines = set(line.strip() for line in lines if line.strip())
        if len(lines) > 10 and len(unique_lines) / len(lines) < 0.5:
            return False, "Too much repetitive content"
        
        return True, "Content validation passed"
    
    def process_scraped_files(self) -> Dict:
        """Process all new scraped files and add to RAG system"""
        # Find all markdown files
        markdown_files = list(self.scraped_dir.glob("*.md"))
        new_files = [f for f in markdown_files if f.name not in self.processed_files]
        
        if not new_files:
            logger.info("📭 No new scraped files to process")
            return {"processed": 0, "skipped": 0, "errors": 0}
        
        logger.info(f"🔄 Processing {len(new_files)} new scraped files...")
        
        stats = {"processed": 0, "skipped": 0, "errors": 0}
        
        for file_path in new_files:
            try:
                # Read content
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                
                # Extract metadata
                metadata = self.extract_metadata_from_content(raw_content, file_path.name)
                
                # Clean content
                cleaned_content = self.clean_content(raw_content)
                
                # Validate content
                is_valid, validation_msg = self.validate_content(cleaned_content, metadata)
                
                if not is_valid:
                    logger.warning(f"⚠️  Skipping {file_path.name}: {validation_msg}")
                    stats["skipped"] += 1
                    # Still mark as processed to avoid reprocessing
                    self.processed_files.add(file_path.name)
                    continue
                
                # Ensure we have required fields
                url = metadata.get('url', f"file://{file_path.absolute()}")
                title = metadata.get('title', file_path.stem)
                
                # Add to RAG system
                doc_id = self.rag.add_document(
                    url=url,
                    title=title,
                    content=cleaned_content,
                    metadata={
                        **metadata,
                        "original_file": file_path.name,
                        "content_length": len(cleaned_content),
                        "raw_content_length": len(raw_content),
                        "processing_date": datetime.now().isoformat()
                    }
                )
                
                # Mark as processed
                self.processed_files.add(file_path.name)
                stats["processed"] += 1
                
                logger.info(f"✅ Processed: {title} (ID: {doc_id})")
                
            except Exception as e:
                logger.error(f"❌ Error processing {file_path.name}: {e}")
                stats["errors"] += 1
        
        # Save processed files list
        self._save_processed_files()
        
        logger.info(f"🎉 Processing complete: {stats['processed']} processed, {stats['skipped']} skipped, {stats['errors']} errors")
        return stats
    
    def create_scraping_template(self, url: str, suggested_filename: str = None) -> str:
        """Create a template filename for scraped content"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        if suggested_filename:
            clean_name = re.sub(r'[^\w\-_.]', '_', suggested_filename)
            return f"scraped_{timestamp}_{clean_name}.md"
        
        # Generate from URL
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '').replace('.', '_')
            path_parts = [p for p in parsed.path.split('/') if p and p != '/']
            
            if path_parts:
                path_name = '_'.join(path_parts[:3])  # Max 3 path segments
                clean_path = re.sub(r'[^\w\-_]', '_', path_name)
                filename = f"scraped_{timestamp}_{domain}_{clean_path}.md"
            else:
                filename = f"scraped_{timestamp}_{domain}.md"
                
        except:
            filename = f"scraped_{timestamp}_unknown.md"
        
        return filename
    
    def save_scraped_content(self, url: str, title: str, content: str, 
                           suggested_filename: str = None) -> str:
        """Save scraped content with proper formatting"""
        filename = self.create_scraping_template(url, suggested_filename)
        filepath = self.scraped_dir / filename
        
        # Format content with metadata header
        formatted_content = f"""# {title}

Source: {url}
Scraped: {datetime.now().isoformat()}

## Content

{content}
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(formatted_content)
        
        logger.info(f"💾 Saved scraped content: {filename}")
        return str(filepath)
    
    def setup_directories_and_instructions(self):
        """Set up directories and create helpful instructions"""
        
        # Create instructions for Claude
        instructions_path = self.scraped_dir / "PLAYWRIGHT_INSTRUCTIONS.md"
        
        instructions = f"""# 🎭 Playwright MCP → BerryRAG Integration Guide

## 📋 Overview
This system integrates Playwright MCP web scraping with BerryRAG vector database for Claude.

## 🔄 Workflow

### 1. Scraping with Playwright MCP
When using Playwright MCP to scrape content, save files in this directory with the suggested format:

**Filename Format:**
```
scraped_YYYY-MM-DD_HH-MM-SS_domain_page-title.md
```

**Content Format:**
```markdown
# Page Title

Source: https://example.com/page
Scraped: 2024-01-15T14:30:00

## Content

[Your scraped content here...]
```

### 2. Processing Pipeline
```bash
# Process new scraped files into vector database
python src/playwright_integration.py process

# Or use the npm script
npm run process-scraped
```

### 3. Querying the Knowledge Base
```bash
# Search for specific content
python src/rag_system.py search "React hooks"

# Get formatted context for Claude
python src/rag_system.py context "How to implement useState"

# List all documents
python src/rag_system.py list

# Get system statistics
python src/rag_system.py stats
```

## 🤖 Example Claude Commands

### Scraping Documentation
```
"Use Playwright to navigate to https://react.dev/reference/react/useState and extract all the documentation content. Save it as markdown in the scraped_content directory."
```

### Processing into Vector DB
```
"Process all new scraped files in scraped_content/ and add them to the vector database"
```

### Querying Knowledge Base
```
"Search the vector database for information about React useState hook best practices"
```

## 📁 Directory Structure
```
{Path.cwd()}
├── scraped_content/     ← Playwright saves scraped content here
├── storage/             ← Vector database and embeddings
├── src/                 ← Python scripts
└── mcp_servers/         ← MCP server implementations
```

## 🔧 Commands Reference

| Command | Description |
|---------|-------------|
| `npm run process-scraped` | Process new scraped files |
| `npm run search` | Search the vector database |
| `npm run list-docs` | List all documents |
| `python src/rag_system.py context "query"` | Get context for Claude |

## 💡 Tips for Better Scraping

1. **Include context**: Scrape related pages together
2. **Clean titles**: Use descriptive, searchable titles
3. **Batch processing**: Process multiple related docs at once
4. **Validate content**: Check that scraped content is meaningful

## 🔍 Quality Filters

The system automatically filters out:
- Content shorter than 100 characters
- Navigation-only content
- Repetitive/duplicate content
- Files larger than 500KB

## 📊 Monitoring

Check processing status:
```bash
# View recent activity
cat {self.scraped_dir}/.processed_files.json

# Check vector database stats
python src/rag_system.py stats
```

## 🚀 Getting Started

1. Install dependencies: `npm run install-deps`
2. Scrape content with Playwright MCP
3. Process: `npm run process-scraped`
4. Query: `python src/rag_system.py search "your query"`

Happy scraping! 🕷️✨
"""
        
        with open(instructions_path, 'w') as f:
            f.write(instructions)
        
        # Create a sample content file
        sample_path = self.scraped_dir / "sample_scraped_content.md"
        if not sample_path.exists():
            sample_content = f"""# Sample Documentation Page

Source: https://example.com/docs/getting-started
Scraped: {datetime.now().isoformat()}

## Content

This is a sample of how scraped content should be formatted.

### Getting Started

This section would contain the actual documentation content that was scraped from the webpage.

### Key Features

- Feature 1: Description of feature
- Feature 2: Another important feature
- Feature 3: Yet another feature

### Code Examples

```javascript
function example() {{
    console.log("This is example code from the documentation");
}}
```

### Best Practices

1. Always include meaningful titles
2. Preserve the original structure when possible
3. Include source URL for reference
4. Add timestamp for tracking freshness
"""
            
            with open(sample_path, 'w') as f:
                f.write(sample_content)
        
        logger.info(f"📋 Created instructions at {instructions_path}")
        logger.info(f"📄 Created sample content at {sample_path}")
        
        # Create a .gitignore for the scraped content directory
        gitignore_path = self.scraped_dir / ".gitignore"
        gitignore_content = """# Scraped content - adjust based on your needs
*.md
!PLAYWRIGHT_INSTRUCTIONS.md
!sample_scraped_content.md
.processed_files.json
"""
        with open(gitignore_path, 'w') as f:
            f.write(gitignore_content)

def main():
    """CLI interface for Playwright integration"""
    import sys
    
    if len(sys.argv) < 2:
        print("""
🎭 BerryRAG Playwright Integration

Usage: python src/playwright_integration.py <command>

Commands:
  process  - Process all new scraped files into vector database
  setup    - Create directories and instructions
  save     - Save content directly (for testing)
  stats    - Show processing statistics

Examples:
  python src/playwright_integration.py process
  python src/playwright_integration.py setup
        """)
        return
    
    integration = PlaywrightRAGIntegration()
    command = sys.argv[1]
    
    try:
        if command == "process":
            stats = integration.process_scraped_files()
            print(f"✅ Processing complete:")
            print(f"   📄 Processed: {stats['processed']}")
            print(f"   ⚠️  Skipped: {stats['skipped']}")
            print(f"   ❌ Errors: {stats['errors']}")
            
        elif command == "setup":
            integration.setup_directories_and_instructions()
            print("🚀 Setup complete!")
            print(f"📁 Scraped content directory: {integration.scraped_dir}")
            print(f"💾 Vector storage: {integration.rag.storage_path}")
            print("📋 Check PLAYWRIGHT_INSTRUCTIONS.md for usage guide")
            
        elif command == "save" and len(sys.argv) >= 5:
            url, title, content = sys.argv[2], sys.argv[3], sys.argv[4]
            filepath = integration.save_scraped_content(url, title, content)
            print(f"💾 Saved content to: {filepath}")
            
        elif command == "stats":
            # Show both integration and RAG stats
            rag_stats = integration.rag.get_stats()
            processed_count = len(integration.processed_files)
            
            print("📊 Integration Statistics:")
            print(f"   📁 Scraped files processed: {processed_count}")
            print(f"   📚 Documents in database: {rag_stats['document_count']}")
            print(f"   🧩 Total chunks: {rag_stats['chunk_count']}")
            print(f"   💾 Storage used: {rag_stats['total_storage_mb']} MB")
            print(f"   🤖 Embedding provider: {rag_stats['embedding_provider']}")
            
        else:
            print(f"❌ Unknown command: {command}")
            
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
