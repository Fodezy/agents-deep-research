"""
HYBRID-04a-05: End-to-end integration tests for Outlines-based Summariser agents

Tests the complete workflow from agent initialization through structured/legacy generation
with performance benchmarking and regression validation.
"""
import pytest
import time
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.tool_agents import init_tool_agents
from deep_researcher.agents.tool_agents.search_agent import OutlinesSearchAgent
from deep_researcher.agents.tool_agents.crawl_agent import OutlinesCrawlAgent
from deep_researcher.agents.utils.outlines_schemas import EnhancedToolAgentOutput


class TestEndToEndIntegration:
    """End-to-end integration tests for SearchAgent and CrawlAgent"""
    
    @pytest.fixture
    def real_config(self):
        """Real LLMConfig for integration testing"""
        return LLMConfig(search_provider='searxng')
    
    @pytest.fixture
    def mock_tools(self):
        """Mock tools for controlled testing"""
        search_tool = Mock()
        search_tool.name = "web_search"
        search_tool.func = AsyncMock(return_value="""
        Search Results:
        1. AI Breakthrough 2024 - New neural architectures show 40% improvement
           URL: https://ai-research.org/breakthrough-2024
        2. Machine Learning Advances - Quantum-enhanced algorithms published
           URL: https://ml-journal.com/quantum-ml-2024
        """)
        
        crawl_tool = Mock()
        crawl_tool.name = "crawl_website" 
        crawl_tool.func = AsyncMock(return_value="""
        Company Annual Report 2024
        
        Financial Highlights:
        - Revenue grew 25% to $2.4B 
        - Net income increased 30% to $480M
        - Strong performance across all business segments
        
        Market Position:
        - Leading market share in core segments
        - Successful expansion into new markets
        - Innovation pipeline remains strong
        
        Outlook:
        - Positive growth trajectory expected
        - New product launches planned for Q2
        """)
        
        return {"search": search_tool, "crawl": crawl_tool}
    
    def test_agent_initialization_with_real_config(self, real_config):
        """Test agent initialization with real configuration"""
        agents = init_tool_agents(real_config)
        
        assert "WebSearchAgent" in agents
        assert "SiteCrawlerAgent" in agents
        
        search_agent = agents["WebSearchAgent"]
        crawl_agent = agents["SiteCrawlerAgent"]
        
        # Verify enhanced agents are returned
        assert isinstance(search_agent, OutlinesSearchAgent)
        assert isinstance(crawl_agent, OutlinesCrawlAgent)
        
        # Verify model role consistency
        assert search_agent.model == crawl_agent.model  # Both use SUMMARISER
        
        # Verify dual-path architecture
        assert hasattr(search_agent, 'supports_structured')
        assert hasattr(crawl_agent, 'supports_structured')
        
        # Verify enhanced output types
        assert search_agent.output_type == EnhancedToolAgentOutput or search_agent.output_type.__name__ == 'ToolAgentOutput'
        assert crawl_agent.output_type == EnhancedToolAgentOutput or crawl_agent.output_type.__name__ == 'ToolAgentOutput'
    
    @pytest.mark.asyncio
    async def test_search_agent_end_to_end_workflow(self, real_config, mock_tools):
        """Test complete SearchAgent workflow from input to enhanced output"""
        # Create agent with mocked tools
        search_agent = OutlinesSearchAgent(
            config=real_config, 
            web_search_tool=mock_tools["search"],
            summariser=Mock()
        )
        
        # Test AgentTask-like input
        task_input = {
            "gap": "recent AI breakthroughs in 2024",
            "query": "AI breakthrough 2024",
            "entity_website": "https://ai-research.org"
        }
        
        start_time = time.time()
        result = await search_agent.run_implementation(str(task_input))
        end_time = time.time()
        
        # Verify enhanced output structure
        assert "output" in result
        assert "sources" in result
        assert "processing_method" in result
        assert "confidence" in result  
        assert "processing_time_ms" in result
        
        # Verify content quality
        assert len(result["output"]) >= 10  # Meaningful summary
        assert isinstance(result["sources"], list)
        assert len(result["sources"]) > 0
        
        # Verify processing metadata
        assert result["processing_method"] in ["structured", "legacy", "error_fallback"]
        assert isinstance(result["confidence"], (int, float))
        assert 0.0 <= result["confidence"] <= 1.0
        assert isinstance(result["processing_time_ms"], int)
        assert result["processing_time_ms"] > 0
        
        # Verify performance (should complete in reasonable time)
        processing_time_seconds = end_time - start_time
        assert processing_time_seconds < 10.0  # Should complete within 10 seconds
        
        print(f"SearchAgent E2E: {processing_time_seconds:.2f}s, method: {result['processing_method']}")
    
    @pytest.mark.asyncio
    async def test_crawl_agent_end_to_end_workflow(self, real_config, mock_tools):
        """Test complete CrawlAgent workflow from input to enhanced output"""
        # Create agent with mocked tools
        crawl_agent = OutlinesCrawlAgent(
            config=real_config,
            crawl_tool=mock_tools["crawl"],
            summariser=Mock()
        )
        
        # Test URL input
        url_input = "https://company.com/annual-report-2024"
        
        start_time = time.time()
        result = await crawl_agent.run_implementation(url_input)
        end_time = time.time()
        
        # Verify enhanced output structure
        assert "output" in result
        assert "sources" in result
        assert "processing_method" in result
        assert "confidence" in result
        assert "processing_time_ms" in result
        
        # Verify content quality
        assert len(result["output"]) >= 10  # Meaningful summary
        assert isinstance(result["sources"], list)
        assert len(result["sources"]) > 0
        assert url_input in str(result["sources"])  # Should include target URL
        
        # Verify processing metadata
        assert result["processing_method"] in ["structured", "legacy", "error_fallback"]
        assert isinstance(result["confidence"], (int, float))
        assert 0.0 <= result["confidence"] <= 1.0
        
        # Verify performance
        processing_time_seconds = end_time - start_time
        assert processing_time_seconds < 10.0
        
        print(f"CrawlAgent E2E: {processing_time_seconds:.2f}s, method: {result['processing_method']}")
    
    @pytest.mark.asyncio
    async def test_hierarchical_summariser_integration(self, real_config, mock_tools):
        """Test HierarchicalSummariser integration with large content"""
        # Mock large crawled content
        large_content = "Large document content. " * 200  # >2000 chars
        mock_tools["crawl"].func.return_value = large_content
        
        # Mock summariser
        mock_summariser = Mock()
        mock_summariser.summarise_large_content = AsyncMock(return_value={
            "final_summary": "Summarized content focusing on key financial metrics and growth indicators.",
            "chunk_count": 3,
            "processing_metadata": {"chunks_processed": 3, "processing_time_ms": 150}
        })
        
        crawl_agent = OutlinesCrawlAgent(
            config=real_config,
            crawl_tool=mock_tools["crawl"],
            summariser=mock_summariser
        )
        
        result = await crawl_agent.run_implementation("https://large-report.com")
        
        # Verify summariser was called
        mock_summariser.summarise_large_content.assert_called_once()
        
        # Verify result quality
        assert "output" in result
        assert len(result["output"]) >= 10
        assert "processing_method" in result
    
    @pytest.mark.asyncio  
    async def test_performance_benchmarking(self, real_config, mock_tools):
        """Benchmark performance between different processing methods"""
        search_agent = OutlinesSearchAgent(
            config=real_config,
            web_search_tool=mock_tools["search"], 
            summariser=Mock()
        )
        
        crawl_agent = OutlinesCrawlAgent(
            config=real_config,
            crawl_tool=mock_tools["crawl"],
            summariser=Mock()
        )
        
        # Benchmark multiple runs
        search_times = []
        crawl_times = []
        
        for _ in range(3):
            # Search agent benchmark
            start = time.time()
            search_result = await search_agent.run_implementation("AI research trends")
            search_times.append((time.time() - start) * 1000)  # Convert to ms
            
            # Crawl agent benchmark  
            start = time.time()
            crawl_result = await crawl_agent.run_implementation("https://research.com")
            crawl_times.append((time.time() - start) * 1000)
        
        # Calculate averages
        avg_search_time = sum(search_times) / len(search_times)
        avg_crawl_time = sum(crawl_times) / len(crawl_times)
        
        print(f"Performance Benchmark:")
        print(f"  SearchAgent avg: {avg_search_time:.1f}ms")
        print(f"  CrawlAgent avg: {avg_crawl_time:.1f}ms")
        
        # Performance assertions (should be reasonable)
        assert avg_search_time < 5000  # <5 seconds avg
        assert avg_crawl_time < 5000   # <5 seconds avg
        
        # Verify performance metadata matches actual timing roughly
        assert abs(search_result["processing_time_ms"] - search_times[-1]) < 100  # Within 100ms
        assert abs(crawl_result["processing_time_ms"] - crawl_times[-1]) < 100
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_validation(self, real_config, mock_tools):
        """Test that enhanced agents maintain backward compatibility"""
        agents = init_tool_agents(real_config)
        search_agent = agents["WebSearchAgent"] 
        crawl_agent = agents["SiteCrawlerAgent"]
        
        # Replace tools with mocks
        search_agent.tools = [mock_tools["search"]]
        crawl_agent.tools = [mock_tools["crawl"]]
        
        # Test legacy interface expectations
        search_result = await search_agent.run_implementation("test query")
        crawl_result = await crawl_agent.run_implementation("https://test.com")
        
        # Verify legacy consumers get expected structure
        assert "output" in search_result
        assert "sources" in search_result
        assert isinstance(search_result["output"], str)
        assert isinstance(search_result["sources"], list)
        
        assert "output" in crawl_result
        assert "sources" in crawl_result  
        assert isinstance(crawl_result["output"], str)
        assert isinstance(crawl_result["sources"], list)
        
        # Enhanced fields should be present but optional
        assert "processing_method" in search_result
        assert "confidence" in search_result
        assert "processing_time_ms" in search_result


