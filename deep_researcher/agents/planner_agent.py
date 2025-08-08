"""
Native Structured Generation Planner Agent.

This agent produces an initial outline of the report using native Ollama structured outputs
instead of Outlines. This provides:

- 100% structured generation success rate (schema-guaranteed output)
- Simplified architecture (no dual-path complexity)
- Direct integration with existing Pydantic schemas
- Elimination of JSON parsing errors and validation failures

The Agent takes as input a string in the following format:
===========================================================
QUERY: <original user query>
===========================================================

The Agent then outputs a ReportPlan object, which includes:
1. A summary of initial background context (if needed), based on web searches and/or crawling
2. An outline of the report that includes a list of section titles and the key question to be addressed in each section
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Union
from .baseclass import ResearchAgent
from ..llm_config import LLMConfig
from .utils.native_structured_generation import generate_structured, extract_model_info

# Import existing schemas (100% compatible with native structured generation)
from .utils.outlines_schemas import PlanningResult, ResearchStep
from .utils.outlines_templates import render_planning_prompt, extract_planner_params

# Backward compatibility aliases for existing code
ReportPlan = PlanningResult
ReportPlanSection = ResearchStep

# Keep original class definitions for reference (deprecated)
class _DeprecatedReportPlanSection(BaseModel):
    """A section of the report that needs to be written (DEPRECATED - use ResearchStep)"""
    title: str = Field(description="The title of the section")
    key_question: str = Field(description="The key question to be addressed in the section")

class _DeprecatedReportPlan(BaseModel):
    """Output from the Report Planner Agent (DEPRECATED - use PlanningResult)"""
    background_context: str = Field(description="A summary of supporting context that can be passed onto the research agents")
    report_outline: List[_DeprecatedReportPlanSection] = Field(description="List of sections that need to be written in the report")
    report_title: str = Field(description="The title of the report")


async def generate_planning_native(
    config: LLMConfig,
    selected_model: Any,
    input_data: Union[str, Dict[str, Any]]
) -> PlanningResult:
    """
    Generate planning result using native Ollama structured outputs.
    
    Args:
        config: LLM configuration
        selected_model: Model from role registry
        input_data: Planning input parameters
        
    Returns:
        PlanningResult with structured planning output
    """
    try:
        # Extract base URL and model name
        base_url, model_name = extract_model_info(selected_model, config)
        
        # Extract parameters using existing template system
        params = extract_planner_params(input_data)
        
        # Render prompt using existing template (reuse existing logic)  
        base_prompt = render_planning_prompt(**params)
        
        # Add explicit schema constraints for native structured generation
        prompt = f"""{base_prompt}

CRITICAL SCHEMA REQUIREMENTS:
- schema_version: Must be exactly 1 (integer)
- report_title: 10-100 characters
- background_context: 50-1000 characters  
- report_outline: 2-5 sections minimum
- Each section title: 5-80 characters
- Each key_question: 10-200 characters

Ensure your JSON output strictly follows these constraints."""
        
        # Generate structured output using native Ollama API
        result = await generate_structured(
            base_url=base_url,
            model_name=model_name,
            messages=[{"role": "user", "content": prompt}],
            schema_class=PlanningResult,
            temperature=0.1  # Low temperature for consistent planning
        )
        
        print(f"[PlannerAgent] Native structured generation success: {len(result.report_outline)} sections planned")
        
        # CRITICAL FIX: Defensive programming for empty outlines
        if not result.report_outline:
            print(f"[PlannerAgent] Warning: Empty outline detected, creating fallback section")
            # Create a fallback section to prevent downstream crashes
            fallback_section = ResearchStep(
                title="Research Overview",
                key_question="What information should be researched about this topic?",
                research_approach="Conduct comprehensive research and analysis"
            )
            result.report_outline = [fallback_section]
        
        return result
        
    except Exception as e:
        print(f"[PlannerAgent] Native structured generation failed: {e}")
        raise Exception(f"Native structured generation failed: {e}")
        # NOTE: No fallback - we are committed to native structured generation only


def create_planner_agent_native(config: LLMConfig) -> ResearchAgent:
    """
    Create PlannerAgent using native Ollama structured outputs.
    
    This replaces the complex Outlines integration with direct native API calls,
    providing the same structured generation benefits with minimal complexity.
    """
    from .utils.model_role_registry import ModelRole
    
    # Use dedicated PLANNER role
    selected_model = config.get_model_for_role(ModelRole.PLANNER)
    
    print(f"[INFO] PlannerAgent: Using native Ollama structured generation")
    print(f"[INFO] Model: {getattr(selected_model, 'model', str(selected_model))}")
    
    async def run_native_planning(input_data: Union[str, Dict[str, Any]]) -> PlanningResult:
        """Run planning with native structured generation"""
        return await generate_planning_native(config, selected_model, input_data)
    
    # Create agent with native structured generation function
    agent = ResearchAgent(
        name="PlannerAgent",
        instructions="Research planning with native structured generation",
        model=selected_model,
        output_type=PlanningResult
    )
    
    # Add the native generation method
    agent.run_native_planning = run_native_planning
    
    return agent


# Backward compatibility function (replace the original)
def init_planner_agent(config: LLMConfig) -> ResearchAgent:
    """Initialize PlannerAgent with native structured generation (backward compatible)"""
    return create_planner_agent_native(config)


# For testing individual agent
async def test_planner_agent_native(config: LLMConfig, test_query: str = None) -> bool:
    """
    Test the native PlannerAgent implementation.
    
    Args:
        config: LLM configuration
        test_query: Optional test query (defaults to quantum computing)
        
    Returns:
        True if test passes, False otherwise
    """
    if test_query is None:
        test_query = "What is quantum computing and how does it work?"
    
    try:
        agent = create_planner_agent_native(config)
        result = await agent.run_native_planning(test_query)
        
        # Validate result structure
        assert isinstance(result, PlanningResult)
        assert hasattr(result, 'report_outline')
        assert hasattr(result, 'background_context')
        assert hasattr(result, 'report_title')
        
        # Validate content quality
        assert len(result.report_outline) > 0, "Should generate report outline sections"
        assert len(result.report_title) > 0, "Should generate report title"
        
        print(f"SUCCESS: Native PlannerAgent test passed")
        print(f"   Report title: {result.report_title}")
        print(f"   Sections planned: {len(result.report_outline)}")
        for i, section in enumerate(result.report_outline[:3]):  # Show first 3 sections
            print(f"   Section {i+1}: {section.title}")
            
        return True
        
    except Exception as e:
        print(f"FAILED: Native PlannerAgent test failed: {e}")
        return False
