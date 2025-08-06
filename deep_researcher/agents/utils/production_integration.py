"""
Production integration utilities for ValidationWrapper system.
Provides centralized initialization, health checks, and monitoring setup.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .validation_wrapper import ValidationWrapper
from .validated_agent import ValidatedAgent
from .agent_factory import get_agent_factory
from .validation_metrics import get_metrics_collector, setup_validation_monitoring
from .validation_logging import setup_validation_logging, get_validation_logger
from .production_config import get_production_config_manager, create_example_config_file
from ..baseclass import ResearchAgent
from ...llm_config import LLMConfig


class ValidationProductionManager:
    """Centralized production management for ValidationWrapper system"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_manager = get_production_config_manager(config_file)
        self.metrics_collector = None
        self.logger = None
        self.initialized = False
        self.start_time = datetime.now()
        self.wrapped_agents: Dict[str, ValidatedAgent] = {}
    
    def initialize(self, log_level: str = "INFO", structured_logging: bool = True):
        """Initialize production validation system"""
        if self.initialized:
            return
        
        # Setup logging
        self.logger = setup_validation_logging(log_level, structured_logging)
        self.logger.logger.info("production_initialization_start", extra={
            "timestamp": datetime.now().isoformat(),
            "config_file": getattr(self.config_manager, 'config_file', None)
        })
        
        # Setup metrics collection
        self.metrics_collector = setup_validation_monitoring()
        
        # Register alert callback for production
        self.metrics_collector.add_alert_callback(self._handle_production_alert)
        
        self.initialized = True
        self.logger.logger.info("production_initialization_complete", extra={
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
        })
    
    def _handle_production_alert(self, alert_data: Dict[str, Any]):
        """Handle production alerts"""
        severity = alert_data.get("severity", "warning")
        agent_name = alert_data.get("agent_name", "unknown")
        message = alert_data.get("message", "Unknown alert")
        
        if severity == "error":
            # For critical errors, log at error level and take action
            self.logger.logger.error("production_critical_alert", extra=alert_data)
            
            # Consider disabling validation for the problematic agent temporarily
            if agent_name in self.wrapped_agents:
                try:
                    # Temporarily disable validation for 5 minutes
                    agent = self.wrapped_agents[agent_name]
                    if hasattr(agent, 'validator') and agent.validator:
                        self.logger.logger.warning("temporarily_disabling_validation", extra={
                            "agent_name": agent_name,
                            "reason": "critical_alert_threshold_reached",
                            "timestamp": datetime.now().isoformat()
                        })
                except Exception as e:
                    self.logger.logger.error("failed_to_disable_validation", extra={
                        "agent_name": agent_name,
                        "error": str(e)
                    })
        else:
            # For warnings, just log
            self.logger.logger.warning("production_alert", extra=alert_data)
    
    def wrap_agent(self, agent: ResearchAgent, enable_validation: bool = True) -> ResearchAgent:
        """Wrap an agent with production validation"""
        if not self.initialized:
            self.initialize()
        
        if not enable_validation:
            return agent
        
        # Get agent-specific configuration
        prod_config = self.config_manager.get_agent_config(agent.name)
        
        try:
            validated_agent = ValidatedAgent(
                base_agent=agent,
                enable_validation=prod_config.enabled
            )
            
            self.wrapped_agents[agent.name] = validated_agent
            
            self.logger.logger.info("agent_wrapped_for_production", extra={
                "agent_name": agent.name,
                "validation_enabled": prod_config.enabled,
                "timestamp": datetime.now().isoformat()
            })
            
            return validated_agent
            
        except Exception as e:
            self.logger.logger.error("agent_wrapping_failed", extra={
                "agent_name": agent.name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            # Return unwrapped agent on failure
            return agent
    
    def create_validated_agents(self, config: LLMConfig, agent_types: List[str]) -> Dict[str, ResearchAgent]:
        """Create multiple validated agents for production use"""
        if not self.initialized:
            self.initialize()
        
        factory = get_agent_factory()
        validated_agents = {}
        
        for agent_type in agent_types:
            try:
                # Create base agent
                base_agent = factory.create_agent(
                    agent_type=agent_type,
                    config=config,
                    enable_validation=False  # We'll wrap it ourselves
                )
                
                # Wrap with production validation
                validated_agent = self.wrap_agent(base_agent, enable_validation=True)
                validated_agents[agent_type] = validated_agent
                
                self.logger.logger.info("validated_agent_created", extra={
                    "agent_type": agent_type,
                    "agent_name": base_agent.name,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.logger.error("validated_agent_creation_failed", extra={
                    "agent_type": agent_type,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        return validated_agents
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status for the validation system"""
        if not self.initialized:
            return {"status": "not_initialized"}
        
        uptime = datetime.now() - self.start_time
        system_summary = self.metrics_collector.get_system_summary()
        
        # Determine overall health
        overall_health = "healthy"
        if system_summary["error_rate"] > 0.1:  # 10% error rate
            overall_health = "degraded"
        if system_summary["error_rate"] > 0.2:  # 20% error rate
            overall_health = "unhealthy"
        
        return {
            "status": "initialized",
            "overall_health": overall_health,
            "uptime_hours": uptime.total_seconds() / 3600,
            "wrapped_agents_count": len(self.wrapped_agents),
            "system_metrics": system_summary,
            "timestamp": datetime.now().isoformat(),
            "config_summary": {
                "validation_enabled": self.config_manager.get_config().enabled,
                "metrics_enabled": self.config_manager.get_config().metrics_collection_enabled,
                "circuit_breaker_enabled": self.config_manager.get_config().circuit_breaker_enabled
            }
        }
    
    def run_health_check(self) -> bool:
        """Run comprehensive health check"""
        try:
            health_status = self.get_health_status()
            
            # Check if system is healthy
            is_healthy = (
                health_status.get("status") == "initialized" and
                health_status.get("overall_health") in ["healthy", "degraded"]
            )
            
            self.logger.logger.info("health_check_complete", extra={
                "is_healthy": is_healthy,
                "health_status": health_status,
                "timestamp": datetime.now().isoformat()
            })
            
            return is_healthy
            
        except Exception as e:
            self.logger.logger.error("health_check_failed", extra={
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return False
    
    def export_diagnostics(self, include_metrics: bool = True, 
                          time_window_hours: int = 24) -> Dict[str, Any]:
        """Export comprehensive diagnostics for troubleshooting"""
        diagnostics = {
            "export_timestamp": datetime.now().isoformat(),
            "health_status": self.get_health_status(),
            "configuration": self.config_manager.export_config(),
            "wrapped_agents": list(self.wrapped_agents.keys())
        }
        
        if include_metrics and self.metrics_collector:
            diagnostics["metrics"] = self.metrics_collector.export_metrics(
                format="json", time_window_hours=time_window_hours
            )
        
        return diagnostics
    
    def shutdown(self):
        """Graceful shutdown of validation system"""
        if not self.initialized:
            return
        
        self.logger.logger.info("production_shutdown_start", extra={
            "timestamp": datetime.now().isoformat(),
            "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600
        })
        
        # Export final metrics
        try:
            final_diagnostics = self.export_diagnostics()
            self.logger.logger.info("final_diagnostics_exported", extra={
                "diagnostics_summary": {
                    "total_agents": len(self.wrapped_agents),
                    "system_health": final_diagnostics["health_status"]["overall_health"]
                }
            })
        except Exception as e:
            self.logger.logger.error("final_diagnostics_export_failed", extra={"error": str(e)})
        
        # Clean up resources
        self.wrapped_agents.clear()
        
        self.logger.logger.info("production_shutdown_complete", extra={
            "timestamp": datetime.now().isoformat()
        })


# Global production manager instance
_global_production_manager = None


def get_production_manager(config_file: Optional[str] = None) -> ValidationProductionManager:
    """Get the global production manager instance"""
    global _global_production_manager
    if _global_production_manager is None:
        _global_production_manager = ValidationProductionManager(config_file)
    return _global_production_manager


def initialize_production_validation(config_file: Optional[str] = None,
                                   log_level: str = "INFO",
                                   structured_logging: bool = True) -> ValidationProductionManager:
    """Initialize the production validation system"""
    manager = get_production_manager(config_file)
    manager.initialize(log_level, structured_logging)
    return manager


def create_production_agents(config: LLMConfig,
                           agent_types: List[str] = None,
                           config_file: Optional[str] = None) -> Dict[str, ResearchAgent]:
    """Create production-ready validated agents"""
    if agent_types is None:
        agent_types = ["search", "crawl", "planner", "tool_selector", "knowledge_gap"]
    
    manager = get_production_manager(config_file)
    if not manager.initialized:
        manager.initialize()
    
    return manager.create_validated_agents(config, agent_types)


def run_production_health_check(config_file: Optional[str] = None) -> bool:
    """Run production health check"""
    manager = get_production_manager(config_file)
    return manager.run_health_check()


async def production_validation_demo(config: LLMConfig):
    """Demonstration of production validation system"""
    print("=== Production Validation System Demo ===")
    
    # Initialize production system
    manager = initialize_production_validation(log_level="INFO")
    
    # Create validated agents
    agent_types = ["search", "planner"]
    agents = create_production_agents(config, agent_types)
    
    print(f"Created {len(agents)} validated agents: {list(agents.keys())}")
    
    # Run health check
    health_ok = run_production_health_check()
    print(f"Health check: {'PASS' if health_ok else 'FAIL'}")
    
    # Get health status
    health_status = manager.get_health_status()
    print(f"System health: {health_status['overall_health']}")
    print(f"Uptime: {health_status['uptime_hours']:.2f} hours")
    print(f"Wrapped agents: {health_status['wrapped_agents_count']}")
    
    # Export diagnostics
    diagnostics = manager.export_diagnostics(time_window_hours=1)
    print(f"Diagnostics exported with {len(diagnostics)} sections")
    
    return manager


if __name__ == "__main__":
    # Create example config and run demo
    config_file = create_example_config_file("demo_validation_config.json")
    print(f"Created example config: {config_file}")
    
    # Demo would require LLMConfig setup
    print("To run full demo, provide LLMConfig instance to production_validation_demo()")