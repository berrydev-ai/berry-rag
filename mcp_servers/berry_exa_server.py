#!/usr/bin/env python3

"""
BerryExa MCP Server
Provides web crawling and content extraction via Model Context Protocol
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

# Add the src directory to the path so we can import berry_exa
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from berry_exa import BerryExaSystem, ExaResponse, ExaResult

class BerryExaMCPServer:
    """MCP Server for BerryExa web crawling functionality"""
    
    def __init__(self):
        self.berry_exa = BerryExaSystem()
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return the list of available tools"""
        return [
            {
                "name": "crawl_content",
                "description": "Crawl web content with optional subpage support and keyword targeting",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Main URL to crawl"
                        },
                        "subpages": {
                            "type": "number",
                            "default": 0,
                            "minimum": 0,
                            "maximum": 20,
                            "description": "Number of subpages to crawl (max depth 3)"
                        },
                        "subpage_target": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keywords to target specific subpages"
                        },
                        "include_highlights": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include AI-generated highlights"
                        },
                        "include_summary": {
                            "type": "boolean", 
                            "default": True,
                            "description": "Include AI-generated summary"
                        },
                        "max_depth": {
                            "type": "number",
                            "default": 3,
                            "minimum": 1,
                            "maximum": 3,
                            "description": "Maximum crawling depth for subpages"
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "extract_links",
                "description": "Extract internal links from a webpage for subpage discovery",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to extract links from"
                        },
                        "filter_keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter links by keywords in URL or link text"
                        },
                        "max_links": {
                            "type": "number",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 50,
                            "description": "Maximum number of links to return"
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "get_content_preview",
                "description": "Get a quick preview of webpage content without full processing",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to preview"
                        },
                        "max_chars": {
                            "type": "number",
                            "default": 500,
                            "minimum": 100,
                            "maximum": 2000,
                            "description": "Maximum characters in preview"
                        }
                    },
                    "required": ["url"]
                }
            }
        ]
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a tool call and return the result"""
        try:
            if tool_name == "crawl_content":
                return await self._handle_crawl_content(arguments)
            elif tool_name == "extract_links":
                return await self._handle_extract_links(arguments)
            elif tool_name == "get_content_preview":
                return await self._handle_content_preview(arguments)
            else:
                return {
                    "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                    "isError": True
                }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error in {tool_name}: {str(e)}"}],
                "isError": True
            }
    
    async def _handle_crawl_content(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle crawl_content tool call"""
        url = args["url"]
        subpages = args.get("subpages", 0)
        subpage_target = args.get("subpage_target", [])
        max_depth = args.get("max_depth", 3)
        
        # Call the enhanced get_contents method with subpage support
        response = await self.berry_exa.get_contents_with_subpages(
            url=url,
            subpages=subpages,
            subpage_target=subpage_target,
            max_depth=max_depth,
            add_to_rag=False  # MCP server doesn't handle RAG integration
        )
        
        if not response.results:
            error_msg = "No content extracted"
            if response.statuses:
                error_msg = response.statuses[0].get("error", error_msg)
            
            return {
                "content": [{"type": "text", "text": f"❌ Failed to crawl content: {error_msg}"}],
                "isError": True
            }
        
        # Format response for MCP
        main_result = response.results[0]
        result_data = {
            "main_page": {
                "title": main_result.title,
                "url": main_result.url,
                "text": main_result.text,
                "summary": main_result.summary,
                "highlights": main_result.highlights if main_result.highlights else [],
                "author": main_result.author,
                "published_date": main_result.publishedDate,
                "metadata": {
                    "content_length": len(main_result.text),
                    "highlight_count": len(main_result.highlights or []),
                    "extraction_source": "berry_exa_readability"
                }
            },
            "subpages": [],
            "crawl_metadata": {
                "total_pages": len(response.results),
                "request_id": response.requestId,
                "successful_crawls": len([s for s in (response.statuses or []) if s.get("status") == "success"]),
                "failed_crawls": len([s for s in (response.statuses or []) if s.get("status") == "error"])
            }
        }
        
        # Add subpages if any
        if len(response.results) > 1:
            for subpage_result in response.results[1:]:
                result_data["subpages"].append({
                    "title": subpage_result.title,
                    "url": subpage_result.url,
                    "text": subpage_result.text,
                    "summary": subpage_result.summary,
                    "highlights": subpage_result.highlights if subpage_result.highlights else [],
                    "author": subpage_result.author,
                    "published_date": subpage_result.publishedDate,
                    "depth": getattr(subpage_result, 'depth', 1),
                    "parent_url": getattr(subpage_result, 'parent_url', url),
                    "crawl_path": getattr(subpage_result, 'crawl_path', [url, subpage_result.url])
                })
        
        # Format as readable text for MCP response
        formatted_text = self._format_crawl_result(result_data)
        
        return {
            "content": [{"type": "text", "text": formatted_text}]
        }
    
    async def _handle_extract_links(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle extract_links tool call"""
        url = args["url"]
        filter_keywords = args.get("filter_keywords", [])
        max_links = args.get("max_links", 20)
        
        # Use the berry_exa system to extract links
        links = await self.berry_exa.extract_links_only(url, filter_keywords, max_links)
        
        if not links:
            return {
                "content": [{"type": "text", "text": f"No links found on {url}"}]
            }
        
        # Format links for display
        formatted_links = f"🔗 Found {len(links)} links on {url}:\n\n"
        for i, link in enumerate(links, 1):
            formatted_links += f"{i}. [{link['text'][:60]}...]({link['url']})\n"
        
        return {
            "content": [{"type": "text", "text": formatted_links}]
        }
    
    async def _handle_content_preview(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_content_preview tool call"""
        url = args["url"]
        max_chars = args.get("max_chars", 500)
        
        # Get a quick preview without full processing
        preview = await self.berry_exa.get_content_preview(url, max_chars)
        
        if not preview:
            return {
                "content": [{"type": "text", "text": f"❌ Could not preview content from {url}"}],
                "isError": True
            }
        
        formatted_preview = f"📄 Content Preview: {url}\n\n{preview['title']}\n\n{preview['content'][:max_chars]}..."
        
        return {
            "content": [{"type": "text", "text": formatted_preview}]
        }
    
    def _format_crawl_result(self, result_data: Dict[str, Any]) -> str:
        """Format crawl result for readable MCP response"""
        main_page = result_data["main_page"]
        subpages = result_data["subpages"]
        metadata = result_data["crawl_metadata"]
        
        formatted = f"""🍓 BerryExa Crawl Results

📋 **Main Page**: {main_page['title']}
🔗 **URL**: {main_page['url']}
📝 **Content Length**: {main_page['metadata']['content_length']} characters
🔍 **Highlights**: {len(main_page['highlights'])} found
📄 **Summary**: {main_page['summary'][:200]}...

"""
        
        if subpages:
            formatted += f"📚 **Subpages Found**: {len(subpages)}\n\n"
            for i, subpage in enumerate(subpages, 1):
                formatted += f"  {i}. **{subpage['title']}**\n"
                formatted += f"     🔗 {subpage['url']}\n"
                formatted += f"     📝 {len(subpage['text'])} chars, Depth: {subpage['depth']}\n"
                formatted += f"     📄 {subpage['summary'][:100]}...\n\n"
        
        formatted += f"""📊 **Crawl Statistics**:
- Total pages processed: {metadata['total_pages']}
- Successful crawls: {metadata['successful_crawls']}
- Failed crawls: {metadata['failed_crawls']}
- Request ID: {metadata['request_id']}

✅ Content extraction complete! Use this data with BerryRAG's crawl command to add to your vector database."""
        
        return formatted

async def main():
    """Main MCP server loop"""
    server = BerryExaMCPServer()
    
    # MCP communication via stdin/stdout
    while True:
        try:
            line = input()
            if not line:
                continue
                
            request = json.loads(line)
            
            if request.get("method") == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {"tools": server.get_tools()}
                }
            elif request.get("method") == "tools/call":
                params = request.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                result = await server.handle_tool_call(tool_name, arguments)
                response = {
                    "jsonrpc": "2.0", 
                    "id": request.get("id"),
                    "result": result
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {"code": -32601, "message": "Method not found"}
                }
            
            print(json.dumps(response))
            sys.stdout.flush()
            
        except EOFError:
            break
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if 'request' in locals() else None,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    # Log to stderr so it doesn't interfere with MCP communication
    print("🍓 BerryExa MCP Server starting...", file=sys.stderr)
    asyncio.run(main())
