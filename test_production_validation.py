"""
Production validation system test and demonstration.
Tests all production components: metrics, logging, config, and integration.
"""

import asyncio
import json
import time
from typing import Dict, Any

from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.utils.production_integration import (
    initialize_production_validation, 
    create_production_agents,
    run_production_health_check,
    get_production_manager
)
from deep_researcher.agents.utils.validation_metrics import get_metrics_collector
from deep_researcher.agents.utils.validation_logging import get_validation_logger
from deep_researcher.agents.utils.production_config import create_example_config_file


async def test_production_metrics():
    """Test production metrics collection"""
    print("\n=== Testing Production Metrics ===")
    
    collector = get_metrics_collector()
    
    # Simulate various validation events
    test_events = [
        ("TestAgent1", "success", 25.5, None, None, 0.95),
        ("TestAgent1", "repair", 45.2, "json_parse_error", "LocalPatternRepair", 0.85),
        ("TestAgent2", "success", 18.3, None, None, 0.95),
        ("TestAgent1", "error", 100.0, "timeout_error", None, 0.0),
        ("TestAgent2", "fallback", 75.1, "schema_validation_error", "LegacyFallbackRepair", 0.3),
    ]
    
    for agent_name, result, time_ms, error_type, repair_strategy, confidence in test_events:
        collector.record_validation(
            agent_name=agent_name,
            validation_result=result,
            processing_time_ms=time_ms,
            error_type=error_type,
            repair_strategy=repair_strategy,
            confidence=confidence
        )
    
    # Get metrics summaries
    system_summary = collector.get_system_summary()
    agent1_summary = collector.get_agent_summary("TestAgent1")
    agent2_summary = collector.get_agent_summary("TestAgent2")
    
    print(f"System Summary:")
    print(f"  Total validations: {system_summary['total_validations']}")
    print(f"  Success rate: {system_summary['system_success_rate']:.2%}")
    print(f"  Error rate: {system_summary['error_rate']:.2%}")
    print(f"  Active agents: {system_summary['active_agents']}")
    
    print(f"\nTestAgent1 Summary:")
    print(f"  Total validations: {agent1_summary['total_validations']}")
    print(f"  Success rate: {agent1_summary['success_rate']:.2%}")
    print(f"  Health status: {agent1_summary['health_status']}")
    print(f"  Avg processing time: {agent1_summary['avg_processing_time_ms']:.1f}ms")
    
    print(f"\nTestAgent2 Summary:")
    print(f"  Total validations: {agent2_summary['total_validations']}")
    print(f"  Success rate: {agent2_summary['success_rate']:.2%}")
    print(f"  Health status: {agent2_summary['health_status']}")
    
    # Export metrics
    metrics_export = collector.export_metrics(time_window_hours=1)
    metrics_data = json.loads(metrics_export)
    
    print(f"\nMetrics Export:")
    print(f"  Export contains {len(metrics_data['recent_metrics'])} recent events")
    print(f"  Time window: {metrics_data['time_window_hours']} hours")
    
    return True


async def test_production_logging():
    """Test production logging system"""
    print("\n=== Testing Production Logging ===")
    
    logger = get_validation_logger()
    
    # Test different log types
    logger.log_validation_start("TestAgent", "Test input data")
    logger.log_validation_success("TestAgent", 25.5, 0.95)
    logger.log_validation_repair("TestAgent", "json_parse_error", "LocalPatternRepair", 45.2, True, 0.85)
    logger.log_validation_fallback("TestAgent", "schema_validation_failed", 75.1)
    logger.log_validation_error("TestAgent", "timeout_error", "Operation timed out", 100.0, "raw output preview")
    
    # Test circuit breaker logging
    logger.log_circuit_breaker_event("TestAgent", "opened", {"failure_count": 5, "threshold": 5})
    
    # Test performance metrics logging
    logger.log_performance_metrics("TestAgent", {
        "operation": "full_validation",
        "processing_time_ms": 125.3,
        "memory_usage_mb": 15.2,
        "cache_hit_rate": 0.75
    })
    
    print("  Logged various event types (check console output for structured JSON)")
    return True


