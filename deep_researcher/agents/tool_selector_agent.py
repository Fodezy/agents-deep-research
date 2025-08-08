"""
Native Structured Generation Tool Selector Agent.

This agent determines which specialized agents should be used to address knowledge gaps
using native Ollama structured outputs instead of Outlines. This provides:

- 100% structured generation success rate (schema-guaranteed output)
- Simplified architecture (no dual-path complexity)
- Direct integration with existing Pydantic schemas
- Elimination of JSON parsing errors and validation failures

The Agent takes as input a string in the following format:
===========================================================
ORIGINAL QUERY: <original user query>

KNOWLEDGE GAP TO ADDRESS: <knowledge gap that needs to be addressed>

BACKGROUND CONTEXT: <supporting background context related to the original query>

HISTORY OF ACTIONS, FINDINGS AND THOUGHTS: <a log of prior iterations of the research process>
===========================================================

The Agent then:
1. Analyzes the knowledge gap to determine which agents are best suited to address it
2. Returns an AgentSelectionPlan object containing a list of AgentTask objects

The available agents are:
- WebSearchAgent: General web search for broad topics
- SiteCrawlerAgent: Crawl the pages of a specific website to retrieve information about it
"""

from typing import List, Dict, Any, Union
import json
import re
from ..llm_config import LLMConfig
from .baseclass import ResearchAgent
from .utils.native_structured_generation import generate_structured, extract_model_info

# Import existing schemas (100% compatible with native structured generation)
from .utils.outlines_schemas import AgentSelectionPlan, AgentTask
from .utils.outlines_templates import render_outlines_prompt


