import asyncio
import json
import os
import ssl
from typing import List, Optional, Union

import aiohttp
from agents import function_tool
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from ..agents.baseclass import ResearchAgent, ResearchRunner
from ..agents.utils.parse_output import create_type_parser
from ..llm_config import LLMConfig, model_supports_structured_output

load_dotenv()
CONTENT_LENGTH_LIMIT = 10000  # Trim scraped content so we don't exceed token limits

# ------- DEFINE TYPES -------

class ScrapeResult(BaseModel):
    url: str = Field(description="The URL of the webpage")
    text: str = Field(description="The full text content of the webpage")
    title: str = Field(description="The title of the webpage")
    description: str = Field(description="A short description of the webpage")


class WebpageSnippet(BaseModel):
    url: str = Field(description="The URL of the webpage")
    title: str = Field(description="The title of the webpage")
    description: Optional[str] = Field(description="A short description of the webpage")


class SearchResults(BaseModel):
    results_list: List[WebpageSnippet]


# ------- DEFINE TOOL -------

def create_web_search_tool(config: LLMConfig):
    """
    Returns a function_tool that performs a web search and scrapes the top results.
    """
    filter_agent = init_filter_agent(config)

    if config.search_provider == "serper":
        search_client = SerperClient(filter_agent)
    elif config.search_provider == "searxng":
        search_client = SearchXNGClient(filter_agent, config.searxng_host)
    else:
        raise ValueError(f"Invalid search provider: {config.search_provider}")

    @function_tool
    async def web_search(query: str) -> Union[List[ScrapeResult], str]:
        """Perform a web search for a given query and return scraped results."""
        try:
            snippets = await search_client.search(
                query, filter_for_relevance=True, max_results=5
            )
            return await scrape_urls(snippets)
        except Exception as e:
            return f"Sorry, I encountered an error while searching: {e!s}"

    # ensure the tool has a stable name
    web_search.__name__ = "web_search"
    return web_search


# ------- FILTER AGENT -------

FILTER_AGENT_INSTRUCTIONS = """
You are a search result filter. Your task is to analyze a list of search results and return only the relevant ones.
Return JSON in this exact format:
{
  "results_list": [
    {"url": "...", "title": "...", "description": "..."}
  ]
}
"""

def init_filter_agent(config: LLMConfig) -> ResearchAgent:
    selected_model = config.reasoning_model
    return ResearchAgent(
        name="SearchFilterAgent",
        instructions=FILTER_AGENT_INSTRUCTIONS,
        model=selected_model,
        output_type=(SearchResults if model_supports_structured_output(selected_model) else None),
        output_parser=(create_type_parser(SearchResults) if not model_supports_structured_output(selected_model) else None),
    )


# ------- UNDERLYING SEARCH CLIENTS -------

# Shared SSL context to allow older ciphers if needed
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.set_ciphers("DEFAULT:@SECLEVEL=1")


class SerperClient:
    """A client for the Serper API to perform Google searches."""

    def __init__(self, filter_agent: ResearchAgent, api_key: str = None):
        self.filter_agent = filter_agent
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("No SERPER_API_KEY configured")

        self.url = "https://google.serper.dev/search"
        self.headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

    async def search(self, query: str, filter_for_relevance: bool = True, max_results: int = 5) -> List[WebpageSnippet]:
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                self.url, headers=self.headers, json={"q": query, "autocorrect": False}
            ) as response:
                response.raise_for_status()
                data = await response.json()
                snippets = [
                    WebpageSnippet(
                        url=item.get("link", ""),
                        title=item.get("title", ""),
                        description=item.get("snippet", ""),
                    )
                    for item in data.get("organic", [])
                ]

        if not snippets:
            return []
        if not filter_for_relevance:
            return snippets[:max_results]
        return await self._filter_results(snippets, query, max_results)

    async def _filter_results(self, results: List[WebpageSnippet], query: str, max_results: int) -> List[WebpageSnippet]:
        payload = [r.model_dump() for r in results]
        prompt = f"Original search query: {query}\n\nSearch results:\n{json.dumps(payload, indent=2)}\n\nReturn up to {max_results} relevant results."
        try:
            out = await ResearchRunner.run(self.filter_agent, prompt)
            return out.final_output_as(SearchResults).results_list
        except Exception:
            return results[:max_results]


class SearchXNGClient:
    """A client for a SearchXNG-compatible API endpoint."""

    def __init__(self, filter_agent: ResearchAgent, host: str):
        self.filter_agent = filter_agent
        self.host = host.rstrip("/") + "/search"

    async def search(self, query: str, filter_for_relevance: bool = True, max_results: int = 5) -> List[WebpageSnippet]:
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            params = {"q": query, "format": "json"}
            async with session.get(self.host, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                snippets = [
                    WebpageSnippet(
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        description=item.get("content", ""),
                    )
                    for item in data.get("results", [])
                ]

        if not snippets:
            return []
        if not filter_for_relevance:
            return snippets[:max_results]
        return await self._filter_results(snippets, query, max_results)

    async def _filter_results(self, results: List[WebpageSnippet], query: str, max_results: int) -> List[WebpageSnippet]:
        payload = [r.model_dump() for r in results]
        prompt = f"Original search query: {query}\n\nSearch results:\n{json.dumps(payload, indent=2)}\n\nReturn up to {max_results} relevant results."
        try:
            out = await ResearchRunner.run(self.filter_agent, prompt)
            return out.final_output_as(SearchResults).results_list
        except Exception:
            return results[:max_results]


# ------- SCRAPING LOGIC -------

async def scrape_urls(items: List[WebpageSnippet]) -> List[ScrapeResult]:
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_and_process_url(session, item) for item in items if item.url]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, ScrapeResult)]


async def fetch_and_process_url(session: aiohttp.ClientSession, item: WebpageSnippet) -> ScrapeResult:
    # skip binary or document URLs
    if any(item.url.lower().endswith(ext) for ext in (".pdf", ".doc", ".jpg", ".png")):
        return ScrapeResult(
            url=item.url,
            title=item.title,
            description=item.description,
            text="Error fetching content: unsupported file type"
        )

    try:
        async with session.get(item.url, timeout=8) as resp:
            if resp.status != 200:
                return ScrapeResult(
                    url=item.url,
                    title=item.title,
                    description=item.description,
                    text=f"Error fetching content: HTTP {resp.status}"
                )
            html = await resp.text()
    except Exception as e:
        return ScrapeResult(
            url=item.url,
            title=item.title,
            description=item.description,
            text=f"Error fetching content: {e}"
        )

    # extract text
    text = await asyncio.get_event_loop().run_in_executor(None, html_to_text, html)
    return ScrapeResult(
        url=item.url,
        title=item.title,
        description=item.description,
        text=text[:CONTENT_LENGTH_LIMIT],
    )


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    tags = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote")
    return "\n".join(el.get_text(strip=True) for el in soup.find_all(tags) if el.get_text(strip=True))


def is_valid_url(url: str) -> bool:
    # filter out obvious non‐HTML resources
    blocked = [
        ".pdf", ".doc", ".xls", ".ppt", ".zip", ".rar",
        ".png", ".jpg", ".jpeg", ".gif", ".mp3", ".mp4"
    ]
    return not any(ext in url.lower() for ext in blocked)
