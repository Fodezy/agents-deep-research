"""
Production configuration management for ValidationWrapper system.
Provides environment-specific settings, feature flags, and runtime configuration.
"""

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationProductionConfig:
    """Production configuration for ValidationWrapper system"""
    
    # Core validation settings
    enabled: bool = True
    max_retries: int = 3
    timeout_ms: int = 30000  # 30 seconds
    
    # Performance settings
    max_concurrent_validations: int = 10
    cache_validation_results: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 30
    min_requests_for_circuit_breaker: int = 5
    
    # Repair strategy settings
    repair_strategies_enabled: List[str] = field(default_factory=lambda: [
        "LocalPatternRepair",
        "LLMRetryRepair", 
        "SchemaRelaxationRepair",
        "LegacyFallbackRepair"
    ])
    llm_retry_enabled: bool = True
    schema_relaxation_enabled: bool = True
    
    # Monitoring and observability
    metrics_collection_enabled: bool = True
    structured_logging_enabled: bool = True
    log_level: str = "INFO"
    export_metrics_interval_minutes: int = 60
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "success_rate_threshold": 0.95,
        "max_processing_time_ms": 1000,
        "max_error_rate": 0.05
    })
    
    # Resource limits
    max_memory_mb: int = 500
    max_validation_queue_size: int = 1000
    
    # Debug and development
    debug_mode: bool = False
    save_failed_validations: bool = False
    validation_debug_dir: str = "/tmp/validation_debug"
    
    # Agent-specific overrides
    agent_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Feature flags
    feature_flags: Dict[str, bool] = field(default_factory=lambda: {
        "enhanced_error_reporting": True,
        "adaptive_retry_timing": True,
        "validation_analytics": True,
        "predictive_repair": False  # Experimental
    })


class ProductionConfigManager:
    """Manages production configuration with environment-based overrides"""
    
    def __init__(self, config_file: Optional[str] = None, env_prefix: str = "VALIDATION_"):
        self.env_prefix = env_prefix
        self.config_file = config_file
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file and environment"""
        # Start with defaults
        self._config = ValidationProductionConfig()
        
        # Override with config file if provided
        if self.config_file and Path(self.config_file).exists():
            self._load_from_file(self.config_file)
        
        # Override with environment variables
        self._load_from_environment()
        
        # Validate configuration
        self._validate_config()
    
    def _load_from_file(self, config_file: str):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
            
            for key, value in file_config.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
                else:
                    print(f"Warning: Unknown config key in file: {key}")
        
        except Exception as e:
            print(f"Error loading config file {config_file}: {e}")
    
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        env_mappings = {
            f"{self.env_prefix}ENABLED": ("enabled", bool),
            f"{self.env_prefix}MAX_RETRIES": ("max_retries", int),
            f"{self.env_prefix}TIMEOUT_MS": ("timeout_ms", int),
            f"{self.env_prefix}MAX_CONCURRENT": ("max_concurrent_validations", int),
            f"{self.env_prefix}CACHE_ENABLED": ("cache_validation_results", bool),
            f"{self.env_prefix}CACHE_TTL": ("cache_ttl_seconds", int),
            f"{self.env_prefix}CIRCUIT_BREAKER_ENABLED": ("circuit_breaker_enabled", bool),
            f"{self.env_prefix}FAILURE_THRESHOLD": ("failure_threshold", int),
            f"{self.env_prefix}RECOVERY_TIMEOUT": ("recovery_timeout_seconds", int),
            f"{self.env_prefix}LOG_LEVEL": ("log_level", str),
            f"{self.env_prefix}METRICS_ENABLED": ("metrics_collection_enabled", bool),
            f"{self.env_prefix}STRUCTURED_LOGGING": ("structured_logging_enabled", bool),
            f"{self.env_prefix}DEBUG_MODE": ("debug_mode", bool),
            f"{self.env_prefix}MAX_MEMORY_MB": ("max_memory_mb", int),
            f"{self.env_prefix}SAVE_FAILED": ("save_failed_validations", bool),
        }
        
        for env_var, (attr_name, type_func) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    if type_func == bool:
                        parsed_value = value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        parsed_value = type_func(value)
                    
                    setattr(self._config, attr_name, parsed_value)
                except ValueError as e:
                    print(f"Warning: Invalid value for {env_var}: {value} ({e})")
        
        # Handle complex environment variables
        self._load_complex_env_vars()
    
    def _load_complex_env_vars(self):
        """Load complex configuration from environment variables"""
        # Repair strategies
        strategies_env = os.getenv(f"{self.env_prefix}REPAIR_STRATEGIES")
        if strategies_env:
            try:
                strategies = [s.strip() for s in strategies_env.split(',')]
                self._config.repair_strategies_enabled = strategies
            except Exception as e:
                print(f"Warning: Invalid repair strategies config: {e}")
        
        # Alert thresholds
        thresholds_env = os.getenv(f"{self.env_prefix}ALERT_THRESHOLDS")
        if thresholds_env:
            try:
                thresholds = json.loads(thresholds_env)
                self._config.alert_thresholds.update(thresholds)
            except Exception as e:
                print(f"Warning: Invalid alert thresholds config: {e}")
        
        # Feature flags
        features_env = os.getenv(f"{self.env_prefix}FEATURE_FLAGS")
        if features_env:
            try:
                features = json.loads(features_env)
                self._config.feature_flags.update(features)
            except Exception as e:
                print(f"Warning: Invalid feature flags config: {e}")
    
    def _validate_config(self):
        """Validate configuration values"""
        # Ensure positive values
        assert self._config.max_retries > 0, "max_retries must be positive"
        assert self._config.timeout_ms > 0, "timeout_ms must be positive"
        assert self._config.max_concurrent_validations > 0, "max_concurrent_validations must be positive"
        assert self._config.failure_threshold > 0, "failure_threshold must be positive"
        
        # Ensure reasonable ranges
        assert 0 <= self._config.alert_thresholds["success_rate_threshold"] <= 1.0, "success_rate_threshold must be between 0 and 1"
        assert 0 <= self._config.alert_thresholds["max_error_rate"] <= 1.0, "max_error_rate must be between 0 and 1"
        
        # Ensure log level is valid
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert self._config.log_level.upper() in valid_log_levels, f"log_level must be one of {valid_log_levels}"
        
        print(f"ValidationWrapper production configuration validated successfully")
    
    def get_config(self) -> ValidationProductionConfig:
        """Get the current configuration"""
        return self._config
    
    def get_agent_config(self, agent_name: str) -> ValidationProductionConfig:
        """Get configuration with agent-specific overrides applied"""
        if agent_name not in self._config.agent_overrides:
            return self._config
        
        # Create a copy of the base config
        agent_config = ValidationProductionConfig(**self._config.__dict__)
        
        # Apply agent-specific overrides
        overrides = self._config.agent_overrides[agent_name]
        for key, value in overrides.items():
            if hasattr(agent_config, key):
                setattr(agent_config, key, value)
            else:
                print(f"Warning: Unknown agent override key: {key}")
        
        return agent_config
    
    def update_config(self, updates: Dict[str, Any]):
        """Update configuration at runtime"""
        for key, value in updates.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
                print(f"Updated config: {key} = {value}")
            else:
                print(f"Warning: Unknown config key: {key}")
        
        # Re-validate after updates
        self._validate_config()
    
    def export_config(self) -> Dict[str, Any]:
        """Export current configuration as dictionary"""
        config_dict = {}
        for field in self._config.__dataclass_fields__:
            value = getattr(self._config, field)
            config_dict[field] = value
        return config_dict
    
    def save_config(self, output_file: str):
        """Save current configuration to file"""
        config_dict = self.export_config()
        with open(output_file, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
        print(f"Configuration saved to: {output_file}")


# Global configuration manager
_global_config_manager = None


def get_production_config_manager(config_file: Optional[str] = None) -> ProductionConfigManager:
    """Get the global production configuration manager"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ProductionConfigManager(config_file)
    return _global_config_manager


