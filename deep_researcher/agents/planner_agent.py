"""
Agent used to produce an initial outline of the report, including a list of section titles and the key question to be 
addressed in each section.

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
from .. import llm_config  # Module-qualified for proper mocking
from .utils.parse_output import create_type_parser
from .utils.outlines_schemas import PlanningResult, ResearchStep
from .utils.outlines_templates import render_planning_prompt, render_legacy_planning_prompt, extract_planner_params


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

def init_planner_agent(config: LLMConfig) -> ResearchAgent:
    """Initialize PlannerAgent with dual-path Outlines integration"""
    from .utils.model_role_registry import ModelRole
    
    selected_model = config.get_model_for_role(ModelRole.PLANNER)
    
    # Check Outlines availability and model support
    outlines_available = False
    generator = None
    
    try:
        import outlines
        if llm_config.model_supports_structured_output(selected_model):
            # Create JSON schema and generator for structured output
            schema = outlines.json_schema(PlanningResult)
            generator = outlines.Generator(selected_model, schema)
            outlines_available = True
    except (ImportError, Exception) as e:
        print(f"[WARNING] Outlines not available ({e}), falling back to legacy parsing")
        outlines_available = False
        generator = None
    
    if outlines_available:
        # Structured path with Outlines integration
        def structured_generator(input_data: Union[str, Dict[str, Any]]) -> PlanningResult:
            """Generate structured planning output using Outlines"""
            params = extract_planner_params(input_data)
            prompt = render_planning_prompt(**params)
            return generator(prompt)
        
        return ResearchAgent(
            name="PlannerAgent",
            instructions="",  # Template handles instructions
            model=selected_model,
            output_type=PlanningResult,
            structured_generator=structured_generator
        )
    else:
        # Legacy path with dynamic instructions and parsing
        def dynamic_instructions(input_data: Union[str, Dict[str, Any]]) -> str:
            """Generate dynamic instructions for legacy parsing"""
            params = extract_planner_params(input_data)
            return render_legacy_planning_prompt(**params)
        
        return ResearchAgent(
            name="PlannerAgent",
            instructions=dynamic_instructions,  # Function for dynamic instructions
            model=selected_model,
            output_parser=create_type_parser(PlanningResult)
        )
