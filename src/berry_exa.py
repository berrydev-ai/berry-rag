#!/usr/bin/env python3
"""
BerryExa: Exa-like Web Content Extraction System
MVP implementation for single website crawling and content extraction
"""

import os
import json
import uuid
import hashlib
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse
import logging

# Third-party imports
import requests
import subprocess
from playwright.async_api import async_playwright
import openai
from dotenv import load_dotenv

# Local imports
from rag_system import BerryRAGSystem

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ExaResult:
    """Single result matching Exa API format but optimized for MCP/LLM usage"""
    title: str
    url: str
    publishedDate: Optional[str] = None
    author: Optional[str] = None
    text: str = ""
    summary: str = ""
    highlights: Optional[List[str]] = None
    highlightScores: Optional[List[float]] = None
    subpages: Optional[List[Dict]] = None
    extras: Optional[Dict[str, Any]] = None
    depth: int = 0
    parent_url: Optional[str] = None
    crawl_path: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.highlights is None:
            self.highlights = []
        if self.highlightScores is None:
            self.highlightScores = []
        if self.subpages is None:
            self.subpages = []
        if self.extras is None:
            self.extras = {"links": []}
        if self.crawl_path is None:
            self.crawl_path = [self.url]

@dataclass
class ExaResponse:
    """Complete response matching Exa API format"""
    requestId: str
    results: List[ExaResult]
    context: str = ""
    statuses: Optional[List[Dict]] = None
    
    def __post_init__(self):
        if self.statuses is None:
            self.statuses = []

class ReadabilityExtractor:
    """Extract content using Mozilla's Readability library via Node.js"""
    
    def __init__(self):
        self.extractor_path = Path(__file__).parent / "readability_extractor.cjs"
        logger.info("🔧 Readability extractor initialized")
    
    def extract_content(self, html: str, url: str) -> Tuple[Dict[str, Any], bool]:
        """Extract content using Readability"""
        try:
            # Call the Node.js Readability extractor
            result = subprocess.run(
                ['node', str(self.extractor_path), html, url],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Readability extractor failed: {result.stderr}")
                return {}, False
            
            # Parse the JSON response
            data = json.loads(result.stdout)
            
            if not data.get('success', False):
                logger.warning(f"Content not readable: {data.get('error', 'Unknown error')}")
                return data, False
            
            logger.info("✅ Content extracted with Readability")
            return data, True
            
        except subprocess.TimeoutExpired:
            logger.error("Readability extractor timed out")
            return {'error': 'Extraction timeout'}, False
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Readability output: {e}")
            return {'error': 'Invalid JSON response'}, False
        except Exception as e:
            logger.error(f"Readability extraction failed: {e}")
            return {'error': str(e)}, False
    
    def extract_links_from_html(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract internal links for potential subpage discovery"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            links = []
            base_domain = urlparse(base_url).netloc
            
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if not href:
                    continue
                    
                # Convert relative URLs to absolute
                href_str = str(href) if href else ""
                if not href_str:
                    continue
                    
                full_url = urljoin(base_url, href_str)
                link_domain = urlparse(full_url).netloc
                
                # Only include internal links
                if link_domain == base_domain:
                    link_text = link.get_text().strip()
                    if link_text and len(link_text) > 3:
                        links.append({
                            'url': full_url,
                            'text': link_text[:100]  # Limit text length
                        })
            
            return links[:20]  # Limit number of links
            
        except Exception as e:
            logger.error(f"Failed to extract links: {e}")
            return []

class ContentProcessor:
    """Process content using OpenAI for summarization and highlights"""
    
    def __init__(self):
        self.openai_client = None
        if os.getenv('OPENAI_API_KEY'):
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.openai_client = openai.OpenAI()
            logger.info("✅ OpenAI client initialized")
        else:
            logger.warning("⚠️ OpenAI API key not found. Summarization will be limited.")
    
    async def generate_summary(self, content: str, title: str = "") -> str:
        """Generate a summary using OpenAI"""
        if not self.openai_client or len(content) < 200:
            return self._fallback_summary(content)
        
        try:
            # Truncate content if too long
            max_content = 3000
            if len(content) > max_content:
                content = content[:max_content] + "..."
            
            prompt = f"""Please provide a concise 2-3 sentence summary of the following content:

Title: {title}

Content:
{content}

Summary:"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            if summary:
                logger.info("✅ Generated AI summary")
                return summary.strip()
            else:
                return self._fallback_summary(content)
            
        except Exception as e:
            logger.error(f"OpenAI summarization failed: {e}")
            return self._fallback_summary(content)
    
    def _fallback_summary(self, content: str) -> str:
        """Fallback summary using simple text processing"""
        sentences = content.split('.')[:3]
        summary = '. '.join(s.strip() for s in sentences if s.strip())
        return summary + '.' if summary else "Content summary not available."
    
    async def extract_highlights(self, content: str, max_highlights: int = 5) -> Tuple[List[str], List[float]]:
        """Extract key highlights using OpenAI"""
        if not self.openai_client or len(content) < 200:
            return self._fallback_highlights(content, max_highlights)
        
        try:
            # Truncate content if too long
            max_content = 2500
            if len(content) > max_content:
                content = content[:max_content] + "..."
            
            prompt = f"""Extract the {max_highlights} most important and informative sentences from the following content. Return only the sentences, one per line:

{content}

Key sentences:"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.2
            )
            
            highlights_text = response.choices[0].message.content
            if highlights_text:
                highlights = [h.strip() for h in highlights_text.strip().split('\n') if h.strip()]
            else:
                highlights = []
            
            # Generate mock scores (in real implementation, could use embedding similarity)
            scores = [0.9 - (i * 0.1) for i in range(len(highlights))]
            
            logger.info(f"✅ Extracted {len(highlights)} AI highlights")
            return highlights[:max_highlights], scores[:max_highlights]
            
        except Exception as e:
            logger.error(f"OpenAI highlight extraction failed: {e}")
            return self._fallback_highlights(content, max_highlights)
    
    def _fallback_highlights(self, content: str, max_highlights: int) -> Tuple[List[str], List[float]]:
        """Fallback highlight extraction using simple heuristics"""
        sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 50]
        
        # Simple scoring based on length and position
        scored_sentences = []
        for i, sentence in enumerate(sentences[:20]):  # Only consider first 20 sentences
            score = len(sentence) / 200  # Length factor
            score += (20 - i) / 20  # Position factor (earlier = higher score)
            scored_sentences.append((sentence + '.', score))
        
        # Sort by score and take top highlights
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        highlights = [s[0] for s in scored_sentences[:max_highlights]]
        scores = [s[1] for s in scored_sentences[:max_highlights]]
        
        return highlights, scores

