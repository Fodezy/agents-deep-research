"""Integration tests for HierarchicalSummariser with agents"""
import pytest
from unittest.mock import Mock, AsyncMock
from deep_researcher.agents.tool_agents.search_agent import init_search_agent
from deep_researcher.agents.tool_agents.crawl_agent import init_crawl_agent
from deep_researcher.llm_config import create_default_config


class MockResponse:
    """Mock response for model.chat() calls"""
    def __init__(self, content: str):
        self.content = content


@pytest.fixture
def mock_config():
    """Create mock config with mocked models"""
    config = create_default_config()
    
    # Mock the models
    config.fast_model = Mock()
    config.fast_model.chat = AsyncMock(return_value=MockResponse("Fast model response"))
    
    config.main_model = Mock()
    config.main_model.chat = AsyncMock(return_value=MockResponse("Main model response"))
    
    return config


class TestAgentIntegration:
    """Test agent integration with hierarchical summariser"""
    
    def test_search_agent_has_summariser(self, mock_config):
        """Test that search agent is initialized with summariser"""
        agent = init_search_agent(mock_config)
        
        assert hasattr(agent, 'summariser')
        assert agent.summariser is not None
        assert agent.summariser.chunker.chunk_size == 800
        assert agent.summariser.chunker.overlap == 100
    
    def test_crawl_agent_has_summariser(self, mock_config):
        """Test that crawl agent is initialized with summariser"""
        agent = init_crawl_agent(mock_config)
        
        assert hasattr(agent, 'summariser')
        assert agent.summariser is not None
        assert agent.summariser.chunker.chunk_size == 1000  # Larger for crawl
        assert agent.summariser.chunker.overlap == 150
    
    @pytest.mark.asyncio
    async def test_process_large_content_integration(self, mock_config):
        """Test process_large_content method integration"""
        agent = init_search_agent(mock_config)
        
        # Test with large content that should trigger summarisation (much larger)
        large_content = "This is a long sentence that contains multiple words and ideas for comprehensive testing. " * 500
        
        result = await agent.process_large_content(large_content, "test context")
        
        # Should return summarized content (from mock), not original
        assert result == "Main model response"  # From our mock
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_process_small_content_passthrough(self, mock_config):
        """Test that small content passes through unchanged"""
        agent = init_search_agent(mock_config)
        
        # Test with small content
        small_content = "Small content."
        
        result = await agent.process_large_content(small_content)
        
        # Should return original content unchanged
        assert result == small_content
    
    @pytest.mark.asyncio
    async def test_agent_without_summariser(self):
        """Test agent behavior when no summariser is provided"""
        from deep_researcher.agents.baseclass import ResearchAgent
        
        # Create agent without summariser
        agent = ResearchAgent(
            name="TestAgent",
            instructions="Test instructions",
            tools=[],
            model=Mock()
        )
        
        content = "Any content here."
        result = await agent.process_large_content(content)
        
        # Should return content unchanged when no summariser
        assert result == content


class TestSummariserConfiguration:
    """Test different summariser configurations"""
    
    def test_search_vs_crawl_configuration(self, mock_config):
        """Test that search and crawl agents have different chunk sizes"""
        search_agent = init_search_agent(mock_config)
        crawl_agent = init_crawl_agent(mock_config)
        
        # Search agent: smaller chunks for quick processing
        assert search_agent.summariser.chunker.chunk_size == 800
        assert search_agent.summariser.chunker.overlap == 100
        
        # Crawl agent: larger chunks for better context
        assert crawl_agent.summariser.chunker.chunk_size == 1000
        assert crawl_agent.summariser.chunker.overlap == 150