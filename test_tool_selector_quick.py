#!/usr/bin/env python3
"""Quick test for ToolSelectorAgent"""

import asyncio
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.tool_selector_agent import init_tool_selector_agent

async def test_tool_selector():
    config = LLMConfig(search_provider='searxng')
    ts_agent = init_tool_selector_agent(config)
    result = await ts_agent.run_native_tool_selection("Research quantum entanglement applications")
    
    print(f"Schema version: {result.schema_version}")
    print(f"Tasks count: {len(result.tasks)}")
    for task in result.tasks:
        print(f"Agent: {task.agent}, Query: {task.query}")
    
    valid_agents = ["search_agent", "crawl_agent", "WebSearchAgent", "CrawlAgent"]
    assert result.schema_version == 1
    for task in result.tasks:
        assert task.agent in valid_agents
    print("SUCCESS!")

if __name__ == "__main__":
    asyncio.run(test_tool_selector())