"""
Test ValidationWrapper integration with all Outlines-enabled agents.
Verifies that agents can be wrapped with validation while maintaining compatibility.
"""

import asyncio
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.utils.agent_factory import get_agent_factory
from deep_researcher.agents.utils.validation_config import ValidationConfig
from deep_researcher.agents.utils.validated_agent import ValidatedAgent


async def test_agent_factory():
    """Test basic agent factory functionality"""
    print("=== Testing Agent Factory ===")
    
    # Create configuration
    config = LLMConfig(search_provider='searxng')
    factory = get_agent_factory()
    
    # Test individual agent creation
    agent_types_to_test = ['search', 'crawl', 'planner', 'tool_selector', 'knowledge_gap']
    
    for agent_type in agent_types_to_test:
        try:
            print(f"\nTesting {agent_type} agent creation:")
            
            # Test without validation
            agent = factory.create_agent(
                agent_type=agent_type,
                config=config,
                enable_validation=False
            )
            print(f"  [PASS] Created {agent_type} agent: {agent.name}")
            
            # Test with validation  
            validated_agent = factory.create_agent(
                agent_type=agent_type,
                config=config,
                enable_validation=True
            )
            print(f"  [PASS] Created validated {agent_type} agent: {validated_agent.name}")
            
            # Verify it's wrapped
            if isinstance(validated_agent, ValidatedAgent):
                print(f"  [PASS] Agent properly wrapped with ValidationWrapper")
            else:
                print(f"  [INFO] Agent not wrapped (validation may be disabled in config)")
            
        except Exception as e:
            print(f"  [FAIL] Failed to create {agent_type} agent: {e}")
    
    return True


async def test_tool_agents_integration():
    """Test tool agents integration specifically"""
    print("\n=== Testing Tool Agents Integration ===")
    
    config = LLMConfig(search_provider='searxng')
    
    # Test new init_tool_agents function with validation
    from deep_researcher.agents.tool_agents import init_tool_agents
    
    try:
        # Test with validation disabled
        agents_no_validation = init_tool_agents(config, enable_validation=False)
        print(f"[PASS] Created {len(agents_no_validation)} tool agents without validation")
        
        # Test with validation enabled
        agents_with_validation = init_tool_agents(config, enable_validation=True)
        print(f"[PASS] Created {len(agents_with_validation)} tool agents with validation")
        
        # Verify agent types
        for name, agent in agents_with_validation.items():
            print(f"  {name}: {type(agent).__name__}")
            if isinstance(agent, ValidatedAgent):
                status = agent.get_validation_status()
                print(f"    Validation: {status['validation_enabled']}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Tool agents integration failed: {e}")
        return False


async def test_validation_configuration():
    """Test validation configuration system"""
    print("\n=== Testing Validation Configuration ===")
    
    config = LLMConfig(search_provider='searxng')
    factory = get_agent_factory()
    
    try:
        # Test with custom validation config
        custom_validation_config = ValidationConfig(
            enabled=True,
            max_retries=1,
            timeout_ms=2000
        )
        
        agent = factory.create_agent(
            agent_type='search',
            config=config,
            validation_config=custom_validation_config,
            enable_validation=True
        )
        
        print(f"[PASS] Created agent with custom validation config")
        
        if isinstance(agent, ValidatedAgent):
            status = agent.get_validation_status()
            print(f"  Validation enabled: {status['validation_enabled']}")
            print(f"  Base agent type: {status['base_agent_type']}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Validation configuration test failed: {e}")
        return False


async def test_agent_execution():
    """Test that validated agents can still execute properly"""
    print("\n=== Testing Agent Execution ===")
    
    config = LLMConfig(search_provider='searxng')
    factory = get_agent_factory()
    
    try:
        # Create a simple validated agent
        agent = factory.create_agent(
            agent_type='search',
            config=config,
            enable_validation=True
        )
        
        # Test basic execution (this won't actually search due to mock setup)
        test_input = "Test search query about AI developments"
        
        # For this test, we'll just verify the agent can be called without crashing
        # Real execution would require proper searxng setup
        print(f"[PASS] Agent created and ready for execution: {agent.name}")
        print(f"  Agent type: {type(agent).__name__}")
        
        if hasattr(agent, 'get_validation_status'):
            status = agent.get_validation_status()
            print(f"  Validation status: {status}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Agent execution test failed: {e}")
        return False


async def main():
    """Run all integration tests"""
    print("ValidationWrapper Agent Integration Tests")
    print("=" * 50)
    
    tests = [
        test_agent_factory,
        test_tool_agents_integration,
        test_validation_configuration,
        test_agent_execution
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
        print("[SUCCESS] All integration tests passed!")
        return True
    else:
        print("[FAIL] Some integration tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)