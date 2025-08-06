"""
Agent factory with ValidationWrapper integration.
Provides centralized agent creation with optional validation for all agent types.
"""

from typing import Optional, Dict, Any, Callable
from ..baseclass import ResearchAgent
from ...llm_config import LLMConfig
from .validated_agent import ValidatedAgent
from .validation_config import ValidationConfig, get_validation_config_manager
from .observability import ObservabilityHandler


class AgentFactory:
    """
    Factory for creating agents with optional ValidationWrapper integration.
    Maintains compatibility with existing agent initialization functions.
    """
    
    def __init__(self, 
                 validation_enabled: bool = True,
                 global_observability: Optional[ObservabilityHandler] = None):
        self.validation_enabled = validation_enabled
        self.global_observability = global_observability
        self.config_manager = get_validation_config_manager()
        
        # Registry of agent initialization functions
        self._agent_initializers = {}
        self._register_default_initializers()
    
    def _register_default_initializers(self):
        """Register all default agent initialization functions"""
        # Import all agent initialization functions
        try:
            from ..planner_agent import init_planner_agent
            self._agent_initializers["planner"] = init_planner_agent
            self._agent_initializers["PlannerAgent"] = init_planner_agent
        except ImportError as e:
            print(f"[AgentFactory] Could not import PlannerAgent: {e}")
        
        try:
            from ..tool_selector_agent import init_tool_selector_agent
            self._agent_initializers["tool_selector"] = init_tool_selector_agent
            self._agent_initializers["ToolSelectorAgent"] = init_tool_selector_agent
        except ImportError as e:
            print(f"[AgentFactory] Could not import ToolSelectorAgent: {e}")
        
        try:
            from ..knowledge_gap_agent import init_knowledge_gap_agent
            self._agent_initializers["knowledge_gap"] = init_knowledge_gap_agent
            self._agent_initializers["KnowledgeGapAgent"] = init_knowledge_gap_agent
        except ImportError as e:
            print(f"[AgentFactory] Could not import KnowledgeGapAgent: {e}")
        
        try:
            from ..tool_agents.search_agent import init_search_agent
            self._agent_initializers["search"] = init_search_agent
            self._agent_initializers["SearchAgent"] = init_search_agent
            self._agent_initializers["WebSearchAgent"] = init_search_agent
        except ImportError as e:
            print(f"[AgentFactory] Could not import SearchAgent: {e}")
        
        try:
            from ..tool_agents.crawl_agent import init_crawl_agent
            self._agent_initializers["crawl"] = init_crawl_agent
            self._agent_initializers["CrawlAgent"] = init_crawl_agent
            self._agent_initializers["SiteCrawlerAgent"] = init_crawl_agent
        except ImportError as e:
            print(f"[AgentFactory] Could not import CrawlAgent: {e}")
        
        try:
            from ..writer_agent import init_writer_agent
            self._agent_initializers["writer"] = init_writer_agent
            self._agent_initializers["WriterAgent"] = init_writer_agent
        except ImportError as e:
            print(f"[AgentFactory] Could not import WriterAgent: {e}")
        
        try:
            from ..long_writer_agent import init_long_writer_agent
            self._agent_initializers["long_writer"] = init_long_writer_agent
            self._agent_initializers["LongWriterAgent"] = init_long_writer_agent
        except ImportError as e:
            print(f"[AgentFactory] Could not import LongWriterAgent: {e}")
        
        try:
            from ..thinking_agent import init_thinking_agent
            self._agent_initializers["thinking"] = init_thinking_agent
            self._agent_initializers["ThinkingAgent"] = init_thinking_agent
        except ImportError as e:
            print(f"[AgentFactory] Could not import ThinkingAgent: {e}")
        
        try:
            from ..proofreader_agent import init_proofreader_agent
            self._agent_initializers["proofreader"] = init_proofreader_agent
            self._agent_initializers["ProofreaderAgent"] = init_proofreader_agent
        except ImportError as e:
            print(f"[AgentFactory] Could not import ProofreaderAgent: {e}")
        
        print(f"[AgentFactory] Registered {len(self._agent_initializers)} agent initializers")
    
    def create_agent(self, 
                    agent_type: str, 
                    config: LLMConfig,
                    validation_config: Optional[ValidationConfig] = None,
                    enable_validation: Optional[bool] = None) -> ResearchAgent:
        """
        Create agent with optional validation wrapper.
        
        Args:
            agent_type: Type of agent to create (e.g., 'planner', 'search', 'crawl')
            config: LLM configuration
            validation_config: Optional validation configuration override
            enable_validation: Override global validation setting for this agent
            
        Returns:
            ResearchAgent (optionally wrapped with ValidationWrapper)
        """
        # Determine if validation should be enabled
        validation_enabled = (
            enable_validation if enable_validation is not None 
            else self.validation_enabled
        )
        
        # Get agent initializer
        initializer = self._agent_initializers.get(agent_type)
        if not initializer:
            available_types = list(self._agent_initializers.keys())
            raise ValueError(f"Unknown agent type '{agent_type}'. Available types: {available_types}")
        
        # Create base agent
        try:
            base_agent = initializer(config)
            print(f"[AgentFactory] Created {agent_type} -> {base_agent.name}")
        except Exception as e:
            print(f"[AgentFactory] Failed to create {agent_type}: {e}")
            raise
        
        # Wrap with validation if enabled
        if validation_enabled:
            # Get validation configuration
            effective_config = validation_config or self.config_manager.get_config(base_agent.name)
            
            if effective_config.enabled:
                validated_agent = ValidatedAgent(
                    base_agent=base_agent,
                    validation_config=effective_config,
                    observability=self.global_observability
                )
                print(f"[AgentFactory] Wrapped {base_agent.name} with ValidationWrapper")
                return validated_agent
            else:
                print(f"[AgentFactory] Validation disabled for {base_agent.name} by configuration")
        
        return base_agent
    
    def create_all_agents(self, 
                         config: LLMConfig,
                         agent_types: Optional[list] = None,
                         validation_config: Optional[Dict[str, ValidationConfig]] = None) -> Dict[str, ResearchAgent]:
        """
        Create multiple agents with validation.
        
        Args:
            config: LLM configuration
            agent_types: List of agent types to create (default: all available)
            validation_config: Per-agent validation configurations
            
        Returns:
            Dictionary mapping agent names to agent instances
        """
        if agent_types is None:
            # Create main research pipeline agents
            agent_types = [
                "planner", "tool_selector", "knowledge_gap", 
                "search", "crawl", "writer"
            ]
        
        agents = {}
        
        for agent_type in agent_types:
            try:
                agent_validation_config = (
                    validation_config.get(agent_type) if validation_config else None
                )
                
                agent = self.create_agent(
                    agent_type=agent_type,
                    config=config,
                    validation_config=agent_validation_config
                )
                
                agents[agent.name] = agent
                
            except Exception as e:
                print(f"[AgentFactory] Failed to create {agent_type}: {e}")
                # Continue with other agents
        
        return agents
    
    def register_agent_initializer(self, 
                                 agent_type: str, 
                                 initializer: Callable[[LLMConfig], ResearchAgent]):
        """Register custom agent initializer"""
        self._agent_initializers[agent_type] = initializer
        print(f"[AgentFactory] Registered custom initializer for {agent_type}")
    
    def get_available_agent_types(self) -> list:
        """Get list of available agent types"""
        return list(self._agent_initializers.keys())
    
    def enable_validation(self):
        """Enable validation for all subsequently created agents"""
        self.validation_enabled = True
        print("[AgentFactory] Validation enabled globally")
    
    def disable_validation(self):
        """Disable validation for all subsequently created agents"""
        self.validation_enabled = False
        print("[AgentFactory] Validation disabled globally")
    
    def get_factory_status(self) -> Dict[str, Any]:
        """Get factory status and statistics"""
        return {
            "validation_enabled": self.validation_enabled,
            "available_agent_types": len(self._agent_initializers),
            "registered_types": list(self._agent_initializers.keys()),
            "has_global_observability": self.global_observability is not None
        }


