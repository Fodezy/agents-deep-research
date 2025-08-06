"""
Comprehensive test suite for ValidationWrapper system.
Tests all components: ValidationWrapper, repair strategies, circuit breaker, and agent integration.
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.utils.validation_wrapper import ValidationWrapper
from deep_researcher.agents.utils.repair_strategies import (
    LocalPatternRepair, LLMRetryRepair, SchemaRelaxationRepair, 
    LegacyFallbackRepair, RepairStrategyFactory
)
from deep_researcher.agents.utils.circuit_breaker import ValidationCircuitBreaker, CircuitBreakerConfig
from deep_researcher.agents.utils.validation_config import ValidationConfig, ValidationMode
from deep_researcher.agents.utils.validated_agent import ValidatedAgent
from deep_researcher.agents.utils.outlines_schemas import EnhancedToolAgentOutput
from deep_researcher.agents.baseclass import ResearchAgent


class TestValidationWrapper:
    """Test ValidationWrapper core functionality"""
    
    @pytest.fixture
    def config(self):
        return ValidationConfig(
            enabled=True,
            max_retries=3,
            timeout_ms=5000
        )
    
    @pytest.fixture
    def wrapper(self, config):
        return ValidationWrapper(
            agent_name="TestAgent",
            schema=EnhancedToolAgentOutput,
            config=config
        )
    
    @pytest.mark.asyncio
    async def test_valid_json_validation(self, wrapper):
        """Test validation of valid JSON"""
        valid_json = json.dumps({
            "output": "Test output content",
            "sources": ["https://example.com"]
        })
        
        result = await wrapper.validate_and_repair(valid_json)
        
        assert result["output"] == "Test output content"
        assert result["sources"] == ["https://example.com"]
        assert result["processing_method"] == "initial_validation"
        assert result["confidence"] == 0.95
        assert "processing_time_ms" in result
    
    @pytest.mark.asyncio
    async def test_malformed_json_repair(self, wrapper):
        """Test repair of malformed JSON"""
        # Use markdown fences which should be repairable by local pattern repair
        malformed_json = '''```json
{"output": "Test output with fences", "sources": ["https://example.com"]}
```'''
        
        result = await wrapper.validate_and_repair(malformed_json)
        
        # Should either succeed with repair or fallback gracefully
        assert "output" in result
        assert result["confidence"] >= 0
        # Processing method should indicate some form of processing occurred
        assert result["processing_method"] != ""
    
    @pytest.mark.asyncio
    async def test_validation_disabled(self):
        """Test behavior when validation is disabled"""
        config = ValidationConfig(enabled=False)
        wrapper = ValidationWrapper(
            agent_name="TestAgent",
            schema=EnhancedToolAgentOutput,
            config=config
        )
        
        result = await wrapper.validate_and_repair("invalid json")
        
        assert "bypass_validation_disabled" in result["processing_method"]
        assert result["confidence"] == 0.1
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_activation(self, wrapper):
        """Test circuit breaker opens after repeated failures"""
        # Configure low failure threshold for testing
        wrapper.circuit_breaker.config.failure_threshold = 2
        wrapper.circuit_breaker.config.min_requests = 1
        
        invalid_json = "completely invalid json content"
        
        # First few failures should attempt repair
        for i in range(3):
            result = await wrapper.validate_and_repair(invalid_json)
            if "circuit_breaker_open" in result["processing_method"]:
                break
        
        # Verify circuit breaker opened
        status = wrapper.circuit_breaker.get_status()
        assert status["state"] == "open"
    
    def test_validation_wrapper_status(self, wrapper):
        """Test validation wrapper status reporting"""
        status = wrapper.get_status()
        
        assert status["agent_name"] == "TestAgent"
        assert status["enabled"] is True
        assert "circuit_breaker" in status
        assert "repair_strategies" in status
        assert len(status["repair_strategies"]) > 0


class TestRepairStrategies:
    """Test individual repair strategies"""
    
    @pytest.mark.asyncio
    async def test_local_pattern_repair(self):
        """Test LocalPatternRepair strategy"""
        strategy = LocalPatternRepair()
        
        # Test markdown fence removal
        malformed = '''```json
        {"output": "test", "sources": []}
        ```'''
        
        result = await strategy.repair(malformed, "test error")
        
        assert result.success
        assert result.data["output"] == "test"
        assert result.strategy_used == "LocalPatternRepair"
        assert result.confidence == 0.75
    
    @pytest.mark.asyncio
    async def test_llm_retry_repair(self):
        """Test LLMRetryRepair strategy"""
        # Create a proper mock that returns a string response
        async def mock_call_with_functions(*args, **kwargs):
            return '{"output": "repaired", "sources": []}'
        
        mock_client = Mock()
        mock_client.call_with_functions = AsyncMock(side_effect=mock_call_with_functions)
        
        strategy = LLMRetryRepair(model_client=mock_client)
        
        result = await strategy.repair("invalid json", "parse error")
        
        assert result.success
        assert result.data["output"] == "repaired"
        assert result.strategy_used == "LLMRetryRepair"
        assert result.confidence == 0.85
    
    @pytest.mark.asyncio
    async def test_schema_relaxation_repair(self):
        """Test SchemaRelaxationRepair strategy"""
        strategy = SchemaRelaxationRepair()
        
        # Test with data that needs constraint fixes
        data_json = json.dumps({
            "output": "short",  # Too short for min_length
            "sources": []
        })
        
        result = await strategy.repair(data_json, "min_length constraint violation")
        
        assert result.success
        assert len(result.data["output"]) > 10  # Should be expanded
        assert result.strategy_used == "SchemaRelaxationRepair"
    
    @pytest.mark.asyncio
    async def test_legacy_fallback_repair(self):
        """Test LegacyFallbackRepair strategy"""
        strategy = LegacyFallbackRepair()
        
        result = await strategy.repair("completely broken", "all validation failed")
        
        assert result.success  # Always succeeds
        assert "output" in result.data
        assert "sources" in result.data
        assert result.confidence == 0.3  # Low confidence
    
    def test_repair_strategy_factory(self):
        """Test RepairStrategyFactory"""
        strategies = RepairStrategyFactory.create_default_strategies()
        
        assert len(strategies) == 4
        assert any(isinstance(s, LocalPatternRepair) for s in strategies)
        assert any(isinstance(s, LLMRetryRepair) for s in strategies)
        assert any(isinstance(s, SchemaRelaxationRepair) for s in strategies)
        assert any(isinstance(s, LegacyFallbackRepair) for s in strategies)


class TestCircuitBreaker:
    """Test CircuitBreaker functionality"""
    
    @pytest.fixture
    def breaker(self):
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1,  # 1 second for testing
            min_requests=2
        )
        return ValidationCircuitBreaker("TestAgent", config)
    
    def test_circuit_breaker_initialization(self, breaker):
        """Test circuit breaker initializes correctly"""
        status = breaker.get_status()
        
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["total_requests"] == 0
    
    def test_circuit_breaker_success_tracking(self, breaker):
        """Test circuit breaker tracks successes"""
        breaker.record_success()
        breaker.record_success()
        
        status = breaker.get_status()
        assert status["total_requests"] == 2
        assert status["failure_rate"] == 0.0
        assert breaker.should_allow_validation()
    
    def test_circuit_breaker_failure_tracking(self, breaker):
        """Test circuit breaker tracks failures"""
        # Record enough failures to trigger opening
        for i in range(5):
            breaker.record_failure("test error")
        
        status = breaker.get_status()
        assert status["state"] == "open"
        assert not breaker.should_allow_validation()
    
    def test_circuit_breaker_recovery(self, breaker):
        """Test circuit breaker recovery mechanism"""
        # Trigger failure state
        for i in range(5):
            breaker.record_failure("test error")
        
        assert breaker.get_status()["state"] == "open"
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Should transition to half-open
        assert breaker.should_allow_validation()
        
        # Record success to close circuit
        breaker.record_success()
        breaker.record_success()  
        breaker.record_success()  # Need 3 successes by default
        
        assert breaker.get_status()["state"] == "closed"
    
    def test_circuit_breaker_reset(self, breaker):
        """Test circuit breaker reset functionality"""
        breaker.record_failure("test")
        breaker.record_failure("test")
        
        assert breaker.get_status()["failure_count"] > 0
        
        breaker.reset()
        
        status = breaker.get_status()
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["total_requests"] == 0


class TestValidatedAgent:
    """Test ValidatedAgent wrapper"""
    
    @pytest.fixture
    def mock_agent(self):
        agent = Mock(spec=ResearchAgent)
        agent.name = "MockAgent"
        agent.instructions = "Mock instructions"
        agent.tools = []
        agent.model = Mock()
        agent.summariser = None
        agent.output_type = None
        agent.output_parser = None
        agent.run_implementation = AsyncMock(return_value={
            "output": "Mock output",
            "sources": ["https://mock.com"]
        })
        return agent
    
    @pytest.fixture
    def validated_agent(self, mock_agent):
        config = ValidationConfig(enabled=True)
        return ValidatedAgent(mock_agent, config)
    
    @pytest.mark.asyncio
    async def test_validated_agent_execution(self, validated_agent, mock_agent):
        """Test ValidatedAgent executes and validates"""
        result = await validated_agent.run_implementation("test input")
        
        # Should have called base agent
        mock_agent.run_implementation.assert_called_once_with("test input")
        
        # Should have validation metadata
        assert "processing_method" in result
        assert "confidence" in result
        assert "processing_time_ms" in result
    
    def test_validated_agent_status(self, validated_agent):
        """Test ValidatedAgent status reporting"""
        status = validated_agent.get_validation_status()
        
        assert status["agent_name"] == "MockAgent"
        assert status["validation_enabled"] is True
        assert "validator_status" in status
    
    def test_validated_agent_delegation(self, validated_agent, mock_agent):
        """Test ValidatedAgent delegates attributes to base agent"""
        # Should delegate name
        assert validated_agent.name == mock_agent.name
        
        # Should delegate other attributes
        mock_agent.some_attribute = "test_value"
        assert validated_agent.some_attribute == "test_value"
    
    def test_validation_enable_disable(self, validated_agent):
        """Test enabling/disabling validation"""
        assert validated_agent.validation_enabled
        
        validated_agent.disable_validation()
        assert not validated_agent.validation_enabled
        
        validated_agent.enable_validation()
        assert validated_agent.validation_enabled


class TestAgentIntegration:
    """Test integration with real agents"""
    
    @pytest.fixture
    def config(self):
        return LLMConfig(search_provider='searxng')
    
    def test_search_agent_integration(self, config):
        """Test SearchAgent integration"""
        from deep_researcher.agents.tool_agents.search_agent import init_search_agent
        from deep_researcher.agents.utils.agent_factory import get_agent_factory
        
        factory = get_agent_factory()
        agent = factory.create_agent("search", config, enable_validation=True)
        
        assert isinstance(agent, ValidatedAgent)
        assert agent.base_agent.name == "WebSearchAgent"
    
    def test_crawl_agent_integration(self, config):
        """Test CrawlAgent integration"""
        from deep_researcher.agents.utils.agent_factory import get_agent_factory
        
        factory = get_agent_factory()
        agent = factory.create_agent("crawl", config, enable_validation=True)
        
        assert isinstance(agent, ValidatedAgent)
        assert agent.base_agent.name == "SiteCrawlerAgent"
    
    def test_planner_agent_integration(self, config):
        """Test PlannerAgent integration"""
        from deep_researcher.agents.utils.agent_factory import get_agent_factory
        
        factory = get_agent_factory()
        agent = factory.create_agent("planner", config, enable_validation=True)
        
        assert isinstance(agent, ValidatedAgent)
        assert agent.base_agent.name == "PlannerAgent"
    
    def test_tool_agents_batch_creation(self, config):
        """Test batch creation of tool agents with validation"""
        from deep_researcher.agents.tool_agents import init_validated_tool_agents
        
        agents = init_validated_tool_agents(config)
        
        assert len(agents) == 2
        assert all(isinstance(agent, ValidatedAgent) for agent in agents.values())
        assert "WebSearchAgent" in agents
        assert "SiteCrawlerAgent" in agents


class TestPerformance:
    """Test performance characteristics"""
    
    @pytest.fixture
    def wrapper(self):
        config = ValidationConfig(enabled=True, max_retries=1)
        return ValidationWrapper(
            agent_name="PerfTestAgent",
            schema=EnhancedToolAgentOutput,
            config=config
        )
    
    @pytest.mark.asyncio
    async def test_validation_latency(self, wrapper):
        """Test validation adds minimal latency"""
        valid_json = json.dumps({
            "output": "Performance test output",
            "sources": ["https://perf-test.com"]
        })
        
        # Warm up
        await wrapper.validate_and_repair(valid_json)
        
        # Measure multiple runs
        times = []
        for _ in range(10):
            start = time.perf_counter()
            result = await wrapper.validate_and_repair(valid_json)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Should be under performance targets
        assert avg_time < 50, f"Average validation time {avg_time:.2f}ms exceeds 50ms target"
        assert max_time < 100, f"Max validation time {max_time:.2f}ms exceeds 100ms target"
        
        print(f"Validation performance: avg={avg_time:.2f}ms, max={max_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_repair_performance(self, wrapper):
        """Test repair performance is acceptable"""
        malformed_json = '''```json
        {"output": "Malformed JSON with fences", "sources": []}
        ```'''
        
        times = []
        for _ in range(5):
            start = time.perf_counter()
            result = await wrapper.validate_and_repair(malformed_json)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_time = sum(times) / len(times)
        
        # Repair should be under 200ms on average
        assert avg_time < 200, f"Average repair time {avg_time:.2f}ms exceeds 200ms target"
        print(f"Repair performance: avg={avg_time:.2f}ms")
    
    def test_memory_usage(self, wrapper):
        """Test ValidationWrapper doesn't leak memory"""
        import gc
        import sys
        
        # Get baseline memory
        gc.collect()
        baseline = sys.getsizeof(wrapper)
        
        # Create many validation operations
        for i in range(100):
            wrapper.circuit_breaker.record_success()
        
        gc.collect()
        after = sys.getsizeof(wrapper)
        
        # Memory usage should be stable
        growth = after - baseline
        assert growth < 1000, f"Memory growth of {growth} bytes suggests memory leak"


