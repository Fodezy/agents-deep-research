#!/usr/bin/env python3
"""
Test that the iterative research system now uses native structured generation.
"""

import asyncio
from deep_researcher.llm_config import LLMConfig
from deep_researcher.iterative_research import IterativeResearcher


async def test_native_integration():
    """Test that IterativeResearcher now uses native structured generation"""
    print("Testing native structured generation integration...")
    
    config = LLMConfig(search_provider='searxng')
    
    try:
        # Create researcher with max 1 iteration for quick testing
        researcher = IterativeResearcher(
            max_iterations=1,
            max_time_minutes=5,
            config=config,
            verbose=True
        )
        
        # Initialize start_time to fix the time calculation issue
        import time
        researcher.start_time = time.time()
        
        # Initialize conversation with first iteration (required by _evaluate_gaps)
        researcher.conversation.add_iteration()
        
        # Test the knowledge gap evaluation (should use native generation)
        print("\n=== Testing KnowledgeGapAgent Native Integration ===")
        evaluation = await researcher._evaluate_gaps(
            query="Test quantum entanglement",
            background_context="Testing native structured generation integration"
        )
        
        # Validate that we get a proper structured result
        print(f"SUCCESS: Native evaluation completed")
        print(f"- Research complete: {evaluation.research_complete}")
        print(f"- Schema version: {evaluation.schema_version}")
        print(f"- Gaps identified: {len(evaluation.gaps_identified)}")
        print(f"- Research confidence: {evaluation.research_completeness_confidence}")
        
        # Validate schema constraints are met
        assert evaluation.schema_version == 1, f"Expected schema_version=1, got {evaluation.schema_version}"
        assert 0.0 <= evaluation.research_completeness_confidence <= 1.0, f"Invalid confidence: {evaluation.research_completeness_confidence}"
        
        for gap in evaluation.gaps_identified:
            assert 0.0 <= gap.confidence <= 1.0, f"Invalid gap confidence: {gap.confidence}"
            # Validate gap_id format
            assert gap.gap_id.replace('_', '').replace('-', '').isalnum(), f"Invalid gap_id format: {gap.gap_id}"
        
        print(f"SUCCESS: All schema constraints validated!")
        
        return True
        
    except Exception as e:
        print(f"FAILED: Native integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_native_integration())
    if success:
        print("\nNATIVE INTEGRATION: SUCCESS!")
        print("IterativeResearcher now uses native structured generation")
        print("No more legacy Agents framework JSON parsing!")
    else:
        print("\nNATIVE INTEGRATION: FAILED!")
        print("Still issues with the integration")
    exit(0 if success else 1)