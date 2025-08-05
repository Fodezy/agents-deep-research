#!/usr/bin/env python3
"""
Integration tests for Runtime Assertion Framework.

Tests the runtime model-role validation system integrated with ResearchRunner,
ensuring it prevents the tool execution pipeline failures discovered during HYBRID-05.
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from deep_researcher.agents.baseclass import ResearchAgent, ResearchRunner
from deep_researcher.agents.utils.runtime_assertions import (
    RuntimeAssertionFramework,
    RuntimeAssertionError,
    ModelRole,
    ModelRoleAssertion,
    AssertionResult,
    AssertionSeverity,
    get_assertion_framework
)
from deep_researcher.agents.utils.model_role_registry import ModelInfo


class TestRuntimeAssertionFramework:
    """Test suite for RuntimeAssertionFramework."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.framework = RuntimeAssertionFramework()
    
    def test_assertion_framework_initialization(self):
        """Test that assertion framework initializes correctly."""
        assert self.framework.registry is not None
        assert self.framework._enabled is True
        assert len(self.framework._assertion_cache) == 0
    
    def test_enable_disable_assertions(self):
        """Test enabling and disabling assertions."""
        self.framework.disable()
        assert self.framework._enabled is False
        
        self.framework.enable()
        assert self.framework._enabled is True
    
    def test_cache_key_generation(self):
        """Test cache key generation for assertions."""
        assertion = ModelRoleAssertion(
            role=ModelRole.TOOL_CALLING,
            model_id="test-model",
            provider="local"
        )
        
        cache_key = self.framework._get_cache_key(assertion)
        assert cache_key == "local:test-model:tool_calling"
    
    async def test_validate_single_assertion_success(self):
        """Test successful single assertion validation."""
        # Mock the registry's methods directly
        with patch.object(self.framework.registry, 'get_model_info') as mock_get_info, \
             patch.object(self.framework.registry, 'validate_model_for_role') as mock_validate:
            
            # Mock model info for valid tool calling model
            mock_model_info = ModelInfo(
                model_id="xlam-model",
                provider="local", 
                tags={'text-generation', 'function-calling'},
                supports_function_calling=True
            )
            mock_get_info.return_value = mock_model_info
            mock_validate.return_value = (True, [])
            
            assertion = ModelRoleAssertion(
                role=ModelRole.TOOL_CALLING,
                model_id="xlam-model", 
                provider="local"
            )
            
            result = await self.framework.validate_single_assertion(assertion)
            
            assert result.passed is True
            assert result.severity == AssertionSeverity.CRITICAL
            assert "valid" in result.message.lower()
            assert result.execution_time_ms > 0
    
    @patch('deep_researcher.agents.utils.runtime_assertions.get_model_registry')
    async def test_validate_single_assertion_failure(self, mock_get_registry):
        """Test failed single assertion validation."""
        # Mock registry
        mock_registry = AsyncMock()
        mock_get_registry.return_value = mock_registry
        
        # Mock model info for invalid tool calling model
        mock_model_info = ModelInfo(
            model_id="basic-model",
            provider="local",
            tags={'text-generation'},
            supports_function_calling=False
        )
        mock_registry.get_model_info.return_value = mock_model_info
        mock_registry.validate_model_for_role.return_value = (False, ["Missing function calling capability"])
        
        assertion = ModelRoleAssertion(
            role=ModelRole.TOOL_CALLING,
            model_id="basic-model",
            provider="local"
        )
        
        result = await self.framework.validate_single_assertion(assertion)
        
        assert result.passed is False
        assert result.severity == AssertionSeverity.CRITICAL
        assert "validation failed" in result.message.lower()
        assert len(result.suggestions) > 0
        assert any("xlam" in suggestion.lower() for suggestion in result.suggestions)
    
    async def test_validate_assertions_parallel(self):
        """Test parallel validation of multiple assertions."""
        assertions = [
            ModelRoleAssertion(ModelRole.PLANNER, "model1", "local"),
            ModelRoleAssertion(ModelRole.TOOL_CALLING, "model2", "local"),
            ModelRoleAssertion(ModelRole.SUMMARISER, "model3", "local")
        ]
        
        with patch.object(self.framework, 'validate_single_assertion') as mock_validate:
            mock_validate.side_effect = [
                AssertionResult(True, AssertionSeverity.CRITICAL, "Valid", 10.0),
                AssertionResult(False, AssertionSeverity.CRITICAL, "Invalid", 15.0),
                AssertionResult(True, AssertionSeverity.WARNING, "Warning", 12.0)
            ]
            
            results = await self.framework.validate_assertions(assertions)
            
            assert len(results) == 3
            assert results[0].passed is True
            assert results[1].passed is False
            assert results[2].passed is True
            assert mock_validate.call_count == 3
    
    async def test_validate_assertions_disabled(self):
        """Test that validation is skipped when disabled."""
        self.framework.disable()
        
        assertions = [ModelRoleAssertion(ModelRole.PLANNER, "model1", "local")]
        results = await self.framework.validate_assertions(assertions)
        
        assert len(results) == 0
    
    def test_check_assertion_results_success(self):
        """Test checking assertion results with all passing."""
        results = [
            AssertionResult(True, AssertionSeverity.CRITICAL, "Valid 1", 10.0),
            AssertionResult(True, AssertionSeverity.WARNING, "Valid 2", 12.0)
        ]
        
        # Should not raise exception
        self.framework.check_assertion_results(results)
    
    def test_check_assertion_results_critical_failure(self):
        """Test checking assertion results with critical failures."""
        results = [
            AssertionResult(True, AssertionSeverity.CRITICAL, "Valid", 10.0),
            AssertionResult(False, AssertionSeverity.CRITICAL, "Critical failure", 15.0, ["Use better model"])
        ]
        
        with pytest.raises(RuntimeAssertionError) as exc_info:
            self.framework.check_assertion_results(results)
        
        assert "Critical model validation failures" in str(exc_info.value)
        assert len(exc_info.value.failed_assertions) == 1
    
    def test_check_assertion_results_warnings_only(self):
        """Test checking assertion results with warnings only."""
        results = [
            AssertionResult(True, AssertionSeverity.CRITICAL, "Valid", 10.0),
            AssertionResult(False, AssertionSeverity.WARNING, "Warning", 15.0)
        ]
        
        # Should not raise exception for warnings
        self.framework.check_assertion_results(results)
    
    async def test_assert_model_role_compatibility_success(self):
        """Test successful model-role compatibility assertion."""
        with patch.object(self.framework, 'validate_single_assertion') as mock_validate:
            mock_validate.return_value = AssertionResult(True, AssertionSeverity.CRITICAL, "Valid", 10.0)
            
            result = await self.framework.assert_model_role_compatibility(
                "xlam-model", "local", ModelRole.TOOL_CALLING
            )
            
            assert result.passed is True
            mock_validate.assert_called_once()
    
    async def test_assert_model_role_compatibility_failure(self):
        """Test failed model-role compatibility assertion."""
        with patch.object(self.framework, 'validate_single_assertion') as mock_validate:
            mock_validate.return_value = AssertionResult(False, AssertionSeverity.CRITICAL, "Invalid", 10.0)
            
            with pytest.raises(RuntimeAssertionError):
                await self.framework.assert_model_role_compatibility(
                    "bad-model", "local", ModelRole.TOOL_CALLING, required=True
                )
    
    async def test_assert_agent_model_compatibility_context_manager(self):
        """Test agent model compatibility context manager."""
        with patch.object(self.framework, 'assert_model_role_compatibility') as mock_assert:
            mock_assert.return_value = AssertionResult(True, AssertionSeverity.CRITICAL, "Valid", 10.0)
            
            async with self.framework.assert_agent_model_compatibility(
                "test-model", "local", ModelRole.PLANNER
            ) as result:
                assert result.passed is True
            
            mock_assert.assert_called_once()
    
    def test_get_assertion_stats(self):
        """Test assertion statistics gathering."""
        # Add some mock cache entries
        self.framework._assertion_cache = {
            "key1": AssertionResult(True, AssertionSeverity.CRITICAL, "Valid", 10.0),
            "key2": AssertionResult(False, AssertionSeverity.CRITICAL, "Invalid", 15.0),
            "key3": AssertionResult(True, AssertionSeverity.WARNING, "Warning", 12.0)
        }
        
        stats = self.framework.get_assertion_stats()
        
        assert stats["total_assertions"] == 3
        assert stats["passed_assertions"] == 2
        assert stats["failed_assertions"] == 1
        assert stats["avg_execution_time_ms"] == (10.0 + 15.0 + 12.0) / 3
        assert stats["enabled"] is True
    
    def test_global_assertion_framework_singleton(self):
        """Test that global assertion framework returns same instance."""
        framework1 = get_assertion_framework()
        framework2 = get_assertion_framework()
        
        assert framework1 is framework2


