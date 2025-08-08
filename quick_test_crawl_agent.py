#!/usr/bin/env python3
"""
Quick test for migrated CrawlAgent to verify it's working.
"""

import asyncio
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.tool_agents.crawl_agent_native import init_crawl_agent_native


async def quick_test():
    """Quick functionality test"""
    print("Quick CrawlAgent migration test...")
    
    config = LLMConfig(search_provider='searxng')
    agent = init_crawl_agent_native(config)
    
    # Use a simple URL string for testing
    test_input = "https://example.com"
    
    try:
        result_dict = await agent.run_implementation(test_input)
        
        print(f"SUCCESS: Native structured generation working!")
        print(f"   Output length: {len(result_dict['output'])} chars")
        print(f"   Sources: {len(result_dict['sources'])} sources")
        print(f"   Processing: {result_dict.get('processing_method', 'unknown')}")
        print(f"   Confidence: {result_dict.get('confidence', 'unknown')}")
        
        if result_dict['output']:
            print(f"   Output preview: {result_dict['output'][:80]}...")
        
        if result_dict['sources']:
            print(f"   First source: {result_dict['sources'][0]}")
            
        return True
        
    except Exception as e:
        print(f"FAILED: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(quick_test())
    print("Phase 2.3 CrawlAgent migration:", "SUCCESS" if success else "FAILED")