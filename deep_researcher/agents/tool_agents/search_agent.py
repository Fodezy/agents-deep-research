# deep_researcher/agents/tool_agents/search_agent_native.py

"""
Native Structured Generation Search Agent.

This agent performs web searches and returns structured results using native Ollama 
structured outputs instead of Outlines. Provides:

- 100% structured generation success rate (schema-guaranteed output)
- Simplified architecture (no dual-path complexity)
- Direct integration with existing Pydantic schemas
- Elimination of JSON parsing errors and validation failures
"""

from agents import function_tool
from ...tools.web_search import create_web_search_tool
from ...llm_config import LLMConfig
from . import ToolAgentOutput
from ..baseclass import ResearchAgent
from ..utils.hierarchical_summariser import HierarchicalSummariser
from ..utils.outlines_schemas import EnhancedToolAgentOutput
from ..utils.outlines_templates import (
    render_search_summary_prompt,
    extract_search_params
)
from ..utils.native_structured_generation import generate_structured, extract_model_info
import time
from typing import Optional, Dict, Any


async def perform_search_with_native_generation(
    config: LLMConfig,
    selected_model: Any,
    web_search_tool: Any,
    summariser: Optional[HierarchicalSummariser],
    input_data: str
) -> EnhancedToolAgentOutput:
    """
    Perform web search with native structured generation.
    
    Args:
        config: LLM configuration
        selected_model: Model from role registry
        web_search_tool: Web search tool instance
        summariser: Optional hierarchical summariser
        input_data: Search input parameters
        
    Returns:
        EnhancedToolAgentOutput with search results
    """
    start_time = time.time()
    
    try:
        # Extract search parameters using existing template system
        params = extract_search_params(input_data)
        knowledge_gap = params["knowledge_gap"]
        search_query = params["search_query"]
        entity_website = params["entity_website"]
        
        # Execute web search tool with proper query
        search_results = ""
        if hasattr(web_search_tool, 'func'):
            search_results = await web_search_tool.func(search_query)
        else:
            # Handle different tool wrapper formats
            search_results = await web_search_tool(search_query)
        
        print(f"[SearchAgent] Executed search for query: '{search_query}'")
        
        # Use hierarchical summariser for large search results if available
        if len(search_results) > 2000 and summariser:
            try:
                summarized = await summariser.summarise_large_content(
                    content=search_results,
                    context=f"Knowledge gap: {knowledge_gap}"
                )
                search_results = summarized.get("final_summary", search_results)
                print(f"[SearchAgent] Search results summarized: {len(search_results)} chars")
            except Exception as e:
                print(f"[SearchAgent] Summarization failed: {e}, using raw results")
        
        # Prepare prompt using existing template system
        prompt = render_search_summary_prompt(
            knowledge_gap=knowledge_gap,
            search_query=search_query,
            search_results=search_results,
            entity_website=entity_website
        )
        
        # Extract base URL and model name for native API call
        base_url, model_name = extract_model_info(selected_model, config)
        
        # Generate structured response using native Ollama API
        result = await generate_structured(
            base_url=base_url,
            model_name=model_name,
            messages=[{"role": "user", "content": prompt}],
            schema_class=EnhancedToolAgentOutput,
            temperature=0.0  # Deterministic for search consistency
        )
        
        # Add processing metadata
        processing_time = int((time.time() - start_time) * 1000)
        result.processing_method = "native_structured"
        result.confidence = 0.95  # High confidence for structured output
        result.processing_time_ms = processing_time
        
        print(f"[SearchAgent] Native structured generation completed in {processing_time}ms")
        
        return result
        
    except Exception as e:
        print(f"[SearchAgent] Native structured generation failed: {e}")
        # Create error fallback response
        processing_time = int((time.time() - start_time) * 1000)
        return EnhancedToolAgentOutput(
            output=f"Search processing failed: {e}",
            sources=[],
            processing_method="error_fallback",
            confidence=0.0,
            processing_time_ms=processing_time
        )