# Global factory instance
_global_agent_factory = None

def get_agent_factory() -> AgentFactory:
    """Get global agent factory instance"""
    global _global_agent_factory
    if _global_agent_factory is None:
        _global_agent_factory = AgentFactory()
    return _global_agent_factory


def create_validated_agent(agent_type: str, 
                         config: LLMConfig,
                         validation_config: Optional[ValidationConfig] = None) -> ResearchAgent:
    """
    Convenience function to create a single validated agent.
    
    Args:
        agent_type: Type of agent to create
        config: LLM configuration  
        validation_config: Optional validation configuration
        
    Returns:
        ResearchAgent with validation wrapper
    """
    factory = get_agent_factory()
    return factory.create_agent(
        agent_type=agent_type,
        config=config,
        validation_config=validation_config,
        enable_validation=True
    )


def create_all_validated_agents(config: LLMConfig,
                              validation_configs: Optional[Dict[str, ValidationConfig]] = None) -> Dict[str, ResearchAgent]:
    """
    Convenience function to create all main research agents with validation.
    
    Args:
        config: LLM configuration
        validation_configs: Per-agent validation configurations
        
    Returns:
        Dictionary of validated agents
    """
    factory = get_agent_factory()
    return factory.create_all_agents(
        config=config,
        validation_config=validation_configs
    )


# Legacy compatibility functions
def init_validated_planner_agent(config: LLMConfig) -> ResearchAgent:
    """Legacy compatibility: Create validated planner agent"""
    return create_validated_agent("planner", config)

def init_validated_tool_selector_agent(config: LLMConfig) -> ResearchAgent:
    """Legacy compatibility: Create validated tool selector agent"""  
    return create_validated_agent("tool_selector", config)

def init_validated_knowledge_gap_agent(config: LLMConfig) -> ResearchAgent:
    """Legacy compatibility: Create validated knowledge gap agent"""
    return create_validated_agent("knowledge_gap", config)

def init_validated_search_agent(config: LLMConfig) -> ResearchAgent:
    """Legacy compatibility: Create validated search agent"""
    return create_validated_agent("search", config)

def init_validated_crawl_agent(config: LLMConfig) -> ResearchAgent:
    """Legacy compatibility: Create validated crawl agent"""
    return create_validated_agent("crawl", config)