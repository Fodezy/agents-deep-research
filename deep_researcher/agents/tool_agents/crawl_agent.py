"""
Agent used to crawl a website and return the results.

The SearchAgent takes as input a string in the format of AgentTask.model_dump_json(), or can take a simple starting url string as input

The Agent then:
1. Uses the crawl_website tool to crawl the website
2. Writes a 3+ paragraph summary of the crawled contents
3. Includes citations/URLs in brackets next to information sources
4. Returns the formatted summary as a string
"""

from ...tools import crawl_website
from . import ToolAgentOutput
from ...llm_config import LLMConfig, model_supports_structured_output
from ..baseclass import ResearchAgent
from ..utils.parse_output import create_type_parser
from ..utils.hierarchical_summariser import HierarchicalSummariser


INSTRUCTIONS = """
You are the SiteCrawlerAgent. You receive an AgentTask containing:
- gap: the knowledge gap to fill
- query: (optional) a short query string
- entity_website: the URL to start crawling

Your job is to call the crawler exactly once. You MUST respond with exactly this JSON—nothing else:

{
  "name": "crawl_website",
  "parameters": {
    "starting_url": "<entity_website>"
  }
}
"""


def init_crawl_agent(config: LLMConfig) -> ResearchAgent:
    selected_model = config.fast_model

    # Add hierarchical summariser for large crawled content
    summariser = HierarchicalSummariser(
        fast_model=config.fast_model,
        slow_model=config.main_model,
        chunk_size=1000,  # Larger chunks for crawled content
        overlap=150
    )

    return ResearchAgent(
        name="SiteCrawlerAgent",
        instructions=INSTRUCTIONS,
        tools=[crawl_website],
        model=selected_model,
        summariser=summariser,
        output_type=ToolAgentOutput if model_supports_structured_output(selected_model) else None,
        output_parser=create_type_parser(ToolAgentOutput) if not model_supports_structured_output(selected_model) else None
    )