class TestErrorHandlingAndResilience:
    """Test error handling and resilience patterns"""
    
    @pytest.fixture
    def config_with_failing_tools(self):
        """Config with tools that simulate failures"""
        return LLMConfig(search_provider='searxng')
    
    @pytest.mark.asyncio
    async def test_tool_failure_resilience(self, config_with_failing_tools):
        """Test agents handle tool failures gracefully"""
        # Mock failing search tool
        failing_search_tool = Mock()
        failing_search_tool.name = "web_search"
        failing_search_tool.func = AsyncMock(side_effect=Exception("Search service unavailable"))
        
        search_agent = OutlinesSearchAgent(
            config=config_with_failing_tools,
            web_search_tool=failing_search_tool,
            summariser=Mock()
        )
        
        # Should not crash, should return error response
        result = await search_agent.run_implementation("test query")
        
        assert "output" in result
        assert "error_fallback" in result.get("processing_method", "")
        assert result["confidence"] == 0.0
        assert "Search service unavailable" in result["output"] or "failed" in result["output"].lower()
    
    @pytest.mark.asyncio
    async def test_model_failure_resilience(self, config_with_failing_tools):
        """Test agents handle model failures gracefully"""
        # Mock model that fails
        failing_model = Mock()
        failing_model.chat = AsyncMock(side_effect=Exception("Model timeout"))
        
        search_tool = Mock()
        search_tool.name = "web_search"
        search_tool.func = AsyncMock(return_value="Mock search results")
        
        search_agent = OutlinesSearchAgent(
            config=config_with_failing_tools,
            web_search_tool=search_tool,
            summariser=Mock()
        )
        search_agent.model = failing_model
        
        result = await search_agent.run_implementation("test query")
        
        assert "output" in result
        assert result["processing_method"] == "error_fallback"
        assert result["confidence"] == 0.0
    
    @pytest.mark.asyncio
    async def test_structured_to_legacy_fallback(self, config_with_failing_tools):
        """Test fallback from structured to legacy generation"""
        with patch('deep_researcher.agents.tool_agents.search_agent.model_supports_structured_output', return_value=True), \
             patch('deep_researcher.agents.tool_agents.search_agent.OUTLINES_AVAILABLE', True):
            
            # Mock Outlines generator that fails
            mock_generator = Mock()
            mock_generator.generate.side_effect = Exception("Structured generation failed")
            
            # Mock successful legacy model
            legacy_model = Mock()
            legacy_response = Mock()
            legacy_response.content = '{"output": "Legacy fallback summary", "sources": ["https://test.com"]}'
            legacy_model.chat.return_value = legacy_response
            
            search_tool = Mock()
            search_tool.name = "web_search"
            search_tool.func = AsyncMock(return_value="Mock results")
            
            with patch('deep_researcher.agents.tool_agents.search_agent.outlines.Generator', return_value=mock_generator):
                search_agent = OutlinesSearchAgent(
                    config=config_with_failing_tools,
                    web_search_tool=search_tool,
                    summariser=Mock()
                )
                search_agent.model = legacy_model
                search_agent.supports_structured = True
                search_agent.outlines_generator = mock_generator
                
                # Mock parser for legacy path
                mock_parser = Mock()
                mock_parser.parse.return_value = {
                    "output": "Legacy fallback summary",
                    "sources": ["https://test.com"]
                }
                search_agent.output_parser = mock_parser
                
                result = await search_agent.run_implementation("test query")
                
                # Should fall back to legacy successfully
                assert result["processing_method"] == "legacy"
                assert result["confidence"] == 0.85
                assert result["output"] == "Legacy fallback summary"


