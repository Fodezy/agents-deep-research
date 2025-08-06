"""
Configuration classes for ValidationWrapper system.
Provides flexible configuration for validation behavior across different agents.
"""

from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel

from .repair_strategies import RepairStrategy, RepairStrategyFactory
from .circuit_breaker import CircuitBreakerConfig
from .observability import ObservabilityHandler


class ValidationMode(Enum):
    """Validation operation modes"""
    STRICT = "strict"        # All validations must pass
    RELAXED = "relaxed"      # Allow some validation failures  
    FALLBACK_ONLY = "fallback_only"  # Only use fallback strategies
    DISABLED = "disabled"    # Skip validation entirely


class RepairStrategyType(Enum):
    """Available repair strategy types"""
    LOCAL_PATTERN = "local_pattern"
    LLM_RETRY = "llm_retry"
    SCHEMA_RELAXATION = "schema_relaxation"
    LEGACY_FALLBACK = "legacy_fallback"


@dataclass
class ValidationConfig:
    """Configuration for validation behavior"""
    
    # Core validation settings
    enabled: bool = True
    mode: ValidationMode = ValidationMode.STRICT
    max_retries: int = 3
    timeout_ms: int = 5000
    
    # Schema and repair settings
    schema: Optional[BaseModel] = None
    repair_strategies: List[RepairStrategyType] = field(default_factory=lambda: [
        RepairStrategyType.LOCAL_PATTERN,
        RepairStrategyType.LLM_RETRY,
        RepairStrategyType.SCHEMA_RELAXATION,
        RepairStrategyType.LEGACY_FALLBACK
    ])
    
    # Circuit breaker settings
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    
    # Performance settings
    cache_results: bool = True
    cache_ttl_seconds: int = 300
    parallel_repair: bool = False
    
    # Observability settings
    collect_metrics: bool = True
    log_failures: bool = True
    log_successes: bool = False
    
    # Agent-specific overrides
    agent_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def get_agent_config(self, agent_name: str) -> 'ValidationConfig':
        """Get configuration with agent-specific overrides applied"""
        if agent_name not in self.agent_overrides:
            return self
        
        # Create a copy with overrides applied
        import copy
        config = copy.deepcopy(self)
        overrides = self.agent_overrides[agent_name]
        
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config


@dataclass
class AgentValidationProfile:
    """Predefined validation profiles for different agent types"""
    
    name: str
    description: str
    config: ValidationConfig
    
    @staticmethod
    def get_search_agent_profile() -> 'AgentValidationProfile':
        """Profile optimized for SearchAgent"""
        from ..utils.outlines_schemas import EnhancedToolAgentOutput
        
        config = ValidationConfig(
            mode=ValidationMode.STRICT,
            max_retries=2,
            timeout_ms=3000,
            schema=EnhancedToolAgentOutput,
            repair_strategies=[
                RepairStrategyType.LOCAL_PATTERN,
                RepairStrategyType.LLM_RETRY,
                RepairStrategyType.LEGACY_FALLBACK
            ],
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=180,
                min_requests=3
            ),
            parallel_repair=False,  # Search results need sequential processing
            cache_results=True
        )
        
        return AgentValidationProfile(
            name="SearchAgent",
            description="Optimized for web search result validation",
            config=config
        )
    
    @staticmethod
    def get_crawl_agent_profile() -> 'AgentValidationProfile':
        """Profile optimized for CrawlAgent"""
        from ..utils.outlines_schemas import EnhancedToolAgentOutput
        
        config = ValidationConfig(
            mode=ValidationMode.RELAXED,  # Crawled content more variable
            max_retries=3,
            timeout_ms=5000,  # Longer timeout for large content
            schema=EnhancedToolAgentOutput,
            repair_strategies=[
                RepairStrategyType.LOCAL_PATTERN,
                RepairStrategyType.SCHEMA_RELAXATION,  # More important for variable content
                RepairStrategyType.LLM_RETRY,
                RepairStrategyType.LEGACY_FALLBACK
            ],
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=5,  # More tolerant
                recovery_timeout=300,
                min_requests=5
            ),
            cache_results=True,
            cache_ttl_seconds=600  # Cache crawl results longer
        )
        
        return AgentValidationProfile(
            name="CrawlAgent", 
            description="Optimized for website crawl content validation",
            config=config
        )
    
    @staticmethod
    def get_planner_agent_profile() -> 'AgentValidationProfile':
        """Profile optimized for PlannerAgent"""
        from ..utils.outlines_schemas import PlanningResult
        
        config = ValidationConfig(
            mode=ValidationMode.STRICT,  # Planning requires strict validation
            max_retries=2,
            timeout_ms=4000,
            schema=PlanningResult,
            repair_strategies=[
                RepairStrategyType.LOCAL_PATTERN,
                RepairStrategyType.LLM_RETRY,
                RepairStrategyType.LEGACY_FALLBACK  # Skip schema relaxation for planning
            ],
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=2,  # Less tolerant for critical planning
                recovery_timeout=600,
                min_requests=2
            ),
            cache_results=False,  # Don't cache planning results
            parallel_repair=False
        )
        
        return AgentValidationProfile(
            name="PlannerAgent",
            description="Strict validation for research planning outputs", 
            config=config
        )
    
    @staticmethod
    def get_tool_selector_profile() -> 'AgentValidationProfile':
        """Profile optimized for ToolSelectorAgent"""
        from ..utils.outlines_schemas import AgentSelectionPlan
        
        config = ValidationConfig(
            mode=ValidationMode.STRICT,
            max_retries=1,  # Tool selection should be fast
            timeout_ms=2000,
            schema=AgentSelectionPlan,
            repair_strategies=[
                RepairStrategyType.LOCAL_PATTERN,
                RepairStrategyType.LEGACY_FALLBACK  # Skip expensive repairs
            ],
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=120,  # Quick recovery
                min_requests=2
            ),
            cache_results=True,
            cache_ttl_seconds=60  # Short cache for dynamic tool selection
        )
        
        return AgentValidationProfile(
            name="ToolSelectorAgent",
            description="Fast validation for tool selection decisions",
            config=config
        )
    
    @staticmethod  
    def get_knowledge_gap_profile() -> 'AgentValidationProfile':
        """Profile optimized for KnowledgeGapAgent"""
        from ..utils.outlines_schemas import KnowledgeGap
        
        config = ValidationConfig(
            mode=ValidationMode.RELAXED,  # Knowledge gaps can be subjective
            max_retries=2,
            timeout_ms=3000,
            schema=KnowledgeGap,
            repair_strategies=[
                RepairStrategyType.LOCAL_PATTERN,
                RepairStrategyType.SCHEMA_RELAXATION,
                RepairStrategyType.LLM_RETRY,
                RepairStrategyType.LEGACY_FALLBACK
            ],
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=4,
                recovery_timeout=240,
                min_requests=3
            ),
            cache_results=True,
            cache_ttl_seconds=300
        )
        
        return AgentValidationProfile(
            name="KnowledgeGapAgent",
            description="Relaxed validation for subjective knowledge gap analysis",
            config=config
        )


