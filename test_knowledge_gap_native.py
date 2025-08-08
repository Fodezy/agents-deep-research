#!/usr/bin/env python3
"""
Test script for migrated KnowledgeGapAgent using native structured generation.
"""

import asyncio
import sys
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.knowledge_gap_agent_native import test_knowledge_gap_agent_native, create_knowledge_gap_agent_native


async def test_basic_functionality():
    """Test basic knowledge gap analysis functionality"""
    print("Testing basic KnowledgeGapAgent functionality...")
    
    # Initialize config (same as production)
    config = LLMConfig(search_provider='searxng')
    
    test_input = """
    Research Context: Quantum entanglement research for physics paper
    Current Progress: Found basic definitions and Einstein's objections  
    Remaining Questions: How is it used in quantum computing? What are the practical applications?
    """
    
    success = await test_knowledge_gap_agent_native(config, test_input)
    return success


async def test_structured_input():
    """Test with structured dictionary input"""
    print("\nTesting structured dictionary input...")
    
    config = LLMConfig(search_provider='searxng')
    agent = create_knowledge_gap_agent_native(config)
    
    structured_input = {
        "research_context": "Machine learning model optimization",
        "current_progress": "Implemented basic neural network, tested on small dataset",
        "remaining_questions": "How to handle overfitting? What about hyperparameter tuning?",
        "entity_website": None
    }
    
    try:
        result = await agent.run_native_analysis(structured_input)
        
        print("SUCCESS: Structured input test passed")
        print(f"   Gaps identified: {len(result.gaps_identified)}")
        print(f"   Research complete: {result.research_complete}")
        
        # Validate structure
        assert hasattr(result, 'gaps_identified')
        assert hasattr(result, 'research_complete')
        assert len(result.gaps_identified) >= 0
        
        return True
        
    except Exception as e:
        print(f"FAILED: Structured input test failed: {e}")
        return False


async def test_empty_research_handling():
    """Test handling of minimal research context"""
    print("\nTesting empty/minimal research handling...")
    
    config = LLMConfig(search_provider='searxng')
    agent = create_knowledge_gap_agent_native(config)
    
    minimal_input = "Brief research on climate change"
    
    try:
        result = await agent.run_native_analysis(minimal_input)
        
        print("SUCCESS: Minimal input test passed")
        print(f"   Gaps identified: {len(result.gaps_identified)}")
        print(f"   Research complete: {result.research_complete}")
        
        # Should identify gaps for minimal research
        if not result.research_complete:
            assert len(result.gaps_identified) > 0, "Should create gaps for minimal research"
        
        return True
        
    except Exception as e:
        print(f"FAILED: Minimal input test failed: {e}")
        return False


async def test_schema_validation():
    """Test that output always matches expected schema"""
    print("\nTesting schema validation...")
    
    config = LLMConfig(search_provider='searxng')
    agent = create_knowledge_gap_agent_native(config)
    
    test_input = "Research artificial intelligence applications in healthcare"
    
    try:
        result = await agent.run_native_analysis(test_input)
        
        # Validate schema compliance
        from deep_researcher.agents.utils.outlines_schemas import KnowledgeGapResult, KnowledgeGap
        
        assert isinstance(result, KnowledgeGapResult), f"Expected KnowledgeGapResult, got {type(result)}"
        assert isinstance(result.gaps_identified, list), "gaps_identified must be a list"
        assert isinstance(result.research_complete, bool), "research_complete must be boolean"
        
        # Validate individual gaps
        for gap in result.gaps_identified:
            assert isinstance(gap, KnowledgeGap), f"Each gap must be KnowledgeGap, got {type(gap)}"
            assert hasattr(gap, 'gap'), "Gap must have 'gap' field"
            assert hasattr(gap, 'priority'), "Gap must have 'priority' field"
            assert hasattr(gap, 'confidence'), "Gap must have 'confidence' field"
        
        print("SUCCESS: Schema validation test passed")
        print(f"   All fields present and correct types")
        
        return True
        
    except Exception as e:
        print(f"FAILED: Schema validation test failed: {e}")
        return False


async def main():
    """Run all KnowledgeGapAgent migration tests"""
    print("Starting KnowledgeGapAgent native migration tests...")
    print("Using native Ollama structured generation")
    
    tests = [
        test_basic_functionality,
        test_structured_input,
        test_empty_research_handling,
        test_schema_validation
    ]
    
    passed = 0
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"FAILED: Test {test.__name__} crashed: {e}")
    
    print(f"\nKnowledgeGapAgent Migration Test Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("SUCCESS: KnowledgeGapAgent native migration successful!")
        print("   - 100% structured generation working")
        print("   - Schema validation passing")
        print("   - All input formats supported")
        print("   - Ready for production integration")
    else:
        print("WARNING: Some tests failed. Check configuration and model availability.")
        
    return passed == len(tests)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)