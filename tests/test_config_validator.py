#!/usr/bin/env python3
"""
Test suite for Configuration Validator.

Tests the comprehensive 4-model architecture validation including:
- Environment variable validation
- Migration from 3-model to 4-model
- Production vs development mode differences
- Error detection and reporting
"""

import pytest
import os
import tempfile
from unittest.mock import patch
from deep_researcher.config_validator import (
    ConfigurationValidator, 
    ConfigurationMode, 
    ValidationSeverity,
    ValidationIssue
)


class TestConfigurationValidator:
    """Test the ConfigurationValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigurationValidator(ConfigurationMode.PRODUCTION)
        
    def test_complete_4model_config_validation(self):
        """Test validation with complete 4-model configuration."""
        env_vars = {
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
        
        is_valid = self.validator.validate_environment(env_vars)
        assert is_valid == True
        assert len(self.validator.issues) == 0
        
    def test_missing_infrastructure_validation(self):
        """Test validation with missing infrastructure configuration."""
        env_vars = {}
        
        is_valid = self.validator.validate_environment(env_vars)
        assert is_valid == False
        
        # Should have error for missing search provider
        errors = [i for i in self.validator.issues if i.severity == ValidationSeverity.ERROR]
        search_errors = [e for e in errors if e.variable == 'SEARCH_PROVIDER']
        assert len(search_errors) == 1
        assert 'Search provider not configured' in search_errors[0].message
        
    def test_legacy_configuration_detection(self):
        """Test detection and migration suggestions for legacy configuration."""
        env_vars = {
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
        
        is_valid = self.validator.validate_environment(env_vars)
        
        # Should have warnings for legacy configuration
        warnings = [i for i in self.validator.issues if i.severity == ValidationSeverity.WARNING]
        legacy_warnings = [w for w in warnings if 'legacy configuration' in w.message]
        assert len(legacy_warnings) == 3  # PLANNER, SUMMARISER, WRITER
        
        # Should have info about migration
        info = [i for i in self.validator.issues if i.severity == ValidationSeverity.INFO]
        migration_info = [i for i in info if 'legacy configuration variables' in i.message]
        assert len(migration_info) == 1
        
    def test_invalid_provider_validation(self):
        """Test validation with invalid provider values."""
        env_vars = {
            'SEARCH_PROVIDER': 'invalid_provider',
            'PLANNER_MODEL_PROVIDER': 'invalid_provider',
            'PLANNER_MODEL': 'hermes3:8b',
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
            'SUMMARISER_MODEL_PROVIDER': 'local',
            'SUMMARISER_MODEL': 'qwen2.5-coder:latest',
            'WRITER_MODEL_PROVIDER': 'local',
            'WRITER_MODEL': 'llama3.2:latest'
        }
        
        is_valid = self.validator.validate_environment(env_vars)
        assert is_valid == False
        
        errors = [i for i in self.validator.issues if i.severity == ValidationSeverity.ERROR]
        
        search_errors = [e for e in errors if e.variable == 'SEARCH_PROVIDER']
        assert len(search_errors) == 1
        assert 'Invalid search provider' in search_errors[0].message
        
        provider_errors = [e for e in errors if e.variable == 'PLANNER_MODEL_PROVIDER']
        assert len(provider_errors) == 1
        assert 'Invalid provider' in provider_errors[0].message
        
    def test_missing_api_keys_validation(self):
        """Test validation of missing API keys for cloud providers."""
        env_vars = {
            'SEARCH_PROVIDER': 'searxng',
            'PLANNER_MODEL_PROVIDER': 'openai',  # Cloud provider without API key
            'PLANNER_MODEL': 'gpt-4',
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
            'SUMMARISER_MODEL_PROVIDER': 'local',
            'SUMMARISER_MODEL': 'qwen2.5-coder:latest',
            'WRITER_MODEL_PROVIDER': 'local',
            'WRITER_MODEL': 'llama3.2:latest'
        }
        
        is_valid = self.validator.validate_environment(env_vars)
        assert is_valid == False
        
        errors = [i for i in self.validator.issues if i.severity == ValidationSeverity.ERROR]
        api_key_errors = [e for e in errors if e.variable == 'OPENAI_API_KEY']
        assert len(api_key_errors) == 1
        assert 'API key missing' in api_key_errors[0].message
        
    def test_development_mode_relaxed_validation(self):
        """Test relaxed validation in development mode."""
        dev_validator = ConfigurationValidator(ConfigurationMode.DEVELOPMENT)
        
        env_vars = {
            'SEARCH_PROVIDER': 'searxng',
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M'
            # Missing other models - should be OK in dev mode
        }
        
        is_valid = dev_validator.validate_environment(env_vars)
        # Should pass in development mode even with missing models
        assert is_valid == True or len([i for i in dev_validator.issues if i.severity == ValidationSeverity.ERROR]) == 0
        
    def test_tool_calling_model_warning(self):
        """Test warning for suboptimal tool calling model."""
        env_vars = {
            'SEARCH_PROVIDER': 'searxng',
            'PLANNER_MODEL_PROVIDER': 'local',
            'PLANNER_MODEL': 'hermes3:8b',
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'hermes3:8b',  # Not optimized for tool calling
            'SUMMARISER_MODEL_PROVIDER': 'local',
            'SUMMARISER_MODEL': 'qwen2.5-coder:latest',
            'WRITER_MODEL_PROVIDER': 'local',
            'WRITER_MODEL': 'llama3.2:latest'
        }
        
        is_valid = self.validator.validate_environment(env_vars)
        
        warnings = [i for i in self.validator.issues if i.severity == ValidationSeverity.WARNING]
        tool_warnings = [w for w in warnings if 'may not be optimized for function calling' in w.message]
        assert len(tool_warnings) == 1
        
    def test_url_format_validation(self):
        """Test URL format validation."""
        env_vars = {
            'SEARCH_PROVIDER': 'searxng',
            'SEARXNG_HOST': 'invalid-url-format',  # Missing http://
            'LOCAL_MODEL_URL': 'also-invalid',     # Missing http://
            'PLANNER_MODEL_PROVIDER': 'local',
            'PLANNER_MODEL': 'hermes3:8b',
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
            'SUMMARISER_MODEL_PROVIDER': 'local',
            'SUMMARISER_MODEL': 'qwen2.5-coder:latest',
            'WRITER_MODEL_PROVIDER': 'local',
            'WRITER_MODEL': 'llama3.2:latest'
        }
        
        is_valid = self.validator.validate_environment(env_vars)
        
        warnings = [i for i in self.validator.issues if i.severity == ValidationSeverity.WARNING]
        url_warnings = [w for w in warnings if 'URL format may be incorrect' in w.message]
        assert len(url_warnings) == 2  # SEARXNG_HOST and LOCAL_MODEL_URL
        
    def test_validation_report_generation(self):
        """Test generation of validation report."""
        env_vars = {
            'SEARCH_PROVIDER': 'invalid',  # Error
            'LOCAL_MODEL_URL': 'bad-url',  # Warning
            'PLANNER_MODEL_PROVIDER': 'local',
            'PLANNER_MODEL': 'hermes3:8b',
            'TOOL_CALLING_MODEL_PROVIDER': 'local', 
            'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
            'SUMMARISER_MODEL_PROVIDER': 'local',
            'SUMMARISER_MODEL': 'qwen2.5-coder:latest',
            'WRITER_MODEL_PROVIDER': 'local',
            'WRITER_MODEL': 'llama3.2:latest'
        }
        
        self.validator.validate_environment(env_vars)
        report = self.validator.get_validation_report()
        
        assert 'Configuration Validation Report' in report
        assert 'Mode: PRODUCTION' in report
        assert '[ERROR]' in report
        assert '[WARNING]' in report
        assert '[FAILED]' in report
        
    def test_migration_script_generation(self):
        """Test generation of migration script."""
        script = self.validator.generate_migration_script('.env')
        
        assert '#!/bin/bash' in script
        assert 'Migration script from 3-model to 4-model' in script
        assert 'REASONING_MODEL_PROVIDER' in script
        assert 'PLANNER_MODEL_PROVIDER' in script
        assert 'backup' in script.lower()
        
    def test_model_role_mismatch_detection(self):
        """Test detection of models assigned to wrong roles."""
        env_vars = {
            'SEARCH_PROVIDER': 'searxng',
            'PLANNER_MODEL_PROVIDER': 'local',
            'PLANNER_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',  # Function calling model used for planning
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
            'SUMMARISER_MODEL_PROVIDER': 'local',
            'SUMMARISER_MODEL': 'qwen2.5-coder:latest',
            'WRITER_MODEL_PROVIDER': 'local',
            'WRITER_MODEL': 'llama3.2:latest'
        }
        
        is_valid = self.validator.validate_environment(env_vars)
        
        warnings = [i for i in self.validator.issues if i.severity == ValidationSeverity.WARNING]
        role_warnings = [w for w in warnings if 'Function calling model used for' in w.message]
        assert len(role_warnings) == 1
        

class TestConfigurationModes:
    """Test different configuration validation modes."""
    
    def test_production_mode_strict_requirements(self):
        """Test that production mode requires all models."""
        validator = ConfigurationValidator(ConfigurationMode.PRODUCTION)
        
        env_vars = {
            'SEARCH_PROVIDER': 'searxng',
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M'
            # Missing other required models
        }
        
        is_valid = validator.validate_environment(env_vars)
        assert is_valid == False
        
        errors = [i for i in validator.issues if i.severity == ValidationSeverity.ERROR]
        production_errors = [e for e in errors if 'Production mode requires explicit' in e.message]
        assert len(production_errors) >= 3  # PLANNER, SUMMARISER, WRITER
        
    def test_development_mode_relaxed_requirements(self):
        """Test that development mode is more permissive."""
        validator = ConfigurationValidator(ConfigurationMode.DEVELOPMENT)
        
        env_vars = {
            'SEARCH_PROVIDER': 'searxng',
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M'
            # Missing other models - should be OK in dev mode
        }
        
        is_valid = validator.validate_environment(env_vars)
        
        # In development mode, missing non-tool-calling models should not cause errors
        errors = [i for i in validator.issues if i.severity == ValidationSeverity.ERROR]
        model_errors = [e for e in errors if 'model not configured' in e.message.lower()]
        # Should have fewer errors than production mode
        assert len(model_errors) < 3
        
    def test_legacy_mode_backward_compatibility(self):
        """Test legacy mode for backward compatibility."""
        validator = ConfigurationValidator(ConfigurationMode.LEGACY)
        
        env_vars = {
            'SEARCH_PROVIDER': 'searxng',
            'REASONING_MODEL_PROVIDER': 'local',
            'REASONING_MODEL': 'hermes3:8b',
            'MAIN_MODEL_PROVIDER': 'local', 
            'MAIN_MODEL': 'qwen2.5-coder:latest',
            'FAST_MODEL_PROVIDER': 'local',
            'FAST_MODEL': 'llama3.2:latest'
        }
        
        is_valid = validator.validate_environment(env_vars)
        
        # Legacy mode should be more permissive of old configuration
        errors = [i for i in validator.issues if i.severity == ValidationSeverity.ERROR]
        legacy_blocking_errors = [e for e in errors if 'legacy' not in e.message.lower()]
        # Should have minimal blocking errors for valid legacy config
        assert len(legacy_blocking_errors) <= 1  # Maybe missing tool calling model


class TestEnvironmentFileHandling:
    """Test handling of .env files and environment variables."""
    
    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        validator = ConfigurationValidator(ConfigurationMode.PRODUCTION)
        
        # Test with os.environ (default behavior)
        with patch.dict(os.environ, {
            'SEARCH_PROVIDER': 'searxng',
            'PLANNER_MODEL_PROVIDER': 'local',
            'PLANNER_MODEL': 'hermes3:8b',
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
            'SUMMARISER_MODEL_PROVIDER': 'local',
            'SUMMARISER_MODEL': 'qwen2.5-coder:latest',
            'WRITER_MODEL_PROVIDER': 'local',
            'WRITER_MODEL': 'llama3.2:latest'
        }):
            is_valid = validator.validate_environment()
            assert is_valid == True
            
    def test_custom_env_vars_dict(self):
        """Test validation with custom environment variables dictionary."""
        validator = ConfigurationValidator(ConfigurationMode.PRODUCTION)
        
        custom_env = {
            'SEARCH_PROVIDER': 'searxng',
            'PLANNER_MODEL_PROVIDER': 'local',
            'PLANNER_MODEL': 'hermes3:8b',
            'TOOL_CALLING_MODEL_PROVIDER': 'local',
            'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
            'SUMMARISER_MODEL_PROVIDER': 'local',
            'SUMMARISER_MODEL': 'qwen2.5-coder:latest',
            'WRITER_MODEL_PROVIDER': 'local',
            'WRITER_MODEL': 'llama3.2:latest'
        }
        
        is_valid = validator.validate_environment(custom_env)
        assert is_valid == True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])