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
- query: a 3–6 word search string  
- entity_website: (optional) a domain to bias your search

When you respond, you MUST emit exactly one function call in JSON—no prose, no summaries—in this format:

{
  "name": "web_search",
  "parameters": {
    "query": "<your 3–6 word search here>"
  }
}

That will trigger the actual `web_search` tool. Do NOT write anything else.
"""



def init_search_agent(config: LLMConfig) -> ResearchAgent:
    # choose the right model & search provider
    print(f"[init_search_agent] search_provider={config.search_provider!r}, fast_model={config.fast_model!r}", flush=True)

    selected_model = config.fast_model
    provider_base_url = get_base_url(selected_model)
    if config.search_provider == "openai" and 'openai.com' not in provider_base_url:
        raise ValueError(f"SEARCH_PROVIDER='openai' but using non-OpenAI model {selected_model}")
    if config.search_provider == "openai":
        web_search_tool = function_tool(
            name="web_search",
            description="Perform a web search for a given query and return scraped results."
        )(create_web_search_tool(config))
    else:
        print(f"[init_search_agent] using custom web search tool for {config.search_provider!r}", flush=True)
        web_search_tool = create_web_search_tool(config)

    # Add hierarchical summariser for large content
    summariser = HierarchicalSummariser(
        fast_model=config.fast_model,
        slow_model=config.main_model,
        chunk_size=800,
        overlap=100
    )

    print(f"[init_search_agent] registered tool: {web_search_tool.__name__!r}", flush=True)
    return ResearchAgent(
        name="WebSearchAgent",
        instructions=INSTRUCTIONS,
        tools=[web_search_tool],
        model=selected_model,
        summariser=summariser,
        output_type=ToolAgentOutput if model_supports_structured_output(selected_model) else None,
        output_parser=create_type_parser(ToolAgentOutput) if not model_supports_structured_output(selected_model) else None
    )
