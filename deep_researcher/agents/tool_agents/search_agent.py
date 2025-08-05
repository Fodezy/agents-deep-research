# deep_researcher/agents/tool_agents/search_agent.py

from agents import function_tool
from ...tools.web_search import create_web_search_tool
from ...llm_config import LLMConfig, model_supports_structured_output, get_base_url
from . import ToolAgentOutput
from ..baseclass import ResearchAgent
from ..utils.parse_output import create_type_parser
from ..utils.hierarchical_summariser import HierarchicalSummariser

INSTRUCTIONS = """
You are the WebSearchAgent. You receive an AgentTask containing:
- gap: the knowledge gap to fill  
- query: a 3-6 word search string  
- entity_website: (optional) a domain to bias your search

Your task is to perform a web search and return the results. You have access to the web_search tool.

IMPORTANT: You must first use the web_search tool to find information, then provide your final response.

After using the web_search tool, you MUST respond with valid JSON in exactly this format:

{
  "output": "A summary of your search findings that addresses the knowledge gap",
  "sources": ["https://url1.com", "https://url2.com", "..."]
}

Steps:
1. Use the web_search tool with the provided query
2. Analyze the search results
3. Write a summary that addresses the knowledge gap
4. List the source URLs from the search results
5. Format your response as the JSON above
"""



def init_search_agent(config: LLMConfig) -> ResearchAgent:
    # choose the right model & search provider
    from ..utils.model_role_registry import ModelRole
    selected_model = config.get_model_for_role(ModelRole.SUMMARISER)
    print(f"[init_search_agent] search_provider={config.search_provider!r}, summariser_model={selected_model!r}", flush=True)
    provider_base_url = get_base_url(selected_model)
    if config.search_provider == "openai" and 'openai.com' not in provider_base_url:
        raise ValueError(f"SEARCH_PROVIDER='openai' but using non-OpenAI model {selected_model}")
    
    # Create the web search tool (already wrapped as FunctionTool)
    web_search_tool = create_web_search_tool(config)

    # Add hierarchical summariser for large content
    summariser = HierarchicalSummariser(
        fast_model=config.fast_model,
        slow_model=config.main_model,
        chunk_size=800,
        overlap=100
    )

    print(f"[init_search_agent] registered tool: {getattr(web_search_tool, 'name', 'web_search')!r}", flush=True)
    return ResearchAgent(
        name="WebSearchAgent",
        instructions=INSTRUCTIONS,
        tools=[web_search_tool],
        model=selected_model,
        summariser=summariser,
        output_type=ToolAgentOutput if model_supports_structured_output(selected_model) else None,
        output_parser=create_type_parser(ToolAgentOutput) if not model_supports_structured_output(selected_model) else None
    )
