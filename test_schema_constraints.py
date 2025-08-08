#!/usr/bin/env python3
"""
Test schema constraint fixes for native structured generation.
"""

import asyncio
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.knowledge_gap_agent import init_knowledge_gap_agent


async def test_schema_constraints():
    """Test that models now follow schema constraints properly"""
    print("Testing schema constraint fixes...")
    
    config = LLMConfig(search_provider='searxng')
    
    try:
        kg_agent = init_knowledge_gap_agent(config)
        result = await kg_agent.run_native_analysis("Test quantum physics research")
        
        # Validate schema constraints
        print(f"SUCCESS: Schema version: {result.schema_version} (expected: 1)")
        assert result.schema_version == 1, f"Schema version should be 1, got {result.schema_version}"
        
        print(f"SUCCESS: Research completeness confidence: {result.research_completeness_confidence} (expected: 0.0-1.0)")
        assert 0.0 <= result.research_completeness_confidence <= 1.0, f"Confidence should be 0.0-1.0, got {result.research_completeness_confidence}"
        
        for i, gap in enumerate(result.gaps_identified):
            print(f"SUCCESS: Gap {i+1} confidence: {gap.confidence} (expected: 0.0-1.0)")
            assert 0.0 <= gap.confidence <= 1.0, f"Gap confidence should be 0.0-1.0, got {gap.confidence}"
        
        print(f"\nSUCCESS: All schema constraints validated!")
        print(f"- Schema version: {result.schema_version}")
        print(f"- Research confidence: {result.research_completeness_confidence}")
        print(f"- Gap confidences: {[gap.confidence for gap in result.gaps_identified]}")
        
        return True
        
    except Exception as e:
        print(f"FAILED: Schema constraint test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_schema_constraints())
    if success:
        print("\nSCHEMA CONSTRAINTS: FIXED!")
        print("Models now properly follow numeric format requirements")
    exit(0 if success else 1)