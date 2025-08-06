"""
ValidatedAgent wrapper that integrates ValidationWrapper with ResearchAgent instances.
Provides transparent validation for all Outlines-enabled agents.
"""

import time
from typing import Any, Dict, Optional
from ..baseclass import ResearchAgent
from .validation_wrapper import ValidationWrapper
from .validation_config import ValidationConfig, get_validation_config_manager
from .observability import ObservabilityHandler


class ValidatedAgent(ResearchAgent):
    """
    Wrapper that adds validation to any ResearchAgent.
    Maintains full compatibility with existing agent interfaces.
    """
    
    def __init__(self, 
                 base_agent: ResearchAgent,
                 validation_config: Optional[ValidationConfig] = None,
                 observability: Optional[ObservabilityHandler] = None):
        
        # Initialize with base agent attributes
        super().__init__(
            name=base_agent.name,
            instructions=base_agent.instructions,
            tools=base_agent.tools,
            model=base_agent.model,
            summariser=base_agent.summariser,
            output_type=base_agent.output_type,
            output_parser=base_agent.output_parser
        )
        
        self.base_agent = base_agent
        self.observability = observability or ObservabilityHandler()
        
        # Get configuration
        config_manager = get_validation_config_manager()
        agent_config = validation_config or config_manager.get_config(base_agent.name)
        
        # Initialize ValidationWrapper if enabled
        if agent_config.enabled:
            self.validator = ValidationWrapper(
                agent_name=base_agent.name,
                schema=getattr(base_agent, 'output_type', None),
                config=agent_config,
                observability=self.observability
            )
            self.validation_enabled = True
            print(f"[ValidatedAgent] Validation enabled for {base_agent.name}")
        else:
            self.validator = None
            self.validation_enabled = False
            print(f"[ValidatedAgent] Validation disabled for {base_agent.name}")
    
    async def run_implementation(self, input_data: str) -> Dict[str, Any]:
        """
        Enhanced run implementation with validation.
        Maintains compatibility with both dual-path and legacy agents.
        """
        start_time = time.time()
        
        try:
            # Execute base agent
            result = await self.base_agent.run_implementation(input_data)
            
            # Apply validation if enabled
            if self.validation_enabled and self.validator:
                # Convert result to string for validation if it's a dict
                if isinstance(result, dict):
                    import json
                    result_str = json.dumps(result)
                else:
                    result_str = str(result)
                
                # Validate and potentially repair
                validated_result = await self.validator.validate_and_repair(
                    llm_response=result_str,
                    model_client=getattr(self.base_agent, 'model', None)
                )
                
                self.observability.increment(f'validated_agent.{self.base_agent.name}.validation_applied')
                return validated_result
            else:
                # Return original result
                self.observability.increment(f'validated_agent.{self.base_agent.name}.validation_bypassed')
                
                # Ensure consistent output format
                if isinstance(result, dict):
                    result.setdefault('processing_method', 'no_validation')
                    result.setdefault('confidence', 0.9)  # High confidence for no validation
                    result.setdefault('processing_time_ms', int((time.time() - start_time) * 1000))
                
                return result
                
        except Exception as e:
            self.observability.increment(f'validated_agent.{self.base_agent.name}.error')
            
            # Create error response in consistent format
            return {
                "output": f"Agent execution failed: {e}",
                "sources": [],
                "processing_method": "execution_error",
                "confidence": 0.0,
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
    
    def get_validation_status(self) -> Dict[str, Any]:
        """Get validation status for this agent"""
        status = {
            "agent_name": self.base_agent.name,
            "validation_enabled": self.validation_enabled,
            "base_agent_type": type(self.base_agent).__name__
        }
        
        if self.validator:
            status["validator_status"] = self.validator.get_status()
        
        return status
    
    def disable_validation(self):
        """Disable validation for this agent"""
        self.validation_enabled = False
        print(f"[ValidatedAgent] Validation disabled for {self.base_agent.name}")
    
    def enable_validation(self):
        """Enable validation for this agent"""
        if self.validator:
            self.validation_enabled = True
            print(f"[ValidatedAgent] Validation enabled for {self.base_agent.name}")
        else:
            print(f"[ValidatedAgent] Cannot enable validation - no validator configured for {self.base_agent.name}")
    
    # Delegate attribute access to base agent for full compatibility
    def __getattr__(self, name):
        """Delegate attribute access to base agent"""
        if hasattr(self.base_agent, name):
            return getattr(self.base_agent, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


def wrap_agent_with_validation(agent: ResearchAgent, 
                              config: Optional[ValidationConfig] = None,
                              observability: Optional[ObservabilityHandler] = None) -> ValidatedAgent:
    """
    Convenience function to wrap any ResearchAgent with validation.
    
    Args:
        agent: The base agent to wrap
        config: Optional validation configuration
        observability: Optional observability handler
        
    Returns:
        ValidatedAgent wrapper
    """
    return ValidatedAgent(agent, config, observability)


def create_validated_agent_factory(validation_enabled: bool = True,
                                 global_config: Optional[ValidationConfig] = None):
    """
    Create a factory function for wrapping agents with validation.
    Useful for batch processing or conditional validation.
    
    Args:
        validation_enabled: Whether to enable validation by default
        global_config: Global configuration to apply to all wrapped agents
        
    Returns:
        Factory function that wraps agents
    """
    def factory(agent: ResearchAgent, 
                agent_config: Optional[ValidationConfig] = None) -> ResearchAgent:
        
        if not validation_enabled:
            return agent
        
        effective_config = agent_config or global_config
        
        # Apply global overrides if specified
        if effective_config and global_config:
            # Merge configurations with global taking precedence for enabled flag
            if hasattr(global_config, 'enabled'):
                effective_config.enabled = global_config.enabled
        
        return ValidatedAgent(agent, effective_config)
    
    return factory