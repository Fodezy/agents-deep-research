#!/usr/bin/env python3
"""Test qwen3:14b model capability detection"""

from deep_researcher.agents.utils.model_role_registry import ModelRoleRegistry, ModelRole

async def test_qwen3_detection():
    registry = ModelRoleRegistry()
    
    # Test qwen3:14b detection
    model_info = await registry.get_model_info('qwen3:14b', 'local')
    
    print(f"Model: qwen3:14b")
    print(f"Tags: {model_info.tags}")
    print(f"Validated roles: {model_info.validated_roles}")
    print(f"Has text-generation: {'text-generation' in model_info.tags}")
    print(f"Can be WRITER: {ModelRole.WRITER in model_info.validated_roles}")
    
    # Test validation
    result = await registry.validate_model_for_role('qwen3:14b', 'local', ModelRole.WRITER)
    print(f"\nValidation result: {result.is_valid}")
    print(f"Message: {result.message}")
    if result.suggestions:
        for suggestion in result.suggestions:
            print(f"Suggestion: {suggestion}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_qwen3_detection())