class TestRegressionValidation:
    """Validate no breaking changes to existing functionality"""
    
    @pytest.fixture
    def baseline_config(self):
        """Configuration that represents previous system state"""
        return LLMConfig(search_provider='searxng')
    
    @pytest.mark.asyncio
    async def test_search_agent_output_format_regression(self, baseline_config):
        """Ensure SearchAgent output format hasn't changed for existing consumers"""
        # Mock old-style tool
        mock_tool = Mock()
        mock_tool.name = "web_search"
        mock_tool.func = AsyncMock(return_value="Standard search results")
        
        agent = OutlinesSearchAgent(
            config=baseline_config,
            web_search_tool=mock_tool,
            summariser=Mock()
        )
        
        result = await agent.run_implementation("legacy query format")
        
        # Core contract must be preserved
        assert isinstance(result, dict)
        assert "output" in result
        assert "sources" in result
        assert isinstance(result["output"], str)
        assert isinstance(result["sources"], list)
        
        # New fields should be additive only
        for field in ["processing_method", "confidence", "processing_time_ms"]:
            if field in result:
                assert result[field] is not None
    
    @pytest.mark.asyncio  
    async def test_crawl_agent_output_format_regression(self, baseline_config):
        """Ensure CrawlAgent output format hasn't changed for existing consumers"""
        mock_tool = Mock()
        mock_tool.name = "crawl_website"
        mock_tool.func = AsyncMock(return_value="Standard crawled content")
        
        agent = OutlinesCrawlAgent(
            config=baseline_config,
            crawl_tool=mock_tool,
            summariser=Mock()
        )
        
        result = await agent.run_implementation("https://legacy-format.com")
        
        # Core contract preservation
        assert isinstance(result, dict)
        assert "output" in result
        assert "sources" in result
        assert isinstance(result["output"], str)
        assert isinstance(result["sources"], list)
        
        # Sources should include the target website
        assert any("legacy-format.com" in str(source) for source in result["sources"])
    
    def test_agent_interface_regression(self, baseline_config):
        """Test that agent interfaces haven't changed"""
        agents = init_tool_agents(baseline_config)
        
        search_agent = agents["WebSearchAgent"]
        crawl_agent = agents["SiteCrawlerAgent"]
        
        # Required attributes for existing consumers
        required_attrs = ["name", "model", "tools", "summariser"]
        
        for attr in required_attrs:
            assert hasattr(search_agent, attr), f"SearchAgent missing {attr}"
            assert hasattr(crawl_agent, attr), f"CrawlAgent missing {attr}"
        
        # Required methods
        assert hasattr(search_agent, "run_implementation")
        assert hasattr(crawl_agent, "run_implementation")
        
        # Type consistency
        assert search_agent.name == "WebSearchAgent"
        assert crawl_agent.name == "SiteCrawlerAgent"
        assert len(search_agent.tools) > 0
        assert len(crawl_agent.tools) > 0


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s"])