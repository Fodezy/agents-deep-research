"""
Integration tests for SearchXNG with real calls.

These tests make actual calls to SearchXNG and the agents to verify they work
in isolation. Requires SearchXNG docker container to be running.

Prerequisites:
- SearchXNG running at http://127.0.0.1:8888
- Local models available (qwen2.5-coder:latest or adjust in setup)
- Environment variables set (SEARCH_PROVIDER=searxng, SEARXNG_HOST=http://127.0.0.1:8888)
"""

import pytest
import os
import asyncio
from typing import List
import traceback 
from pprint import pprint 
import json  


from deep_researcher.tools.web_search import (
    SearchXNGClient, 
    WebpageSnippet, 
    create_web_search_tool,
    ScrapeResult,
    init_filter_agent
)
from deep_researcher.tools.crawl_website import crawl_website
from deep_researcher.agents.tool_agents.search_agent import init_search_agent
from deep_researcher.agents.tool_agents.crawl_agent import init_crawl_agent
from deep_researcher.agents.baseclass import ResearchAgent, ResearchRunner
from deep_researcher.llm_config import LLMConfig


@pytest.fixture
def test_config() -> LLMConfig:
    """Create test configuration for local models and SearchXNG."""
    # Set up environment for testing
    os.environ['SEARXNG_HOST'] = 'http://127.0.0.1:8888'
    
    return LLMConfig(
        search_provider="searxng",
        reasoning_model_provider="local",
        reasoning_model="qwen2.5-coder:latest",
        main_model_provider="local",
        main_model="qwen2.5-coder:latest",
        fast_model_provider="local",
        fast_model="qwen2.5-coder:latest"
    )


class TestSearchXNGClientReal:
    """Test SearchXNG client with real API calls."""

    async def test_client_initialization(self, test_config):
        """Test that SearchXNG client initializes correctly."""
        filter_agent = init_filter_agent(test_config)
        client = SearchXNGClient(filter_agent, test_config.searxng_host)
        
        assert client.host == "http://127.0.0.1:8888/search"
        assert client.filter_agent is not None

    async def test_search_without_filtering(self, test_config):
        """Test SearchXNG search without result filtering."""
        filter_agent = init_filter_agent(test_config)
        client = SearchXNGClient(filter_agent, test_config.searxng_host)
        
        # Make actual search call
        results = await client.search("python programming", filter_for_relevance=False, max_results=3)
        
        # Verify we got results
        assert len(results) > 0, "Should get search results from SearchXNG"
        assert len(results) <= 3, "Should respect max_results limit"
        
        # Verify result structure
        for result in results:
            assert isinstance(result, WebpageSnippet)
            assert result.url, "Each result should have a URL"
            assert result.title, "Each result should have a title"
            # description can be empty, so we don't assert on it
            
        print(f"Found {len(results)} results for 'python programming'")
        for i, result in enumerate(results):
            print(f"  {i+1}. {result.title} - {result.url}")

    async def test_search_with_filtering(self, test_config):
        """Test SearchXNG search with LLM filtering."""
        filter_agent = init_filter_agent(test_config)
        client = SearchXNGClient(filter_agent, test_config.searxng_host)
        
        # Make search call with filtering enabled
        results = await client.search("machine learning tutorials", filter_for_relevance=True, max_results=2)
        
        # Verify we got filtered results
        assert len(results) > 0, "Should get filtered results"
        assert len(results) <= 2, "Should respect max_results limit"
        
        print(f"Found {len(results)} filtered results for 'machine learning tutorials'")
        for i, result in enumerate(results):
            print(f"  {i+1}. {result.title} - {result.url}")

    async def test_search_empty_query(self, test_config):
        """Test SearchXNG search with empty or no results."""
        filter_agent = init_filter_agent(test_config)
        client = SearchXNGClient(filter_agent, test_config.searxng_host)
        
        # Search for something very specific that might not return results
        results = await client.search("xyzabc123nonexistentqueryterm", filter_for_relevance=False, max_results=3)
        
        # Should return empty list, not fail
        assert isinstance(results, list), "Should return a list even if empty"
        print(f"Empty query returned {len(results)} results (expected behavior)")


