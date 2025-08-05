#!/usr/bin/env python3
"""
Demo script for Model Role Registry functionality.

This script demonstrates the 4-model architecture validation system,
showing how it prevents the tool execution pipeline failures discovered
during HYBRID-05 investigation.
"""

import asyncio
import os
from deep_researcher.agents.utils.model_role_registry import (
    ModelRole,
    ModelRoleRegistry,
    get_model_registry
)


async def demo_model_validation():
    """Demonstrate model role validation functionality."""
    print("Model Role Registry Demo - 4-Model Architecture Validation")
    print("=" * 70)
    
    registry = get_model_registry()
    
    # 1. Show role specifications
    print("\nDefined Model Roles:")
    for role in ModelRole:
        spec = registry.get_role_specification(role)
        print(f"  {role.value.upper()}:")
        print(f"    - Description: {spec.description}")
        print(f"    - Required: {spec.required_capabilities}")
        print(f"    - Function Calling: {spec.supports_function_calling}")
        print(f"    - Min Context: {spec.min_context_length}")
        print()
    
    # 2. Test individual model validation
    print("\nTesting Individual Model Validation:")
    print("-" * 40)
    
    test_models = [
        ("hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M", "local"),
        ("hermes3:8b", "local"),
        ("qwen2.5-coder:latest", "local"),
    ]
    
    for model_id, provider in test_models:
        print(f"\nAnalyzing: {model_id}")
        model_info = await registry.get_model_info(model_id, provider)
        
        print(f"  Provider: {model_info.provider}")
        print(f"  HF Model ID: {model_info.hf_model_id}")
        print(f"  Tags: {sorted(model_info.tags)}")
        print(f"  Function Calling: {model_info.supports_function_calling}")
        print(f"  Context Length: {model_info.context_length}")
        print(f"  Validated Roles: {[r.value for r in model_info.validated_roles]}")
        
        # Test against each role
        print("  Role Validation:")
        for role in ModelRole:
            is_valid, issues = registry.validate_model_for_role(model_info, role)
            status = "VALID" if is_valid else "INVALID"
            print(f"    {role.value.upper()}: {status}")
            if issues:
                for issue in issues:
                    print(f"      - {issue}")
    
    # 3. Test complete 4-model configuration
    print("\n4-Model Configuration Validation:")
    print("-" * 45)
    
    # Example configuration from .env setup
    config = {
        'PLANNER_MODEL': 'hermes3:8b',
        'PLANNER_MODEL_PROVIDER': 'local',
        'TOOL_CALLING_MODEL': 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M',
        'TOOL_CALLING_MODEL_PROVIDER': 'local',
        'SUMMARISER_MODEL': 'qwen2.5-coder:latest',
        'SUMMARISER_MODEL_PROVIDER': 'local',
        'WRITER_MODEL': 'hermes3:8b',
        'WRITER_MODEL_PROVIDER': 'local'
    }
    
    print("Testing configuration:")
    for key, value in config.items():
        if not key.endswith('_PROVIDER'):
            print(f"  {key}: {value}")
    
    validation_results = await registry.validate_4_model_config(config)
    
    print("\nValidation Results:")
    summary = registry.get_validation_summary(validation_results)
    print(summary)
    
    # 4. Show the critical difference that prevents pipeline failures
    print("\nCritical Discovery - Tool Execution Pipeline:")
    print("-" * 50)
    
    hermes_info = await registry.get_model_info('hermes3:8b', 'local')
    xlam_info = await registry.get_model_info('hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M', 'local')
    
    hermes_valid, hermes_issues = registry.validate_model_for_role(hermes_info, ModelRole.TOOL_CALLING)
    xlam_valid, xlam_issues = registry.validate_model_for_role(xlam_info, ModelRole.TOOL_CALLING)
    
    print("Previous Pipeline Failure (HYBRID-05 investigation):")
    print(f"  hermes3:8b -> ResponseOutputMessage -> functions count: 0 -> No Tools [FAILED]")
    print(f"  Tool Calling Valid: {hermes_valid}")
    if hermes_issues:
        print("  Issues:")
        for issue in hermes_issues:
            print(f"    - {issue}")
    
    print("\nFixed Pipeline (4-Model Architecture):")
    print(f"  XLAM-Model -> ResponseFunctionToolCall -> functions count: 1 -> Tool Executed [SUCCESS]")
    print(f"  Tool Calling Valid: {xlam_valid}")
    if xlam_issues:
        print("  Issues:")
        for issue in xlam_issues:
            print(f"    - {issue}")
    
    # 5. Check Ollama availability
    print("\nOllama Integration:")
    print("-" * 25)
    
    ollama_models = await registry.get_ollama_models()
    if ollama_models:
        print(f"Found {len(ollama_models)} models in Ollama:")
        for model in ollama_models[:5]:  # Show first 5
            print(f"  - {model}")
        if len(ollama_models) > 5:
            print(f"  ... and {len(ollama_models) - 5} more")
    else:
        print("WARNING: Could not connect to Ollama (this is expected if not running)")
    
    print("\nDemo Complete! The Model Role Registry provides:")
    print("   - Runtime validation of 4-model architecture")
    print("   - Prevention of tool execution pipeline failures") 
    print("   - Clear error messages for configuration issues")
    print("   - Integration with both HuggingFace and Ollama")


if __name__ == "__main__":
    asyncio.run(demo_model_validation())