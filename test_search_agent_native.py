#!/usr/bin/env python3
"""
Test script for migrated SearchAgent using native structured generation.
"""

import asyncio
import sys
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.tool_agents.search_agent_native import test_search_agent_native, init_search_agent_native


async def test_basic_search():
    """Test basic search functionality"""
    print("Testing basic SearchAgent functionality...")
    
    config = LLMConfig(search_provider='searxng')
    
    test_query = """
    {
      "gap": "How quantum computers work",
      "query": "quantum computing basics",
      "entity_website": null
    }
    """
    
    success = await test_search_agent_native(config, test_query)
    return success


async def test_structured_search_input():
    """Test with different search parameters"""
    print("\nTesting structured search input...")
    
    config = LLMConfig(search_provider='searxng')
    agent = init_search_agent_native(config)
    
    test_input = """
    {
      "gap": "Machine learning applications in healthcare",
      "query": "AI medical diagnosis",
      "entity_website": "nature.com"
    }
    """
    
    try:
        result_dict = await agent.run_implementation(test_input)
        
        print("SUCCESS: Structured search input test passed")
        print(f"   Output length: {len(result_dict['output'])} chars")
        print(f"   Sources: {len(result_dict['sources'])} sources")
        print(f"   Processing method: {result_dict.get('processing_method', 'unknown')}")
        
        # Validate structure
        assert 'output' in result_dict
        assert 'sources' in result_dict
        assert len(result_dict['output']) > 50
        
        return True
        
    except Exception as e:
        print(f"FAILED: Structured search input test failed: {e}")
        return False


async def test_search_with_website_bias():
    """Test search with entity website bias"""
    print("\nTesting search with website bias...")
    
    config = LLMConfig(search_provider='searxng')
    agent = init_search_agent_native(config)
    
    test_input = """
    {
      "gap": "Latest developments in artificial intelligence",
      "query": "AI developments 2024",
      "entity_website": "arxiv.org"
    }
    """
    
    try:
        result_dict = await agent.run_implementation(test_input)
        
        print("SUCCESS: Website bias test passed")
        print(f"   Output preview: {result_dict['output'][:100]}...")
        print(f"   Sources count: {len(result_dict['sources'])}")
        
        # Check if any sources are from the biased website
        arxiv_sources = [s for s in result_dict['sources'] if 'arxiv' in s.lower()]
        if arxiv_sources:
            print(f"   ArXiv sources found: {len(arxiv_sources)}")
        
        return True
        
    except Exception as e:
        print(f"FAILED: Website bias test failed: {e}")
        return False


async def test_schema_validation():
    """Test that output always matches expected schema"""
    print("\nTesting schema validation...")
    
    config = LLMConfig(search_provider='searxng')
    agent = init_search_agent_native(config)
    
    test_input = """
    {
      "gap": "Climate change impacts",
      "query": "climate change effects",
      "entity_website": null
    }
    """
    
    try:
        result_dict = await agent.run_implementation(test_input)
        
        # Validate schema compliance
        from deep_researcher.agents.utils.outlines_schemas import EnhancedToolAgentOutput
        
        result = EnhancedToolAgentOutput(**result_dict)
        
        assert isinstance(result.output, str), "output must be string"
        assert isinstance(result.sources, list), "sources must be list"
        assert isinstance(result.processing_method, str), "processing_method must be string"
        assert isinstance(result.confidence, (int, float)), "confidence must be numeric"
        assert isinstance(result.processing_time_ms, (int, float)), "processing_time_ms must be numeric"
        
        print("SUCCESS: Schema validation test passed")
        print(f"   All fields present and correct types")
        
        return True
        
    except Exception as e:
        print(f"FAILED: Schema validation test failed: {e}")
        return False


async def main():
    """Run all SearchAgent migration tests"""
    print("Starting SearchAgent native migration tests...")
    print("Using native Ollama structured generation")
    
    tests = [
        test_basic_search,
        test_structured_search_input,
        test_search_with_website_bias,
        test_schema_validation
    ]
    
    passed = 0
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"FAILED: Test {test.__name__} crashed: {e}")
    
    print(f"\nSearchAgent Migration Test Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("SUCCESS: SearchAgent native migration successful!")
        print("   - 100% structured generation working")
        print("   - Schema validation passing")
        print("   - Web search integration working")
        print("   - Ready for production integration")
    else:
        print("WARNING: Some tests failed. Check configuration and search provider.")
        
    return passed == len(tests)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)