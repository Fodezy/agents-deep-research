"""
Unit tests for SearchXNG integration.

These tests validate the SearchXNG client functionality with mocked responses
and test error handling scenarios.
"""

import pytest
import pytest_asyncio
import json
import aiohttp
import os
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from deep_researcher.tools.web_search import (
    SearchXNGClient, 
    WebpageSnippet, 
    create_web_search_tool,
    ScrapeResult
)
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.baseclass import ResearchAgent


class TestSearchXNGClient:
    """Test the SearchXNG client class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock filter agent
        self.mock_filter_agent = MagicMock(spec=ResearchAgent)
        self.host = "http://test-searxng:8080"
        self.client = SearchXNGClient(self.mock_filter_agent, self.host)

    def test_init(self):
        """Test SearchXNG client initialization."""
        assert self.client.filter_agent == self.mock_filter_agent
        assert self.client.host == "http://test-searxng:8080/search"

    def test_init_strips_trailing_slash(self):
        """Test that trailing slashes are handled correctly."""
        client = SearchXNGClient(self.mock_filter_agent, "http://test-searxng:8080/")
        assert client.host == "http://test-searxng:8080/search"

    async def test_search_success(self):
        """Test successful search with mock response."""
        # Mock SearchXNG API response
        mock_response_data = {
            "results": [
                {
                    "url": "https://example.com/page1",
                    "title": "Test Page 1",
                    "content": "Content about quantum entanglement"
                },
                {
                    "url": "https://example.com/page2", 
                    "title": "Test Page 2",
                    "content": "More quantum physics content"
                }
            ]
        }

        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)

        # Mock session and session.get properly as async context manager
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_session.get.return_value.__aexit__.return_value = None

        with patch('aiohttp.ClientSession', return_value=mock_session):
            results = await self.client.search("test query", filter_for_relevance=False)

        # Verify results
        assert len(results) == 2
        assert isinstance(results[0], WebpageSnippet)
        assert results[0].url == "https://example.com/page1"
        assert results[0].title == "Test Page 1"
        assert results[0].description == "Content about quantum entanglement"

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Test search with empty results."""
        mock_response_data = {"results": []}
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)

        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with patch('aiohttp.ClientSession', return_value=mock_session):
            results = await self.client.search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        """Test search with HTTP error response."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=500,
            message="Internal Server Error"
        )

        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with patch('aiohttp.ClientSession', return_value=mock_session):
            results = await self.client.search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_network_error(self):
        """Test search with network connectivity error."""
        mock_session = AsyncMock()
        mock_session.get.side_effect = aiohttp.ClientConnectorError(
            connection_key=MagicMock(),
            os_error=OSError("Connection failed")
        )

        with patch('aiohttp.ClientSession', return_value=mock_session):
            results = await self.client.search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_invalid_json(self):
        """Test search with invalid JSON response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with patch('aiohttp.ClientSession', return_value=mock_session):
            results = await self.client.search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_filter_results_success(self):
        """Test successful result filtering."""
        # Create test snippets
        snippets = [
            WebpageSnippet(url="https://example.com/1", title="Title 1", description="Desc 1"),
            WebpageSnippet(url="https://example.com/2", title="Title 2", description="Desc 2")
        ]

        # Mock the ResearchRunner.run call
        with patch('deep_researcher.tools.web_search.ResearchRunner.run') as mock_run:
            mock_result = MagicMock()
            mock_result.final_output_as.return_value.results_list = snippets[:1]  # Return first snippet
            mock_run.return_value = mock_result

            results = await self.client._filter_results(snippets, "test query", 1)

        assert len(results) == 1
        assert results[0] == snippets[0]

    @pytest.mark.asyncio
    async def test_filter_results_failure_fallback(self):
        """Test filter results with agent failure, should fallback to unfiltered."""
        snippets = [
            WebpageSnippet(url="https://example.com/1", title="Title 1", description="Desc 1"),
            WebpageSnippet(url="https://example.com/2", title="Title 2", description="Desc 2")
        ]

        # Mock the ResearchRunner.run to raise an exception
        with patch('deep_researcher.tools.web_search.ResearchRunner.run') as mock_run:
            mock_run.side_effect = Exception("Filter agent failed")

            results = await self.client._filter_results(snippets, "test query", 1)

        # Should fallback to unfiltered results (first 1)
        assert len(results) == 1
        assert results[0] == snippets[0]


