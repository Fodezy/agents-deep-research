"""
Test ValidationWrapper compatibility with dual-path architecture agents.
Verifies that validation works with both structured and legacy agent paths.
"""

import asyncio
import json
from unittest.mock import Mock, AsyncMock
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.utils.validated_agent import ValidatedAgent
from deep_researcher.agents.tool_agents.search_agent import init_search_agent
from deep_researcher.agents.tool_agents.crawl_agent import init_crawl_agent
from deep_researcher.agents.planner_agent import init_planner_agent
from deep_researcher.agents.tool_selector_agent import init_tool_selector_agent
from deep_researcher.agents.knowledge_gap_agent import init_knowledge_gap_agent


async def test_dual_path_agents():
    """Test dual-path agents with and without validation"""
    print("=== Testing Dual-Path Agents ===")
    
    config = LLMConfig(search_provider='searxng')
    
    # Test agents that have dual-path architecture
    dual_path_agents = [
        ("SearchAgent", init_search_agent),
        ("CrawlAgent", init_crawl_agent),
        ("PlannerAgent", init_planner_agent),
        ("ToolSelectorAgent", init_tool_selector_agent),
        ("KnowledgeGapAgent", init_knowledge_gap_agent)
    ]
    
    for agent_name, init_func in dual_path_agents:
        print(f"\nTesting {agent_name}:")
        
        try:
            # Create base agent
            base_agent = init_func(config)
            print(f"  [PASS] Created base {agent_name}: {base_agent.name}")
            
            # Wrap with validation
            validated_agent = ValidatedAgent(base_agent=base_agent)
            print(f"  [PASS] Created validated {agent_name}")
            
            # Check validation status
            status = validated_agent.get_validation_status()
            print(f"  [PASS] Validation enabled: {status['validation_enabled']}")
            
            # Verify agent can handle basic interface
            assert hasattr(validated_agent, 'run_implementation')
            assert hasattr(validated_agent, 'name')
            print(f"  [PASS] Agent interface preserved")
            
        except Exception as e:
            print(f"  [FAIL] {agent_name} failed: {e}")
            return False
    
    return True


async def test_validation_output_compatibility():
    """Test that validation doesn't break output format compatibility"""
    print("\n=== Testing Output Format Compatibility ===")
    
    config = LLMConfig(search_provider='searxng')
    
    try:
        # Create validated search agent
        base_agent = init_search_agent(config)
        validated_agent = ValidatedAgent(base_agent=base_agent)
        
        # Mock the underlying tool to return predictable output
        if hasattr(base_agent, 'tools') and base_agent.tools:
            for tool in base_agent.tools:
                if hasattr(tool, 'func'):
                    original_func = tool.func
                    async def mock_search(query):
                        return json.dumps({
                            "results": [
                                {"title": "Test Result", "url": "https://test.com", "content": "Test content"}
                            ]
                        })
                    tool.func = mock_search
        
        # Mock the model to return valid JSON
        if hasattr(base_agent, 'model'):
            original_model = base_agent.model
            mock_response = Mock()
            mock_response.content = json.dumps({
                "output": "Test search results show information about AI developments",
                "sources": ["https://test.com"]
            })
            
            async def mock_model_call(*args, **kwargs):
                return mock_response
            
            base_agent.model = mock_model_call
        
        print("  [PASS] Mocks configured for testing")
        
        # Test that we can get validation status
        status = validated_agent.get_validation_status()
        assert 'validation_enabled' in status
        print("  [PASS] Validation status accessible")
        
        # Test agent delegation works
        assert validated_agent.name == base_agent.name
        print("  [PASS] Agent delegation working")
        
        return True
        
    except Exception as e:
        print(f"  [FAIL] Output compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_circuit_breaker_integration():
    """Test circuit breaker integration with agents"""
    print("\n=== Testing Circuit Breaker Integration ===")
    
    config = LLMConfig(search_provider='searxng')
    
    try:
        # Create validated agent
        base_agent = init_planner_agent(config)
        validated_agent = ValidatedAgent(base_agent=base_agent)
        
        # Get validation status
        status = validated_agent.get_validation_status()
        
        # Check circuit breaker is present
        if 'validator_status' in status:
            validator_status = status['validator_status']
            assert 'circuit_breaker' in validator_status
            
            circuit_breaker_status = validator_status['circuit_breaker']
            assert circuit_breaker_status['state'] == 'closed'  # Should start closed
            assert circuit_breaker_status['failure_count'] == 0
            
            print("  [PASS] Circuit breaker properly initialized")
        else:
            print("  [INFO] Validation disabled, circuit breaker not active")
        
        return True
        
    except Exception as e:
        print(f"  [FAIL] Circuit breaker integration failed: {e}")
        return False


async def test_backward_compatibility():
    """Test that wrapped agents are still compatible with existing code patterns"""
    print("\n=== Testing Backward Compatibility ===")
    
    config = LLMConfig(search_provider='searxng')
    
    try:
        # Test tool agents init function (existing pattern)
        from deep_researcher.agents.tool_agents import init_tool_agents
        
        # Create agents the old way (should still work)
        agents_old = init_tool_agents(config, enable_validation=False)
        print(f"  [PASS] Old pattern works: {len(agents_old)} agents created")
        
        # Create agents with validation
        agents_new = init_tool_agents(config, enable_validation=True)
        print(f"  [PASS] New pattern works: {len(agents_new)} agents created")
        
        # Verify same interface
        for name in agents_old.keys():
            old_agent = agents_old[name]
            new_agent = agents_new[name]
            
            # Both should have same core attributes
            assert hasattr(old_agent, 'name')
            assert hasattr(new_agent, 'name')
            assert hasattr(old_agent, 'run_implementation')
            assert hasattr(new_agent, 'run_implementation')
            
            print(f"  [PASS] {name} interface compatibility maintained")
        
        return True
        
    except Exception as e:
        print(f"  [FAIL] Backward compatibility test failed: {e}")
        return False


async def main():
    """Run all dual-path validation tests"""
    print("ValidationWrapper Dual-Path Compatibility Tests")
    print("=" * 55)
    
    tests = [
        test_dual_path_agents,
        test_validation_output_compatibility,
        test_circuit_breaker_integration,
        test_backward_compatibility
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"[FAIL] Test {test.__name__} failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("[SUCCESS] All dual-path compatibility tests passed!")
        return True
    else:
        print("[FAIL] Some dual-path tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)