class TestRuntimeAssertionError:
    """Test suite for RuntimeAssertionError."""
    
    def test_error_initialization(self):
        """Test RuntimeAssertionError initialization."""
        failed_assertion = AssertionResult(
            False, 
            AssertionSeverity.CRITICAL, 
            "Test failure", 
            10.0, 
            ["Use better model"]
        )
        
        error = RuntimeAssertionError("Test error", [failed_assertion])
        
        assert str(error) == "Test error"
        assert len(error.failed_assertions) == 1 
        assert error.failed_assertions[0] == failed_assertion
    
    def test_get_actionable_message(self):
        """Test actionable error message generation."""
        failed_assertion = AssertionResult(
            False,
            AssertionSeverity.CRITICAL,
            "Model validation failed",
            10.0,
            ["Use hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M"]
        )
        
        error = RuntimeAssertionError("Test", [failed_assertion])
        message = error.get_actionable_message()
        
        assert "CRITICAL: Model-Role Validation Failed" in message
        assert "Model validation failed" in message
        assert "hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M" in message
        assert "Resolution Steps:" in message
        assert "HYBRID-05" in message


class TestResearchRunnerIntegration:
    """Test suite for ResearchRunner integration with runtime assertions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear any environment variables that might interfere
        os.environ.pop('DISABLE_RUNTIME_ASSERTIONS', None)
        os.environ.pop('FAIL_ON_ASSERTION_ERRORS', None)
    
    def test_extract_model_info_success(self):
        """Test successful model info extraction from agent."""
        # Create mock agent with model
        mock_model = MagicMock()
        mock_model.model = "test-model"
        mock_model._client._base_url = "http://localhost:11434/v1"
        
        mock_agent = MagicMock()
        mock_agent.model = mock_model
        
        result = ResearchRunner._extract_model_info(mock_agent)
        
        assert result is not None
        assert result == ("test-model", "local")
    
    def test_extract_model_info_openai_provider(self):
        """Test model info extraction with OpenAI provider."""
        mock_model = MagicMock()
        mock_model.model = "gpt-4"
        mock_model._client._base_url = "https://api.openai.com/v1"
        
        mock_agent = MagicMock()
        mock_agent.model = mock_model
        
        result = ResearchRunner._extract_model_info(mock_agent)
        
        assert result == ("gpt-4", "openai")
    
    def test_extract_model_info_failure(self):
        """Test model info extraction failure."""
        mock_agent = MagicMock()
        mock_agent.model = None
        
        result = ResearchRunner._extract_model_info(mock_agent)
        
        assert result is None
    
    @patch('deep_researcher.agents.baseclass.get_assertion_framework')
    async def test_validate_agent_model_compatibility_success(self, mock_get_framework):
        """Test successful agent model compatibility validation."""
        # Mock assertion framework
        mock_framework = AsyncMock()
        mock_get_framework.return_value = mock_framework
        mock_framework.validate_single_assertion.return_value = AssertionResult(
            True, AssertionSeverity.CRITICAL, "Valid", 10.0
        )
        
        # Create mock agent
        mock_agent = ResearchAgent(
            name="TestAgent",
            model=MagicMock(),
            instructions="Test agent"
        )
        mock_agent.model.model = "test-model"
        mock_agent.model._client._base_url = "http://localhost:11434/v1"
        
        # Should not raise exception
        await ResearchRunner._validate_agent_model_compatibility(mock_agent)
        
        mock_framework.validate_single_assertion.assert_called_once()
    
    @patch('deep_researcher.agents.baseclass.get_assertion_framework')
    async def test_validate_agent_model_compatibility_failure(self, mock_get_framework):
        """Test failed agent model compatibility validation."""
        # Mock assertion framework
        mock_framework = AsyncMock()
        mock_get_framework.return_value = mock_framework
        mock_framework.validate_single_assertion.return_value = AssertionResult(
            False, AssertionSeverity.CRITICAL, "Invalid model", 10.0, ["Use better model"]
        )
        
        # Create mock agent
        mock_agent = ResearchAgent(
            name="TestAgent",
            model=MagicMock(),
            instructions="Test agent"
        )
        mock_agent.model.model = "bad-model"
        mock_agent.model._client._base_url = "http://localhost:11434/v1"
        
        with pytest.raises(RuntimeAssertionError):
            await ResearchRunner._validate_agent_model_compatibility(mock_agent)
    
    async def test_validate_agent_disabled_via_env(self):
        """Test validation disabled via environment variable."""
        os.environ['DISABLE_RUNTIME_ASSERTIONS'] = 'true'
        
        mock_agent = ResearchAgent(name="TestAgent", instructions="Test")
        
        # Should not raise exception or do validation
        await ResearchRunner._validate_agent_model_compatibility(mock_agent)
    
    async def test_validate_non_research_agent(self):
        """Test validation skipped for non-ResearchAgent."""
        mock_agent = MagicMock()  # Not a ResearchAgent
        
        # Should not raise exception
        await ResearchRunner._validate_agent_model_compatibility(mock_agent)
    
    def test_agent_role_inference_tool_calling(self):
        """Test agent role inference for tool calling agents."""
        # Agent with tools should be inferred as TOOL_CALLING
        agent = ResearchAgent(
            name="WebSearchAgent",
            instructions="Search the web",
            tools=[MagicMock()]  # Has tools
        )
        
        role = agent.infer_agent_role()
        assert role == ModelRole.TOOL_CALLING
    
    def test_agent_role_inference_by_name(self):
        """Test agent role inference by name patterns."""
        test_cases = [
            ("PlannerAgent", ModelRole.PLANNER),
            ("StrategyAgent", ModelRole.PLANNER),
            ("SummarizerAgent", ModelRole.SUMMARISER),
            ("ExtractorAgent", ModelRole.SUMMARISER),
            ("WriterAgent", ModelRole.WRITER),  
            ("ReportAgent", ModelRole.WRITER),
            ("ToolSelectorAgent", ModelRole.TOOL_CALLING),
            ("SearchAgent", ModelRole.TOOL_CALLING)
        ]
        
        for agent_name, expected_role in test_cases:
            agent = ResearchAgent(name=agent_name, instructions="Test")
            role = agent.infer_agent_role()
            assert role == expected_role, f"Failed for {agent_name}: got {role}, expected {expected_role}"
    
    def test_agent_role_explicit_assignment(self):
        """Test explicit role assignment overrides inference."""
        agent = ResearchAgent(
            name="SearchAgent",  # Would normally infer TOOL_CALLING
            instructions="Test", 
            role=ModelRole.WRITER  # Explicit assignment
        )
        
        role = agent.infer_agent_role()
        assert role == ModelRole.WRITER


class TestIntegrationScenarios:
    """Integration test scenarios for real-world usage."""
    
    @pytest.mark.asyncio
    async def test_tool_calling_agent_validation_pipeline(self):
        """Test the complete validation pipeline for a tool calling agent."""
        from deep_researcher.llm_config import LLMConfig
        
        # Create configuration with known good tool calling model
        config = LLMConfig(
            search_provider="searxng",
            reasoning_model_provider="local",
            reasoning_model="hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M",
            main_model_provider="local",
            main_model="hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M",
            fast_model_provider="local",
            fast_model="hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M"
        )
        
        # Create tool calling agent
        agent = ResearchAgent(
            name="WebSearchAgent",
            model=config.main_model,
            instructions="Search for information",
            tools=[MagicMock()],  # Has tools - should infer TOOL_CALLING role
            role=ModelRole.TOOL_CALLING  # Explicit role assignment
        )
        
        # Test role inference
        inferred_role = agent.infer_agent_role()
        assert inferred_role == ModelRole.TOOL_CALLING
        
        # Test model info extraction  
        model_info = ResearchRunner._extract_model_info(agent)
        assert model_info is not None
        model_id, provider = model_info
        assert "xlam" in model_id.lower()
        assert provider == "local"
    
    @pytest.mark.asyncio 
    async def test_failed_validation_prevents_execution(self):
        """Test that failed validation prevents agent execution."""
        from deep_researcher.llm_config import LLMConfig
        
        # Create configuration with model that will fail tool calling validation
        config = LLMConfig(
            search_provider="searxng",
            reasoning_model_provider="local", 
            reasoning_model="hermes3:8b",  # Not good for tool calling
            main_model_provider="local",
            main_model="hermes3:8b",
            fast_model_provider="local",
            fast_model="hermes3:8b"
        )
        
        # Create tool calling agent with bad model
        agent = ResearchAgent(
            name="WebSearchAgent",
            model=config.main_model,
            instructions="Search for information",
            tools=[MagicMock()],  # Has tools - will infer TOOL_CALLING role
        )
        
        # Mock the base Runner.run to avoid actual execution
        with patch('deep_researcher.agents.baseclass.Runner.run') as mock_run:
            with pytest.raises(RuntimeAssertionError) as exc_info:
                await ResearchRunner.run(starting_agent=agent, input="test query")
            
            # Should not reach actual Runner.run due to validation failure
            mock_run.assert_not_called()
            
            # Check error details
            error = exc_info.value
            assert "Model validation failed" in str(error)
            assert len(error.failed_assertions) > 0
            
            # Check actionable message contains suggestions
            message = error.get_actionable_message()
            assert "hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M" in message
            assert "HYBRID-05" in message


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])