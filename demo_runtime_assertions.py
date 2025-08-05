#!/usr/bin/env python3
"""
Demo script for Runtime Assertion Framework.

This script demonstrates how the runtime assertions prevent the tool execution
pipeline failures discovered during HYBRID-05 investigation, by validating
model-role compatibility before agent execution.
"""

import asyncio
import os
from deep_researcher.agents.baseclass import ResearchAgent, ResearchRunner
from deep_researcher.agents.utils.runtime_assertions import (
    get_assertion_framework,
    RuntimeAssertionError,
    ModelRole
)
from deep_researcher.llm_config import LLMConfig
from agents.model_settings import ModelSettings


async def demo_runtime_assertions():
    """Demonstrate runtime assertion functionality."""
    print("Runtime Assertion Framework Demo - Pipeline Failure Prevention")
    print("=" * 70)
    
    framework = get_assertion_framework()
    
    # 1. Show assertion framework status
    print("\nAssertion Framework Status:")
    print(f"  Enabled: {framework._enabled}")
    print(f"  Cache TTL: {framework._cache_ttl_seconds} seconds")
    
    stats = framework.get_assertion_stats()
    print(f"  Total Assertions: {stats['total_assertions']}")
    print(f"  Passed Assertions: {stats['passed_assertions']}")
    print(f"  Failed Assertions: {stats['failed_assertions']}")
    
    # 2. Test individual model-role assertions
    print("\nTesting Individual Model-Role Assertions:")
    print("-" * 45)
    
    test_cases = [
        # Valid tool calling model
        ("hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M", "local", ModelRole.TOOL_CALLING),
        # Invalid tool calling model (should fail)
        ("hermes3:8b", "local", ModelRole.TOOL_CALLING),
        # Valid planning model
        ("hermes3:8b", "local", ModelRole.PLANNER),
        # Valid summarization model
        ("qwen2.5-coder:latest", "local", ModelRole.SUMMARISER)
    ]
    
    for model_id, provider, role in test_cases:
        print(f"\nTesting: {model_id} for {role.value.upper()} role")
        try:
            result = await framework.assert_model_role_compatibility(
                model_id=model_id,
                provider=provider,
                role=role,
                required=False  # Don't fail for demo
            )
            
            status = "PASSED" if result.passed else "FAILED"
            print(f"  Result: {status}")
            print(f"  Message: {result.message}")
            print(f"  Execution Time: {result.execution_time_ms:.1f}ms")
            
            if result.suggestions:
                print("  Suggestions:")
                for suggestion in result.suggestions:
                    print(f"    - {suggestion}")
                    
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # 3. Demonstrate agent role inference
    print("\nAgent Role Inference:")
    print("-" * 25)
    
    test_agents = [
        ResearchAgent(name="WebSearchAgent", instructions="Search", tools=[object()]),
        ResearchAgent(name="PlannerAgent", instructions="Plan"),
        ResearchAgent(name="SummarizerAgent", instructions="Summarize"),
        ResearchAgent(name="WriterAgent", instructions="Write"),
        ResearchAgent(name="ToolSelectorAgent", instructions="Select tools")
    ]
    
    for agent in test_agents:
        inferred_role = agent.infer_agent_role()
        print(f"  {agent.name}: {inferred_role.value if inferred_role else 'None'}")
    
    # 4. Test successful validation scenario
    print("\nSuccessful Validation Scenario:")
    print("-" * 35)
    
    try:
        # Create configuration with validated tool calling model
        config = LLMConfig(
            search_provider="searxng",
            reasoning_model_provider="local",
            reasoning_model="hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M",
            main_model_provider="local",
            main_model="hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M",
            fast_model_provider="local",
            fast_model="hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M"
        )
        
        # Create tool calling agent with good model
        good_agent = ResearchAgent(
            name="ValidatedSearchAgent",
            model=config.main_model,
            instructions="Search for information using validated model",
            tools=[object()],  # Has tools
            role=ModelRole.TOOL_CALLING
        )
        
        print("Created agent with validated XLAM model")
        print(f"  Agent: {good_agent.name}")
        print(f"  Role: {good_agent.infer_agent_role().value}")
        
        model_info = ResearchRunner._extract_model_info(good_agent)
        if model_info:
            model_id, provider = model_info
            print(f"  Model: {model_id}")
            print(f"  Provider: {provider}")
        
        # Test validation (should pass)
        print("Running validation...")
        await ResearchRunner._validate_agent_model_compatibility(good_agent)
        print("SUCCESS: Validation passed!")
        
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
    
    # 5. Test failure prevention scenario
    print("\nFailure Prevention Scenario:")
    print("-" * 32)
    
    try:
        # Create configuration with model that will fail tool calling validation
        bad_config = LLMConfig(
            search_provider="searxng",
            reasoning_model_provider="local",
            reasoning_model="hermes3:8b",  # Not optimal for tool calling
            main_model_provider="local",
            main_model="hermes3:8b",
            fast_model_provider="local",
            fast_model="hermes3:8b"
        )
        
        # Create tool calling agent with suboptimal model
        bad_agent = ResearchAgent(
            name="ProblematicSearchAgent",
            model=bad_config.main_model,
            instructions="Search for information with suboptimal model",
            tools=[object()],  # Has tools - will infer TOOL_CALLING role
        )
        
        print("Created agent with suboptimal model for tool calling")
        print(f"  Agent: {bad_agent.name}")
        print(f"  Role: {bad_agent.infer_agent_role().value}")
        
        model_info = ResearchRunner._extract_model_info(bad_agent)
        if model_info:
            model_id, provider = model_info
            print(f"  Model: {model_id}")
            print(f"  Provider: {provider}")
        
        # Test validation (should fail)
        print("Running validation...")
        await ResearchRunner._validate_agent_model_compatibility(bad_agent)
        print("UNEXPECTED: Validation should have failed!")
        
    except RuntimeAssertionError as e:
        print("EXPECTED: Validation failed as designed!")
        print(f"  Error: {e}")
        print("\nActionable Error Message:")
        print("-" * 28)
        # Show first few lines of actionable message
        actionable = e.get_actionable_message()
        lines = actionable.split('\n')
        for line in lines[:10]:  # Show first 10 lines
            print(f"  {line}")
        if len(lines) > 10:
            print(f"  ... and {len(lines) - 10} more lines")
    
    # 6. Performance metrics
    print("\nPerformance Metrics:")
    print("-" * 20)
    
    final_stats = framework.get_assertion_stats()
    print(f"  Total Assertions Run: {final_stats['total_assertions']}")
    print(f"  Success Rate: {final_stats['passed_assertions']}/{final_stats['total_assertions']}")
    print(f"  Average Execution Time: {final_stats['avg_execution_time_ms']:.1f}ms")
    
    if final_stats['avg_execution_time_ms'] < 100:
        print("  Performance Target: MET (<100ms)")
    else:
        print("  Performance Target: MISSED (>100ms)")
    
    # 7. Environment variable controls
    print("\nEnvironment Variable Controls:")
    print("-" * 33)
    print("  DISABLE_RUNTIME_ASSERTIONS=true    - Disables all validation")
    print("  FAIL_ON_ASSERTION_ERRORS=true     - Strict error handling")
    print("")
    print("Current settings:")
    print(f"  DISABLE_RUNTIME_ASSERTIONS: {os.getenv('DISABLE_RUNTIME_ASSERTIONS', 'false')}")
    print(f"  FAIL_ON_ASSERTION_ERRORS: {os.getenv('FAIL_ON_ASSERTION_ERRORS', 'false')}")
    
    print("\nDemo Complete! Key Benefits:")
    print("  - Prevents HYBRID-05 pipeline failures at runtime")
    print("  - Provides actionable error messages for misconfigurations")
    print("  - Validates the 4-model architecture requirements")
    print("  - Caches results for <100ms performance overhead")
    print("  - Integrates seamlessly with ResearchRunner workflow")


if __name__ == "__main__":
    asyncio.run(demo_runtime_assertions())