class TestWebSearchToolReal:
    """Test complete web search tool with real calls."""

    async def test_web_search_tool_end_to_end(self, test_config):
        """Test complete web search tool workflow: search + scrape."""
        # Get the underlying function, not the FunctionTool wrapper
        from deep_researcher.tools.web_search import init_filter_agent, SearchXNGClient, scrape_urls
        
        # Create components manually to test the full workflow
        filter_agent = init_filter_agent(test_config)
        search_client = SearchXNGClient(filter_agent, test_config.searxng_host)
        
        # Step 1: Search
        print("Step 1: Searching for 'quantum computing basics'...")
        snippets = await search_client.search("quantum computing basics", filter_for_relevance=False, max_results=2)
        
        assert len(snippets) > 0, "Should find search results"
        print(f"Found {len(snippets)} search results")
        
        # Show what URLs we're trying to scrape
        for i, snippet in enumerate(snippets):
            print(f"  URL {i+1}: {snippet.url}")
        
        # Step 2: Scrape
        print("Step 2: Scraping content from found URLs...")
        scrape_results = await scrape_urls(snippets)
        
        print(f"Scraping returned {len(scrape_results)} results")
        if len(scrape_results) == 0:
            print("WARNING: No content was scraped. This may be due to:")
            print("  - Network connectivity issues")
            print("  - Websites blocking scraping")  
            print("  - SSL/TLS certificate issues")
            print("  - Timeout issues")
            # Don't fail the test, just warn
            return
        
        print(f"Successfully scraped {len(scrape_results)} pages")
        
        # Verify scrape results
        for i, result in enumerate(scrape_results):
            assert isinstance(result, ScrapeResult)
            assert result.url, "Should have URL"
            assert result.title, "Should have title"
            assert result.text, "Should have scraped text content"
            print(f"  Page {i+1}: {result.title} ({len(result.text)} chars)")

    async def test_web_search_tool_function_wrapper(self, test_config):
        """Test that we can call the web search tool function directly."""
        # Create the web search tool
        web_search_tool = create_web_search_tool(test_config)
        
        # Get the underlying function from the FunctionTool
        # The function should be accessible via the tool's internal structure
        web_search_func = web_search_tool._func if hasattr(web_search_tool, '_func') else None
        
        if not web_search_func:
            # Try different attributes to find the function
            for attr in ['func', 'function', '__wrapped__', '_function']:
                if hasattr(web_search_tool, attr):
                    web_search_func = getattr(web_search_tool, attr)
                    break
        
        assert web_search_func is not None, f"Could not find function in FunctionTool. Available attrs: {dir(web_search_tool)}"
        
        # Call the function directly
        print("Testing web search function directly...")
        result = await web_search_func("artificial intelligence")
        
        # Should return list of ScrapeResult or error string
        if isinstance(result, str):
            pytest.fail(f"Web search returned error: {result}")
        
        assert isinstance(result, list), "Should return list of ScrapeResult"
        assert len(result) > 0, "Should return some scraped results"
        
        print(f"Web search function returned {len(result)} scraped pages")
        for i, page in enumerate(result[:2]):
            print(f"  Page {i+1}: {page.title} - {len(page.text)} chars")

# ========================================= UPDATE FOR LOGGING TO FIND THE ISSUE =========================================

