# 🍓 BerryExa: Exa-like Web Content Extraction System

BerryExa is an MVP implementation that replicates the core functionality of Exa's `get contents` API for single website crawling and content extraction, built specifically for the BerryRAG ecosystem.

## ✨ Features

- **Mozilla Readability Integration**: Uses the battle-tested Readability library (from Firefox Reader View) for superior content extraction
- **Playwright Web Crawling**: Robust JavaScript-enabled web scraping
- **OpenAI-Powered Enhancement**: AI-generated summaries and highlights
- **BerryRAG Integration**: Automatic addition to your local vector database
- **Exa-Compatible Output**: JSON response format optimized for LLM consumption
- **Link Discovery**: Extracts internal links for potential subpage crawling

## 🏗️ Architecture

```
BerryExa System
├── WebCrawler (Playwright)
│   ├── JavaScript-enabled crawling
│   ├── Custom user agent
│   └── Timeout handling
├── ReadabilityExtractor (Mozilla)
│   ├── Content readability detection
│   ├── Clean HTML-to-Markdown conversion
│   └── Metadata extraction
├── ContentProcessor (OpenAI)
│   ├── AI-generated summaries
│   ├── Key highlight extraction
│   └── Fallback processing
└── BerryRAG Integration
    ├── Automatic vector storage
    ├── Rich metadata preservation
    └── Searchable content indexing
```

## 🚀 Quick Start

### Installation

The system is already integrated into your BerryRAG project. Dependencies are automatically installed:

```bash
# Node.js dependencies (already installed)
npm install @mozilla/readability jsdom

# Python dependencies (already in requirements.txt)
pip install playwright openai beautifulsoup4
```

### Basic Usage

```bash
# Extract content and add to RAG database
python src/berry_exa.py crawl "https://docs.python.org/3/tutorial/"

# Extract content without adding to RAG (for testing)
python src/berry_exa.py crawl-no-rag "https://example.com/article"
```

### Programmatic Usage

```python
import asyncio
from src.berry_exa import BerryExaSystem

async def extract_content():
    berry_exa = BerryExaSystem()

    # Extract content from URL
    response = await berry_exa.get_contents(
        url="https://docs.python.org/3/tutorial/",
        add_to_rag=True  # Automatically add to vector database
    )

    if response.results:
        result = response.results[0]
        print(f"Title: {result.title}")
        print(f"Summary: {result.summary}")
        print(f"Content length: {len(result.text)} characters")
        print(f"Highlights: {len(result.highlights)} found")

        # Get LLM-optimized context
        print("\nFormatted for LLM:")
        print(response.context)

# Run the extraction
asyncio.run(extract_content())
```

## 📊 Response Format

BerryExa returns an `ExaResponse` object with the following structure:

```json
{
  "requestId": "uuid-string",
  "results": [
    {
      "title": "Page Title",
      "url": "https://example.com",
      "publishedDate": "2024-01-15T10:30:00Z",
      "author": "Author Name",
      "text": "Clean markdown content...",
      "summary": "AI-generated summary...",
      "highlights": ["Key sentence 1", "Key sentence 2"],
      "highlightScores": [0.9, 0.8],
      "extras": {
        "links": [{ "url": "...", "text": "..." }]
      }
    }
  ],
  "context": "LLM-optimized formatted content",
  "statuses": [{ "id": "url", "status": "success" }]
}
```

## 🔧 Configuration

### OpenAI Integration

Set your OpenAI API key for enhanced summaries and highlights:

```bash
export OPENAI_API_KEY=your_key_here
```

Without OpenAI, the system falls back to simple text processing.

### Readability Options

The system uses Mozilla Readability with optimized settings:

- **Character Threshold**: 100 (minimum content length)
- **Classes Preserved**: `highlight`, `code`, `pre`
- **Content Validation**: Automatic readability detection
- **Markdown Conversion**: Clean HTML-to-Markdown transformation

