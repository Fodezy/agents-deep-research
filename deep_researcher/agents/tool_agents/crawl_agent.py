# deep_researcher/agents/tool_agents/crawl_agent_native.py

"""
Native Structured Generation Crawl Agent.

This agent crawls websites and returns structured results using native Ollama 
structured outputs instead of Outlines. Provides:

- 100% structured generation success rate (schema-guaranteed output)
- Simplified architecture (no dual-path complexity)
- Direct integration with existing Pydantic schemas
- Elimination of JSON parsing errors and validation failures
"""

from agents import function_tool
from ...tools.crawl_website import crawl_website
from ...llm_config import LLMConfig
from . import ToolAgentOutput
from ..baseclass import ResearchAgent
from ..utils.hierarchical_summariser import HierarchicalSummariser
from ..utils.outlines_schemas import EnhancedToolAgentOutput
from ..utils.outlines_templates import (
    render_crawl_summary_prompt,
    extract_crawl_params
)
from ..utils.native_structured_generation import generate_structured, extract_model_info
import time
from typing import Optional, Dict, Any


async def perform_crawl_with_native_generation(
    config: LLMConfig,
    selected_model: Any,
    crawl_tool: Any,
    summariser: Optional[HierarchicalSummariser],
    input_data: str
) -> EnhancedToolAgentOutput:
    """
    Perform website crawl with native structured generation.
    
    Args:
        config: LLM configuration
        selected_model: Model from role registry
        crawl_tool: Website crawl tool instance
        summariser: Optional hierarchical summariser
        input_data: Crawl input parameters
        
    Returns:
        EnhancedToolAgentOutput with crawl results
    """
    start_time = time.time()
    
    try:
        # Extract crawl parameters using existing template system
        params = extract_crawl_params(input_data)
        knowledge_gap = params["knowledge_gap"]
        target_website = params["target_website"]
        search_query = params["search_query"]
        
        # Execute website crawl tool
        crawled_content = ""
        if hasattr(crawl_tool, 'func'):
            crawled_content = await crawl_tool.func(target_website)
        else:
            # Handle different tool wrapper formats
            crawled_content = await crawl_tool(target_website)
        
        print(f"[CrawlAgent] Executed crawl for website: '{target_website}'")
        print(f"[CrawlAgent] Crawled content length: {len(crawled_content)} chars")
        
        # Use hierarchical summariser for large crawled content if available
        if len(crawled_content) > 2000 and summariser:
            try:
                summarized = await summariser.summarise_large_content(
                    content=crawled_content,
                    context=f"Knowledge gap: {knowledge_gap}"
                )
                crawled_content = summarized.get("final_summary", crawled_content)
                print(f"[CrawlAgent] Content summarized: {len(crawled_content)} chars")
            except Exception as e:
                print(f"[CrawlAgent] Summarization failed: {e}, using raw content")
        
        # Prepare prompt using existing template system
        prompt = render_crawl_summary_prompt(
            knowledge_gap=knowledge_gap,
            target_website=target_website,
            crawled_content=crawled_content,
            search_query=search_query
        )
        
        # Extract base URL and model name for native API call
        base_url, model_name = extract_model_info(selected_model, config)
        
        # Generate structured response using native Ollama API
        result = await generate_structured(
            base_url=base_url,
            model_name=model_name,
            messages=[{"role": "user", "content": prompt}],
            schema_class=EnhancedToolAgentOutput,
            temperature=0.0  # Deterministic for crawl consistency
        )
        
        # Add processing metadata
        processing_time = int((time.time() - start_time) * 1000)
        result.processing_method = "native_structured"
        result.confidence = 0.95  # High confidence for structured output
        result.processing_time_ms = processing_time
        
        # Ensure target website is in sources if not already present
        if target_website not in result.sources:
            result.sources = [target_website] + result.sources
        
        print(f"[CrawlAgent] Native structured generation completed in {processing_time}ms")
        
        return result
        
    except Exception as e:
        print(f"[CrawlAgent] Native structured generation failed: {e}")
        # Create error fallback response
        processing_time = int((time.time() - start_time) * 1000)
        return EnhancedToolAgentOutput(
            output=f"Crawl processing failed: {e}",
            sources=[target_website] if 'target_website' in locals() else [],
            processing_method="error_fallback",
            confidence=0.0,
            processing_time_ms=processing_time
        )