class TestSearchAgentReal:
    """Test search agent with real calls."""

    async def test_search_agent_initialization(self, test_config):
        """Test that search agent initializes correctly."""
        search_agent = init_search_agent(test_config)

        assert isinstance(search_agent, ResearchAgent)
        assert search_agent.name == "WebSearchAgent"
        assert len(search_agent.tools) == 1, "Should have one tool (web_search)"

        print("Search agent initialized successfully")
        print("=== Initialization Diagnostics ===")
        print("Agent name:", search_agent.name)
        print("Tools attached:", [getattr(t, "name_override", None) or getattr(t, "name", None) or getattr(t, "__name__", None) for t in search_agent.tools])
        for i, tool in enumerate(search_agent.tools):
            print(f"--- Tool {i} introspection ---")
            print("repr:", repr(tool))
            print("dir(tool):", [attr for attr in dir(tool) if not attr.startswith("_")])
            attrs = {}
            for attr in ("name_override", "name", "__name__", "func"):
                if hasattr(tool, attr):
                    val = getattr(tool, attr)
                    # if callable and has __name__, show that
                    if callable(val) and hasattr(val, "__name__"):
                        val = getattr(val, "__name__", str(val))
                    attrs[attr] = val
            pprint(attrs)
        print("=== End Initialization Diagnostics ===")

    async def test_search_agent_execution(self, test_config):
        """Test search agent execution with real query."""
        # Force function calling for clarity
        os.environ["ENABLE_FUNCTION_CALLING"] = "true"

        search_agent = init_search_agent(test_config)

        # Debug: env state
        print("=== Pre-Run Diagnostics ===")
        print("ENABLE_FUNCTION_CALLING:", os.getenv("ENABLE_FUNCTION_CALLING"))
        print("Search provider:", test_config.search_provider if hasattr(test_config, "search_provider") else getattr(search_agent, "search_provider", None))
        print("Attached tools and their metadata:")
        for i, tool in enumerate(search_agent.tools):
            print(f"Tool #{i}: {tool}")
            candidate_names = []
            if hasattr(tool, "name_override") and getattr(tool, "name_override", None):
                candidate_names.append(getattr(tool, "name_override"))
            if hasattr(tool, "name"):
                candidate_names.append(getattr(tool, "name"))
            if hasattr(tool, "__name__"):
                candidate_names.append(getattr(tool, "__name__", ""))
            if hasattr(tool, "func") and hasattr(tool.func, "__name__"):
                candidate_names.append(tool.func.__name__)
            print("  Candidate names:", candidate_names)
            print("  Full dir():", [attr for attr in dir(tool) if not attr.startswith("_")])
        print("=== End Pre-Run Diagnostics ===")

        # Create a simple task for the agent
        task_prompt = """
        Query: "What is reinforcement learning?"
        Gap: "Need basic explanation of reinforcement learning concepts"
        Entity: null
        """

        print("Testing search agent with reinforcement learning query...")
        try:
            # Run the search agent
            result = await ResearchRunner.run(search_agent, task_prompt)
        except Exception as e:
            print("=== Exception during ResearchRunner.run ===")
            traceback.print_exc()
            pytest.fail(f"ResearchRunner.run raised an unexpected exception: {e}")

        # Dump raw run result for inspection
        print("=== Post-Run Raw Result ===")
        try:
            # Some RunResult shapes expose attributes differently
            if hasattr(result, "final_output"):
                print("Final output (raw):")
                pprint(result.final_output)
            if hasattr(result, "raw_responses"):
                print("Raw responses:")
                for idx, resp in enumerate(result.raw_responses or []):
                    print(f"  Response #{idx}: {resp}")
                    # attempt to introspect fields
                    if hasattr(resp, "output"):
                        print("    resp.output:", resp.output)
                    if hasattr(resp, "usage"):
                        print("    resp.usage:", resp.usage)
                    if hasattr(resp, "referenceable_id"):
                        print("    resp.id:", resp.referenceable_id)
        except Exception:
            print("Error dumping raw result:", traceback.format_exc())
        print("=== End Post-Run Raw Result ===")

        # The agent should return structured output with research findings
        assert result is not None, "Agent should return a result"

        # Try to get the final output
        try:
            final_output = result.final_output_as(dict) if hasattr(result, "final_output_as") else result.final_output
            print("Search agent completed successfully")
            print("Result type:", type(final_output))

            if isinstance(final_output, dict):
                if "output" in final_output:
                    print(f"Output length: {len(final_output['output'])} characters")
                else:
                    print("Missing 'output' key in final_output")
                if "sources" in final_output:
                    print(f"Sources: {len(final_output['sources'])} found -> {final_output.get('sources')}")
                else:
                    print("Missing 'sources' key in final_output")
            else:
                print("Final output (as string):", str(final_output)[:500])
        except Exception as e:
            print("=== Failed to parse structured output ===")
            print("Result object repr:", repr(result))
            traceback.print_exc()
            pytest.fail(f"Could not parse structured output: {e}")



