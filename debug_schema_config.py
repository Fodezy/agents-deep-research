#!/usr/bin/env python3
"""Debug schema config settings"""

from deep_researcher.agents.utils.outlines_schemas import (
    KnowledgeGapResult, AgentSelectionPlan, PlanningResult
)

def debug_schema(schema_class):
    print(f"\n=== {schema_class.__name__} ===")
    model_config = getattr(schema_class, 'model_config', None)
    print(f"model_config: {model_config}")
    print(f"model_config type: {type(model_config)}")
    
    if model_config:
        print(f"model_config.__dict__: {getattr(model_config, '__dict__', 'no __dict__')}")
        print(f"hasattr extra: {hasattr(model_config, 'extra')}")
        if hasattr(model_config, 'extra'):
            print(f"model_config.extra: {model_config.extra}")
        
        # Try different ways to access it
        for attr in dir(model_config):
            if not attr.startswith('_'):
                val = getattr(model_config, attr)
                print(f"  {attr}: {val}")

if __name__ == "__main__":
    for schema in [KnowledgeGapResult, AgentSelectionPlan, PlanningResult]:
        debug_schema(schema)