class TestWebSearchTool:
    """Test the web search tool function."""

    def setup_method(self):
        """Set up test fixtures."""
        # Set up the environment variable for SearchXNG
        os.environ['SEARXNG_HOST'] = 'http://test-searxng:8080'
        
        self.config = LLMConfig(
            search_provider="searxng",
            reasoning_model_provider="local",
            reasoning_model="test-model",
            main_model_provider="local",
            main_model="test-model",
            fast_model_provider="local", 
            fast_model="test-model"
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up environment variable
        if 'SEARXNG_HOST' in os.environ:
            del os.environ['SEARXNG_HOST']

    @pytest.mark.asyncio
    async def test_web_search_tool_success(self):
        """Test successful web search tool execution."""
        # Mock search results
        mock_snippets = [
            WebpageSnippet(url="https://example.com/1", title="Title 1", description="Desc 1")
        ]
        
        # Mock scrape results
        mock_scrape_results = [
            ScrapeResult(url="https://example.com/1", title="Title 1", description="Desc 1", text="Content 1")
        ]

        with patch('deep_researcher.tools.web_search.init_filter_agent') as mock_init_filter:
            mock_filter_agent = MagicMock()
            mock_init_filter.return_value = mock_filter_agent
            
            with patch('deep_researcher.tools.web_search.SearchXNGClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.search.return_value = mock_snippets
                mock_client_class.return_value = mock_client
                
                with patch('deep_researcher.tools.web_search.scrape_urls') as mock_scrape:
                    mock_scrape.return_value = mock_scrape_results
                    
                    # Create and test the tool
                    web_search_tool = create_web_search_tool(self.config)
                    result = await web_search_tool("test query")

        # Verify the result
        assert result == mock_scrape_results
        mock_client.search.assert_called_once_with("test query", filter_for_relevance=False, max_results=5)

    @pytest.mark.asyncio
    async def test_web_search_tool_no_results(self):
        """Test web search tool with no search results."""
        with patch('deep_researcher.tools.web_search.init_filter_agent') as mock_init_filter:
            mock_filter_agent = MagicMock()
            mock_init_filter.return_value = mock_filter_agent
            
            with patch('deep_researcher.tools.web_search.SearchXNGClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.search.return_value = []  # No results
                mock_client_class.return_value = mock_client
                
                # Create and test the tool
                web_search_tool = create_web_search_tool(self.config)
                result = await web_search_tool("test query")

        # Should return error message
        assert isinstance(result, str)
        assert "No search results found" in result

    @pytest.mark.asyncio
    async def test_web_search_tool_scraping_failure(self):
        """Test web search tool when scraping fails."""
        mock_snippets = [
            WebpageSnippet(url="https://example.com/1", title="Title 1", description="Desc 1")
        ]

        with patch('deep_researcher.tools.web_search.init_filter_agent') as mock_init_filter:
            mock_filter_agent = MagicMock()
            mock_init_filter.return_value = mock_filter_agent
            
            with patch('deep_researcher.tools.web_search.SearchXNGClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.search.return_value = mock_snippets
                mock_client_class.return_value = mock_client
                
                with patch('deep_researcher.tools.web_search.scrape_urls') as mock_scrape:
                    mock_scrape.return_value = []  # Scraping failed
                    
                    # Create and test the tool
                    web_search_tool = create_web_search_tool(self.config)
                    result = await web_search_tool("test query")

        # Should return error message about scraping failure
        assert isinstance(result, str)
        assert "could not scrape any content" in result

    @pytest.mark.asyncio
    async def test_web_search_tool_exception(self):
        """Test web search tool with exception."""
        with patch('deep_researcher.tools.web_search.init_filter_agent') as mock_init_filter:
            mock_filter_agent = MagicMock()
            mock_init_filter.return_value = mock_filter_agent
            
            with patch('deep_researcher.tools.web_search.SearchXNGClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.search.side_effect = Exception("Test error")
                mock_client_class.return_value = mock_client
                
                # Create and test the tool
                web_search_tool = create_web_search_tool(self.config)
                result = await web_search_tool("test query")

        # Should return error message
        assert isinstance(result, str)
        assert "Search failed with Exception: Test error" in result


class TestConfigurationValidation:
    """Test SearchXNG configuration validation."""

    def test_invalid_search_provider(self):
        """Test that invalid search provider raises error."""
        with pytest.raises(ValueError, match="Invalid search provider"):
            config = LLMConfig(
                search_provider="invalid_provider",
                reasoning_model_provider="local",
                reasoning_model="test-model",
                main_model_provider="local",
                main_model="test-model",
                fast_model_provider="local",
                fast_model="test-model"
            )

    def test_searxng_provider_config(self):
        """Test SearchXNG provider configuration."""
        with patch.dict('os.environ', {'SEARXNG_HOST': 'http://localhost:8080'}):
            config = LLMConfig(
                search_provider="searxng",
                reasoning_model_provider="local",
                reasoning_model="test-model",
                main_model_provider="local",
                main_model="test-model",
                fast_model_provider="local",
                fast_model="test-model"
            )
            
            with patch('deep_researcher.tools.web_search.init_filter_agent') as mock_init_filter:
                mock_filter_agent = MagicMock()
                mock_init_filter.return_value = mock_filter_agent
                
                # Should not raise an exception
                tool = create_web_search_tool(config)
                assert tool is not None