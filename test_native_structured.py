#!/usr/bin/env python3
"""
Test script for native Ollama structured generation.

This script validates that our native structured generation utility works
correctly with the Ollama API before integrating it into agents.
"""

import asyncio
from pydantic import BaseModel
from typing import List
from deep_researcher.agents.utils.native_structured_generation import (
    generate_structured,
    test_structured_generation
)


class SimpleResponse(BaseModel):
    """Simple test schema"""
    message: str
    confidence: float
    success: bool


class ComplexResponse(BaseModel):
    """Complex test schema similar to agent outputs"""
    summary: str
    key_points: List[str]
    confidence: float
    sources: List[str]


async def test_basic_generation():
    """Test basic structured generation"""
    print("Testing basic structured generation...")
    
    base_url = "http://127.0.0.1:11434/v1" 
    model_name = "phi3-medium:q6"  # From .env KNOWLEDGE_GAP_MODEL
    
    try:
        result = await generate_structured(
            base_url=base_url,
            model_name=model_name,
            messages=[{
                "role": "user", 
                "content": "Respond with a test message 'Native structured generation works!', confidence 0.95, and success true."
            }],
            schema_class=SimpleResponse,
            temperature=0.0
        )
        
        print(f"SUCCESS: Basic test successful!")
        print(f"   Message: {result.message}")
        print(f"   Confidence: {result.confidence}")
        print(f"   Success: {result.success}")
        return True
        
    except Exception as e:
        print(f"FAILED: Basic test failed: {e}")
        return False


async def test_complex_generation():
    """Test complex structured generation similar to agent outputs"""
    print("\nTesting complex structured generation...")
    
    base_url = "http://127.0.0.1:11434/v1"
    model_name = "phi3-medium:q6"
    
    try:
        result = await generate_structured(
            base_url=base_url,
            model_name=model_name,
            messages=[{
                "role": "user",
                "content": """
                Analyze the concept of quantum entanglement and provide:
                - A summary of what it is
                - 3 key points about it
                - A confidence score between 0 and 1
                - 2 example source URLs
                """
            }],
            schema_class=ComplexResponse,
            temperature=0.0
        )
        
        print(f"SUCCESS: Complex test successful!")
        print(f"   Summary: {result.summary[:100]}...")
        print(f"   Key points: {len(result.key_points)} points")
        print(f"   Confidence: {result.confidence}")
        print(f"   Sources: {len(result.sources)} sources")
        return True
        
    except Exception as e:
        print(f"FAILED: Complex test failed: {e}")
        return False


async def test_built_in_function():
    """Test the built-in test function"""
    print("\nTesting built-in test function...")
    
    base_url = "http://127.0.0.1:11434/v1"
    model_name = "phi3-medium:q6"
    
    result = await test_structured_generation(base_url, model_name)
    
    if result:
        print("SUCCESS: Built-in test passed!")
    else:
        print("FAILED: Built-in test failed!")
        
    return result


async def main():
    """Run all tests"""
    print("Starting native Ollama structured generation tests...")
    print("   Using model: phi3-medium:q6")
    print("   Using endpoint: http://127.0.0.1:11434/api/chat")
    
    tests = [
        test_basic_generation,
        test_complex_generation, 
        test_built_in_function
    ]
    
    passed = 0
    for test in tests:
        if await test():
            passed += 1
            
    print(f"\nTest Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("SUCCESS: All tests passed! Native structured generation is working correctly.")
        print("   Ready to proceed with Phase 2 agent migration.")
    else:
        print("WARNING: Some tests failed. Please check Ollama setup and model availability.")
        
    return passed == len(tests)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)