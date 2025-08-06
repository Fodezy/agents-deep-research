"""Tests for HYBRID-04a-04 CrawlAgent Outlines integration"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from deep_researcher.agents.tool_agents.crawl_agent import OutlinesCrawlAgent, init_crawl_agent
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.utils.outlines_schemas import EnhancedToolAgentOutput


class TestOutlinesCrawlAgent:
    """Test OutlinesCrawlAgent dual-path architecture"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock LLMConfig for testing"""
        config = Mock(spec=LLMConfig)
        config.fast_model = Mock()
        config.main_model = Mock()
        return config
    
    @pytest.fixture
    def mock_crawl_tool(self):
        """Mock crawl website tool"""
        tool = Mock()
        tool.name = "crawl_website"
        tool.func = AsyncMock(return_value="Mock crawled content: Company financial report shows strong Q4 performance...")
        return tool
    
    @pytest.fixture
    def mock_summariser(self):
        """Mock hierarchical summariser"""
        summariser = Mock()
        summariser.summarise_large_content = AsyncMock(return_value={
            "final_summary": "Summarized financial report content..."
        })
        return summariser
    
    @pytest.fixture
    def mock_selected_model(self):
        """Mock selected model for testing"""
        model = Mock()
        model.chat = AsyncMock()
        return model
    
    def test_agent_initialization_with_outlines_support(self, mock_config, mock_crawl_tool, mock_summariser):
        """Test agent initialization when Outlines is supported"""
        with patch('deep_researcher.agents.tool_agents.crawl_agent.model_supports_structured_output', return_value=True), \
             patch('deep_researcher.agents.tool_agents.crawl_agent.outlines.Generator') as mock_generator, \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole') as mock_role:
            
            mock_config.get_model_for_role.return_value = Mock()
            mock_generator.return_value = Mock()
            
            agent = OutlinesCrawlAgent(mock_config, mock_crawl_tool, mock_summariser)
            
            assert agent.name == "SiteCrawlerAgent"
            assert agent.supports_structured is True
            assert agent.outlines_generator is not None
            assert agent.output_type == EnhancedToolAgentOutput
    
    def test_agent_initialization_without_outlines_support(self, mock_config, mock_crawl_tool, mock_summariser):
        """Test agent initialization when Outlines is not supported"""
        with patch('deep_researcher.agents.tool_agents.crawl_agent.model_supports_structured_output', return_value=False), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole') as mock_role:
            
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = OutlinesCrawlAgent(mock_config, mock_crawl_tool, mock_summariser)
            
            assert agent.name == "SiteCrawlerAgent"
            assert agent.supports_structured is False
            assert agent.outlines_generator is None
            assert agent.output_parser is not None
    
    def test_model_role_consistency_with_search_agent(self, mock_config, mock_crawl_tool, mock_summariser):
        """Test that CrawlAgent uses SUMMARISER role like SearchAgent"""
        with patch('deep_researcher.agents.tool_agents.crawl_agent.model_supports_structured_output', return_value=False), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole') as mock_role:
            
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = OutlinesCrawlAgent(mock_config, mock_crawl_tool, mock_summariser)
            
            # Verify SUMMARISER role was requested
            from deep_researcher.agents.utils.model_role_registry import ModelRole
            mock_config.get_model_for_role.assert_called_with(ModelRole.SUMMARISER)
    
    @pytest.mark.asyncio
    async def test_parameter_extraction_from_dict_input(self, mock_config, mock_crawl_tool, mock_summariser):
        """Test parameter extraction from dictionary input"""
        with patch('deep_researcher.agents.tool_agents.crawl_agent.model_supports_structured_output', return_value=False), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = OutlinesCrawlAgent(mock_config, mock_crawl_tool, mock_summariser)
            
            # Mock the parameter extraction
            input_data = '{"gap": "financial performance", "entity_website": "https://company.com/report", "query": "Q4 results"}'
            
            with patch.object(agent, '_legacy_path', return_value={"output": "test", "sources": []}) as mock_legacy:
                await agent.run_implementation(input_data)
                
                # Verify parameter extraction was called
                assert mock_legacy.called
    
    @pytest.mark.asyncio
    async def test_hierarchical_summariser_integration(self, mock_config, mock_crawl_tool, mock_summariser):
        """Test integration with HierarchicalSummariser for large content"""
        with patch('deep_researcher.agents.tool_agents.crawl_agent.model_supports_structured_output', return_value=False), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            mock_config.get_model_for_role.return_value = Mock()
            
            # Mock large crawled content (>2000 chars)
            large_content = "A" * 3000
            mock_crawl_tool.func.return_value = large_content
            
            agent = OutlinesCrawlAgent(mock_config, mock_crawl_tool, mock_summariser)
            
            with patch.object(agent, '_legacy_path', return_value={"output": "test", "sources": []}) as mock_legacy:
                await agent.run_implementation("https://example.com")
                
                # Verify summariser was called for large content
                mock_summariser.summarise_large_content.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_structured_path_execution(self, mock_config, mock_crawl_tool, mock_summariser):
        """Test structured path execution with Outlines"""
        with patch('deep_researcher.agents.tool_agents.crawl_agent.model_supports_structured_output', return_value=True), \
             patch('deep_researcher.agents.tool_agents.crawl_agent.outlines.Generator') as mock_generator_class, \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            # Setup mocks
            mock_generator = Mock()
            mock_generator.generate.return_value = {
                "output": "The website shows strong financial performance with revenue growth of 15%...",
                "sources": ["https://company.com/report"]
            }
            mock_generator_class.return_value = mock_generator
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = OutlinesCrawlAgent(mock_config, mock_crawl_tool, mock_summariser)
            
            # Test structured execution
            result = await agent.run_implementation("https://company.com/report")
            
            assert result["processing_method"] == "structured"
            assert result["confidence"] == 0.95
            assert "processing_time_ms" in result
            assert "strong financial performance" in result["output"]
            assert result["sources"] == ["https://company.com/report"]
    
    @pytest.mark.asyncio
    async def test_legacy_path_execution(self, mock_config, mock_crawl_tool, mock_summariser, mock_selected_model):
        """Test legacy path execution with JSON parsing"""
        with patch('deep_researcher.agents.tool_agents.crawl_agent.model_supports_structured_output', return_value=False), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            mock_config.get_model_for_role.return_value = mock_selected_model
            
            # Setup model response
            mock_response = Mock()
            mock_response.content = '{"output": "Legacy crawl analysis of company website...", "sources": ["https://company.com"]}'
            mock_selected_model.chat.return_value = mock_response
            
            agent = OutlinesCrawlAgent(mock_config, mock_crawl_tool, mock_summariser)
            
            # Mock the output parser properly
            mock_parser = Mock()
            mock_parser.parse.return_value = {
                "output": "Legacy crawl analysis of company website...",
                "sources": ["https://company.com"]
            }
            agent.output_parser = mock_parser
            
            # Test legacy execution
            result = await agent.run_implementation("https://company.com")
            
            assert result["processing_method"] == "legacy"
            assert result["confidence"] == 0.85
            assert "processing_time_ms" in result
            assert result["output"] == "Legacy crawl analysis of company website..."
            assert result["sources"] == ["https://company.com"]
    
    @pytest.mark.asyncio
    async def test_structured_path_fallback_to_legacy(self, mock_config, mock_crawl_tool, mock_summariser, mock_selected_model):
        """Test fallback from structured to legacy when generation fails"""
        with patch('deep_researcher.agents.tool_agents.crawl_agent.model_supports_structured_output', return_value=True), \
             patch('deep_researcher.agents.tool_agents.crawl_agent.outlines.Generator') as mock_generator_class, \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            # Setup generator that fails during generation
            mock_generator = Mock()
            mock_generator.generate.side_effect = Exception("Generation failed")
            mock_generator_class.return_value = mock_generator
            mock_config.get_model_for_role.return_value = mock_selected_model
            
            # Setup model response for fallback
            mock_response = Mock()
            mock_response.content = '{"output": "Fallback crawl analysis...", "sources": ["https://fallback.com"]}'
            mock_selected_model.chat.return_value = mock_response
            
            agent = OutlinesCrawlAgent(mock_config, mock_crawl_tool, mock_summariser)
            
            # Mock parser for legacy path
            mock_parser = Mock()
            mock_parser.parse.return_value = {
                "output": "Fallback crawl analysis...",
                "sources": ["https://fallback.com"]
            }
            agent.output_parser = mock_parser
            
            # Test fallback execution
            result = await agent.run_implementation("https://test.com")
            
            assert result["processing_method"] == "legacy"
            assert result["confidence"] == 0.85
            assert result["output"] == "Fallback crawl analysis..."
    
    @pytest.mark.asyncio
    async def test_error_fallback_response(self, mock_config, mock_crawl_tool, mock_summariser, mock_selected_model):
        """Test error fallback when all processing fails"""
        with patch('deep_researcher.agents.tool_agents.crawl_agent.model_supports_structured_output', return_value=False), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            mock_config.get_model_for_role.return_value = mock_selected_model
            
            # Setup model to fail
            mock_selected_model.chat.side_effect = Exception("Model failed")
            
            agent = OutlinesCrawlAgent(mock_config, mock_crawl_tool, mock_summariser)
            
            # Test error fallback
            result = await agent.run_implementation("https://test.com")
            
            assert result["processing_method"] == "error_fallback"
            assert result["confidence"] == 0.0
            assert "Crawl processing failed" in result["output"]
            assert result["sources"] == ["https://test.com"]
    
    @pytest.mark.asyncio
    async def test_crawl_tool_execution(self, mock_config, mock_crawl_tool, mock_summariser):
        """Test crawl tool is properly executed"""
        with patch('deep_researcher.agents.tool_agents.crawl_agent.model_supports_structured_output', return_value=False), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = OutlinesCrawlAgent(mock_config, mock_crawl_tool, mock_summariser)
            
            with patch.object(agent, '_legacy_path', return_value={"output": "test", "sources": []}) as mock_legacy:
                await agent.run_implementation("https://example.com")
                
                # Verify crawl tool was called
                mock_crawl_tool.func.assert_called_once()
                assert mock_legacy.called
    
    def test_backward_compatibility_with_existing_consumers(self, mock_config, mock_crawl_tool, mock_summariser):
        """Test that existing consumers can still use the agent"""
        with patch('deep_researcher.agents.tool_agents.crawl_agent.model_supports_structured_output', return_value=False), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = OutlinesCrawlAgent(mock_config, mock_crawl_tool, mock_summariser)
            
            # Agent should have expected interface
            assert hasattr(agent, 'name')
            assert hasattr(agent, 'tools')
            assert hasattr(agent, 'model')
            assert hasattr(agent, 'summariser')
            assert hasattr(agent, 'run_implementation')


