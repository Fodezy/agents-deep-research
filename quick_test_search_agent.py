#!/usr/bin/env python3
"""
Quick test for migrated SearchAgent to verify it's working.
"""

import asyncio
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.tool_agents.search_agent_native import init_search_agent_native


async def quick_test():
    """Quick functionality test"""
    print("Quick SearchAgent migration test...")
    
    config = LLMConfig(search_provider='searxng')
    agent = init_search_agent_native(config)
    
    # Test with simple string query
    test_input = "quantum computing basics"
    
    try:
        result_dict = await agent.run_implementation(test_input)
        
        print(f"SUCCESS: Native structured generation working!")
        print(f"   Output length: {len(result_dict['output'])} chars")
        print(f"   Sources: {len(result_dict['sources'])} sources")
        print(f"   Processing: {result_dict.get('processing_method', 'unknown')}")
        print(f"   Confidence: {result_dict.get('confidence', 'unknown')}")
        
        if result_dict['output']:
            print(f"   Output preview: {result_dict['output'][:80]}...")
            
        return True
        
    except Exception as e:
        print(f"FAILED: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(quick_test())
    print("Phase 2.2 SearchAgent migration:", "SUCCESS" if success else "FAILED")