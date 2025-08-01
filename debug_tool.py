#!/usr/bin/env python3
"""
Quick debug script to figure out how to call the FunctionTool.
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deep_researcher.tools.web_search import create_web_search_tool
from deep_researcher.llm_config import LLMConfig

load_dotenv()

async def debug_tool():
    """Debug the FunctionTool object."""
    print("Creating LLMConfig...")
    config = LLMConfig(
        search_provider="searxng",
        reasoning_model_provider="local",
        reasoning_model="qwen2.5-coder:latest",
        main_model_provider="local",
        main_model="qwen2.5-coder:latest",
        fast_model_provider="local",
        fast_model="qwen2.5-coder:latest"
    )
    
    print("Creating web search tool...")
    web_search_tool = create_web_search_tool(config)
    
    print(f"Tool type: {type(web_search_tool)}")
    print(f"Tool name: {web_search_tool.__name__ if hasattr(web_search_tool, '__name__') else 'No name'}")
    
    # Show all attributes
    attrs = [attr for attr in dir(web_search_tool) if not attr.startswith('_')]
    print(f"Public attributes: {attrs}")
    
    # Try different ways to call it
    print("\nTrying different calling methods...")
    
    try:
        if callable(web_search_tool):
            print("Tool is callable directly")
            result = await web_search_tool("test query")
            print(f"Direct call result type: {type(result)}")
        else:
            print("Tool is not directly callable")
    except Exception as e:
        print(f"Direct call failed: {e}")
    
    # Check for common function attributes
    for attr_name in ['func', 'function', '__wrapped__', '__call__']:
        if hasattr(web_search_tool, attr_name):
            attr = getattr(web_search_tool, attr_name)
            print(f"Has {attr_name}: {attr} (callable: {callable(attr)})")

if __name__ == "__main__":
    asyncio.run(debug_tool())