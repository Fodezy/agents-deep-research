"""
Agent used to determine which specialized agents should be used to address knowledge gaps.

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
from .. import llm_config
from .baseclass import ResearchAgent
from .utils.outlines_schemas import AgentSelectionPlan, AgentTask
from .utils.outlines_templates import render_outlines_prompt, render_legacy_prompt
from .utils.parse_output import create_type_parser


def extract_tool_selector_params(input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """FIXED: Extract research context and knowledge gaps from formatted input"""
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


def init_tool_selector_agent(config: LLMConfig) -> ResearchAgent:
    """Initialize ToolSelectorAgent with Outlines structured output"""
    from .utils.model_role_registry import ModelRole
    selected_model = config.get_model_for_role(ModelRole.TOOL_CALLING)
    
    if llm_config.model_supports_structured_output(selected_model):
        # Outlines structured generation path
        try:
            import outlines
            # Create JSON schema and generator for structured output
            schema = outlines.json_schema(AgentSelectionPlan)
            generator = outlines.Generator(selected_model, schema)
            outlines_available = True
        except (ImportError, Exception) as e:
            print(f"[WARNING] Outlines not available ({e}), falling back to legacy parsing")
            outlines_available = False
            generator = None
        
        def structured_call(input_data: Union[str, Dict[str, Any]]) -> AgentSelectionPlan:
            """Generate structured agent selection plan using Outlines"""
            params = extract_tool_selector_params(input_data)
            prompt = render_outlines_prompt(**params)
            
            if outlines_available and generator:
                try:
                    # Use Outlines for structured generation
                    result = generator(prompt)
                    
                    # Ensure we return an AgentSelectionPlan object
                    if isinstance(result, dict):
                        return AgentSelectionPlan(**result)
                    elif isinstance(result, AgentSelectionPlan):
                        return result
                    else:
                        # Fallback if generation fails
                        return AgentSelectionPlan(tasks=[
                            AgentTask(
                                gap=params.get("knowledge_gaps", ["Unknown gap"])[0] if params.get("knowledge_gaps") else "Unknown gap",
                                agent="WebSearchAgent", 
                                query=params.get("research_context", "research query")[:50]
                            )
                        ])
                except Exception as e:
                    print(f"[WARNING] Outlines generation failed: {e}, falling back to basic plan")
                    # Fallback plan on any error
                    return AgentSelectionPlan(tasks=[
                        AgentTask(
                            gap=params.get("knowledge_gaps", ["Unknown gap"])[0] if params.get("knowledge_gaps") else "Unknown gap",
                            agent="WebSearchAgent",
                            query=params.get("research_context", "research query")[:50]
                        )
                    ])
            else:
                # Outlines not available, return basic plan
                return AgentSelectionPlan(tasks=[
                    AgentTask(
                        gap=params.get("knowledge_gaps", ["Unknown gap"])[0] if params.get("knowledge_gaps") else "Unknown gap",
                        agent="WebSearchAgent",
                        query=params.get("research_context", "research query")[:50]
                    )
                ])
        
        return ResearchAgent(
            name="ToolSelectorAgent",
            instructions="",  # Template handles instructions
            model=selected_model,
            structured_generator=structured_call,
            output_type=AgentSelectionPlan
        )
    else:
        # Legacy fallback path (FIXED: real values, no placeholders)
        def dynamic_instructions(input_data: Union[str, Dict[str, Any]]) -> str:
            params = extract_tool_selector_params(input_data)
            return render_legacy_prompt(**params)
        
        return ResearchAgent(
            name="ToolSelectorAgent",
            instructions=dynamic_instructions,  # Function, not string
            model=selected_model,
            output_parser=create_type_parser(AgentSelectionPlan)
        )