class WebCrawler:
    """Web crawler using Playwright for robust content extraction"""
    
    def __init__(self):
        self.timeout = 30000  # 30 seconds
        self.user_agent = "BerryExa/1.0 (Web Content Extractor)"
    
    async def crawl_url(self, url: str) -> Tuple[str, str, bool]:
        """Crawl a single URL and return HTML content"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.user_agent,
                    viewport={'width': 1280, 'height': 720}
                )
                
                page = await context.new_page()
                
                # Navigate to URL
                response = await page.goto(url, timeout=self.timeout, wait_until='domcontentloaded')
                
                if not response or response.status >= 400:
                    await browser.close()
                    return "", f"HTTP {response.status if response else 'No response'}", False
                
                # Wait for content to load
                await page.wait_for_timeout(2000)
                
                # Get HTML content
                html_content = await page.content()
                
                await browser.close()
                
                logger.info(f"✅ Successfully crawled: {url}")
                return html_content, "success", True
                
        except Exception as e:
            logger.error(f"❌ Failed to crawl {url}: {e}")
            return "", str(e), False

class BerryExaSystem:
    """Main BerryExa system combining all components"""
    
    def __init__(self, rag_storage_dir: str = "./storage"):
        self.crawler = WebCrawler()
        self.extractor = ReadabilityExtractor()
        self.processor = ContentProcessor()
        self.rag_system = BerryRAGSystem(rag_storage_dir)
        
        logger.info("🍓 BerryExa system initialized with Readability")
    
    async def get_contents(self, url: str, add_to_rag: bool = True) -> ExaResponse:
        """Main method to get contents from a URL (Exa-like interface)"""
        request_id = str(uuid.uuid4())
        
        try:
            # Crawl the URL
            html_content, error_msg, success = await self.crawler.crawl_url(url)
            
            if not success:
                return ExaResponse(
                    requestId=request_id,
                    results=[],
                    statuses=[{"id": url, "status": "error", "error": error_msg}]
                )
            
            # Extract content using Readability
            extraction_result, success = self.extractor.extract_content(html_content, url)
            
            if not success:
                error_msg = extraction_result.get('error', 'Failed to extract content')
                return ExaResponse(
                    requestId=request_id,
                    results=[],
                    statuses=[{"id": url, "status": "error", "error": error_msg}]
                )
            
            # Get the article data
            article = extraction_result['article']
            metadata = extraction_result['metadata']
            
            # Use the clean markdown content from Readability
            clean_content = article['textContent']
            
            if len(clean_content) < 100:
                return ExaResponse(
                    requestId=request_id,
                    results=[],
                    statuses=[{"id": url, "status": "error", "error": "Content too short or empty"}]
                )
            
            # Extract links for extras
            links = self.extractor.extract_links_from_html(html_content, url)
            
            # Process content with AI
            summary = await self.processor.generate_summary(clean_content, metadata.get('title', ''))
            highlights, highlight_scores = await self.processor.extract_highlights(clean_content)
            
            # Create result using Readability data
            result = ExaResult(
                title=article['title'],
                url=url,
                publishedDate=article['publishedTime'],
                author=article['byline'],
                text=clean_content,
                summary=summary,
                highlights=highlights,
                highlightScores=highlight_scores,
                extras={"links": links}
            )
            
            # Add to RAG system if requested
            if add_to_rag:
                try:
                    doc_id = self.rag_system.add_document(
                        url=url,
                        title=result.title,
                        content=clean_content,
                        metadata={
                            'source': 'berry_exa_readability',
                            'author': result.author,
                            'published_date': result.publishedDate,
                            'summary': summary,
                            'extraction_date': datetime.now().isoformat(),
                            'readability_length': article['length'],
                            'readability_excerpt': article['excerpt'],
                            'site_name': article['siteName'],
                            'content_direction': article['dir'],
                            'content_language': article['lang']
                        }
                    )
                    logger.info(f"✅ Added to RAG system: {doc_id}")
                except Exception as e:
                    logger.error(f"Failed to add to RAG system: {e}")
            
            # Generate context string optimized for LLMs
            context = self._format_context_for_llm(result)
            
            return ExaResponse(
                requestId=request_id,
                results=[result],
                context=context,
                statuses=[{"id": url, "status": "success"}]
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing {url}: {e}")
            return ExaResponse(
                requestId=request_id,
                results=[],
                statuses=[{"id": url, "status": "error", "error": str(e)}]
            )
    
    def _format_context_for_llm(self, result: ExaResult) -> str:
        """Format the result as context optimized for LLM consumption"""
        context_parts = [
            f"# {result.title}",
            f"**Source:** {result.url}",
        ]
        
        if result.author:
            context_parts.append(f"**Author:** {result.author}")
        
        if result.publishedDate:
            context_parts.append(f"**Published:** {result.publishedDate}")
        
        if result.summary:
            context_parts.append(f"\n## Summary\n{result.summary}")
        
        if result.highlights:
            context_parts.append("\n## Key Points")
            for i, highlight in enumerate(result.highlights, 1):
                context_parts.append(f"{i}. {highlight}")
        
        context_parts.append(f"\n## Full Content\n{result.text}")
        
        return "\n".join(context_parts)
    
    async def get_contents_with_subpages(
        self, 
        url: str, 
        subpages: int = 0, 
        subpage_target: Optional[List[str]] = None,
        max_depth: int = 3,
        add_to_rag: bool = False
    ) -> ExaResponse:
        """Enhanced method to get contents with subpage support"""
        request_id = str(uuid.uuid4())
        all_results = []
        all_statuses = []
        
        try:
            # First, crawl the main page
            main_response = await self.get_contents(url, add_to_rag=add_to_rag)
            
            if not main_response.results:
                return main_response
            
            main_result = main_response.results[0]
            all_results.append(main_result)
            if main_response.statuses:
                all_statuses.extend(main_response.statuses)
            
            # If subpages requested, crawl them
            if subpages > 0:
                subpage_results = await self._crawl_subpages(
                    main_result, subpages, subpage_target, max_depth, add_to_rag
                )
                all_results.extend(subpage_results['results'])
                all_statuses.extend(subpage_results['statuses'])
            
            # Generate combined context
            context = self._format_combined_context(all_results)
            
            return ExaResponse(
                requestId=request_id,
                results=all_results,
                context=context,
                statuses=all_statuses
            )
            
        except Exception as e:
            logger.error(f"❌ Error in subpage crawling: {e}")
            return ExaResponse(
                requestId=request_id,
                results=[],
                statuses=[{"id": url, "status": "error", "error": str(e)}]
            )
    
    async def _crawl_subpages(
        self, 
        main_result: ExaResult, 
        max_subpages: int,
        keyword_targets: Optional[List[str]],
        max_depth: int,
        add_to_rag: bool
    ) -> Dict[str, List]:
        """Crawl subpages with keyword targeting and depth control"""
        results = []
        statuses = []
        crawled_urls = {main_result.url}  # Track to avoid duplicates
        
        # Get links from main page
        links = main_result.extras.get('links', []) if main_result.extras else []
        
        if not links:
            logger.info("No links found for subpage crawling")
            return {'results': results, 'statuses': statuses}
        
        # Score and filter links
        scored_links = self._score_links(links, keyword_targets, main_result.url)
        
        # Limit to requested number of subpages
        selected_links = scored_links[:max_subpages]
        
        logger.info(f"🔍 Selected {len(selected_links)} subpages to crawl")
        
        # Crawl subpages with rate limiting
        for i, (link, score) in enumerate(selected_links):
            if link['url'] in crawled_urls:
                continue
                
            try:
                # Rate limiting: 1 second delay between requests
                if i > 0:
                    await asyncio.sleep(1.0)
                
                logger.info(f"🕷️ Crawling subpage {i+1}/{len(selected_links)}: {link['url']}")
                
                subpage_response = await self.get_contents(link['url'], add_to_rag=add_to_rag)
                
                if subpage_response.results:
                    subpage_result = subpage_response.results[0]
                    # Add subpage metadata
                    subpage_result.depth = 1
                    subpage_result.parent_url = main_result.url
                    subpage_result.crawl_path = [main_result.url, link['url']]
                    
                    results.append(subpage_result)
                    crawled_urls.add(link['url'])
                    
                if subpage_response.statuses:
                    statuses.extend(subpage_response.statuses)
                
            except Exception as e:
                logger.error(f"Failed to crawl subpage {link['url']}: {e}")
                statuses.append({
                    "id": link['url'], 
                    "status": "error", 
                    "error": str(e)
                })
        
        logger.info(f"✅ Completed subpage crawling: {len(results)} successful")
        return {'results': results, 'statuses': statuses}
    
    def _score_links(
        self, 
        links: List[Dict[str, str]], 
        keyword_targets: Optional[List[str]],
        base_url: str
    ) -> List[Tuple[Dict[str, str], float]]:
        """Score links based on relevance and position"""
        scored_links = []
        
        for i, link in enumerate(links):
            score = 0.0
            
            # Position score (earlier links get higher scores)
            position_score = 1.0 - (i / len(links)) * 0.3
            score += position_score * 0.3
            
            # Keyword relevance score
            if keyword_targets:
                relevance_score = self._calculate_keyword_relevance(
                    link, keyword_targets
                )
                score += relevance_score * 0.7
            else:
                # Default scoring without keywords
                score += 0.5
            
            scored_links.append((link, score))
        
        # Sort by score (highest first)
        scored_links.sort(key=lambda x: x[1], reverse=True)
        return scored_links
    
    def _calculate_keyword_relevance(
        self, 
        link: Dict[str, str], 
        keywords: List[str]
    ) -> float:
        """Calculate how relevant a link is to the target keywords"""
        if not keywords:
            return 0.5
        
        url_text = link['url'].lower()
        link_text = link['text'].lower()
        combined_text = f"{url_text} {link_text}"
        
        matches = 0
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in combined_text:
                matches += 1
        
        return min(matches / len(keywords), 1.0)
    
    def _format_combined_context(self, results: List[ExaResult]) -> str:
        """Format multiple results as combined context"""
        if not results:
            return ""
        
        main_result = results[0]
        context_parts = [
            f"# {main_result.title}",
            f"**Main URL:** {main_result.url}",
        ]
        
        if main_result.author:
            context_parts.append(f"**Author:** {main_result.author}")
        
        if main_result.summary:
            context_parts.append(f"\n## Main Page Summary\n{main_result.summary}")
        
        # Add subpages if any
        if len(results) > 1:
            context_parts.append(f"\n## Related Subpages ({len(results)-1} found)")
            for i, subpage in enumerate(results[1:], 1):
                context_parts.append(f"\n### {i}. {subpage.title}")
                context_parts.append(f"**URL:** {subpage.url}")
                if subpage.summary:
                    context_parts.append(f"**Summary:** {subpage.summary}")
        
        context_parts.append(f"\n## Main Content\n{main_result.text}")
        
        # Add subpage content
        for i, subpage in enumerate(results[1:], 1):
            context_parts.append(f"\n## Subpage {i}: {subpage.title}\n{subpage.text}")
        
        return "\n".join(context_parts)
    
    async def extract_links_only(
        self, 
        url: str, 
        filter_keywords: Optional[List[str]] = None,
        max_links: int = 20
    ) -> List[Dict[str, str]]:
        """Extract links from a URL without full content processing"""
        try:
            html_content, error_msg, success = await self.crawler.crawl_url(url)
            
            if not success:
                logger.error(f"Failed to crawl {url}: {error_msg}")
                return []
            
            # Extract links
            links = self.extractor.extract_links_from_html(html_content, url)
            
            # Filter by keywords if provided
            if filter_keywords:
                filtered_links = []
                for link in links:
                    relevance = self._calculate_keyword_relevance(link, filter_keywords)
                    if relevance > 0:
                        filtered_links.append(link)
                links = filtered_links
            
            return links[:max_links]
            
        except Exception as e:
            logger.error(f"Failed to extract links from {url}: {e}")
            return []
    
    async def get_content_preview(
        self, 
        url: str, 
        max_chars: int = 500
    ) -> Optional[Dict[str, str]]:
        """Get a quick preview of webpage content"""
        try:
            html_content, error_msg, success = await self.crawler.crawl_url(url)
            
            if not success:
                return None
            
            # Quick extraction without full processing
            extraction_result, success = self.extractor.extract_content(html_content, url)
            
            if not success:
                return None
            
            article = extraction_result['article']
            preview_content = article['textContent'][:max_chars]
            
            return {
                'title': article['title'],
                'content': preview_content,
                'url': url
            }
            
        except Exception as e:
            logger.error(f"Failed to preview {url}: {e}")
            return None

def main():
    """CLI interface for BerryExa"""
    import sys
    
    if len(sys.argv) < 2:
        print("""
