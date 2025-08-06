"""Tests for HYBRID-04a-03 SearchAgent Outlines integration"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from deep_researcher.agents.tool_agents.search_agent import OutlinesSearchAgent, init_search_agent
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.utils.outlines_schemas import EnhancedToolAgentOutput


class TestOutlinesSearchAgent:
    """Test OutlinesSearchAgent dual-path architecture"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock LLMConfig for testing"""
        config = Mock(spec=LLMConfig)
        config.search_provider = "searxng"
        config.fast_model = Mock()
        config.main_model = Mock()
        return config
    
    @pytest.fixture
    def mock_web_search_tool(self):
        """Mock web search tool"""
        tool = Mock()
        tool.name = "web_search"
        tool.func = AsyncMock(return_value="Mock search results: AI breakthrough 2024...")
        return tool
    
    @pytest.fixture
    def mock_summariser(self):
        """Mock hierarchical summariser"""
        return Mock()
    
    @pytest.fixture
    def mock_selected_model(self):
        """Mock selected model for testing"""
        model = Mock()
        model.chat = AsyncMock()
        return model
    
    def test_agent_initialization_with_outlines_support(self, mock_config, mock_web_search_tool, mock_summariser):
        """Test agent initialization when Outlines is supported"""
        with patch('deep_researcher.agents.tool_agents.search_agent.model_supports_structured_output', return_value=True), \
             patch('deep_researcher.agents.tool_agents.search_agent.outlines.Generator') as mock_generator, \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole') as mock_role:
            
            mock_config.get_model_for_role.return_value = Mock()
            mock_generator.return_value = Mock()
            
            agent = OutlinesSearchAgent(mock_config, mock_web_search_tool, mock_summariser)
            
            assert agent.name == "WebSearchAgent"
            assert agent.supports_structured is True
            assert agent.outlines_generator is not None
            assert agent.output_type == EnhancedToolAgentOutput
    
    def test_agent_initialization_without_outlines_support(self, mock_config, mock_web_search_tool, mock_summariser):
        """Test agent initialization when Outlines is not supported"""
        with patch('deep_researcher.agents.tool_agents.search_agent.model_supports_structured_output', return_value=False), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole') as mock_role:
            
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = OutlinesSearchAgent(mock_config, mock_web_search_tool, mock_summariser)
            
            assert agent.name == "WebSearchAgent"
            assert agent.supports_structured is False
            assert agent.outlines_generator is None
            assert agent.output_parser is not None
    
    def test_outlines_initialization_failure_fallback(self, mock_config, mock_web_search_tool, mock_summariser):
        """Test fallback to legacy when Outlines initialization fails"""
        with patch('deep_researcher.agents.tool_agents.search_agent.model_supports_structured_output', return_value=True), \
             patch('deep_researcher.agents.tool_agents.search_agent.outlines.Generator', side_effect=Exception("Outlines error")), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole') as mock_role:
            
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = OutlinesSearchAgent(mock_config, mock_web_search_tool, mock_summariser)
            
            assert agent.supports_structured is False
            assert agent.outlines_generator is None
            assert agent.output_parser is not None
    
    @pytest.mark.asyncio
    async def test_parameter_extraction_from_dict_input(self, mock_config, mock_web_search_tool, mock_summariser):
        """Test parameter extraction from dictionary input"""
        with patch('deep_researcher.agents.tool_agents.search_agent.model_supports_structured_output', return_value=False), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = OutlinesSearchAgent(mock_config, mock_web_search_tool, mock_summariser)
            
            # Mock the parameter extraction
            input_data = '{"gap": "AI breakthroughs", "query": "AI 2024", "entity_website": "https://ai.org"}'
            
            with patch.object(agent, '_legacy_path', return_value={"output": "test", "sources": []}) as mock_legacy:
                await agent.run_implementation(input_data)
                
                # Verify parameter extraction was called
                assert mock_legacy.called
    
    @pytest.mark.asyncio
    async def test_structured_path_execution(self, mock_config, mock_web_search_tool, mock_summariser):
        """Test structured path execution with Outlines"""
        with patch('deep_researcher.agents.tool_agents.search_agent.model_supports_structured_output', return_value=True), \
             patch('deep_researcher.agents.tool_agents.search_agent.outlines.Generator') as mock_generator_class, \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            # Setup mocks
            mock_generator = Mock()
            mock_generator.generate.return_value = {
                "output": "AI has made significant breakthroughs in 2024...",
                "sources": ["https://ai.org", "https://tech.com"]
            }
            mock_generator_class.return_value = mock_generator
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = OutlinesSearchAgent(mock_config, mock_web_search_tool, mock_summariser)
            
            # Test structured execution
            result = await agent.run_implementation("AI breakthroughs 2024")
            
            assert result["processing_method"] == "structured"
            assert result["confidence"] == 0.95
            assert "processing_time_ms" in result
            assert result["output"] == "AI has made significant breakthroughs in 2024..."
            assert result["sources"] == ["https://ai.org", "https://tech.com"]
    
    @pytest.mark.asyncio
    async def test_legacy_path_execution(self, mock_config, mock_web_search_tool, mock_summariser, mock_selected_model):
        """Test legacy path execution with JSON parsing"""
        with patch('deep_researcher.agents.tool_agents.search_agent.model_supports_structured_output', return_value=False), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            mock_config.get_model_for_role.return_value = mock_selected_model
            
            # Setup model response
            mock_response = Mock()
            mock_response.content = '{"output": "Legacy AI research summary...", "sources": ["https://legacy.com"]}'
            mock_selected_model.chat.return_value = mock_response
            
            agent = OutlinesSearchAgent(mock_config, mock_web_search_tool, mock_summariser)
            
            # Mock the output parser properly
            mock_parser = Mock()
            mock_parser.parse.return_value = {
                "output": "Legacy AI research summary...",
                "sources": ["https://legacy.com"]
            }
            agent.output_parser = mock_parser
            
            # Test legacy execution
            result = await agent.run_implementation("AI research")
            
            assert result["processing_method"] == "legacy"
            assert result["confidence"] == 0.85
            assert "processing_time_ms" in result
            assert result["output"] == "Legacy AI research summary..."
            assert result["sources"] == ["https://legacy.com"]
    
    @pytest.mark.asyncio
    async def test_structured_path_fallback_to_legacy(self, mock_config, mock_web_search_tool, mock_summariser, mock_selected_model):
        """Test fallback from structured to legacy when generation fails"""
        with patch('deep_researcher.agents.tool_agents.search_agent.model_supports_structured_output', return_value=True), \
             patch('deep_researcher.agents.tool_agents.search_agent.outlines.Generator') as mock_generator_class, \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            # Setup generator that fails during generation
            mock_generator = Mock()
            mock_generator.generate.side_effect = Exception("Generation failed")
            mock_generator_class.return_value = mock_generator
            mock_config.get_model_for_role.return_value = mock_selected_model
            
            # Setup model response for fallback
            mock_response = Mock()
            mock_response.content = '{"output": "Fallback summary...", "sources": ["https://fallback.com"]}'
            mock_selected_model.chat.return_value = mock_response
            
            agent = OutlinesSearchAgent(mock_config, mock_web_search_tool, mock_summariser)
            
            # Test fallback execution
            result = await agent.run_implementation("test query")
            
            assert result["processing_method"] == "legacy"
            assert result["confidence"] == 0.85
            assert result["output"] == "Fallback summary..."
    
    @pytest.mark.asyncio
    async def test_error_fallback_response(self, mock_config, mock_web_search_tool, mock_summariser, mock_selected_model):
        """Test error fallback when all processing fails"""
        with patch('deep_researcher.agents.tool_agents.search_agent.model_supports_structured_output', return_value=False), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            mock_config.get_model_for_role.return_value = mock_selected_model
            
            # Setup model to fail
            mock_selected_model.chat.side_effect = Exception("Model failed")
            
            agent = OutlinesSearchAgent(mock_config, mock_web_search_tool, mock_summariser)
            
            # Test error fallback
            result = await agent.run_implementation("test query")
            
            assert result["processing_method"] == "error_fallback"
            assert result["confidence"] == 0.0
            assert "Search processing failed" in result["output"]
            assert result["sources"] == []
    
    @pytest.mark.asyncio
    async def test_web_search_tool_execution(self, mock_config, mock_web_search_tool, mock_summariser):
        """Test web search tool is properly executed"""
        with patch('deep_researcher.agents.tool_agents.search_agent.model_supports_structured_output', return_value=False), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = OutlinesSearchAgent(mock_config, mock_web_search_tool, mock_summariser)
            
            with patch.object(agent, '_legacy_path', return_value={"output": "test", "sources": []}) as mock_legacy:
                await agent.run_implementation("test search")
                
                # Verify web search tool was called
                mock_web_search_tool.func.assert_called_once()
                assert mock_legacy.called
    
    def test_backward_compatibility_with_existing_consumers(self, mock_config, mock_web_search_tool, mock_summariser):
        """Test that existing consumers can still use the agent"""
        with patch('deep_researcher.agents.tool_agents.search_agent.model_supports_structured_output', return_value=False), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole'):
            
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = OutlinesSearchAgent(mock_config, mock_web_search_tool, mock_summariser)
            
            # Agent should have expected interface
            assert hasattr(agent, 'name')
            assert hasattr(agent, 'tools')
            assert hasattr(agent, 'model')
            assert hasattr(agent, 'summariser')
            assert hasattr(agent, 'run_implementation')


