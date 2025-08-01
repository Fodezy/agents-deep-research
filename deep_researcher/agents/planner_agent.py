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
from typing import List
from .baseclass import ResearchAgent
from ..llm_config import LLMConfig, model_supports_structured_output
from .utils.parse_output import create_type_parser
from datetime import datetime


class ReportPlanSection(BaseModel):
    """A section of the report that needs to be written"""
    title: str = Field(description="The title of the section")
    key_question: str = Field(description="The key question to be addressed in the section")


class ReportPlan(BaseModel):
    """Output from the Report Planner Agent"""
    background_context: str = Field(description="A summary of supporting context that can be passed onto the research agents")
    report_outline: List[ReportPlanSection] = Field(description="List of sections that need to be written in the report")
    report_title: str = Field(description="The title of the report")

INSTRUCTIONS = f"""
You are the Report Planner for a research project. Today's date is {datetime.now():%Y-%m-%d}.

You will receive:
- QUERY: <the user’s research question>

Your task:
1. Provide a concise report title.
2. Summarize any initial background context in 1–2 paragraphs.
3. Outline the report as a list of sections, each with a title and a key question.

You MUST respond with only valid JSON matching exactly this schema—no extra keys, no markdown fences, no commentary:

{{
  "report_title": "A concise, descriptive title for the report",
  "background_context": "1–2 paragraphs of background context.",
  "report_outline": [
    {{
      "title": "Section 1 Title",
      "key_question": "The specific question this section answers"
    }},
    {{
      "title": "Section 2 Title",
      "key_question": "Another section question"
    }}
  ]
}}
"""

def init_planner_agent(config: LLMConfig) -> ResearchAgent:
    selected_model = config.reasoning_model

    return ResearchAgent(
        name="PlannerAgent",
        instructions=INSTRUCTIONS,
        model=selected_model,
        output_type=ReportPlan if model_supports_structured_output(selected_model) else None,
        output_parser=create_type_parser(ReportPlan) if not model_supports_structured_output(selected_model) else None
    )
