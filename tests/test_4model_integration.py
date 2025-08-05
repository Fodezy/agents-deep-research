#!/usr/bin/env python3
"""
HYBRID-08.5: Integration Testing & Documentation
Comprehensive integration tests for 4-model architecture with existing agents.

Tests that all structured agents (ToolSelector, Planner, KnowledgeGap) work
properly with the validated 4-model setup and runtime assertions.
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from deep_researcher.llm_config import LLMConfig, create_default_config
from deep_researcher.agents.utils.model_role_registry import ModelRole
from deep_researcher.agents.utils.runtime_assertions import RuntimeAssertionFramework
from deep_researcher.config_validator import ConfigurationValidator, ConfigurationMode


@pytest.fixture
def valid_4model_config():
    """Create a valid 4-model configuration for testing."""
    return {
        'SEARCH_PROVIDER': 'searxng',
        'SEARXNG_HOST': 'http://127.0.0.1:8888',
        'LOCAL_MODEL_URL': 'http://127.0.0.1:11434/v1',
        'PLANNER_MODEL_PROVIDER': 'local',
        'PLANNER_MODEL': 'hermes3:8b',
        'TOOL_CALLING_MODEL_PROVIDER': 'local',
        'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
        'SUMMARISER_MODEL_PROVIDER': 'local',
        'SUMMARISER_MODEL': 'qwen2.5-coder:latest',
        'WRITER_MODEL_PROVIDER': 'local',
        'WRITER_MODEL': 'llama3.2:latest'
    }


@pytest.fixture
def mock_llm_config(valid_4model_config):
    """Create mock LLMConfig with 4-model setup."""
    with patch.dict('os.environ', valid_4model_config):
        config = create_default_config()
        
        # Mock model instances
        config.planner_model = MagicMock()
        config.tool_calling_model = MagicMock()
        config.summariser_model = MagicMock()
        config.writer_model = MagicMock()
        
        return config


class TestConfigurationValidation:
    """Test configuration validation with 4-model architecture."""
    
    def test_4model_configuration_validates(self, valid_4model_config):
        """Test that complete 4-model configuration passes validation."""
        validator = ConfigurationValidator(ConfigurationMode.PRODUCTION)
        is_valid = validator.validate_environment(valid_4model_config)
        
        assert is_valid == True
        assert len([i for i in validator.issues if i.severity.value == 'error']) == 0
        
        report = validator.get_validation_report()
        assert '[SUCCESS]' in report
    
    def test_legacy_configuration_migration(self):
        """Test legacy 3-model configuration migration."""
        legacy_config = {
            'SEARCH_PROVIDER': 'searxng',
            'REASONING_MODEL_PROVIDER': 'local',
            'REASONING_MODEL': 'hermes3:8b',
            'MAIN_MODEL_PROVIDER': 'local',
            'MAIN_MODEL': 'qwen2.5-coder:latest',
            'FAST_MODEL_PROVIDER': 'local',
            'FAST_MODEL': 'llama3.2:latest',
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M'
        }
        
        validator = ConfigurationValidator(ConfigurationMode.PRODUCTION)
        is_valid = validator.validate_environment(legacy_config)
        
        # Should detect legacy configuration and suggest migration
        warnings = [i for i in validator.issues if i.severity.value == 'warning']
        legacy_warnings = [w for w in warnings if 'legacy configuration' in w.message]
        assert len(legacy_warnings) == 3  # PLANNER, SUMMARISER, WRITER
    
    def test_development_mode_relaxed_validation(self):
        """Test development mode allows partial configuration."""
        dev_config = {
            'SEARCH_PROVIDER': 'searxng',
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M'
            # Missing other models - should be OK in dev mode
        }
        
        validator = ConfigurationValidator(ConfigurationMode.DEVELOPMENT)
        is_valid = validator.validate_environment(dev_config)
        
        # Should have fewer errors than production mode
        errors = [i for i in validator.issues if i.severity.value == 'error']
        assert len(errors) <= 1  # Only critical errors should block


class TestModelRoleValidation:
    """Test model role validation and assignments."""
    
    @pytest.fixture
    def mock_registry(self):
        """Mock model registry for testing."""
        with patch('deep_researcher.agents.utils.runtime_assertions.get_model_registry') as mock_get_registry:
            registry = MagicMock()
            # validate_model_for_role is synchronous
            registry.validate_model_for_role.return_value = (True, [])
            # get_model_info is async
            registry.get_model_info = AsyncMock(return_value={
                'model_name': 'test-model',
                'tags': {'text-generation'},
                'role_compatibility': ['planner', 'summariser', 'writer']
            })
            mock_get_registry.return_value = registry
            yield registry
    
    @pytest.mark.asyncio
    async def test_runtime_assertions_framework(self, mock_registry):
        """Test runtime assertion framework integration."""
        framework = RuntimeAssertionFramework()
        
        # Test model-role compatibility validation
        result = await framework.assert_model_role_compatibility(
            model_id='hermes3:8b',
            role=ModelRole.PLANNER,
            provider='local'
        )
        
        assert result.passed == True
        mock_registry.validate_model_for_role.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_performance_overhead_acceptable(self, mock_registry):
        """Test that role validation adds <100ms overhead."""
        framework = RuntimeAssertionFramework()
        
        # Measure validation time
        start_time = time.time()
        for _ in range(10):  # Test multiple validations
            await framework.assert_model_role_compatibility(
                model_id='hermes3:8b',
                role=ModelRole.PLANNER,
                provider='local'
            )
        end_time = time.time()
        
        avg_time_ms = ((end_time - start_time) / 10) * 1000
        assert avg_time_ms < 100, f"Validation took {avg_time_ms:.2f}ms, should be <100ms"


class TestAgentIntegration:
    """Test integration with existing agents."""
    
    @pytest.fixture
    def mock_agents(self):
        """Mock agent implementations for testing."""
        agents = {}
        
        # Mock ToolSelector Agent
        tool_selector = MagicMock()
        tool_selector.name = "ToolSelectorAgent"
        tool_selector.role = ModelRole.TOOL_CALLING
        agents['tool_selector'] = tool_selector
        
        # Mock Planner Agent
        planner = MagicMock()
        planner.name = "PlannerAgent"
        planner.role = ModelRole.PLANNER
        agents['planner'] = planner
        
        # Mock KnowledgeGap Agent
        knowledge_gap = MagicMock()
        knowledge_gap.name = "KnowledgeGapAgent"
        knowledge_gap.role = ModelRole.PLANNER
        agents['knowledge_gap'] = knowledge_gap
        
        # Mock Search Agent (uses SUMMARISER)
        search_agent = MagicMock()
        search_agent.name = "WebSearchAgent"
        search_agent.role = ModelRole.SUMMARISER
        agents['search'] = search_agent
        
        # Mock Writer Agent
        writer = MagicMock()
        writer.name = "WriterAgent"
        writer.role = ModelRole.WRITER
        agents['writer'] = writer
        
        return agents
    
    def test_tool_selector_integration(self, mock_llm_config, mock_agents):
        """Test ToolSelector integration with 4-model architecture."""
        from deep_researcher.agents.tool_selector_agent import init_tool_selector_agent
        
        with patch('deep_researcher.agents.utils.runtime_assertions.RuntimeAssertionFramework'):
            # Skip runtime assertions for integration tests
            
            agent = init_tool_selector_agent(mock_llm_config)
            
            assert agent.name == "ToolSelectorAgent"
            assert hasattr(agent, 'model')
            
            # Should be using TOOL_CALLING model
            expected_model = mock_llm_config.get_model_for_role(ModelRole.TOOL_CALLING)
            assert agent.model == expected_model
    
    def test_planner_integration(self, mock_llm_config):
        """Test Planner agent integration with 4-model architecture."""
        from deep_researcher.agents.planner_agent import init_planner_agent
        
        with patch('deep_researcher.agents.utils.runtime_assertions.RuntimeAssertionFramework'):
            # Skip runtime assertions for integration tests
            
            agent = init_planner_agent(mock_llm_config)
            
            assert agent.name == "PlannerAgent"
            
            # Should be using PLANNER model
            expected_model = mock_llm_config.get_model_for_role(ModelRole.PLANNER)
            assert agent.model == expected_model
    
    def test_knowledge_gap_integration(self, mock_llm_config):
        """Test KnowledgeGap agent integration with 4-model architecture."""
        from deep_researcher.agents.knowledge_gap_agent import init_knowledge_gap_agent
        
        with patch('deep_researcher.agents.utils.runtime_assertions.RuntimeAssertionFramework'):
            # Skip runtime assertions for integration tests
            
            agent = init_knowledge_gap_agent(mock_llm_config)
            
            assert agent.name == "KnowledgeGapAgent"
            
            # Should be using PLANNER model (for analysis)
            expected_model = mock_llm_config.get_model_for_role(ModelRole.PLANNER)
            assert agent.model == expected_model
    
    def test_search_agent_integration(self, mock_llm_config):
        """Test WebSearch agent integration with SUMMARISER role."""
        from deep_researcher.agents.tool_agents.search_agent import init_search_agent
        
        with patch('deep_researcher.agents.utils.runtime_assertions.RuntimeAssertionFramework'):
            # Skip runtime assertions for integration tests
            
            agent = init_search_agent(mock_llm_config)
            
            assert agent.name == "WebSearchAgent"
            
            # Should be using SUMMARISER model
            expected_model = mock_llm_config.get_model_for_role(ModelRole.SUMMARISER)
            assert agent.model == expected_model
    
    def test_writer_agent_integration(self, mock_llm_config):
        """Test Writer agent integration with WRITER role."""
        from deep_researcher.agents.writer_agent import init_writer_agent
        
        with patch('deep_researcher.agents.utils.runtime_assertions.RuntimeAssertionFramework'):
            # Skip runtime assertions for integration tests
            
            agent = init_writer_agent(mock_llm_config)
            
            assert agent.name == "WriterAgent"
            
            # Should be using WRITER model
            expected_model = mock_llm_config.get_model_for_role(ModelRole.WRITER)
            assert agent.model == expected_model


class TestErrorHandling:
    """Test error handling and fail-fast behavior."""
    
    def test_model_role_mismatch_detection(self, valid_4model_config):
        """Test detection of model-role mismatches."""
        # Create config with wrong model for tool calling
        invalid_config = valid_4model_config.copy()
        invalid_config['TOOL_CALLING_MODEL'] = 'hermes3:8b'  # Not optimized for function calling
        
        validator = ConfigurationValidator(ConfigurationMode.PRODUCTION)
        is_valid = validator.validate_environment(invalid_config)
        
        warnings = [i for i in validator.issues if i.severity.value == 'warning']
        tool_warnings = [w for w in warnings if 'may not be optimized for function calling' in w.message]
        assert len(tool_warnings) == 1
    
    def test_missing_api_keys_detection(self, valid_4model_config):
        """Test detection of missing API keys for cloud providers."""
        cloud_config = valid_4model_config.copy()
        cloud_config['PLANNER_MODEL_PROVIDER'] = 'openai'
        cloud_config['PLANNER_MODEL'] = 'gpt-4'
        # Missing OPENAI_API_KEY
        
        validator = ConfigurationValidator(ConfigurationMode.PRODUCTION)
        is_valid = validator.validate_environment(cloud_config)
        
        assert is_valid == False
        errors = [i for i in validator.issues if i.severity.value == 'error']
        api_errors = [e for e in errors if 'API key missing' in e.message]
        assert len(api_errors) == 1
    
    @pytest.mark.asyncio
    async def test_runtime_assertion_failure(self):
        """Test runtime assertion failure handling."""
        with patch('deep_researcher.agents.utils.runtime_assertions.get_model_registry') as mock_get_registry:
            registry = MagicMock()
            # Return validation failure
            registry.validate_model_for_role.return_value = (False, ["Model not suitable for role"])
            registry.get_model_info = AsyncMock(return_value={
                'model_name': 'unsuitable-model',
                'tags': {'text-generation'},
                'role_compatibility': []
            })
            mock_get_registry.return_value = registry
            
            framework = RuntimeAssertionFramework()
            
            # For critical assertions, the framework should raise an exception
            with pytest.raises(Exception) as exc_info:
                await framework.assert_model_role_compatibility(
                    model_id='unsuitable-model',
                    role=ModelRole.TOOL_CALLING,
                    provider='local',
                    required=True  # Critical assertion
                )
            
            # Should contain the validation failure message
            assert "Model not suitable for role" in str(exc_info.value)


class TestPerformanceBenchmarks:
    """Performance benchmarks for 4-model architecture."""
    
    def test_configuration_validation_performance(self, valid_4model_config):
        """Test that configuration validation is fast (<50ms)."""
        validator = ConfigurationValidator(ConfigurationMode.PRODUCTION)
        
        start_time = time.time()
        for _ in range(10):
            validator.validate_environment(valid_4model_config)
        end_time = time.time()
        
        avg_time_ms = ((end_time - start_time) / 10) * 1000
        assert avg_time_ms < 50, f"Validation took {avg_time_ms:.2f}ms, should be <50ms"
    
    @pytest.mark.asyncio
    async def test_model_role_registry_performance(self):
        """Test that model registry operations are fast."""
        with patch('deep_researcher.agents.utils.runtime_assertions.get_model_registry') as mock_get_registry:
            registry = MagicMock()
            registry.validate_model_for_role.return_value = (True, [])
            registry.get_model_info = AsyncMock(return_value={
                'model_name': 'hermes3:8b',
                'tags': {'text-generation'},
                'role_compatibility': ['planner']
            })
            mock_get_registry.return_value = registry
            
            framework = RuntimeAssertionFramework()
            
            start_time = time.time()
            for _ in range(20):  # Reduced iterations for async operations
                await framework.assert_model_role_compatibility(
                    model_id='hermes3:8b',
                    role=ModelRole.PLANNER,
                    provider='local'
                )
            end_time = time.time()
            
            avg_time_ms = ((end_time - start_time) / 20) * 1000
            assert avg_time_ms < 10, f"Registry lookup took {avg_time_ms:.2f}ms, should be <10ms"
    
    def test_llm_config_instantiation_performance(self, valid_4model_config):
        """Test that LLMConfig instantiation without validation is fast."""
        with patch.dict('os.environ', valid_4model_config):
            start_time = time.time()
            for _ in range(5):
                # Create config without model role validation for performance test
                config = LLMConfig(
                    search_provider='searxng',
                    planner_model_provider='local',
                    planner_model='hermes3:8b',
                    tool_calling_model_provider='local',
                    tool_calling_model='hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
                    summariser_model_provider='local',
                    summariser_model='qwen2.5-coder:latest',
                    writer_model_provider='local',
                    writer_model='llama3.2:latest',
                    validate_model_roles=False  # Skip validation for performance test
                )
            end_time = time.time()
            
            avg_time_ms = ((end_time - start_time) / 5) * 1000
            assert avg_time_ms < 1500, f"LLMConfig creation took {avg_time_ms:.2f}ms, should be <1500ms"


class TestBackwardCompatibility:
    """Test backward compatibility with existing systems."""
    
    def test_legacy_3model_config_still_works(self):
        """Test that legacy 3-model configuration still works."""
        legacy_env = {
            'SEARCH_PROVIDER': 'searxng',
            'REASONING_MODEL_PROVIDER': 'local',
            'REASONING_MODEL': 'hermes3:8b',
            'MAIN_MODEL_PROVIDER': 'local',
            'MAIN_MODEL': 'qwen2.5-coder:latest',
            'FAST_MODEL_PROVIDER': 'local',
            'FAST_MODEL': 'llama3.2:latest'
        }
        
        with patch.dict('os.environ', legacy_env):
            # Should not raise exception
            config = LLMConfig(
                search_provider='searxng',
                reasoning_model_provider='local',
                reasoning_model='hermes3:8b',
                main_model_provider='local',
                main_model='qwen2.5-coder:latest',
                fast_model_provider='local',
                fast_model='llama3.2:latest',
                validate_model_roles=False
            )
            
            assert config.reasoning_model is not None
            assert config.main_model is not None
            assert config.fast_model is not None
    
    def test_existing_agent_initialization_unchanged(self, mock_llm_config):
        """Test that existing agent initialization patterns still work."""
        # Test that agents can still be initialized with basic LLMConfig
        from deep_researcher.agents.thinking_agent import init_thinking_agent
        
        agent = init_thinking_agent(mock_llm_config)
        
        assert agent.name == "ThinkingAgent"
        assert hasattr(agent, 'model')
        assert hasattr(agent, 'instructions')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])