class TestInitCrawlAgent:
    """Test init_crawl_agent function"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock LLMConfig for testing"""
        config = Mock(spec=LLMConfig)
        config.fast_model = Mock()
        config.main_model = Mock()
        return config
    
    def test_init_crawl_agent_returns_outlines_agent(self, mock_config):
        """Test that init_crawl_agent returns OutlinesCrawlAgent"""
        with patch('deep_researcher.agents.utils.model_role_registry.ModelRole') as mock_role:
            
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = init_crawl_agent(mock_config)
            
            assert isinstance(agent, OutlinesCrawlAgent)
            assert agent.name == "SiteCrawlerAgent"
    
    def test_crawl_tool_creation_and_exposure(self, mock_config):
        """Test crawl tool creation and function exposure"""
        with patch('deep_researcher.agents.utils.model_role_registry.ModelRole') as mock_role:
            
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = init_crawl_agent(mock_config)
            
            # Should have exactly one crawl tool
            assert len(agent.tools) == 1
            crawl_tool = agent.tools[0]
            
            # Tool should have proper attributes for testing
            assert hasattr(crawl_tool, 'func')
            assert hasattr(crawl_tool, '__name__')
            assert crawl_tool.__name__ == 'crawl_website_func'
    
    def test_hierarchical_summariser_configuration(self, mock_config):
        """Test HierarchicalSummariser is properly configured"""
        with patch('deep_researcher.agents.utils.model_role_registry.ModelRole') as mock_role:
            
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = init_crawl_agent(mock_config)
            
            assert agent.summariser is not None
            # CrawlAgent should have larger chunk size than SearchAgent
            assert hasattr(agent.summariser, 'chunker')
    
    def test_model_role_usage(self, mock_config):
        """Test that SUMMARISER model role is used consistently"""
        with patch('deep_researcher.agents.utils.model_role_registry.ModelRole') as mock_role:
            
            mock_config.get_model_for_role.return_value = Mock()
            
            init_crawl_agent(mock_config)
            
            # Verify SUMMARISER role was requested
            from deep_researcher.agents.utils.model_role_registry import ModelRole
            mock_config.get_model_for_role.assert_called_with(ModelRole.SUMMARISER)