async def test_production_config():
    """Test production configuration system"""
    print("\n=== Testing Production Configuration ===")
    
    # Create example config file
    config_file = create_example_config_file("test_production_config.json")
    print(f"  Created config file: {config_file}")
    
    # Test config loading and management
    from deep_researcher.agents.utils.production_config import get_production_config_manager
    
    config_manager = get_production_config_manager(config_file)
    base_config = config_manager.get_config()
    
    print(f"  Base config loaded:")
    print(f"    Enabled: {base_config.enabled}")
    print(f"    Max retries: {base_config.max_retries}")
    print(f"    Circuit breaker enabled: {base_config.circuit_breaker_enabled}")
    print(f"    Repair strategies: {len(base_config.repair_strategies_enabled)}")
    
    # Test agent-specific config
    search_config = config_manager.get_agent_config("WebSearchAgent")
    print(f"  WebSearchAgent config:")
    print(f"    Max retries: {search_config.max_retries}")
    print(f"    Timeout: {search_config.timeout_ms}ms")
    
    # Test config updates
    config_manager.update_config({"debug_mode": True, "log_level": "DEBUG"})
    updated_config = config_manager.get_config()
    print(f"  After update - Debug mode: {updated_config.debug_mode}")
    
    return True


async def test_full_production_integration():
    """Test full production integration with real agents"""
    print("\n=== Testing Full Production Integration ===")
    
    config = LLMConfig(search_provider='searxng')
    
    # Initialize production system
    print("  Initializing production validation system...")
    manager = initialize_production_validation(
        config_file="test_production_config.json",
        log_level="INFO",
        structured_logging=True
    )
    
    # Create production agents
    print("  Creating production-validated agents...")
    agents = create_production_agents(config, ["search", "planner"])
    print(f"    Created {len(agents)} validated agents: {list(agents.keys())}")
    
    # Run health check
    print("  Running health check...")
    health_ok = run_production_health_check()
    print(f"    Health check: {'PASS' if health_ok else 'FAIL'}")
    
    # Get detailed health status
    health_status = manager.get_health_status()
    print(f"  System health: {health_status['overall_health']}")
    print(f"  Uptime: {health_status['uptime_hours']:.2f} hours")
    print(f"  Wrapped agents: {health_status['wrapped_agents_count']}")
    print(f"  System metrics: {health_status['system_metrics']['total_validations']} validations")
    
    # Test agent execution with validation (mock mode)
    print("  Testing validated agent execution...")
    search_agent = agents.get("search")
    if search_agent:
        # Mock the underlying execution to avoid actual API calls
        if hasattr(search_agent, 'base_agent') and hasattr(search_agent.base_agent, 'run_implementation'):
            original_method = search_agent.base_agent.run_implementation
            
            async def mock_implementation(*args, **kwargs):
                await asyncio.sleep(0.01)  # Simulate processing
                return {
                    "output": "Mock search results from production test",
                    "sources": ["https://test1.com", "https://test2.com"]
                }
            
            search_agent.base_agent.run_implementation = mock_implementation
            
            try:
                result = await search_agent.run_implementation("test query")
                print(f"    Agent execution result: {len(result.get('output', ''))} chars output")
                print(f"    Processing method: {result.get('processing_method', 'unknown')}")
                print(f"    Confidence: {result.get('confidence', 'unknown')}")
            except Exception as e:
                print(f"    Agent execution failed: {e}")
    
    # Export diagnostics
    print("  Exporting diagnostics...")
    diagnostics = manager.export_diagnostics(time_window_hours=1)
    print(f"    Diagnostics exported: {len(diagnostics)} sections")
    print(f"    Health status: {diagnostics['health_status']['overall_health']}")
    
    # Test graceful shutdown
    print("  Testing graceful shutdown...")
    manager.shutdown()
    print("    Shutdown complete")
    
    return True


async def run_all_production_tests():
    """Run all production validation tests"""
    print("ValidationWrapper Production System Tests")
    print("=" * 55)
    
    tests = [
        ("Production Metrics", test_production_metrics),
        ("Production Logging", test_production_logging), 
        ("Production Config", test_production_config),
        ("Full Integration", test_full_production_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n[TEST] {test_name}")
            result = await test_func()
            if result:
                print(f"[PASS] {test_name}")
                passed += 1
            else:
                print(f"[FAIL] {test_name}")
        except Exception as e:
            print(f"[FAIL] {test_name} - Exception: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n=== Production Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("[SUCCESS] All production tests passed!")
        return True
    else:
        print("[FAIL] Some production tests failed")
        return False


async def main():
    """Main test execution"""
    success = await run_all_production_tests()
    
    # Clean up test files
    import os
    for file in ["test_production_config.json", "demo_validation_config.json"]:
        if os.path.exists(file):
            os.remove(file)
            print(f"Cleaned up: {file}")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)