#!/usr/bin/env python3
"""
Test script for BerryExa subpage functionality
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from berry_exa import BerryExaSystem

async def test_subpage_crawling():
    """Test the subpage crawling functionality"""
    print("🍓 Testing BerryExa Subpage Functionality")
    print("=" * 50)
    
    berry_exa = BerryExaSystem()
    
    # Test URL with good internal links
    test_url = "https://docs.python.org/3/tutorial/"
    
    print(f"📋 Testing URL: {test_url}")
    print(f"🔍 Crawling main page + 3 subpages with 'tutorial' keyword targeting")
    print()
    
    try:
        # Test subpage crawling
        response = await berry_exa.get_contents_with_subpages(
            url=test_url,
            subpages=3,
            subpage_target=["tutorial", "introduction", "basics"],
            max_depth=1,
            add_to_rag=False
        )
        
        if response.results:
            print(f"✅ Successfully crawled {len(response.results)} pages")
            
            # Main page
            main_result = response.results[0]
            print(f"\n📄 Main Page:")
            print(f"   Title: {main_result.title}")
            print(f"   URL: {main_result.url}")
            print(f"   Content: {len(main_result.text)} chars")
            print(f"   Summary: {main_result.summary[:100]}...")
            links_count = len(main_result.extras.get('links', [])) if main_result.extras else 0
            print(f"   Links found: {links_count}")
            
            # Subpages
            if len(response.results) > 1:
                print(f"\n📚 Subpages ({len(response.results)-1} found):")
                for i, subpage in enumerate(response.results[1:], 1):
                    print(f"   {i}. {subpage.title}")
                    print(f"      URL: {subpage.url}")
                    print(f"      Content: {len(subpage.text)} chars")
                    print(f"      Depth: {subpage.depth}")
                    print(f"      Parent: {subpage.parent_url}")
                    print()
            
            # Status summary
            print(f"📊 Crawl Statistics:")
            print(f"   Total pages: {len(response.results)}")
            print(f"   Request ID: {response.requestId}")
            if response.statuses:
                successful = len([s for s in response.statuses if s.get("status") == "success"])
                failed = len([s for s in response.statuses if s.get("status") == "error"])
                print(f"   Successful: {successful}")
                print(f"   Failed: {failed}")
            
        else:
            print("❌ No results returned")
            if response.statuses:
                for status in response.statuses:
                    if status.get("status") == "error":
                        print(f"   Error: {status.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_link_extraction():
    """Test link extraction functionality"""
    print("\n" + "=" * 50)
    print("🔗 Testing Link Extraction")
    print("=" * 50)
    
    berry_exa = BerryExaSystem()
    test_url = "https://docs.python.org/3/tutorial/"
    
    try:
        links = await berry_exa.extract_links_only(
            url=test_url,
            filter_keywords=["tutorial", "introduction"],
            max_links=10
        )
        
        print(f"✅ Found {len(links)} filtered links:")
        for i, link in enumerate(links, 1):
            print(f"   {i}. {link['text'][:50]}...")
            print(f"      URL: {link['url']}")
        
    except Exception as e:
        print(f"❌ Link extraction failed: {e}")

async def test_content_preview():
    """Test content preview functionality"""
    print("\n" + "=" * 50)
    print("📄 Testing Content Preview")
    print("=" * 50)
    
    berry_exa = BerryExaSystem()
    test_url = "https://docs.python.org/3/tutorial/introduction.html"
    
    try:
        preview = await berry_exa.get_content_preview(
            url=test_url,
            max_chars=300
        )
        
        if preview:
            print(f"✅ Preview generated:")
            print(f"   Title: {preview['title']}")
            print(f"   Content: {preview['content'][:200]}...")
        else:
            print("❌ No preview generated")
            
    except Exception as e:
        print(f"❌ Preview failed: {e}")

async def main():
    """Run all tests"""
    print("🧪 BerryExa Subpage Functionality Tests")
    print("=" * 60)
    
    await test_subpage_crawling()
    await test_link_extraction()
    await test_content_preview()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
