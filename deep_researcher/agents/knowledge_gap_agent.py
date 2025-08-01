"""
Agent used to evaluate the state of the research report (typically done in a loop) and identify knowledge gaps that still 
need to be addressed.

The Agent takes as input a string in the following format:
===========================================================
ORIGINAL QUERY: <original user query>

HISTORY OF ACTIONS, FINDINGS AND THOUGHTS: <breakdown of activities and findings carried out so far>
===========================================================

The Agent then:
1. Carefully reviews the current draft and assesses its completeness in answering the original query
2. Identifies specific knowledge gaps that still exist and need to be filled
3. Returns a KnowledgeGapOutput object
"""

from pydantic import BaseModel, Field
from typing import List
from .baseclass import ResearchAgent
from ..llm_config import LLMConfig, model_supports_structured_output
from datetime import datetime
from .utils.parse_output import create_type_parser

class KnowledgeGapOutput(BaseModel):
    """Output from the Knowledge Gap Agent"""
    research_complete: bool = Field(description="Whether the research and findings are complete enough to end the research loop")
    outstanding_gaps: List[str] = Field(description="List of knowledge gaps that still need to be addressed")


# We've removed the 'f' from the front and the date variable
INSTRUCTIONS = f"""
You are the Knowledge-Gap Agent. Today's date is {datetime.now():%Y-%m-%d}.

You will receive:
- ORIGINAL QUERY: <the user’s question>
- HISTORY OF ACTIONS, FINDINGS AND THOUGHTS: <what’s been done so far>

Your task:
1. Decide whether the research is complete.
2. If complete, output `"research_complete": true` and an empty list of gaps.
3. If not complete, output `"research_complete": false` and list up to three concise, actionable knowledge gaps.

You MUST respond with only valid JSON matching exactly this schema—no extra keys, no commentary, no markdown fences:

{{
  "research_complete": false,
  "outstanding_gaps": [
    "A single, concise knowledge gap that must be addressed next.",
    "Another specific gap (if applicable)."
  ]
}}
"""



def init_knowledge_gap_agent(config: LLMConfig) -> ResearchAgent:
    selected_model = config.reasoning_model

    return ResearchAgent(
        name="KnowledgeGapAgent",
        instructions=INSTRUCTIONS,
        model=selected_model,
        output_type=KnowledgeGapOutput if model_supports_structured_output(selected_model) else None,
        output_parser=create_type_parser(KnowledgeGapOutput) if not model_supports_structured_output(selected_model) else None
    )