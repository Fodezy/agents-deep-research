#!/usr/bin/env python3
"""
Test the function call shim with synthetic data to validate it works.
"""

import json
from openai.types.chat import ChatCompletionMessage
from deep_researcher.llm_config import create_default_config  # This loads the monkey patches

def test_function_call_shim():
    """Test the shim converts plaintext function calls to structured calls."""
    
    print("=== Testing Function Call Shim ===", flush=True)
    
    # Import the patched converter 
    from agents.models.openai_chatcompletions import _Converter
    
    # Test case 1: Plaintext function call with wrapper tags (like we saw from hermes3)
    test_message_1 = ChatCompletionMessage(
        role="assistant",
        content='</REFLECTION>\n{"name": "web_search", "arguments": {"query": "latest developments in quantum computing 2024"}}\n</tool_call>',
        tool_calls=None
    )
    
    print("Test 1: Function call with wrapper tags", flush=True)
    print(f"  Input content: {test_message_1.content}", flush=True)
    
    result_1 = _Converter.message_to_output_items(test_message_1)
    print(f"  Output items: {len(result_1)}", flush=True)
    
    function_calls_1 = [item for item in result_1 if hasattr(item, 'name') and hasattr(item, 'arguments')]
    print(f"  Function calls detected: {len(function_calls_1)}", flush=True)
    
    if function_calls_1:
        fc = function_calls_1[0]
        print(f"    Name: {fc.name}", flush=True)
        print(f"    Arguments: {fc.arguments}", flush=True)
        print("  SUCCESS: Wrapper tag format detected and converted!", flush=True)
    else:
        print("  ❌ FAILURE: Wrapper tag format not detected", flush=True)
    
    print("", flush=True)
    
    # Test case 2: Clean JSON function call (no wrapper tags)
    test_message_2 = ChatCompletionMessage(
        role="assistant", 
        content='{"name": "web_search", "arguments": {"query": "artificial intelligence trends"}}',
        tool_calls=None
    )
    
    print("Test 2: Clean JSON function call", flush=True)
    print(f"  Input content: {test_message_2.content}", flush=True)
    
    result_2 = _Converter.message_to_output_items(test_message_2)
    print(f"  Output items: {len(result_2)}", flush=True)
    
    function_calls_2 = [item for item in result_2 if hasattr(item, 'name') and hasattr(item, 'arguments')]
    print(f"  Function calls detected: {len(function_calls_2)}", flush=True)
    
    if function_calls_2:
        fc = function_calls_2[0]
        print(f"    Name: {fc.name}", flush=True)
        print(f"    Arguments: {fc.arguments}", flush=True)
        print("  SUCCESS: Clean JSON format detected and converted!", flush=True)
    else:
        print("  FAILURE: Clean JSON format not detected", flush=True)
    
    print("", flush=True)
    
    # Test case 3: Arguments-first format
    test_message_3 = ChatCompletionMessage(
        role="assistant",
        content='{"arguments": {"query": "machine learning frameworks"}, "name": "web_search"}',
        tool_calls=None
    )
    
    print("Test 3: Arguments-first JSON format", flush=True)
    print(f"  Input content: {test_message_3.content}", flush=True)
    
    result_3 = _Converter.message_to_output_items(test_message_3)
    print(f"  Output items: {len(result_3)}", flush=True)
    
    function_calls_3 = [item for item in result_3 if hasattr(item, 'name') and hasattr(item, 'arguments')]
    print(f"  Function calls detected: {len(function_calls_3)}", flush=True)
    
    if function_calls_3:
        fc = function_calls_3[0]
        print(f"    Name: {fc.name}", flush=True)
        print(f"    Arguments: {fc.arguments}", flush=True)
        print("  SUCCESS: Arguments-first format detected and converted!", flush=True)
    else:
        print("  FAILURE: Arguments-first format not detected", flush=True)
    
    print("", flush=True)
    
    # Test case 4: Regular text (should not be converted)
    test_message_4 = ChatCompletionMessage(
        role="assistant",
        content="This is just regular text without any function calls.",
        tool_calls=None
    )
    
    print("Test 4: Regular text (should not convert)", flush=True)
    print(f"  Input content: {test_message_4.content}", flush=True)
    
    result_4 = _Converter.message_to_output_items(test_message_4)
    print(f"  Output items: {len(result_4)}", flush=True)
    
    function_calls_4 = [item for item in result_4 if hasattr(item, 'name') and hasattr(item, 'arguments')]
    print(f"  Function calls detected: {len(function_calls_4)}", flush=True)
    
    if len(function_calls_4) == 0:
        print("  SUCCESS: Regular text correctly ignored!", flush=True)
    else:
        print("  FAILURE: Regular text incorrectly detected as function call", flush=True)
    
    # Summary
    print("=== Shim Validation Summary ===", flush=True)
    success_count = sum([
        len(function_calls_1) > 0,
        len(function_calls_2) > 0, 
        len(function_calls_3) > 0,
        len(function_calls_4) == 0
    ])
    print(f"Tests passed: {success_count}/4", flush=True)
    
    if success_count == 4:
        print("ALL TESTS PASSED: Function call shim is working correctly!", flush=True)
        return True
    else:
        print("SOME TESTS FAILED: Function call shim needs refinement", flush=True)
        return False

if __name__ == "__main__":
    # Load the monkey patches
    config = create_default_config()
    
    success = test_function_call_shim()
    print(f"Overall result: {'PASSED' if success else 'FAILED'}", flush=True)