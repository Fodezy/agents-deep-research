# deep_researcher/agents/tool_agents/search_agent.py

from agents import function_tool
from ...tools.web_search import create_web_search_tool
from ...llm_config import LLMConfig, model_supports_structured_output, get_base_url
from . import ToolAgentOutput
from ..baseclass import ResearchAgent
from ..utils.parse_output import create_type_parser

INSTRUCTIONS = """
You are a research assistant that specializes in retrieving and summarizing information from the web.

OBJECTIVE:
Given an AgentTask, follow these steps:
- Convert the 'query' into an optimized SERP search term (3–5 words)
- If an 'entity_website' is provided, include that domain in your search term
- Call the `web_search` tool
- Write a 3+ paragraph summary addressing the 'gap'
- Include citations/URLs in brackets

If the results aren’t relevant, respond “No relevant results found”.

Output **only** JSON with `output` and `sources`.
"""

def init_search_agent(config: LLMConfig) -> ResearchAgent:
    # choose the right model & search provider
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
        web_search_tool = create_web_search_tool(config)

    return ResearchAgent(
        name="WebSearchAgent",
        instructions=INSTRUCTIONS,
        tools=[web_search_tool],
        model=selected_model,
        output_type=ToolAgentOutput if model_supports_structured_output(selected_model) else None,
        output_parser=create_type_parser(ToolAgentOutput) if not model_supports_structured_output(selected_model) else None
    )
