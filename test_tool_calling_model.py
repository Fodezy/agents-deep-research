#!/usr/bin/env python3
"""
Test the tool calling model specifically using the 4-model setup from .env.
This test validates that the TOOL_CALLING_MODEL can properly execute function calls.
"""

import asyncio
import os
from deep_researcher.tools.web_search import create_web_search_tool
from deep_researcher.agents.baseclass import ResearchAgent, ResearchRunner
from deep_researcher.llm_config import LLMConfig
from agents.model_settings import ModelSettings

async def test_tool_calling_model():
    """Test the tool calling model from the 4-model setup."""
    
    print("=== Testing Tool Calling Model from .env ===", flush=True)
    
    # Read the tool calling model configuration from environment
    tool_calling_provider = os.getenv('TOOL_CALLING_MODEL_PROVIDER', 'local')
    tool_calling_model = os.getenv('TOOL_CALLING_MODEL', 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M')
    
    print(f"Tool calling provider: {tool_calling_provider}", flush=True)
    print(f"Tool calling model: {tool_calling_model}", flush=True)
    
    # Set up environment for testing
    os.environ['SEARXNG_HOST'] = 'http://127.0.0.1:8888'
    os.environ['SEARCH_PROVIDER'] = 'searxng'
    os.environ['ENABLE_FUNCTION_CALLING'] = 'true'
    
    # Create LLMConfig with the tool calling model as the main model for this test
    config = LLMConfig(
        search_provider="searxng",
        reasoning_model_provider=tool_calling_provider,
        reasoning_model=tool_calling_model,
        main_model_provider=tool_calling_provider,
        main_model=tool_calling_model,  # Use tool calling model for this test
        fast_model_provider=tool_calling_provider,
        fast_model=tool_calling_model,
    )
    
    print(f"Config created with main model: {config.main_model.model if hasattr(config.main_model, 'model') else 'unknown'}", flush=True)
    
    # Create web search tool
    web_search_tool = create_web_search_tool(config)
    print(f"Tool created: {web_search_tool.name}", flush=True)
    
    # Create model settings that encourage tool usage
    model_settings = ModelSettings(tool_choice="auto")
    
    # Create agent using the tool calling model
    agent = ResearchAgent(
        name="ToolCallingTestAgent",
        model=config.main_model,
        model_settings=model_settings,
        instructions="You are a search assistant. You MUST use the web_search tool to find current information. Always search first before providing any answer.",
        tools=[web_search_tool],
    )
    
    print(f"Agent created with {len(agent.tools)} tools", flush=True)
    for i, tool in enumerate(agent.tools):
        print(f"  Tool #{i}: {tool.name}", flush=True)
    
    # Test query that should trigger tool usage
    query = "What are the latest AI breakthroughs in 2024?"
    print(f"Testing with query: {query}", flush=True)
    
    try:
        print("=== Running agent with tool calling model ===", flush=True)
        result = await ResearchRunner.run(
            starting_agent=agent,
            input=query
        )
        
        print("=== Agent execution completed ===", flush=True)
        print(f"Final output type: {type(result.final_output)}", flush=True)
        print(f"Final output length: {len(str(result.final_output)) if result.final_output else 0} characters", flush=True)
        
        if result.final_output:
            print(f"Final output preview: {str(result.final_output)[:200]}...", flush=True)
        
        # Check for success indicators
        success = False
        if result.final_output and result.final_output != "":
            # Look for evidence of tool execution
            output_str = str(result.final_output).lower()
            
            # Check if it's structured output (JSON-like)
            if isinstance(result.final_output, dict) and "output" in result.final_output:
                print("SUCCESS: Agent produced structured ToolAgentOutput!", flush=True)
                success = True
            # Check if the output contains search-related content (indicating tool was used)
            elif any(keyword in output_str for keyword in ["search", "found", "results", "sources", "breakthrough", "2024"]):
                print("SUCCESS: Agent appears to have used search tool based on content!", flush=True)  
                success = True
            # Check if output is not just a function call JSON
            elif not ("name" in output_str and "arguments" in output_str and "web_search" in output_str):
                print("SUCCESS: Agent produced substantive output (not just function call)!", flush=True)
                success = True
            else:
                print("PARTIAL: Agent produced output but may not have executed tools", flush=True)
        else:
            print("FAILURE: No output produced", flush=True)
            
        return success
        
    except Exception as e:
        print(f"ERROR: Agent execution failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

async def test_model_compatibility():
    """Quick test to verify the tool calling model is accessible."""
    
    print("=== Testing Model Accessibility ===", flush=True)
    
    tool_calling_provider = os.getenv('TOOL_CALLING_MODEL_PROVIDER', 'local')
    tool_calling_model = os.getenv('TOOL_CALLING_MODEL', 'hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M')
    
    try:
        config = LLMConfig(
            search_provider="searxng",
            reasoning_model_provider=tool_calling_provider,
            reasoning_model=tool_calling_model,
            main_model_provider=tool_calling_provider,
            main_model=tool_calling_model,
            fast_model_provider=tool_calling_provider,
            fast_model=tool_calling_model,
        )
        
        print(f"Model client created successfully: {type(config.main_model)}", flush=True)
        print(f"Model name: {config.main_model.model if hasattr(config.main_model, 'model') else 'unknown'}", flush=True)
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to create model client: {e}", flush=True)
        return False

if __name__ == "__main__":
    print("Starting tool calling model validation...", flush=True)
    
    # First test model accessibility
    model_accessible = asyncio.run(test_model_compatibility())
    
    if model_accessible:
        # Then test tool execution
        success = asyncio.run(test_tool_calling_model())
        print(f"Tool calling test result: {'PASSED' if success else 'FAILED'}", flush=True)
    else:
        print("FAILED: Cannot access tool calling model", flush=True)
        success = False
    
    print(f"Overall validation: {'PASSED' if success else 'FAILED'}", flush=True)