def get_production_config(agent_name: Optional[str] = None) -> ValidationProductionConfig:
    """Get production configuration with optional agent-specific overrides"""
    manager = get_production_config_manager()
    if agent_name:
        return manager.get_agent_config(agent_name)
    return manager.get_config()


def create_example_config_file(output_path: str = "validation_production_config.json"):
    """Create an example configuration file with all options documented"""
    example_config = {
        "_comment": "ValidationWrapper Production Configuration",
        "enabled": True,
        "max_retries": 3,
        "timeout_ms": 30000,
        "max_concurrent_validations": 10,
        "cache_validation_results": True,
        "cache_ttl_seconds": 300,
        "circuit_breaker_enabled": True,
        "failure_threshold": 5,
        "recovery_timeout_seconds": 30,
        "min_requests_for_circuit_breaker": 5,
        "repair_strategies_enabled": [
            "LocalPatternRepair",
            "LLMRetryRepair",
            "SchemaRelaxationRepair",
            "LegacyFallbackRepair"
        ],
        "llm_retry_enabled": True,
        "schema_relaxation_enabled": True,
        "metrics_collection_enabled": True,
        "structured_logging_enabled": True,
        "log_level": "INFO",
        "export_metrics_interval_minutes": 60,
        "alert_thresholds": {
            "success_rate_threshold": 0.95,
            "max_processing_time_ms": 1000,
            "max_error_rate": 0.05
        },
        "max_memory_mb": 500,
        "max_validation_queue_size": 1000,
        "debug_mode": False,
        "save_failed_validations": False,
        "validation_debug_dir": "/tmp/validation_debug",
        "agent_overrides": {
            "WebSearchAgent": {
                "max_retries": 5,
                "timeout_ms": 45000
            },
            "SiteCrawlerAgent": {
                "max_retries": 2,
                "timeout_ms": 60000
            }
        },
        "feature_flags": {
            "enhanced_error_reporting": True,
            "adaptive_retry_timing": True,
            "validation_analytics": True,
            "predictive_repair": False
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(example_config, f, indent=2)
    
    print(f"Example configuration file created: {output_path}")
    return output_path


if __name__ == "__main__":
    # Create example config file when run directly
    create_example_config_file()