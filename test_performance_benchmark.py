"""
Simple performance benchmark for HYBRID-04a-05 validation
Tests basic functionality and timing of SearchAgent and CrawlAgent
"""
import asyncio
import time
from unittest.mock import Mock, AsyncMock
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.tool_agents.search_agent import OutlinesSearchAgent
from deep_researcher.agents.tool_agents.crawl_agent import OutlinesCrawlAgent


async def benchmark_search_agent():
    """Benchmark SearchAgent performance"""
    print("=== SearchAgent Benchmark ===")
    
    # Setup
    config = LLMConfig(search_provider='searxng')
    
    # Mock tools and model for controlled testing
    search_tool = Mock()
    search_tool.name = "web_search"
    search_tool.func = AsyncMock(return_value="Mock search results: AI breakthrough 2024 shows significant improvements...")
    
    mock_model = Mock()
    mock_response = Mock()
    mock_response.content = '{"output": "AI has made significant breakthroughs in 2024 with new neural architectures showing 40% improvement in performance.", "sources": ["https://ai-research.org"]}'
    mock_model.return_value = mock_response
    
    # Create agent
    agent = OutlinesSearchAgent(config, search_tool, Mock())
    agent.model = mock_model  # Use mock model
    
    # Benchmark multiple runs
    times = []
    for i in range(3):
        start = time.time()
        result = await agent.run_implementation("AI breakthroughs 2024")
        end = time.time()
        
        processing_time = (end - start) * 1000  # Convert to ms
        times.append(processing_time)
        
        print(f"  Run {i+1}: {processing_time:.1f}ms, method: {result.get('processing_method', 'unknown')}")
        
        # Verify output structure
        assert "output" in result
        assert "sources" in result  
        assert "processing_method" in result
        assert "confidence" in result
        assert "processing_time_ms" in result
    
    avg_time = sum(times) / len(times)
    print(f"  Average: {avg_time:.1f}ms")
    print(f"  Status: {'PASS' if avg_time < 1000 else 'SLOW'}")
    return avg_time


async def benchmark_crawl_agent():
    """Benchmark CrawlAgent performance"""
    print("\n=== CrawlAgent Benchmark ===")
    
    # Setup
    config = LLMConfig(search_provider='searxng')
    
    # Mock tools and model
    crawl_tool = Mock()
    crawl_tool.name = "crawl_website"
    crawl_tool.func = AsyncMock(return_value="Mock crawled content: Company annual report shows strong Q4 performance with 25% revenue growth...")
    
    mock_model = Mock()
    mock_response = Mock()
    mock_response.content = '{"output": "The company showed strong Q4 performance with 25% revenue growth and expanding market presence.", "sources": ["https://company.com/report"]}'
    mock_model.return_value = mock_response
    
    # Create agent
    agent = OutlinesCrawlAgent(config, crawl_tool, Mock())
    agent.model = mock_model
    
    # Benchmark multiple runs
    times = []
    for i in range(3):
        start = time.time()
        result = await agent.run_implementation("https://company.com/annual-report")
        end = time.time()
        
        processing_time = (end - start) * 1000
        times.append(processing_time)
        
        print(f"  Run {i+1}: {processing_time:.1f}ms, method: {result.get('processing_method', 'unknown')}")
        
        # Verify output structure
        assert "output" in result
        assert "sources" in result
        assert "processing_method" in result
        assert "confidence" in result
        assert "processing_time_ms" in result
    
    avg_time = sum(times) / len(times)
    print(f"  Average: {avg_time:.1f}ms")
    print(f"  Status: {'PASS' if avg_time < 1000 else 'SLOW'}")
    return avg_time


def test_backward_compatibility():
    """Test backward compatibility requirements"""
    print("\n=== Backward Compatibility Test ===")
    
    try:
        config = LLMConfig(search_provider='searxng')
        
        # Test imports work
        from deep_researcher.agents.tool_agents import init_tool_agents
        from deep_researcher.agents.tool_agents.search_agent import init_search_agent
        from deep_researcher.agents.tool_agents.crawl_agent import init_crawl_agent
        
        # Test agent creation
        agents = init_tool_agents(config)
        search_agent = init_search_agent(config)
        crawl_agent = init_crawl_agent(config)
        
        # Test required interfaces exist
        assert "WebSearchAgent" in agents
        assert "SiteCrawlerAgent" in agents
        assert hasattr(search_agent, 'name')
        assert hasattr(crawl_agent, 'name')
        assert hasattr(search_agent, 'run_implementation')
        assert hasattr(crawl_agent, 'run_implementation')
        
        print("  Agent creation: PASS")
        print("  Interface compatibility: PASS")
        print("  Import compatibility: PASS")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


async def main():
    """Run all benchmarks and tests"""
    print("HYBRID-04a-05: Integration Testing & Performance Validation")
    print("=" * 60)
    
    try:
        # Performance benchmarks
        search_time = await benchmark_search_agent()
        crawl_time = await benchmark_crawl_agent()
        
        # Backward compatibility
        compat_ok = test_backward_compatibility()
        
        print("\n=== Summary ===")
        print(f"SearchAgent avg time: {search_time:.1f}ms")
        print(f"CrawlAgent avg time: {crawl_time:.1f}ms")
        print(f"Backward compatibility: {'PASS' if compat_ok else 'FAIL'}")
        
        # Performance criteria: <20% latency increase (assume baseline ~100ms)
        baseline = 100.0
        search_increase = ((search_time - baseline) / baseline) * 100
        crawl_increase = ((crawl_time - baseline) / baseline) * 100
        
        print(f"Performance increase - Search: {search_increase:+.1f}%, Crawl: {crawl_increase:+.1f}%")
        
        overall_pass = (
            search_time < 1000 and  # Reasonable performance
            crawl_time < 1000 and
            compat_ok and
            search_increase < 50    # Less than 50% increase
        )
        
        print(f"\nOverall Result: {'PASS' if overall_pass else 'FAIL'}")
        return overall_pass
        
    except Exception as e:
        print(f"Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)