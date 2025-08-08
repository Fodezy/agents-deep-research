from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict

class ToolAgentOutput(BaseModel):
    """Standard output for all tool agents"""
    model_config = ConfigDict(extra='forbid')
    output: str
    sources: list[str] = Field(default_factory=list)

from .search_agent import init_search_agent
from .crawl_agent import init_crawl_agent
from ...llm_config import LLMConfig
from ..baseclass import ResearchAgent
from ..utils.validated_agent import ValidatedAgent
from ..utils.validation_config import ValidationConfig, get_validation_config_manager

def init_tool_agents(config: LLMConfig, 
                    enable_validation: bool = False,  # PHASE 3: Disabled by default (native structured generation)
                    validation_configs: Optional[Dict[str, ValidationConfig]] = None) -> dict[str, ResearchAgent]:
    """
    Initialize tool agents with optional ValidationWrapper integration.
    
    Args:
        config: LLM configuration
        enable_validation: Whether to enable validation wrappers
        validation_configs: Per-agent validation configurations
        
    Returns:
        Dictionary mapping agent names to agent instances (optionally validated)
    """
    # Create base agents
    search_agent = init_search_agent(config)
    crawl_agent = init_crawl_agent(config)
    
    agents = {
        "WebSearchAgent": search_agent,
        "SiteCrawlerAgent": crawl_agent,
    }
    
    # Apply validation wrappers if enabled
    if enable_validation:
        config_manager = get_validation_config_manager()
        validated_agents = {}
        
        for agent_name, agent in agents.items():
            # Get validation configuration
            agent_config = None
            if validation_configs and agent_name in validation_configs:
                agent_config = validation_configs[agent_name]
            else:
                agent_config = config_manager.get_config(agent.name)
            
            # Wrap with validation if enabled in config
            if agent_config.enabled:
                validated_agents[agent_name] = ValidatedAgent(
                    base_agent=agent,
                    validation_config=agent_config
                )
                print(f"[init_tool_agents] Wrapped {agent_name} with ValidationWrapper")
            else:
                validated_agents[agent_name] = agent
                print(f"[init_tool_agents] Validation disabled for {agent_name} by configuration")
        
        return validated_agents
    
    return agents


def init_validated_tool_agents(config: LLMConfig,
                              validation_configs: Optional[Dict[str, ValidationConfig]] = None) -> dict[str, ResearchAgent]:
    """
    Convenience function to create tool agents with validation enabled.
    
    Args:
        config: LLM configuration
        validation_configs: Per-agent validation configurations
        
    Returns:
        Dictionary of validated tool agents
    """
    return init_tool_agents(
        config=config,
        enable_validation=True,
        validation_configs=validation_configs
    )
