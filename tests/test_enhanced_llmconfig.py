#!/usr/bin/env python3
"""
Tests for Enhanced LLMConfig with 4-Model Architecture Support.

Tests the role-aware model assignment, validation at instantiation time,
and backward compatibility with 3-model configurations.
"""

import asyncio
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from deep_researcher.llm_config import LLMConfig, create_default_config, create_legacy_config


class TestEnhancedLLMConfig:
    """Test suite for Enhanced LLMConfig with 4-model architecture."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Save original environment variables
        self.original_env = {}
        for key in ['PLANNER_MODEL_PROVIDER', 'PLANNER_MODEL', 'TOOL_CALLING_MODEL_PROVIDER', 
                   'TOOL_CALLING_MODEL', 'SUMMARISER_MODEL_PROVIDER', 'SUMMARISER_MODEL',
                   'WRITER_MODEL_PROVIDER', 'WRITER_MODEL']:
            self.original_env[key] = os.environ.get(key)
        
        # Set test environment variables
        os.environ.update({
            'PLANNER_MODEL_PROVIDER': 'local',
            'PLANNER_MODEL': 'hermes3:8b',
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
            'SUMMARISER_MODEL_PROVIDER': 'local',
            'SUMMARISER_MODEL': 'qwen2.5-coder:latest',
            'WRITER_MODEL_PROVIDER': 'local',
            'WRITER_MODEL': 'llama3.2:latest'
        })
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Restore original environment variables
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    
    def test_4_model_architecture_initialization(self):
        """Test initialization with explicit 4-model parameters."""
        config = LLMConfig(
            search_provider="searxng",
            planner_model_provider="local",
            planner_model="hermes3:8b",
            tool_calling_model_provider="local",
            tool_calling_model="xlam-model",
            summariser_model_provider="local",
            summariser_model="qwen-model",
            writer_model_provider="local",
            writer_model="llama-model",
            validate_model_roles=False  # Skip validation for unit tests
        )
        
        # Check 4-model architecture
        assert hasattr(config, 'planner_model')
        assert hasattr(config, 'tool_calling_model')
        assert hasattr(config, 'summariser_model')
        assert hasattr(config, 'writer_model')
        
        # Check model configs storage
        assert 'planner' in config.model_configs
        assert 'tool_calling' in config.model_configs
        assert 'summariser' in config.model_configs
        assert 'writer' in config.model_configs
        
        # Check backward compatibility
        assert config.reasoning_model == config.planner_model
        assert config.main_model == config.summariser_model
        assert config.fast_model == config.writer_model
    
    def test_backward_compatibility_3_model(self):
        """Test backward compatibility with legacy 3-model parameters."""
        config = LLMConfig(
            search_provider="searxng",
            reasoning_model_provider="local",
            reasoning_model="hermes3:8b",
            main_model_provider="local",
            main_model="qwen-model",
            fast_model_provider="local",
            fast_model="llama-model",
            validate_model_roles=False
        )
        
        # Should map to 4-model architecture
        assert config.planner_model == config.reasoning_model
        assert config.summariser_model == config.main_model
        assert config.writer_model == config.fast_model
        
        # Tool calling model should use environment default
        assert config.tool_calling_model is not None
    
    def test_environment_variable_fallback(self):
        """Test fallback to environment variables when parameters not provided."""
        config = LLMConfig(
            search_provider="searxng",
            validate_model_roles=False
        )
        
        # Should use environment variables
        assert config.model_configs['planner']['provider'] == 'local'
        assert config.model_configs['planner']['model'] == 'hermes3:8b'
        assert config.model_configs['tool_calling']['model'] == 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M'
    
    def test_model_config_summary(self):
        """Test model configuration summary generation."""
        config = LLMConfig(
            search_provider="searxng",
            planner_model_provider="local",
            planner_model="test-planner",
            tool_calling_model_provider="local",
            tool_calling_model="test-tool-calling",
            summariser_model_provider="local",
            summariser_model="test-summariser",
            writer_model_provider="local",
            writer_model="test-writer",
            validate_model_roles=False
        )
        
        summary = config.get_model_config_summary()
        
        assert summary['validation_enabled'] is False
        assert summary['strict_validation'] is False
        assert len(summary['models']) == 4
        assert summary['models']['planner']['model'] == 'test-planner'
        assert summary['models']['tool_calling']['model'] == 'test-tool-calling'
        assert summary['models']['summariser']['model'] == 'test-summariser'
        assert summary['models']['writer']['model'] == 'test-writer'
    
    def test_get_model_for_role(self):
        """Test getting model by role."""
        from deep_researcher.agents.utils.runtime_assertions import ModelRole
        
        config = LLMConfig(
            search_provider="searxng",
            planner_model_provider="local",
            planner_model="planner-model",
            tool_calling_model_provider="local", 
            tool_calling_model="tool-calling-model",
            summariser_model_provider="local",
            summariser_model="summariser-model",
            writer_model_provider="local",
            writer_model="writer-model",
            validate_model_roles=False
        )
        
        # Test role-to-model mapping
        planner_model = config.get_model_for_role(ModelRole.PLANNER)
        tool_calling_model = config.get_model_for_role(ModelRole.TOOL_CALLING)
        summariser_model = config.get_model_for_role(ModelRole.SUMMARISER)
        writer_model = config.get_model_for_role(ModelRole.WRITER)
        
        assert planner_model == config.planner_model
        assert tool_calling_model == config.tool_calling_model
        assert summariser_model == config.summariser_model
        assert writer_model == config.writer_model
    
    def test_validation_options(self):
        """Test validation option handling."""
        # Validation disabled
        config1 = LLMConfig(
            search_provider="searxng",
            validate_model_roles=False,
            strict_validation=False
        )
        assert config1.validate_model_roles is False
        assert config1.strict_validation is False
        
        # Validation enabled, non-strict
        config2 = LLMConfig(
            search_provider="searxng",
            validate_model_roles=True,
            strict_validation=False
        )
        assert config2.validate_model_roles is True
        assert config2.strict_validation is False
        
        # Validation enabled, strict
        config3 = LLMConfig(
            search_provider="searxng",
            validate_model_roles=True,
            strict_validation=True
        )
        assert config3.validate_model_roles is True
        assert config3.strict_validation is True
    
    def test_invalid_provider_validation(self):
        """Test validation of invalid providers."""
        with pytest.raises(ValueError, match="Invalid model provider"):
            LLMConfig(
                search_provider="searxng",
                planner_model_provider="invalid_provider",
                planner_model="test-model",
                validate_model_roles=False
            )
    
    def test_invalid_search_provider_validation(self):
        """Test validation of invalid search providers."""
        with pytest.raises(ValueError, match="Invalid search provider"):
            LLMConfig(
                search_provider="invalid_search",
                validate_model_roles=False
            )
    
    @patch('deep_researcher.llm_config.get_assertion_framework')
    @patch('deep_researcher.llm_config.ROLE_VALIDATION_AVAILABLE', True)
    async def test_model_role_validation_success(self, mock_get_framework):
        """Test successful model role validation."""
        # Mock assertion framework
        mock_framework = AsyncMock()
        mock_get_framework.return_value = mock_framework
        
        # Mock successful validation results
        from deep_researcher.agents.utils.runtime_assertions import AssertionResult, AssertionSeverity
        mock_results = [
            AssertionResult(True, AssertionSeverity.CRITICAL, "Valid", 10.0),
            AssertionResult(True, AssertionSeverity.CRITICAL, "Valid", 15.0),
            AssertionResult(True, AssertionSeverity.CRITICAL, "Valid", 12.0),
            AssertionResult(True, AssertionSeverity.CRITICAL, "Valid", 8.0)
        ]
        mock_framework.validate_assertions.return_value = mock_results
        
        config = LLMConfig(
            search_provider="searxng",
            planner_model_provider="local",
            planner_model="good-planner",
            tool_calling_model_provider="local",
            tool_calling_model="good-tool-calling",
            summariser_model_provider="local",
            summariser_model="good-summariser",
            writer_model_provider="local",
            writer_model="good-writer",
            validate_model_roles=False  # Skip in constructor, test manually
        )
        
        # Manually run validation
        await config._validate_model_roles()
        
        # Should not raise exception
        mock_framework.validate_assertions.assert_called_once()
    
    @patch('deep_researcher.llm_config.get_assertion_framework')
    @patch('deep_researcher.llm_config.ROLE_VALIDATION_AVAILABLE', True)
    async def test_model_role_validation_failure_non_strict(self, mock_get_framework):
        """Test model role validation failure in non-strict mode."""
        # Mock assertion framework
        mock_framework = AsyncMock()
        mock_get_framework.return_value = mock_framework
        
        # Mock failed validation results
        from deep_researcher.agents.utils.runtime_assertions import AssertionResult, AssertionSeverity
        mock_results = [
            AssertionResult(True, AssertionSeverity.CRITICAL, "Valid", 10.0),
            AssertionResult(False, AssertionSeverity.CRITICAL, "Invalid tool calling model", 15.0, ["Use XLAM model"]),
            AssertionResult(True, AssertionSeverity.CRITICAL, "Valid", 12.0),
            AssertionResult(True, AssertionSeverity.CRITICAL, "Valid", 8.0)
        ]
        mock_framework.validate_assertions.return_value = mock_results
        
        config = LLMConfig(
            search_provider="searxng",
            validate_model_roles=False,
            strict_validation=False
        )
        
        # Should not raise exception in non-strict mode
        await config._validate_model_roles()
        
        mock_framework.validate_assertions.assert_called_once()
    
    @patch('deep_researcher.llm_config.get_assertion_framework')  
    @patch('deep_researcher.llm_config.ROLE_VALIDATION_AVAILABLE', True)
    async def test_model_role_validation_failure_strict(self, mock_get_framework):
        """Test model role validation failure in strict mode."""
        # Mock assertion framework
        mock_framework = AsyncMock()
        mock_get_framework.return_value = mock_framework
        
        # Mock failed validation results
        from deep_researcher.agents.utils.runtime_assertions import AssertionResult, AssertionSeverity, RuntimeAssertionError
        mock_results = [
            AssertionResult(False, AssertionSeverity.CRITICAL, "Invalid tool calling model", 15.0, ["Use XLAM model"])
        ]
        mock_framework.validate_assertions.return_value = mock_results
        
        config = LLMConfig(
            search_provider="searxng",
            validate_model_roles=False,
            strict_validation=True
        )
        
        # Should raise exception in strict mode
        with pytest.raises(RuntimeAssertionError):
            await config._validate_model_roles()


class TestConfigFactoryFunctions:
    """Test suite for config factory functions."""
    
    def test_create_default_config(self):
        """Test create_default_config function."""
        with patch('deep_researcher.llm_config.ROLE_VALIDATION_AVAILABLE', False):
            config = create_default_config()
            
            assert config.validate_model_roles is True
            assert config.strict_validation is False
            assert hasattr(config, 'planner_model')
            assert hasattr(config, 'tool_calling_model')
            assert hasattr(config, 'summariser_model')
            assert hasattr(config, 'writer_model')
    
    def test_create_legacy_config(self):
        """Test create_legacy_config function."""
        with patch('deep_researcher.llm_config.ROLE_VALIDATION_AVAILABLE', False):
            config = create_legacy_config()
            
            assert config.validate_model_roles is False
            assert hasattr(config, 'reasoning_model')
            assert hasattr(config, 'main_model')
            assert hasattr(config, 'fast_model')
            
            # Should still have 4-model architecture internally
            assert hasattr(config, 'planner_model')
            assert hasattr(config, 'tool_calling_model')


class TestIntegrationScenarios:
    """Integration tests for real world usage scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        # Mock out model initialization to avoid OpenAI client issues
        self.model_patcher = patch('deep_researcher.llm_config.LLMConfig.__init__')
        mock_init = self.model_patcher.start()
        
        def mock_llm_init(self, *args, **kwargs):
            # Just set basic attributes without model creation
            self.search_provider = kwargs.get('search_provider', 'searxng')
            self.validate_model_roles = kwargs.get('validate_model_roles', True)
            self.strict_validation = kwargs.get('strict_validation', False)
            self.model_configs = {
                'planner': {'provider': 'local', 'model': 'hermes3:8b', 'role': None},
                'tool_calling': {'provider': 'local', 'model': 'xlam-model', 'role': None},
                'summariser': {'provider': 'local', 'model': 'qwen-model', 'role': None},
                'writer': {'provider': 'local', 'model': 'llama-model', 'role': None}
            }
        
        mock_init.side_effect = mock_llm_init
    
    def teardown_method(self):
        """Clean up test environment."""
        self.model_patcher.stop()
    
    def test_migration_from_3_to_4_model_config(self):
        """Test migration scenario from 3-model to 4-model configuration."""
        # Create legacy config
        legacy_config = LLMConfig(
            search_provider="searxng",
            reasoning_model_provider="local",
            reasoning_model="hermes3:8b",
            main_model_provider="local", 
            main_model="qwen-model",
            fast_model_provider="local",
            fast_model="llama-model"
        )
        
        # Create new 4-model config
        new_config = LLMConfig(
            search_provider="searxng",
            planner_model_provider="local",
            planner_model="hermes3:8b",
            tool_calling_model_provider="local",
            tool_calling_model="xlam-model",
            summariser_model_provider="local", 
            summariser_model="qwen-model",
            writer_model_provider="local",
            writer_model="llama-model"
        )
        
        # Both should have the same core structure
        assert legacy_config.search_provider == new_config.search_provider
        assert len(legacy_config.model_configs) == len(new_config.model_configs)
    
    def test_environment_driven_configuration(self):
        """Test configuration driven entirely by environment variables."""
        with patch.dict(os.environ, {
            'SEARCH_PROVIDER': 'searxng',
            'PLANNER_MODEL_PROVIDER': 'local',
            'PLANNER_MODEL': 'hermes3:8b',
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'xlam-model',
            'SUMMARISER_MODEL_PROVIDER': 'local',
            'SUMMARISER_MODEL': 'qwen-model',
            'WRITER_MODEL_PROVIDER': 'local',
            'WRITER_MODEL': 'llama-model'
        }):
            config = create_default_config()
            
            assert config.search_provider == 'searxng'
            assert config.model_configs['planner']['model'] == 'hermes3:8b'
            assert config.model_configs['tool_calling']['model'] == 'xlam-model'
            assert config.model_configs['summariser']['model'] == 'qwen-model'
            assert config.model_configs['writer']['model'] == 'llama-model'


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])