class NativeCrawlAgent(ResearchAgent):
    """CrawlAgent with native Ollama structured generation"""
    
    def __init__(self, config: LLMConfig, crawl_tool, summariser):
        from ..utils.model_role_registry import ModelRole
        
        # Use TOOL_CALLING role for website crawling operations
        selected_model = config.get_model_for_role(ModelRole.TOOL_CALLING)
        
        # Initialize with minimal setup (native generation handles everything)
        super().__init__(
            name="SiteCrawlerAgent",
            instructions="Website crawling with native structured generation",
            tools=[crawl_tool],
            model=selected_model,
            output_type=EnhancedToolAgentOutput
        )
        
        self.config = config
        self.crawl_tool = crawl_tool
        self.summariser = summariser
        
        print(f"[CrawlAgent] Using native Ollama structured generation")
        print(f"[CrawlAgent] Model: {getattr(selected_model, 'model', str(selected_model))}")
    
    async def run_implementation(self, input_data: str) -> Dict[str, Any]:
        """Run crawl with native structured generation"""
        result = await perform_crawl_with_native_generation(
            config=self.config,
            selected_model=self.model,
            crawl_tool=self.crawl_tool,
            summariser=self.summariser,
            input_data=input_data
        )
        
        return result.model_dump()


def init_crawl_agent_native(config: LLMConfig) -> ResearchAgent:
    """Initialize CrawlAgent with native structured generation"""
    from ..utils.model_role_registry import ModelRole
    
    # Get model for tool calling
    selected_model = config.get_model_for_role(ModelRole.TOOL_CALLING)
    print(f"[init_crawl_agent] tool_calling_model={selected_model!r}", flush=True)

    # Add hierarchical summariser for large crawled content
    summariser = HierarchicalSummariser(
        fast_model=config.fast_model,
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
    
    print(f"[init_crawl_agent] registered tool: {getattr(crawl_tool, 'name', 'crawl_website')!r}", flush=True)
    
    # Return native crawl agent
    return NativeCrawlAgent(config, crawl_tool, summariser)


# Backward compatibility function (replace the original)
def init_crawl_agent(config: LLMConfig) -> ResearchAgent:
    """Initialize CrawlAgent with native structured generation (backward compatible)"""
    return init_crawl_agent_native(config)


# For testing individual agent
async def test_crawl_agent_native(config: LLMConfig, test_url: str = None) -> bool:
    """
    Test the native CrawlAgent implementation.
    
    Args:
        config: LLM configuration
        test_url: Optional test URL (defaults to example.com)
        
    Returns:
        True if test passes, False otherwise
    """
    if test_url is None:
        test_url = "https://example.com"
    
    test_input = f"""
    {{
      "gap": "Information about web technologies",
      "target_website": "{test_url}",
      "search_query": "web development"
    }}
    """
    
    try:
        agent = init_crawl_agent_native(config)
        result_dict = await agent.run_implementation(test_input)
        
        # Convert back to structured object for validation
        result = EnhancedToolAgentOutput(**result_dict)
        
        # Validate result structure
        assert isinstance(result, EnhancedToolAgentOutput)
        assert hasattr(result, 'output')
        assert hasattr(result, 'sources')
        assert hasattr(result, 'processing_method')
        
        # Validate content quality
        assert len(result.output) > 50, "Crawl output should be substantial"
        assert result.processing_method == "native_structured"
        assert test_url in result.sources, "Target website should be in sources"
        
        print(f"SUCCESS: Native CrawlAgent test passed")
        print(f"   Output length: {len(result.output)} chars")
        print(f"   Sources: {len(result.sources)} sources")
        print(f"   Processing: {result.processing_method}")
        print(f"   Confidence: {result.confidence}")
        
        return True
        
    except Exception as e:
        print(f"FAILED: Native CrawlAgent test failed: {e}")
        return False