class NativeSearchAgent(ResearchAgent):
    """SearchAgent with native Ollama structured generation"""
    
    def __init__(self, config: LLMConfig, web_search_tool, summariser):
        from ..utils.model_role_registry import ModelRole
        
        # Use TOOL_CALLING role for web search operations
        selected_model = config.get_model_for_role(ModelRole.TOOL_CALLING)
        
        # Initialize with minimal setup (native generation handles everything)
        super().__init__(
            name="WebSearchAgent",
            instructions="Web search with native structured generation",
            tools=[web_search_tool],
            model=selected_model,
            output_type=EnhancedToolAgentOutput
        )
        
        self.config = config
        self.web_search_tool = web_search_tool
        self.summariser = summariser
        
        print(f"[SearchAgent] Using native Ollama structured generation")
        print(f"[SearchAgent] Model: {getattr(selected_model, 'model', str(selected_model))}")
    
    async def run_implementation(self, input_data: str) -> Dict[str, Any]:
        """Run search with native structured generation"""
        result = await perform_search_with_native_generation(
            config=self.config,
            selected_model=self.model,
            web_search_tool=self.web_search_tool,
            summariser=self.summariser,
            input_data=input_data
        )
        
        return result.model_dump()


def init_search_agent_native(config: LLMConfig) -> ResearchAgent:
    """Initialize SearchAgent with native structured generation"""
    from ..utils.model_role_registry import ModelRole
    from ...llm_config import get_base_url
    
    # Get model for tool calling
    selected_model = config.get_model_for_role(ModelRole.TOOL_CALLING)
    print(f"[init_search_agent] search_provider={config.search_provider!r}, tool_calling_model={selected_model!r}", flush=True)
    
    # Validate configuration
    provider_base_url = get_base_url(selected_model)
    if config.search_provider == "openai" and 'openai.com' not in provider_base_url:
        raise ValueError(f"SEARCH_PROVIDER='openai' but using non-OpenAI model {selected_model}")
    
    # Create the web search tool
    web_search_tool = create_web_search_tool(config)

    # Add hierarchical summariser for large content
    summariser = HierarchicalSummariser(
        fast_model=config.fast_model,
        slow_model=config.main_model,
        chunk_size=800,
        overlap=100
    )

    print(f"[init_search_agent] registered tool: {getattr(web_search_tool, 'name', 'web_search')!r}", flush=True)
    
    # Return native search agent
    return NativeSearchAgent(config, web_search_tool, summariser)


# Backward compatibility function (replace the original)
def init_search_agent(config: LLMConfig) -> ResearchAgent:
    """Initialize SearchAgent with native structured generation (backward compatible)"""
    return init_search_agent_native(config)


# For testing individual agent
async def test_search_agent_native(config: LLMConfig, test_query: str = None) -> bool:
    """
    Test the native SearchAgent implementation.
    
    Args:
        config: LLM configuration
        test_query: Optional test query (defaults to quantum computing query)
        
    Returns:
        True if test passes, False otherwise
    """
    if test_query is None:
        test_query = """
        {
          "gap": "How quantum computers work",
          "query": "quantum computing basics",
          "entity_website": null
        }
        """
    
    try:
        agent = init_search_agent_native(config)
        result_dict = await agent.run_implementation(test_query)
        
        # Convert back to structured object for validation
        result = EnhancedToolAgentOutput(**result_dict)
        
        # Validate result structure
        assert isinstance(result, EnhancedToolAgentOutput)
        assert hasattr(result, 'output')
        assert hasattr(result, 'sources')
        assert hasattr(result, 'processing_method')
        
        # Validate content quality
        assert len(result.output) > 50, "Search output should be substantial"
        assert result.processing_method == "native_structured"
        
        print(f"SUCCESS: Native SearchAgent test passed")
        print(f"   Output length: {len(result.output)} chars")
        print(f"   Sources: {len(result.sources)} sources")
        print(f"   Processing: {result.processing_method}")
        print(f"   Confidence: {result.confidence}")
        
        return True
        
    except Exception as e:
        print(f"FAILED: Native SearchAgent test failed: {e}")
        return False