🍓 BerryExa - Web Content Extraction System

Usage: python src/berry_exa.py <command> [args...]

Commands:
  crawl <url>                    - Extract content from URL
  crawl-no-rag <url>            - Extract content without adding to RAG
  
Examples:
  python src/berry_exa.py crawl "https://example.com/article"
  python src/berry_exa.py crawl-no-rag "https://docs.python.org"
        """)
        return
    
    async def run_command():
        berry_exa = BerryExaSystem()
        command = sys.argv[1]
        
        try:
            if command == "crawl" and len(sys.argv) >= 3:
                url = sys.argv[2]
                response = await berry_exa.get_contents(url, add_to_rag=True)
                
                if response.results:
                    result = response.results[0]
                    print(f"✅ Successfully extracted content from: {url}")
                    print(f"📋 Title: {result.title}")
                    print(f"📝 Content length: {len(result.text)} characters")
                    print(f"📄 Summary: {result.summary}")
                    highlights_count = len(result.highlights) if result.highlights else 0
                    links_count = len(result.extras.get('links', [])) if result.extras else 0
                    print(f"🔍 Highlights: {highlights_count} found")
                    print(f"🔗 Links: {links_count} found")
                    print(f"💾 Added to RAG database")
                else:
                    error_msg = "Unknown error"
                    if response.statuses and len(response.statuses) > 0:
                        error_msg = response.statuses[0].get('error', 'Unknown error')
                    print(f"❌ Failed to extract content: {error_msg}")
            
            elif command == "crawl-no-rag" and len(sys.argv) >= 3:
                url = sys.argv[2]
                response = await berry_exa.get_contents(url, add_to_rag=False)
                
                if response.results:
                    result = response.results[0]
                    print(f"✅ Successfully extracted content from: {url}")
                    print(f"📋 Title: {result.title}")
                    print(f"📝 Content length: {len(result.text)} characters")
                    print(f"📄 Summary: {result.summary}")
                    highlights_count = len(result.highlights) if result.highlights else 0
                    links_count = len(result.extras.get('links', [])) if result.extras else 0
                    print(f"🔍 Highlights: {highlights_count} found")
                    print(f"🔗 Links: {links_count} found")
                    
                    # Print formatted context
                    print("\n" + "="*60)
                    print("FORMATTED CONTEXT FOR LLM:")
                    print("="*60)
                    print(response.context)
                else:
                    error_msg = "Unknown error"
                    if response.statuses and len(response.statuses) > 0:
                        error_msg = response.statuses[0].get('error', 'Unknown error')
                    print(f"❌ Failed to extract content: {error_msg}")
            
            else:
                print(f"❌ Unknown command: {command}")
                
        except Exception as e:
            logger.error(f"Command failed: {e}")
            print(f"❌ Error: {e}")
    
    # Run the async command
    asyncio.run(run_command())

if __name__ == "__main__":
    main()
