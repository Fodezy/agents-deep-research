#!/usr/bin/env python3
"""
Standalone test script for SearchXNG integration with local models.

This script tests the SearchXNG client independently of the full deep research system
to isolate and debug search functionality issues.

Usage:
    python test_searxng_standalone.py

Prerequisites:
    1. SearchXNG docker container running on http://127.0.0.1:8888
    2. Local Ollama models available
    3. Environment variables configured in .env
"""

import asyncio
import json
import os
import sys
from typing import List
import aiohttp
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deep_researcher.tools.web_search import SearchXNGClient, WebpageSnippet, create_web_search_tool
from deep_researcher.llm_config import LLMConfig

load_dotenv()

async def test_direct_searxng_api():
    """Test direct SearchXNG API call using aiohttp (like curl)."""
    print("="*60)
    print("TEST 1: Direct SearchXNG API Call")
    print("="*60)
    
    searxng_url = "http://127.0.0.1:8888/search"
    params = {"q": "quantum entanglement", "format": "json"}
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"🔗 GET {searxng_url} with params: {params}")
            async with session.get(searxng_url, params=params) as response:
                print(f"📡 HTTP Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Success! Response keys: {list(data.keys())}")
                    
                    results = data.get("results", [])
                    print(f"📋 Found {len(results)} results")
                    
                    for i, result in enumerate(results[:3]):  # Show first 3
                        print(f"  Result {i+1}:")
                        print(f"    URL: {result.get('url', 'N/A')}")
                        print(f"    Title: {result.get('title', 'N/A')}")
                        print(f"    Content: {result.get('content', 'N/A')[:100]}...")
                    
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ HTTP Error {response.status}: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Exception: {type(e).__name__}: {e}")
        return False

async def test_searxng_client():
    """Test SearchXNG client class with minimal LLM config."""
    print("\n" + "="*60)
    print("TEST 2: SearchXNG Client Class")
    print("="*60)
    
    try:
        # Create minimal LLM config for local testing
        config = LLMConfig(
            search_provider="searxng",
            reasoning_model_provider="local",
            reasoning_model="qwen2.5-coder:latest",  # Use your actual model
            main_model_provider="local",
            main_model="qwen2.5-coder:latest",
            fast_model_provider="local",
            fast_model="qwen2.5-coder:latest"
        )
        
        print(f"🔧 Config: {config.search_provider} @ {config.searxng_host}")
        
        # Create a mock filter agent (for testing we'll bypass filtering)
        from deep_researcher.tools.web_search import init_filter_agent
        filter_agent = init_filter_agent(config)
        
        # Create SearchXNG client
        client = SearchXNGClient(filter_agent, config.searxng_host)
        
        # Test search without filtering
        print(f"🔍 Testing search without filtering...")
        snippets = await client.search("quantum entanglement", filter_for_relevance=False, max_results=3)
        
        print(f"✅ Search completed! Found {len(snippets)} snippets")
        for i, snippet in enumerate(snippets):
            print(f"  Snippet {i+1}:")
            print(f"    URL: {snippet.url}")
            print(f"    Title: {snippet.title}")
            print(f"    Description: {snippet.description[:100]}...")
        
        return len(snippets) > 0
        
    except Exception as e:
        import traceback
        print(f"❌ Exception: {type(e).__name__}: {e}")
        print(f"📋 Full traceback:\n{traceback.format_exc()}")
        return False

async def test_web_search_tool():
    """Test the complete web search tool (search + scrape) by calling underlying function."""
    print("\n" + "="*60)
    print("TEST 3: Complete Web Search Tool")
    print("="*60)
    
    try:
        # Instead of using the FunctionTool wrapper, let's test the underlying functionality directly
        from deep_researcher.tools.web_search import init_filter_agent, SearchXNGClient, scrape_urls
        
        # Create LLM config
        config = LLMConfig(
            search_provider="searxng",
            reasoning_model_provider="local",
            reasoning_model="qwen2.5-coder:latest",
            main_model_provider="local",
            main_model="qwen2.5-coder:latest",
            fast_model_provider="local",
            fast_model="qwen2.5-coder:latest"
        )
        
        print(f"🔍 Testing complete web search workflow...")
        
        # Create the components manually
        filter_agent = init_filter_agent(config)
        search_client = SearchXNGClient(filter_agent, config.searxng_host)
        
        # Test search
        print(f"🔍 Step 1: Searching...")
        snippets = await search_client.search("quantum entanglement", filter_for_relevance=False, max_results=3)
        print(f"🔎 Search completed. Got {len(snippets)} snippet(s)")
        
        if not snippets:
            print(f"❌ No search results found")
            return False
        
        # Test scraping
        print(f"📄 Step 2: Scraping {len(snippets)} pages...")
        results = await scrape_urls(snippets)
        print(f"✅ Scraping completed. Scraped {len(results)} pages successfully")
        
        if not results:
            print(f"❌ No pages could be scraped")
            return False
        
        # Show results
        for i, page in enumerate(results[:2]):  # Show first 2
            print(f"  Page {i+1}:")
            print(f"    URL: {page.url}")
            print(f"    Title: {page.title}")
            print(f"    Content: {len(page.text)} characters")
            if page.text:
                print(f"    Sample: {page.text[:200].replace(chr(10), ' ').replace(chr(13), ' ')}...")
        
        return True
            
    except Exception as e:
        import traceback
        print(f"❌ Exception: {type(e).__name__}: {e}")
        print(f"📋 Full traceback:\n{traceback.format_exc()}")
        return False

async def test_configuration():
    """Test environment and configuration setup."""
    print("="*60)
    print("CONFIGURATION TEST")
    print("="*60)
    
    # Check environment variables
    print(f"🔧 SEARCH_PROVIDER: {os.getenv('SEARCH_PROVIDER', 'Not set')}")
    print(f"🔧 SEARXNG_HOST: {os.getenv('SEARXNG_HOST', 'Not set')}")
    print(f"🔧 REASONING_MODEL_PROVIDER: {os.getenv('REASONING_MODEL_PROVIDER', 'Not set')}")
    print(f"🔧 REASONING_MODEL: {os.getenv('REASONING_MODEL', 'Not set')}")
    
    # Test SearchXNG connectivity
    print(f"\n🌐 Testing SearchXNG connectivity...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://127.0.0.1:8888/search?q=test&format=json", timeout=5) as response:
                if response.status == 200:
                    print(f"✅ SearchXNG is reachable at http://127.0.0.1:8888")
                    return True
                else:
                    print(f"❌ SearchXNG returned status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Cannot reach SearchXNG: {e}")
        print(f"💡 Make sure SearchXNG docker container is running:")
        print(f"   docker-compose up -d")
        return False

async def main():
    """Run all tests."""
    print("SearchXNG Standalone Test Suite")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_configuration),
        ("Direct API", test_direct_searxng_api),
        ("SearchXNG Client", test_searxng_client),
        ("Web Search Tool", test_web_search_tool),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} test...")
        try:
            success = await test_func()
            results[test_name] = success
            status = "PASSED" if success else "FAILED"
            print(f"{test_name}: {status}")
        except Exception as e:
            results[test_name] = False
            print(f"{test_name}: FAILED with exception: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "PASSED" if success else "FAILED"
        print(f"{test_name:<20}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed! SearchXNG integration is working.")
    else:
        print("Some tests failed. Check the output above for details.")
        
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)