"""
Agent used to crawl a website and return the results.

The SearchAgent takes as input a string in the format of AgentTask.model_dump_json(), or can take a simple starting url string as input

The Agent then:
1. Uses the crawl_website tool to crawl the website
2. Writes a 3+ paragraph summary of the crawled contents
3. Includes citations/URLs in brackets next to information sources
4. Returns the formatted summary as a string
"""

from agents import function_tool
from ...tools.crawl_website import crawl_website
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

Your task is to crawl the website and return relevant information. You have access to the crawl_website tool.

You MUST respond with valid JSON in exactly this format:

{
  "output": "A summary of relevant information found on the website that addresses the knowledge gap",
  "sources": ["https://url1.com", "https://url2.com", "..."]
}

Use the crawl_website tool to gather information from the target website, then summarize the key findings that address the knowledge gap.
"""


def init_crawl_agent(config: LLMConfig) -> ResearchAgent:
    selected_model = config.fast_model

    # Add hierarchical summariser for large crawled content
    summariser = HierarchicalSummariser(
        fast_model=config.main_model,  # Use main model as specified in requirements
        slow_model=config.main_model,
        chunk_size=1000,  # Larger chunks for crawled content
        overlap=150
    )

    # Create a proper function to decorate
    def crawl_website_func(url: str):
        """Crawl a website starting from a given URL and return scraped content."""
        return crawl_website(url)

    crawl_tool = function_tool(
        name_override="crawl_website",
        description_override="Crawl a website starting from a given URL and return scraped content."
    )(crawl_website_func)
    
    # Expose inner function for tests
    crawl_tool.func = crawl_website_func
    crawl_tool.__name__ = crawl_website_func.__name__
    
    return ResearchAgent(
        name="SiteCrawlerAgent",
        instructions=INSTRUCTIONS,
        tools=[crawl_tool],
        model=selected_model,
        summariser=summariser,
        output_type=ToolAgentOutput if model_supports_structured_output(selected_model) else None,
        output_parser=create_type_parser(ToolAgentOutput) if not model_supports_structured_output(selected_model) else None
    )
