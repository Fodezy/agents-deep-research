import json
from agents import WebSearchTool
from ...tools.web_search import create_web_search_tool
from ...llm_config import LLMConfig, model_supports_structured_output, get_base_url
from . import ToolAgentOutput
from ..baseclass import ResearchAgent
from ..utils.parse_output import create_type_parser

INSTRUCTIONS = f"""You are a research assistant that specializes in retrieving and summarizing information from the web.

OBJECTIVE:
Given an AgentTask, follow these steps:
- Convert the 'query' into an optimized SERP search term for Google, limited to 3-5 words
- If an 'entity_website' is provided, make sure to include the domain name in your optimized search term
- Enter the optimized search term into the web_search tool
- After using the web_search tool, write a 3+ paragraph summary that captures the main points from the search results

GUIDELINES:
- In your summary, try to comprehensively answer/address the 'gap' provided
- Quote detailed facts, figures and numbers where available
- If the search results are not relevant, write "No relevant results found"
- Use headings and bullets to organize the summary if needed
- Include citations/URLs in brackets next to all associated information
- Do not make additional searches

Only output JSON with "output" and "sources" fields containing your research findings.
"""

def init_search_agent(config: LLMConfig) -> ResearchAgent:
    selected_model = config.fast_model
    base_url = get_base_url(selected_model)

    # Choose which underlying tool to use
    if config.search_provider == "openai":
        if "openai.com" not in base_url:
            raise ValueError(
                f"SEARCH_PROVIDER=openai but model {selected_model.model} is not OpenAI-compatible"
            )
        web_search_tool = WebSearchTool()
    else:
        web_search_tool = create_web_search_tool(config)

    return ResearchAgent(
        name="WebSearchAgent",
        instructions=INSTRUCTIONS,
        tools=[web_search_tool],
        model=selected_model,
        output_type=(
            ToolAgentOutput
            if model_supports_structured_output(selected_model)
            else None
        ),
        output_parser=(
            create_type_parser(ToolAgentOutput)
            if not model_supports_structured_output(selected_model)
            else None
        ),
    )