class ValidationConfigManager:
    """Manages validation configurations across the system"""
    
    def __init__(self):
        self._profiles: Dict[str, AgentValidationProfile] = {}
        self._global_config = ValidationConfig()
        self._load_default_profiles()
    
    def _load_default_profiles(self):
        """Load default agent profiles"""
        profiles = [
            AgentValidationProfile.get_search_agent_profile(),
            AgentValidationProfile.get_crawl_agent_profile(), 
            AgentValidationProfile.get_planner_agent_profile(),
            AgentValidationProfile.get_tool_selector_profile(),
            AgentValidationProfile.get_knowledge_gap_profile()
        ]
        
        for profile in profiles:
            self._profiles[profile.name] = profile
    
    def get_config(self, agent_name: str) -> ValidationConfig:
        """Get validation config for agent"""
        # Try exact match first
        if agent_name in self._profiles:
            return self._profiles[agent_name].config
        
        # Try pattern matching for agent types
        agent_lower = agent_name.lower()
        if 'search' in agent_lower:
            return self._profiles['SearchAgent'].config
        elif 'crawl' in agent_lower or 'site' in agent_lower:
            return self._profiles['CrawlAgent'].config
        elif 'plan' in agent_lower:
            return self._profiles['PlannerAgent'].config
        elif 'tool' in agent_lower and 'selector' in agent_lower:
            return self._profiles['ToolSelectorAgent'].config
        elif 'knowledge' in agent_lower or 'gap' in agent_lower:
            return self._profiles['KnowledgeGapAgent'].config
        
        # Return global config as fallback
        return self._global_config
    
    def register_profile(self, profile: AgentValidationProfile):
        """Register a custom agent profile"""
        self._profiles[profile.name] = profile
    
    def set_global_config(self, config: ValidationConfig):
        """Set global default configuration"""
        self._global_config = config
    
    def get_all_profiles(self) -> Dict[str, AgentValidationProfile]:
        """Get all registered profiles"""
        return self._profiles.copy()
    
    def update_agent_config(self, agent_name: str, updates: Dict[str, Any]):
        """Update configuration for specific agent"""
        if agent_name in self._profiles:
            config = self._profiles[agent_name].config
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    def disable_validation(self, agent_name: Optional[str] = None):
        """Disable validation for specific agent or globally"""
        if agent_name:
            self.update_agent_config(agent_name, {'enabled': False})
        else:
            self._global_config.enabled = False
            for profile in self._profiles.values():
                profile.config.enabled = False
    
    def enable_validation(self, agent_name: Optional[str] = None):
        """Enable validation for specific agent or globally"""
        if agent_name:
            self.update_agent_config(agent_name, {'enabled': True})
        else:
            self._global_config.enabled = True
            for profile in self._profiles.values():
                profile.config.enabled = True
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of validation configuration"""
        return {
            "global_enabled": self._global_config.enabled,
            "total_profiles": len(self._profiles),
            "profile_status": {
                name: {
                    "enabled": profile.config.enabled,
                    "mode": profile.config.mode.value,
                    "max_retries": profile.config.max_retries,
                    "timeout_ms": profile.config.timeout_ms
                }
                for name, profile in self._profiles.items()
            }
        }


# Global configuration manager instance
_config_manager = None

def get_validation_config_manager() -> ValidationConfigManager:
    """Get global validation configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ValidationConfigManager()
    return _config_manager