class TestInitSearchAgent:
    """Test init_search_agent function"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock LLMConfig for testing"""
        config = Mock(spec=LLMConfig)
        config.search_provider = "searxng"
        config.fast_model = Mock()
        config.main_model = Mock()
        return config
    
    def test_init_search_agent_returns_outlines_agent(self, mock_config):
        """Test that init_search_agent returns OutlinesSearchAgent"""
        with patch('deep_researcher.agents.tool_agents.search_agent.create_web_search_tool') as mock_create_tool, \
             patch('deep_researcher.agents.tool_agents.search_agent.get_base_url', return_value="http://localhost"), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole') as mock_role:
            
            mock_create_tool.return_value = Mock(name="web_search")
            mock_config.get_model_for_role.return_value = Mock()
            
            agent = init_search_agent(mock_config)
            
            assert isinstance(agent, OutlinesSearchAgent)
            assert agent.name == "WebSearchAgent"
    
    def test_search_provider_validation(self, mock_config):
        """Test search provider validation logic"""
        mock_config.search_provider = "openai"
        
        with patch('deep_researcher.agents.tool_agents.search_agent.create_web_search_tool') as mock_create_tool, \
             patch('deep_researcher.agents.tool_agents.search_agent.get_base_url', return_value="http://localhost"), \
             patch('deep_researcher.agents.utils.model_role_registry.ModelRole') as mock_role:
            
            mock_create_tool.return_value = Mock(name="web_search")
            mock_config.get_model_for_role.return_value = Mock()
            
            # Should raise error for OpenAI provider with non-OpenAI model
            with pytest.raises(ValueError, match="SEARCH_PROVIDER='openai' but using non-OpenAI model"):
                init_search_agent(mock_config)