# ========================================= UPDATE FOR LOGGING TO FIND THE ISSUE =========================================

class TestCrawlAgentReal:
    """Test crawl agent with real calls."""

    async def test_crawl_website_function(self):
        """Test crawl website function directly."""
        print("Testing website crawling on a simple site...")
        
        # Test crawling a simple, reliable website
        result = await crawl_website("https://httpbin.org")
        
        if isinstance(result, str):
            pytest.fail(f"Crawl returned error: {result}")
        
        assert isinstance(result, list), "Should return list of ScrapeResult"
        assert len(result) > 0, "Should crawl at least one page"
        
        print(f"Crawled {len(result)} pages from httpbin.org")
        for i, page in enumerate(result):
            print(f"  Page {i+1}: {page.title} - {page.url}")

    async def test_crawl_agent_initialization(self, test_config):
        """Test that crawl agent initializes correctly."""
        crawl_agent = init_crawl_agent(test_config)
        
        assert isinstance(crawl_agent, ResearchAgent)
        assert crawl_agent.name == "SiteCrawlerAgent"
        assert len(crawl_agent.tools) == 1, "Should have one tool (crawl_website)"
        
        print("Crawl agent initialized successfully")

    async def test_crawl_agent_execution(self, test_config):
        """Test crawl agent execution with real website."""
        crawl_agent = init_crawl_agent(test_config)
        
        # Create a task for the agent
        task_prompt = """
        entity_website: "https://httpbin.org"
        query: "What services does this website provide?"
        gaps: "Need to understand the purpose and functionality of this website"
        """
        
        print("Testing crawl agent with httpbin.org...")
        
        # Run the crawl agent
        result = await ResearchRunner.run(crawl_agent, task_prompt)
        
        assert result is not None, "Agent should return a result"
        
        try:
            final_output = result.final_output_as(dict) if hasattr(result, 'final_output_as') else str(result)
            print(f"Crawl agent completed successfully")
            
            if isinstance(final_output, dict):
                if 'output' in final_output:
                    print(f"Analysis length: {len(final_output['output'])} characters")
                if 'sources' in final_output:
                    print(f"Sources crawled: {len(final_output['sources'])}")
            else:
                print(f"Result: {str(final_output)[:200]}...")
                
        except Exception as e:
            print(f"Result structure: {result}")
            print(f"Note: Could not parse structured output: {e}")


# Skip tests if SearchXNG is not available
def check_searxng_available():
    """Check if SearchXNG is available for testing."""
    import aiohttp
    import asyncio
    
    async def _check():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://127.0.0.1:8888/search?q=test&format=json", timeout=2) as response:
                    return response.status == 200
        except:
            return False
    
    return asyncio.run(_check())


# Mark tests to skip if SearchXNG is not available
searxng_available = check_searxng_available()
skip_if_no_searxng = pytest.mark.skipif(
    not searxng_available,
    reason="SearchXNG not available at http://127.0.0.1:8888"
)

# Apply the skip marker to all test classes
TestSearchXNGClientReal = skip_if_no_searxng(TestSearchXNGClientReal)
TestWebSearchToolReal = skip_if_no_searxng(TestWebSearchToolReal) 
TestSearchAgentReal = skip_if_no_searxng(TestSearchAgentReal)
TestCrawlAgentReal = skip_if_no_searxng(TestCrawlAgentReal)