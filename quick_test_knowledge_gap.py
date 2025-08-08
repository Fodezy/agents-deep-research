#!/usr/bin/env python3
"""
Quick test for migrated KnowledgeGapAgent to verify it's working.
"""

import asyncio
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.knowledge_gap_agent_native import create_knowledge_gap_agent_native


async def quick_test():
    """Quick functionality test"""
    print("Quick KnowledgeGapAgent migration test...")
    
    config = LLMConfig(search_provider='searxng')
    agent = create_knowledge_gap_agent_native(config)
    
    test_input = "Research artificial intelligence applications in healthcare"
    
    try:
        result = await agent.run_native_analysis(test_input)
        
        print(f"SUCCESS: Native structured generation working!")
        print(f"   Research complete: {result.research_complete}")
        print(f"   Gaps identified: {len(result.gaps_identified)}")
        
        if result.gaps_identified:
            print(f"   First gap: {result.gaps_identified[0].description[:60]}...")
            
        return True
        
    except Exception as e:
        print(f"FAILED: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(quick_test())
    print("Phase 2.1 KnowledgeGapAgent migration:", "SUCCESS" if success else "FAILED")