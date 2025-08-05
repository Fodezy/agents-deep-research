#!/usr/bin/env python3
"""
Test the complete tool execution pipeline with the shim.
This simulates the local model returning plaintext function calls.
"""

import asyncio
import os
import json
from unittest.mock import AsyncMock, MagicMock, patch
from deep_researcher.tools.web_search import create_web_search_tool
from deep_researcher.agents.baseclass import ResearchAgent, ResearchRunner
from deep_researcher.llm_config import create_default_config
from agents.model_settings import ModelSettings

async def test_complete_pipeline_with_shim():
    """Test the complete pipeline with simulated local model response."""
    
    print("=== Complete Pipeline Test with Shim ===", flush=True)
    
    # Set up configuration
    os.environ['SEARXNG_HOST'] = 'http://127.0.0.1:8888'
    os.environ['SEARCH_PROVIDER'] = 'searxng'
    os.environ['ENABLE_FUNCTION_CALLING'] = 'true'
    
    config = create_default_config()
    
    # Create web search tool
    web_search_tool = create_web_search_tool(config)
    print(f"Created tool: {web_search_tool.name}", flush=True)
    
    # Create agent 
    model_settings = ModelSettings(tool_choice="auto")
    agent = ResearchAgent(
        name="TestAgent",
        model=config.main_model,
        model_settings=model_settings,
        instructions="You are a search assistant. Use web_search to find information.",
        tools=[web_search_tool],
    )
    print(f"Created agent with {len(agent.tools)} tools", flush=True)
    
    # Mock the OpenAI client to return a plaintext function call (like local models do)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = '</REFLECTION>\n{"name": "web_search", "arguments": {"query": "test search query"}}\n</tool_call>'
    mock_response.choices[0].message.tool_calls = None  # No structured tool calls
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150
    
    print("=== Simulating local model response with plaintext function call ===", flush=True)
    print(f"Mock response content: {mock_response.choices[0].message.content}", flush=True)
    
    # Mock the actual tool execution to return test data
    mock_search_result = "Test search results about the query"
    
    async def mock_tool_execution(*args, **kwargs):
        print(f"[MOCK] Tool executed with args: {args}, kwargs: {kwargs}", flush=True)
        return mock_search_result
    
    # Patch the model's _fetch_response method directly to avoid OpenAI client complexities
    async def mock_fetch_response(*args, **kwargs):
        print("[MOCK] _fetch_response called, returning mock ChatCompletion", flush=True)
        return mock_response
    
    with patch.object(agent.model, '_fetch_response', side_effect=mock_fetch_response):
        # Also patch the web search tool's actual function
        with patch.object(web_search_tool, 'func', side_effect=mock_tool_execution):
            try:
                print("=== Running agent with mocked response ===", flush=True)
                result = await ResearchRunner.run(
                    starting_agent=agent,
                    input="Test query for search"
                )
                
                print("=== Agent execution completed ===", flush=True)
                print(f"Final output type: {type(result.final_output)}", flush=True)
                print(f"Final output: {result.final_output}", flush=True)
                
                # Check if the pipeline worked
                if result.final_output and result.final_output != "":
                    # Look for evidence that the tool was executed
                    if "test search query" in str(result.final_output).lower() or mock_search_result in str(result.final_output):
                        print("SUCCESS: Tool execution pipeline worked with shim!", flush=True)
                        return True
                    else:
                        print("PARTIAL: Agent produced output but may not have used tool results", flush=True)
                        print(f"Expected to find: '{mock_search_result}' or 'test search query'", flush=True)
                        return False
                else:
                    print("FAILURE: No output produced", flush=True)
                    return False
                    
            except Exception as e:
                print(f"ERROR: Agent execution failed: {e}", flush=True)
                import traceback
                traceback.print_exc()
                return False

if __name__ == "__main__":
    print("Starting complete pipeline test with shim...", flush=True)
    success = asyncio.run(test_complete_pipeline_with_shim())
    print(f"Test result: {'PASSED' if success else 'FAILED'}", flush=True)