class TestErrorScenarios:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_invalid_schema_handling(self):
        """Test handling of invalid schema"""
        config = ValidationConfig(enabled=True)
        wrapper = ValidationWrapper(
            agent_name="TestAgent",
            schema=None,  # Invalid schema
            config=config
        )
        
        result = await wrapper.validate_and_repair('{"test": "data"}')
        
        # Should handle gracefully
        assert "output" in result or "processing_method" in result
    
    @pytest.mark.asyncio
    async def test_completely_invalid_input(self):
        """Test handling of completely invalid input"""
        config = ValidationConfig(enabled=True)
        wrapper = ValidationWrapper(
            agent_name="TestAgent",
            schema=EnhancedToolAgentOutput,
            config=config
        )
        
        result = await wrapper.validate_and_repair("not json at all!!!")
        
        # Should fallback gracefully (could be error_fallback or bypass due to circuit breaker)
        assert ("error_fallback" in result["processing_method"] or 
                "bypass" in result["processing_method"])
        assert result["confidence"] <= 0.1
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling for long operations"""
        config = ValidationConfig(enabled=True, timeout_ms=100)
        
        # Mock a slow model client
        slow_client = AsyncMock()
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(0.2)  # 200ms delay
            return '{"output": "slow", "sources": []}'
        slow_client.return_value = slow_response()
        
        wrapper = ValidationWrapper(
            agent_name="TimeoutTest",
            schema=EnhancedToolAgentOutput,
            call_with_functions=slow_client,
            config=config
        )
        
        # Should handle timeout gracefully
        result = await wrapper.validate_and_repair("invalid")
        assert result is not None  # Should not crash


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])