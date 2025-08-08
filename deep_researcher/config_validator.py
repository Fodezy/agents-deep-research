#!/usr/bin/env python3
"""
Configuration Validator for 4-Model Architecture Setup.

This module provides comprehensive validation of environment variables and
configuration files to ensure proper 4-model setup, preventing runtime failures
and providing clear error messages with setup instructions.
"""

import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for configuration validation issues."""
    ERROR = "error"      # Must be fixed for system to work
    WARNING = "warning"  # Should be fixed for optimal performance
    INFO = "info"       # Informational/recommendations


class ConfigurationMode(Enum):
    """Configuration modes with different validation requirements."""
    PRODUCTION = "production"      # Strict validation, all models required  
    DEVELOPMENT = "development"    # Relaxed validation, some models optional
    TESTING = "testing"           # Minimal validation, mocks allowed
    LEGACY = "legacy"             # 3-model backward compatibility mode


@dataclass
class ValidationIssue:
    """Represents a configuration validation issue."""
    severity: ValidationSeverity
    variable: str
    message: str
    suggestion: str
    category: str = "general"


@dataclass  
class ModelConfig:
    """Configuration for a specific model role."""
    role_name: str
    provider_var: str
    model_var: str
    required: bool = True
    description: str = ""
    recommended_models: List[str] = None
    
    def __post_init__(self):
        if self.recommended_models is None:
            self.recommended_models = []


class ConfigurationValidator:
    """Validates 4-model architecture configuration."""
    
    def __init__(self, mode: ConfigurationMode = ConfigurationMode.PRODUCTION):
        self.mode = mode
        self.issues: List[ValidationIssue] = []
        self.model_configs = self._initialize_model_configs()
        self.legacy_mapping = self._initialize_legacy_mapping()
        
    def _initialize_model_configs(self) -> Dict[str, ModelConfig]:
        """Initialize the 4-model configuration specifications."""
        return {
            'planner': ModelConfig(
                role_name='planner',
                provider_var='PLANNER_MODEL_PROVIDER',
                model_var='PLANNER_MODEL',
                required=True,
                description='High-level thinking, planning, and analysis model',
                recommended_models=[
                    'hermes3:8b',
                    'phi3:14b-medium-4k-instruct-q4_K_M',
                    'qwen2.5:14b-instruct'
                ]
            ),
            'tool_calling': ModelConfig(
                role_name='tool_calling',
                provider_var='TOOL_CALLING_MODEL_PROVIDER',
                model_var='TOOL_CALLING_MODEL',
                required=True,
                description='Specialized function calling and tool interaction model (CRITICAL)',
                recommended_models=[
                    'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
                    'hf.co/microsoft/Phi-3-mini-4k-instruct-GGUF',
                ]
            ),
            'summariser': ModelConfig(
                role_name='summariser', 
                provider_var='SUMMARISER_MODEL_PROVIDER',
                model_var='SUMMARISER_MODEL',
                required=True,
                description='Fast model for data summarization and structured extraction',
                recommended_models=[
                    'qwen2.5-coder:latest',
                    'hermes3:8b',
                    'llama3.2:latest'
                ]
            ),
            'writer': ModelConfig(
                role_name='writer',
                provider_var='WRITER_MODEL_PROVIDER', 
                model_var='WRITER_MODEL',
                required=True,
                description='Long-form text generation and synthesis model',
                recommended_models=[
                    'qwen3:14b',
                    'llama3.2:latest',
                    'hermes3:8b'
                ]
            )
        }
    
    def _initialize_legacy_mapping(self) -> Dict[str, str]:
        """Initialize mapping from legacy to new variable names."""
        return {
            'REASONING_MODEL_PROVIDER': 'PLANNER_MODEL_PROVIDER',
            'REASONING_MODEL': 'PLANNER_MODEL',
            'MAIN_MODEL_PROVIDER': 'SUMMARISER_MODEL_PROVIDER',
            'MAIN_MODEL': 'SUMMARISER_MODEL',
            'FAST_MODEL_PROVIDER': 'WRITER_MODEL_PROVIDER',
            'FAST_MODEL': 'WRITER_MODEL'
        }
    
    def validate_environment(self, env_vars: Optional[Dict[str, str]] = None) -> bool:
        """Validate environment variable configuration."""
        if env_vars is None:
            env_vars = dict(os.environ)
        
        self.issues.clear()
        
        # Check core infrastructure variables
        self._validate_infrastructure(env_vars)
        
        # Check 4-model architecture
        self._validate_4_model_setup(env_vars)
        
        # Check for legacy configuration and suggest migration
        self._check_legacy_configuration(env_vars)
        
        # Mode-specific validation
        if self.mode == ConfigurationMode.PRODUCTION:
            self._validate_production_requirements(env_vars)
        elif self.mode == ConfigurationMode.DEVELOPMENT:
            self._validate_development_requirements(env_vars)
        
        # Check for common misconfigurations
        self._check_common_issues(env_vars)
        
        # Return True if no errors (warnings/info are OK)
        return not any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)
    
    def _validate_infrastructure(self, env_vars: Dict[str, str]):
        """Validate core infrastructure variables."""
        # Search provider
        search_provider = env_vars.get('SEARCH_PROVIDER')
        if not search_provider:
            self.issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                'SEARCH_PROVIDER',
                'Search provider not configured',
                'Set SEARCH_PROVIDER=searxng or SEARCH_PROVIDER=serper',
                'infrastructure'
            ))
        elif search_provider not in ['searxng', 'serper', 'openai']:
            self.issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                'SEARCH_PROVIDER',
                f'Invalid search provider: {search_provider}',
                'Use one of: searxng, serper, openai',
                'infrastructure'
            ))
        
        # SearXNG configuration
        if search_provider == 'searxng':
            if not env_vars.get('SEARXNG_HOST'):
                self.issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    'SEARXNG_HOST',
                    'SearXNG host not configured, using default',
                    'Set SEARXNG_HOST=http://127.0.0.1:8888 or your SearXNG URL',
                    'infrastructure'
                ))
        
        # Local model URL for Ollama
        if not env_vars.get('LOCAL_MODEL_URL'):
            self.issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                'LOCAL_MODEL_URL',
                'Local model URL not configured, using default',
                'Set LOCAL_MODEL_URL=http://127.0.0.1:11434/v1 for Ollama',
                'infrastructure'
            ))
    
    def _validate_4_model_setup(self, env_vars: Dict[str, str]):
        """Validate 4-model architecture configuration."""
        for role_name, config in self.model_configs.items():
            provider = env_vars.get(config.provider_var)
            model = env_vars.get(config.model_var)
            
            # Check if both provider and model are set
            if not provider and not model:
                # Check if legacy variables exist for migration
                legacy_provider, legacy_model = self._get_legacy_equivalent(config, env_vars)
                
                if legacy_provider and legacy_model:
                    self.issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        config.provider_var,
                        f'{role_name.upper()} model using legacy configuration',
                        f'Migrate: {config.provider_var}={legacy_provider}, {config.model_var}={legacy_model}',
                        'migration'
                    ))
                elif config.required and self.mode != ConfigurationMode.DEVELOPMENT:
                    self.issues.append(ValidationIssue(
                        ValidationSeverity.ERROR,
                        config.provider_var,
                        f'{role_name.upper()} model not configured',
                        f'Set {config.provider_var}=local and {config.model_var}=<model_name>',
                        'model_config'
                    ))
            
            elif provider and not model:
                self.issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    config.model_var,
                    f'{role_name.upper()} model name not specified',
                    f'Set {config.model_var} to a valid model name',
                    'model_config'
                ))
            
            elif not provider and model:
                self.issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    config.provider_var,
                    f'{role_name.upper()} model provider not specified',
                    f'Set {config.provider_var}=local (or openai, anthropic, etc.)',
                    'model_config'
                ))
            
            # Validate provider value
            if provider and provider not in ['local', 'openai', 'anthropic', 'deepseek', 'openrouter', 'gemini']:
                self.issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    config.provider_var,
                    f'Invalid provider for {role_name.upper()}: {provider}',
                    'Use: local, openai, anthropic, deepseek, openrouter, or gemini',
                    'model_config'
                ))
            
            # Special validation for tool calling model (critical for pipeline)
            if role_name == 'tool_calling' and model:
                if not any(recommended in model.lower() for recommended in ['xlam', 'phi-3', 'function', 'phi3']):
                    self.issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        config.model_var,
                        f'Tool calling model may not be optimized for function calling: {model}',
                        'Consider using: hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
                        'performance'
                    ))
    
    def _get_legacy_equivalent(self, config: ModelConfig, env_vars: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
        """Get legacy variable values for a model config."""
        legacy_provider_var = None
        legacy_model_var = None
        
        # Map new variables to legacy equivalents
        if config.provider_var == 'PLANNER_MODEL_PROVIDER':
            legacy_provider_var = 'REASONING_MODEL_PROVIDER'
            legacy_model_var = 'REASONING_MODEL'
        elif config.provider_var == 'SUMMARISER_MODEL_PROVIDER':
            legacy_provider_var = 'MAIN_MODEL_PROVIDER'
            legacy_model_var = 'MAIN_MODEL'
        elif config.provider_var == 'WRITER_MODEL_PROVIDER':
            legacy_provider_var = 'FAST_MODEL_PROVIDER'
            legacy_model_var = 'FAST_MODEL'
        
        if legacy_provider_var and legacy_model_var:
            return env_vars.get(legacy_provider_var), env_vars.get(legacy_model_var)
        
        return None, None
    
    def _check_legacy_configuration(self, env_vars: Dict[str, str]):
        """Check for legacy configuration and suggest migration."""
        legacy_vars_found = []
        
        for legacy_var, new_var in self.legacy_mapping.items():
            if legacy_var in env_vars and new_var not in env_vars:
                legacy_vars_found.append((legacy_var, new_var))
        
        if legacy_vars_found:
            self.issues.append(ValidationIssue(
                ValidationSeverity.INFO,
                'CONFIGURATION',
                f'Found {len(legacy_vars_found)} legacy configuration variables',
                'Run migration utility to update to 4-model architecture: python -m deep_researcher.config_validator --migrate',
                'migration'
            ))
    
    def _validate_production_requirements(self, env_vars: Dict[str, str]):
        """Validate production-specific requirements.""" 
        # In production, all models should be explicitly configured
        for role_name, config in self.model_configs.items():
            if config.required:
                provider = env_vars.get(config.provider_var)
                model = env_vars.get(config.model_var)
                
                if not provider or not model:
                    self.issues.append(ValidationIssue(
                        ValidationSeverity.ERROR,
                        config.provider_var,
                        f'Production mode requires explicit {role_name.upper()} model configuration',
                        f'Set {config.provider_var} and {config.model_var}',
                        'production'
                    ))
    
    def _validate_development_requirements(self, env_vars: Dict[str, str]):
        """Validate development-specific requirements."""
        # In development, only tool calling model is critical
        tool_calling_provider = env_vars.get('TOOL_CALLING_MODEL_PROVIDER')
        tool_calling_model = env_vars.get('TOOL_CALLING_MODEL')
        
        if not tool_calling_provider or not tool_calling_model:
            # Check legacy fallback
            legacy_provider, legacy_model = self._get_legacy_equivalent(
                self.model_configs['tool_calling'], env_vars
            )
            
            if not legacy_provider or not legacy_model:
                self.issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    'TOOL_CALLING_MODEL',
                    'Tool calling model not configured - this may cause pipeline failures',
                    'Set TOOL_CALLING_MODEL_PROVIDER=local and TOOL_CALLING_MODEL=hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
                    'development'
                ))
    
    def _check_common_issues(self, env_vars: Dict[str, str]):
        """Check for common configuration issues."""
        # Check for models assigned to wrong roles
        self._check_model_role_mismatch(env_vars)
        
        # Check for missing API keys when using cloud providers
        self._check_api_keys(env_vars)
        
        # Check for URL format issues
        self._check_url_formats(env_vars)
    
    def _check_model_role_mismatch(self, env_vars: Dict[str, str]):
        """Check for models that might be assigned to wrong roles."""
        # Check if tool calling model is used for other roles (common mistake)
        tool_calling_model = env_vars.get('TOOL_CALLING_MODEL', '').lower()
        
        if 'xlam' in tool_calling_model:
            # This is a function calling model, shouldn't be used for other roles
            for role_name, config in self.model_configs.items():
                if role_name != 'tool_calling':
                    model = env_vars.get(config.model_var, '').lower()
                    if model == tool_calling_model:
                        self.issues.append(ValidationIssue(
                            ValidationSeverity.WARNING,
                            config.model_var,
                            f'Function calling model used for {role_name.upper()} role',
                            f'Use a general purpose model for {role_name.upper()}, reserve XLAM for tool calling',
                            'performance'
                        ))
    
    def _check_api_keys(self, env_vars: Dict[str, str]):
        """Check for missing API keys when using cloud providers."""
        provider_key_map = {
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY',
            'gemini': 'GEMINI_API_KEY'
        }
        
        for role_name, config in self.model_configs.items():
            provider = env_vars.get(config.provider_var)
            if provider and provider in provider_key_map:
                api_key = env_vars.get(provider_key_map[provider])
                if not api_key:
                    self.issues.append(ValidationIssue(
                        ValidationSeverity.ERROR,
                        provider_key_map[provider],
                        f'API key missing for {provider} provider used by {role_name.upper()}',
                        f'Set {provider_key_map[provider]}=<your_api_key>',
                        'api_keys'
                    ))
    
    def _check_url_formats(self, env_vars: Dict[str, str]):
        """Check URL format issues."""
        url_vars = ['LOCAL_MODEL_URL', 'SEARXNG_HOST']
        
        for var in url_vars:
            url = env_vars.get(var)
            if url and not (url.startswith('http://') or url.startswith('https://')):
                self.issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    var,
                    f'URL format may be incorrect: {url}',
                    f'{var} should start with http:// or https://',
                    'format'
                ))
    
    def get_validation_report(self) -> str:
        """Generate a comprehensive validation report."""
        if not self.issues:
            return "[SUCCESS] Configuration validation passed - no issues found!"
        
        lines = [
            "Configuration Validation Report",
            "=" * 40,
            f"Mode: {self.mode.value.upper()}",
            f"Total Issues: {len(self.issues)}",
            ""
        ]
        
        # Group issues by severity
        errors = [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
        info = [i for i in self.issues if i.severity == ValidationSeverity.INFO]
        
        if errors:
            lines.extend([
                f"[ERROR] ERRORS ({len(errors)}) - Must be fixed:",
                "-" * 30
            ])
            for issue in errors:
                lines.extend([
                    f"Variable: {issue.variable}",
                    f"Issue: {issue.message}",
                    f"Fix: {issue.suggestion}",
                    ""
                ])
        
        if warnings:
            lines.extend([
                f"[WARNING] WARNINGS ({len(warnings)}) - Should be fixed:",
                "-" * 35
            ])
            for issue in warnings:
                lines.extend([
                    f"Variable: {issue.variable}",
                    f"Issue: {issue.message}",
                    f"Suggestion: {issue.suggestion}",
                    ""
                ])
        
        if info:
            lines.extend([
                f"[INFO] INFO ({len(info)}) - Recommendations:",
                "-" * 25
            ])
            for issue in info:
                lines.extend([
                    f"Category: {issue.category}",
                    f"Info: {issue.message}",
                    f"Action: {issue.suggestion}",
                    ""
                ])
        
        # Add summary
        lines.extend([
            "Summary:",
            f"  Errors: {len(errors)} (blocking)",
            f"  Warnings: {len(warnings)} (recommended fixes)",
            f"  Info: {len(info)} (suggestions)",
            ""
        ])
        
        if errors:
            lines.append("[FAILED] Configuration validation FAILED - fix errors above")
        else:
            lines.append("[SUCCESS] Configuration validation PASSED - warnings are non-blocking")
        
        return "\n".join(lines)
    
    def generate_migration_script(self, env_file_path: str = ".env") -> str:
        """Generate a migration script to update from 3-model to 4-model configuration."""
        lines = [
            "#!/bin/bash",
            "# Migration script from 3-model to 4-model architecture",
            "# Generated by deep_researcher configuration validator",
            "",
            f"ENV_FILE=\"{env_file_path}\"",
            "",
            "echo \"Migrating to 4-model architecture...\"",
            "",
            "# Backup original file",
            "cp \"$ENV_FILE\" \"$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)\"",
            "",
            "# Add new 4-model variables based on legacy ones",
        ]
        
        # Add migration commands
        for legacy_var, new_var in self.legacy_mapping.items():
            lines.extend([
                f"if grep -q \"^{legacy_var}=\" \"$ENV_FILE\"; then",
                f"    LEGACY_VALUE=$(grep \"^{legacy_var}=\" \"$ENV_FILE\" | cut -d'=' -f2)",
                f"    if ! grep -q \"^{new_var}=\" \"$ENV_FILE\"; then",
                f"        echo \"{new_var}=$LEGACY_VALUE\" >> \"$ENV_FILE\"",
                f"        echo \"Added {new_var} based on {legacy_var}\"",
                f"    fi",
                "fi",
                ""
            ])
        
        lines.extend([
            "echo \"Migration completed!\"",
            "echo \"Please review the updated .env file and remove legacy variables if desired.\"",
            "echo \"Backup saved as: $ENV_FILE.backup.<timestamp>\""
        ])
        
        return "\n".join(lines)


def validate_configuration(mode: ConfigurationMode = ConfigurationMode.PRODUCTION) -> bool:
    """Validate the current environment configuration."""
    validator = ConfigurationValidator(mode)
    is_valid = validator.validate_environment()
    
    print(validator.get_validation_report())
    return is_valid


def main():
    """Command line interface for configuration validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate 4-model architecture configuration")
    parser.add_argument("--mode", choices=['production', 'development', 'testing', 'legacy'],
                       default='production', help="Validation mode")
    parser.add_argument("--migrate", action='store_true', 
                       help="Generate migration script from 3-model to 4-model")
    parser.add_argument("--env-file", default=".env",
                       help="Path to environment file")
    
    args = parser.parse_args()
    
    mode = ConfigurationMode(args.mode)
    validator = ConfigurationValidator(mode)
    
    if args.migrate:
        migration_script = validator.generate_migration_script(args.env_file)
        script_path = "migrate_to_4model.sh"
        
        with open(script_path, 'w') as f:
            f.write(migration_script)
        
        print(f"Migration script generated: {script_path}")
        print("Run with: bash migrate_to_4model.sh")
        return
    
    # Run validation
    is_valid = validator.validate_environment()
    print(validator.get_validation_report())
    
    # Exit with appropriate code
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()