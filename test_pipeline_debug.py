#!/usr/bin/env python3
"""
Simple pipeline debugging test to isolate the tool execution issue.
"""

import asyncio
import os
from deep_researcher.tools.web_search import create_web_search_tool
from deep_researcher.agents.baseclass import ResearchAgent, ResearchRunner
from deep_researcher.llm_config import create_default_config
from agents.model_settings import ModelSettings

async def test_tool_execution_pipeline():
    """Test the tool execution pipeline with local models."""
    
    # Use local models as requested - back to original model that produced text output
    os.environ['MAIN_MODEL_PROVIDER'] = 'local'
    os.environ['MAIN_MODEL'] = 'qwen2.5-coder:latest'  # Try with original model
    os.environ['LOCAL_MODEL_URL'] = 'http://localhost:11434/v1'
    os.environ['SEARXNG_HOST'] = 'http://127.0.0.1:8888'
    os.environ['SEARCH_PROVIDER'] = 'searxng'
    os.environ['ENABLE_FUNCTION_CALLING'] = 'true'
    
    print("=== Setting up test configuration ===", flush=True)
    config = create_default_config()
    print(f"Config main model: {config.main_model.model if hasattr(config.main_model, 'model') else 'unknown'}", flush=True)
    
    print("=== Creating web search tool ===", flush=True)
    web_search_tool = create_web_search_tool(config)
    print(f"Tool created: {web_search_tool.name}", flush=True)
    
    print("=== Creating search agent ===", flush=True)
    # Create model settings that allow but don't force tool usage to test shim
    model_settings = ModelSettings(tool_choice="auto")
    
    agent = ResearchAgent(
        name="WebSearchAgent",
        model=config.main_model,
        model_settings=model_settings,
        instructions="You are a web search assistant. You MUST use the web_search tool to find current information. Never provide answers from your training data alone. Always search first.",
        tools=[web_search_tool],
    )
    
    print(f"Agent created with {len(agent.tools)} tools", flush=True)
    for i, tool in enumerate(agent.tools):
        print(f"  Tool #{i}: {tool}", flush=True)
    
    print("=== Running agent with search query ===", flush=True)
    query = "What are the latest developments in quantum computing in 2024?"
    
    try:
        result = await ResearchRunner.run(
            starting_agent=agent,
            input=query
        )
        
        print("=== Agent execution completed ===", flush=True)
        print(f"Final output type: {type(result.final_output)}", flush=True)
        print(f"Final output: {result.final_output}", flush=True)
        
        # Check if we have valid ToolAgentOutput
        if isinstance(result.final_output, dict) and "output" in result.final_output:
            print("SUCCESS: Tool execution pipeline worked!", flush=True)
            return True
        else:
            print("FAILURE: Tool execution pipeline failed", flush=True)
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Agent execution failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting pipeline debugging test...", flush=True)
    success = asyncio.run(test_tool_execution_pipeline())
    print(f"Test result: {'PASSED' if success else 'FAILED'}", flush=True)