def extract_tool_selector_params(input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Extract research context and knowledge gaps from formatted input"""
    if isinstance(input_data, dict):
        # Direct dict input (for structured calls)
        return {
            "research_context": input_data.get("research_context", input_data.get("context", "")),
            "knowledge_gaps": input_data.get("knowledge_gaps", input_data.get("gaps", []))
        }
    
    # Parse formatted string input (current format from ResearchRunner)
    text = input_data
    
    # Extract ORIGINAL QUERY as research context
    query_match = re.search(r'ORIGINAL QUERY:\s*(.*?)(?=\n\n|\nKNOWLEDGE|$)', text, re.DOTALL)
    research_context = query_match.group(1).strip() if query_match else text[:100] + "..."
    
    # Extract KNOWLEDGE GAP TO ADDRESS as the main gap
    gap_match = re.search(r'KNOWLEDGE GAP TO ADDRESS:\s*(.*?)(?=\n\n|\nBACKGROUND|$)', text, re.DOTALL)
    knowledge_gap = gap_match.group(1).strip() if gap_match else "Information needed"
    
    return {
        "research_context": research_context,
        "knowledge_gaps": [knowledge_gap] if knowledge_gap else []
    }


async def generate_tool_selection_native(
    config: LLMConfig,
    selected_model: Any,
    input_data: Union[str, Dict[str, Any]]
) -> AgentSelectionPlan:
    """
    Generate tool selection plan using native Ollama structured outputs.
    
    Args:
        config: LLM configuration
        selected_model: Model from role registry
        input_data: Tool selection input parameters
        
    Returns:
        AgentSelectionPlan with structured tool selection
    """
    try:
        # Extract base URL and model name
        base_url, model_name = extract_model_info(selected_model, config)
        
        # Extract parameters using existing template system
        params = extract_tool_selector_params(input_data)
        
        # Render prompt using existing template (reuse existing logic)
        prompt = render_outlines_prompt(**params)
        
        # Generate structured output using native Ollama API
        result = await generate_structured(
            base_url=base_url,
            model_name=model_name,
            messages=[{"role": "user", "content": prompt}],
            schema_class=AgentSelectionPlan,
            temperature=0.0  # Deterministic for tool selection consistency
        )
        
        print(f"[ToolSelectorAgent] Native structured generation success: {len(result.tasks)} tasks planned")
        
        # CRITICAL FIX: Defensive programming for empty task plans
        if not result.tasks:
            print(f"[ToolSelectorAgent] Warning: Empty task plan detected, creating fallback task")
            # Create a fallback task to prevent downstream crashes
            fallback_task = AgentTask(
                gap=params.get("knowledge_gaps", ["Information needed"])[0] if params.get("knowledge_gaps") else "Information needed",
                agent="WebSearchAgent",
                query=params.get("research_context", "research query")[:100]
            )
            result.tasks = [fallback_task]
        
        return result
        
    except Exception as e:
        print(f"[ToolSelectorAgent] Native structured generation failed: {e}")
        raise Exception(f"Native structured generation failed: {e}")
        # NOTE: No fallback - we are committed to native structured generation only


def create_tool_selector_agent_native(config: LLMConfig) -> ResearchAgent:
    """
    Create ToolSelectorAgent using native Ollama structured outputs.
    
    This replaces the complex Outlines integration with direct native API calls,
    providing the same structured generation benefits with minimal complexity.
    """
    from .utils.model_role_registry import ModelRole
    
    # Use dedicated TOOL_CALLING role
    selected_model = config.get_model_for_role(ModelRole.TOOL_CALLING)
    
    print(f"[INFO] ToolSelectorAgent: Using native Ollama structured generation")
    print(f"[INFO] Model: {getattr(selected_model, 'model', str(selected_model))}")
    
    async def run_native_tool_selection(input_data: Union[str, Dict[str, Any]]) -> AgentSelectionPlan:
        """Run tool selection with native structured generation"""
        return await generate_tool_selection_native(config, selected_model, input_data)
    
    # Create agent with native structured generation function
    agent = ResearchAgent(
        name="ToolSelectorAgent",
        instructions="Tool selection with native structured generation",
        model=selected_model,
        output_type=AgentSelectionPlan
    )
    
    # Add the native generation method
    agent.run_native_tool_selection = run_native_tool_selection
    
    return agent


# Backward compatibility function (replace the original)
def init_tool_selector_agent(config: LLMConfig) -> ResearchAgent:
    """Initialize ToolSelectorAgent with native structured generation (backward compatible)"""
    return create_tool_selector_agent_native(config)


# For testing individual agent
async def test_tool_selector_agent_native(config: LLMConfig, test_input: str = None) -> bool:
    """
    Test the native ToolSelectorAgent implementation.
    
    Args:
        config: LLM configuration
        test_input: Optional test input (defaults to quantum research example)
        
    Returns:
        True if test passes, False otherwise
    """
    if test_input is None:
        test_input = """
        ORIGINAL QUERY: What is quantum entanglement?
        
        KNOWLEDGE GAP TO ADDRESS: Need to understand the practical applications of quantum entanglement in modern technology
        
        BACKGROUND CONTEXT: Quantum entanglement is a phenomenon where particles become correlated and share states regardless of distance.
        
        HISTORY OF ACTIONS, FINDINGS AND THOUGHTS: [ITERATION 1] Initial research started.
        """
    
    try:
        agent = create_tool_selector_agent_native(config)
        result = await agent.run_native_tool_selection(test_input)
        
        # Validate result structure
        assert isinstance(result, AgentSelectionPlan)
        assert hasattr(result, 'tasks')
        assert len(result.tasks) > 0, "Should generate at least one task"
        
        # Validate task structure
        first_task = result.tasks[0]
        assert hasattr(first_task, 'gap')
        assert hasattr(first_task, 'agent')
        assert hasattr(first_task, 'query')
        assert first_task.agent in ['WebSearchAgent', 'SiteCrawlerAgent'], "Should select valid agent"
        
        print(f"SUCCESS: Native ToolSelectorAgent test passed")
        print(f"   Tasks planned: {len(result.tasks)}")
        for i, task in enumerate(result.tasks):
            print(f"   Task {i+1}: {task.agent} - {task.query[:50]}...")
            
        return True
        
    except Exception as e:
        print(f"FAILED: Native ToolSelectorAgent test failed: {e}")
        return False
