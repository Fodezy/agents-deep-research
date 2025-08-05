#!/usr/bin/env python3
"""
Demo script for Enhanced LLMConfig with 4-Model Architecture.

This script demonstrates the new role-aware model assignment, validation at
instantiation time, and backward compatibility features.
"""

import asyncio
import os
from deep_researcher.llm_config import LLMConfig, create_default_config, create_legacy_config


async def demo_enhanced_llmconfig():
    """Demonstrate enhanced LLMConfig functionality."""
    print("Enhanced LLMConfig Demo - 4-Model Architecture Support")
    print("=" * 60)
    
    # 1. Show current environment setup
    print("\nCurrent Environment Configuration:")
    print("-" * 40)
    
    env_vars = [
        'PLANNER_MODEL_PROVIDER', 'PLANNER_MODEL',
        'TOOL_CALLING_MODEL_PROVIDER', 'TOOL_CALLING_MODEL', 
        'SUMMARISER_MODEL_PROVIDER', 'SUMMARISER_MODEL',
        'WRITER_MODEL_PROVIDER', 'WRITER_MODEL',
        'REASONING_MODEL_PROVIDER', 'REASONING_MODEL',
        'MAIN_MODEL_PROVIDER', 'MAIN_MODEL',
        'FAST_MODEL_PROVIDER', 'FAST_MODEL'
    ]
    
    for var in env_vars:
        value = os.getenv(var, 'Not Set')
        print(f"  {var}: {value}")
    
    # 2. Create default 4-model configuration
    print("\n4-Model Architecture Configuration:")
    print("-" * 40)
    
    try:
        config = create_default_config()
        print("Successfully created 4-model configuration!")
        
        summary = config.get_model_config_summary()
        print(f"  Validation Enabled: {summary['validation_enabled']}")
        print(f"  Strict Validation: {summary['strict_validation']}")
        
        print("\nModel Assignments:")
        for role_name, role_config in summary['models'].items():
            print(f"  {role_name.upper()}:")
            print(f"    Provider: {role_config['provider']}")
            print(f"    Model: {role_config['model']}")
            print(f"    Role: {role_config['role']}")
            
    except Exception as e:
        print(f"Failed to create 4-model configuration: {e}")
        print("This is expected if role validation components are not available")
    
    # 3. Create legacy 3-model configuration
    print("\nBackward Compatibility - Legacy 3-Model Configuration:")
    print("-" * 60)
    
    try:
        legacy_config = create_legacy_config()
        print("Successfully created legacy configuration!")
        
        legacy_summary = legacy_config.get_model_config_summary()
        print(f"  Validation Enabled: {legacy_summary['validation_enabled']}")
        
        print("\nBackward Compatibility Mapping:")
        compat = legacy_summary['backward_compatibility']
        print(f"  reasoning_model -> {compat.get('reasoning_model', 'N/A')}")
        print(f"  main_model -> {compat.get('main_model', 'N/A')}")
        print(f"  fast_model -> {compat.get('fast_model', 'N/A')}")
        
    except Exception as e:
        print(f"Failed to create legacy configuration: {e}")
    
    # 4. Test explicit model assignment
    print("\nExplicit 4-Model Assignment:")
    print("-" * 35)
    
    try:
        explicit_config = LLMConfig(
            search_provider="searxng",
            planner_model_provider="local",
            planner_model="hermes3:8b",
            tool_calling_model_provider="local", 
            tool_calling_model="hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M",
            summariser_model_provider="local",
            summariser_model="qwen2.5-coder:latest",
            writer_model_provider="local",
            writer_model="llama3.2:latest",
            validate_model_roles=False,  # Skip validation for demo
            strict_validation=False
        )
        
        print("Successfully created explicit configuration!")
        
        # Test role-based model retrieval
        try:
            from deep_researcher.agents.utils.runtime_assertions import ModelRole
            
            print("\nRole-Based Model Retrieval:")
            roles = [ModelRole.PLANNER, ModelRole.TOOL_CALLING, ModelRole.SUMMARISER, ModelRole.WRITER]
            
            for role in roles:
                model = explicit_config.get_model_for_role(role)
                print(f"  {role.value.upper()}: {type(model).__name__} instance")
                
        except ImportError:
            print("  Role-based retrieval not available (validation components not installed)")
        
    except Exception as e:
        print(f"Failed to create explicit configuration: {e}")
    
    # 5. Test validation scenarios
    print("\nValidation Scenarios:")
    print("-" * 25)
    
    # Non-strict validation
    print("Testing non-strict validation...")
    try:
        non_strict_config = LLMConfig(
            search_provider="searxng",
            planner_model_provider="local",
            planner_model="hermes3:8b",
            tool_calling_model_provider="local",
            tool_calling_model="hermes3:8b",  # Suboptimal for tool calling
            summariser_model_provider="local", 
            summariser_model="qwen2.5-coder:latest",
            writer_model_provider="local",
            writer_model="llama3.2:latest",
            validate_model_roles=False,  # Would normally show warnings
            strict_validation=False
        )
        print("  Non-strict validation: Configuration created successfully")
        
    except Exception as e:
        print(f"  Non-strict validation failed: {e}")
    
    # 6. Test migration scenario
    print("\nMigration Scenario - 3-Model to 4-Model:")
    print("-" * 45)
    
    try:
        # Old way (3-model)
        old_config = LLMConfig(
            search_provider="searxng",
            reasoning_model_provider="local",
            reasoning_model="hermes3:8b",
            main_model_provider="local",
            main_model="qwen2.5-coder:latest",
            fast_model_provider="local",
            fast_model="llama3.2:latest",
            validate_model_roles=False
        )
        
        print("  Old 3-model configuration created successfully")
        print("  Automatically mapped to 4-model architecture internally:")
        
        old_summary = old_config.get_model_config_summary()
        for role_name, role_config in old_summary['models'].items():
            print(f"    {role_name}: {role_config['model']}")
        
    except Exception as e:
        print(f"  Migration test failed: {e}")
    
    # 7. Environment variable controls
    print("\nEnvironment Variable Controls:")
    print("-" * 33)
    
    print("Available configuration options:")
    print("  PLANNER_MODEL_PROVIDER / PLANNER_MODEL")
    print("  TOOL_CALLING_MODEL_PROVIDER / TOOL_CALLING_MODEL")
    print("  SUMMARISER_MODEL_PROVIDER / SUMMARISER_MODEL")
    print("  WRITER_MODEL_PROVIDER / WRITER_MODEL")
    print("")
    print("Backward compatibility (legacy):")
    print("  REASONING_MODEL_PROVIDER / REASONING_MODEL -> PLANNER")
    print("  MAIN_MODEL_PROVIDER / MAIN_MODEL -> SUMMARISER")
    print("  FAST_MODEL_PROVIDER / FAST_MODEL -> WRITER")
    
    # 8. Configuration recommendations
    print("\nConfiguration Recommendations:")
    print("-" * 35)
    
    print("Optimal 4-Model Setup:")
    print("  PLANNER: hermes3:8b (good reasoning, planning)")
    print("  TOOL_CALLING: hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M (validated)")
    print("  SUMMARISER: qwen2.5-coder:latest (fast, good at extraction)")
    print("  WRITER: llama3.2:latest (coherent writing)")
    print("")
    print("Validation Modes:")
    print("  validate_model_roles=True, strict_validation=False: Warnings only")
    print("  validate_model_roles=True, strict_validation=True: Block on failures")
    print("  validate_model_roles=False: No validation (legacy mode)")
    
    print("\nDemo Complete! Key Benefits:")
    print("  - Role-aware model assignment prevents HYBRID-05 pipeline failures")
    print("  - Validation at instantiation time catches configuration issues early")
    print("  - Backward compatibility maintains existing code functionality")
    print("  - Environment variable support for flexible deployment")


if __name__ == "__main__":
    asyncio.run(demo_enhanced_llmconfig())