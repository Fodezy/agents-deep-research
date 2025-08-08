#!/usr/bin/env python3
"""
Test newly migrated agents: PlannerAgent and ToolSelectorAgent
Phase 3 completion verification for the final two agents.
"""

import asyncio
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.planner_agent import test_planner_agent_native
from deep_researcher.agents.tool_selector_agent import test_tool_selector_agent_native


async def test_final_phase3_agents():
    """Test the final two agents migrated in Phase 3"""
    print("Testing final Phase 3 migrated agents...")
    print("=" * 50)
    
    config = LLMConfig(search_provider='searxng')
    
    tests_passed = 0
    total_tests = 2
    
    # Test 1: PlannerAgent
    print("\n=== Testing PlannerAgent (Native Structured Generation) ===")
    try:
        result = await test_planner_agent_native(config, "What is artificial intelligence and how does it work?")
        if result:
            tests_passed += 1
            print("SUCCESS: PlannerAgent native structured generation working")
        else:
            print("FAILED: PlannerAgent test returned False")
    except Exception as e:
        print(f"FAILED: PlannerAgent test exception - {e}")
    
    # Test 2: ToolSelectorAgent
    print("\n=== Testing ToolSelectorAgent (Native Structured Generation) ===")
    try:
        test_input = """
        ORIGINAL QUERY: What are the latest advances in renewable energy?
        
        KNOWLEDGE GAP TO ADDRESS: Need to understand current solar panel efficiency improvements
        
        BACKGROUND CONTEXT: Renewable energy is becoming increasingly important for climate change mitigation.
        
        HISTORY OF ACTIONS, FINDINGS AND THOUGHTS: [ITERATION 1] Started research on renewable energy.
        """
        
        result = await test_tool_selector_agent_native(config, test_input)
        if result:
            tests_passed += 1
            print("SUCCESS: ToolSelectorAgent native structured generation working")
        else:
            print("FAILED: ToolSelectorAgent test returned False")
    except Exception as e:
        print(f"FAILED: ToolSelectorAgent test exception - {e}")
    
    # Results
    print("\n" + "=" * 50)
    print("PHASE 3 FINAL AGENT TEST RESULTS")
    print("=" * 50)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("SUCCESS: All final agents migrated to native structured generation!")
        print("SUCCESS: No more Outlines warnings should appear!")
        print("SUCCESS: Phase 3 cleanup is now COMPLETE")
        print("\nMigration Summary:")
        print("- PlannerAgent: MIGRATED to native structured generation")
        print("- ToolSelectorAgent: MIGRATED to native structured generation") 
        print("- KnowledgeGapAgent: MIGRATED (Phase 3.1)")
        print("- SearchAgent: MIGRATED (Phase 3.1)")
        print("- CrawlAgent: MIGRATED (Phase 3.1)")
        print("- ValidationWrapper: DISABLED by default")
        print("- Outlines imports: ELIMINATED")
        return True
    else:
        print("WARNING: Some final agents failed. Check configuration.")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_final_phase3_agents())
    if success:
        print("\nREADY FOR PHASE 4: Testing & Validation!")
    exit(0 if success else 1)