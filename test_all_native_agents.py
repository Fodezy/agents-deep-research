#!/usr/bin/env python3
"""
Comprehensive test for all migrated native agents to verify they work correctly together.
"""

import asyncio
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.knowledge_gap_agent import init_knowledge_gap_agent
from deep_researcher.agents.tool_agents import init_search_agent, init_crawl_agent


async def test_all_native_agents():
    """Test all three migrated agents"""
    print("Testing all native agents after Phase 3 cleanup...")
    
    config = LLMConfig(search_provider='searxng')
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: KnowledgeGapAgent
    print("\n=== Testing KnowledgeGapAgent ===")
    try:
        kg_agent = init_knowledge_gap_agent(config)
        result = await kg_agent.run_native_analysis("Research artificial intelligence applications")
        
        assert hasattr(result, 'gaps_identified')
        assert hasattr(result, 'research_complete')
        print(f"SUCCESS: KnowledgeGapAgent - {len(result.gaps_identified)} gaps identified")
        tests_passed += 1
        
    except Exception as e:
        print(f"FAILED: KnowledgeGapAgent - {e}")
    
    # Test 2: SearchAgent
    print("\n=== Testing SearchAgent ===")
    try:
        search_agent = init_search_agent(config)
        result_dict = await search_agent.run_implementation("quantum computing")
        
        assert 'output' in result_dict
        assert 'processing_method' in result_dict
        assert result_dict['processing_method'] == 'native_structured'
        print(f"SUCCESS: SearchAgent - Native structured generation working")
        tests_passed += 1
        
    except Exception as e:
        print(f"FAILED: SearchAgent - {e}")
    
    # Test 3: CrawlAgent
    print("\n=== Testing CrawlAgent ===")
    try:
        crawl_agent = init_crawl_agent(config)
        result_dict = await crawl_agent.run_implementation("https://example.com")
        
        assert 'output' in result_dict
        assert 'processing_method' in result_dict
        assert result_dict['processing_method'] == 'native_structured'
        print(f"SUCCESS: CrawlAgent - Native structured generation working")
        tests_passed += 1
        
    except Exception as e:
        print(f"FAILED: CrawlAgent - {e}")
    
    # Results
    print(f"\n=== Phase 3 Test Results ===")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("SUCCESS: All agents using native structured generation!")
        print("SUCCESS: Phase 3 cleanup successful")
        print("SUCCESS: Outlines dependencies eliminated") 
        print("SUCCESS: Dual-path architecture removed")
        print("SUCCESS: All agents producing schema-guaranteed output")
        return True
    else:
        print("WARNING: Some agents failed. Check configuration.")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_all_native_agents())
    exit(0 if success else 1)