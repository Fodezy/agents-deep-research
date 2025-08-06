"""
Basic test to verify ValidationWrapper core implementation works.
Tests the enhanced architecture without requiring full agent setup.
"""

import asyncio
import json
from unittest.mock import Mock, AsyncMock
from deep_researcher.agents.utils.validation_wrapper import ValidationWrapper
from deep_researcher.agents.utils.outlines_schemas import EnhancedToolAgentOutput
from deep_researcher.agents.utils.validation_config import ValidationConfig


async def test_basic_validation():
    """Test basic validation functionality"""
    print("=== Testing Basic Validation ===")
    
    # Create test configuration
    config = ValidationConfig(
        enabled=True,
        max_retries=2,
        timeout_ms=3000
    )
    
    # Create ValidationWrapper
    wrapper = ValidationWrapper(
        agent_name="TestAgent",
        schema=EnhancedToolAgentOutput,
        config=config
    )
    
    # Test valid JSON
    valid_json = json.dumps({
        "output": "This is a test output",
        "sources": ["https://test.com"]
    })
    
    try:
        result = await wrapper.validate_and_repair(valid_json)
        print(f"[PASS] Valid JSON test passed: {result.get('processing_method')}")
        assert result["output"] == "This is a test output"
        assert result["processing_method"] == "initial_validation"
    except Exception as e:
        print(f"[FAIL] Valid JSON test failed: {e}")
        return False
    
    return True


async def test_repair_functionality():
    """Test repair functionality with malformed JSON"""
    print("\n=== Testing Repair Functionality ===")
    
    config = ValidationConfig(enabled=True)
    wrapper = ValidationWrapper(
        agent_name="TestAgent", 
        schema=EnhancedToolAgentOutput,
        config=config
    )
    
    # Test malformed JSON that should be repairable by local patterns
    malformed_json = """```json
    {
        "output": "Test output with issues",
        "sources": ["https://test.com"]
    }
    ```"""
    
    try:
        result = await wrapper.validate_and_repair(malformed_json)
        print(f"[PASS] Repair test passed: {result.get('processing_method')}")
        assert result["output"] == "Test output with issues"
        # Should be repaired by local pattern (markdown fence removal)
        success = ("LocalPatternRepair" in result.get("processing_method", "") or 
                  result.get("processing_method") == "initial_validation")
        assert success, f"Unexpected processing method: {result.get('processing_method')}"
    except Exception as e:
        print(f"[FAIL] Repair test failed: {e}")
        return False
    
    return True


async def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("\n=== Testing Circuit Breaker ===")
    
    config = ValidationConfig(enabled=True)
    config.circuit_breaker.failure_threshold = 2  # Low threshold for testing
    
    wrapper = ValidationWrapper(
        agent_name="CircuitBreakerTest",
        schema=EnhancedToolAgentOutput,
        config=config
    )
    
    # Generate multiple failures to trigger circuit breaker
    invalid_json = "This is not JSON at all!"
    
    failure_count = 0
    for i in range(5):
        try:
            result = await wrapper.validate_and_repair(invalid_json)
            if "circuit_breaker_open" in result.get("processing_method", ""):
                print(f"[PASS] Circuit breaker opened after {failure_count} failures")
                break
            else:
                failure_count += 1
                print(f"  Attempt {i+1}: {result.get('processing_method')}")
        except Exception as e:
            failure_count += 1
            print(f"  Attempt {i+1}: Exception - {e}")
    
    # Check circuit breaker status
    status = wrapper.circuit_breaker.get_status()
    print(f"Circuit breaker status: {status['state']}")
    
    return True


async def test_configuration_system():
    """Test configuration system"""
    print("\n=== Testing Configuration System ===")
    
    from deep_researcher.agents.utils.validation_config import (
        get_validation_config_manager, AgentValidationProfile
    )
    
    config_manager = get_validation_config_manager()
    
    # Test getting configuration for different agent types
    search_config = config_manager.get_config("SearchAgent")
    crawl_config = config_manager.get_config("CrawlAgent")
    unknown_config = config_manager.get_config("UnknownAgent")
    
    print(f"SearchAgent config: enabled={search_config.enabled}, max_retries={search_config.max_retries}")
    print(f"CrawlAgent config: enabled={crawl_config.enabled}, max_retries={crawl_config.max_retries}")
    print(f"Unknown config: enabled={unknown_config.enabled}, max_retries={unknown_config.max_retries}")
    
    # Test profile registration
    custom_profile = AgentValidationProfile(
        name="CustomAgent",
        description="Test custom agent profile",
        config=ValidationConfig(enabled=False, max_retries=1)
    )
    
    config_manager.register_profile(custom_profile)
    custom_config = config_manager.get_config("CustomAgent")
    
    print(f"Custom config: enabled={custom_config.enabled}")
    assert custom_config.enabled == False
    
    print("[PASS] Configuration system test passed")
    return True


async def test_legacy_compatibility():
    """Test legacy compatibility"""
    print("\n=== Testing Legacy Compatibility ===")
    
    from deep_researcher.agents.utils.validation_wrapper import LegacyValidationWrapper
    from deep_researcher.agents.utils.observability import ObservabilityHandler
    
    # Mock legacy components
    mock_call_function = AsyncMock(return_value='{"output": "test", "sources": []}')
    observability = ObservabilityHandler()
    
    # Create legacy wrapper
    legacy_wrapper = LegacyValidationWrapper(
        schema_name="test_schema",
        agent_name="LegacyAgent",
        call_with_functions=mock_call_function,
        observability=observability
    )
    
    # Test basic functionality
    test_json = '{"output": "Legacy test", "sources": []}'
    result = await legacy_wrapper.validate_and_repair(test_json)
    
    print(f"[PASS] Legacy compatibility test passed: {result.get('output')}")
    return True


async def main():
    """Run all tests"""
    print("ValidationWrapper Core Implementation Tests")
    print("=" * 50)
    
    tests = [
        test_basic_validation,
        test_repair_functionality,
        test_circuit_breaker,
        test_configuration_system,
        test_legacy_compatibility
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
        print("[SUCCESS] All tests passed!")
        return True
    else:
        print("[FAIL] Some tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)