## 🎯 Use Cases

### Documentation Extraction

```bash
python src/berry_exa.py crawl "https://docs.python.org/3/tutorial/introduction.html"
```

### Blog Post Processing

```bash
python src/berry_exa.py crawl "https://blog.example.com/article"
```

### Research Paper Extraction

```bash
python src/berry_exa.py crawl "https://arxiv.org/abs/2307.06435"
```

## 🔍 Content Quality

BerryExa automatically filters and validates content:

- ✅ **Readability Detection**: Uses Mozilla's algorithm to determine if content is suitable
- ✅ **Content Cleaning**: Removes navigation, ads, and boilerplate
- ✅ **Structure Preservation**: Maintains headings, lists, and code blocks
- ✅ **Link Extraction**: Discovers internal links for subpage crawling
- ✅ **Metadata Extraction**: Captures title, author, publish date, etc.

## 🔗 Integration with BerryRAG

When `add_to_rag=True`, extracted content is automatically:

1. **Chunked** using BerryRAG's smart text splitting
2. **Embedded** using your configured embedding provider
3. **Stored** in the local vector database
4. **Indexed** for fast similarity search
5. **Enriched** with Readability metadata

### Metadata Stored

```python
{
    'source': 'berry_exa_readability',
    'author': 'Author Name',
    'published_date': '2024-01-15T10:30:00Z',
    'summary': 'AI-generated summary',
    'extraction_date': '2024-01-15T14:30:00Z',
    'readability_length': 5000,
    'readability_excerpt': 'Article excerpt',
    'site_name': 'Site Name',
    'content_direction': 'ltr',
    'content_language': 'en'
}
```

## 🆚 Comparison with Exa API

| Feature             | Exa API | BerryExa     |
| ------------------- | ------- | ------------ |
| Content Extraction  | ✅      | ✅           |
| Metadata Extraction | ✅      | ✅           |
| AI Summaries        | ✅      | ✅           |
| Highlights          | ✅      | ✅           |
| Subpage Discovery   | ✅      | 🔄 (Planned) |
| Local Storage       | ❌      | ✅           |
| Cost                | 💰      | 🆓           |
| Customization       | ❌      | ✅           |
| Privacy             | ❌      | ✅           |

## 🛠️ Technical Details

### Dependencies

- **@mozilla/readability**: Content extraction engine
- **jsdom**: DOM manipulation for Node.js
- **playwright**: Web crawling and JavaScript execution
- **openai**: AI-powered content enhancement
- **beautifulsoup4**: HTML parsing for link extraction

### Performance

- **Crawling**: ~3-5 seconds per page
- **Content Extraction**: ~0.5 seconds with Readability
- **AI Processing**: ~2-5 seconds (with OpenAI)
- **Vector Storage**: ~1 second (with sentence-transformers)

### Error Handling

- **Network Timeouts**: 30-second timeout with retry logic
- **Content Validation**: Automatic readability detection
- **Graceful Degradation**: Falls back to simple processing if AI fails
- **Status Tracking**: Detailed error reporting in response

## 🔮 Future Enhancements

- **Subpage Discovery**: Automatic crawling of related pages
- **Batch Processing**: Multiple URLs in single request
- **Custom Extractors**: Plugin system for specialized content types
- **Rate Limiting**: Built-in throttling for respectful crawling
- **Cache System**: Local caching to avoid re-crawling
- **MCP Integration**: Direct Claude tool access

## 🤝 Contributing

BerryExa is part of the BerryRAG ecosystem. To contribute:

1. Test with various websites and content types
2. Report issues with specific URLs
3. Suggest improvements for content extraction
4. Help optimize AI prompts for better summaries

## 📄 License

MIT License - Part of the BerryRAG project.

---

**BerryExa brings the power of Exa's content extraction to your local environment, with the added benefits of privacy, customization, and seamless BerryRAG integration.** 🍓✨
