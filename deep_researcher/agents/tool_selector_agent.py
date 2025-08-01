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

from pydantic import BaseModel, Field
from typing import List, Optional
from ..llm_config import LLMConfig, model_supports_structured_output
from datetime import datetime
from .baseclass import ResearchAgent
from .utils.parse_output import create_type_parser


class AgentTask(BaseModel):
    """A task for a specific agent to address knowledge gaps"""
    gap: Optional[str] = Field(description="The knowledge gap being addressed", default=None)
    agent: str = Field(description="The name of the agent to use")
    query: str = Field(description="The specific query for the agent")
    entity_website: Optional[str] = Field(description="The website of the entity being researched, if known", default=None)


class AgentSelectionPlan(BaseModel):
    """Plan for which agents to use for knowledge gaps"""
    tasks: List[AgentTask] = Field(description="List of agent tasks to address knowledge gaps")


INSTRUCTIONS = f"""
You are the Tool Selector for a research project. Today's date is {datetime.now():%Y-%m-%d}.

You will be given:
- ORIGINAL QUERY: <the user’s question>
- KNOWLEDGE GAP TO ADDRESS: <the specific gap>
- BACKGROUND CONTEXT: <any relevant context>
- HISTORY OF ACTIONS, FINDINGS AND THOUGHTS: <previous steps in the research>

Decide which specialized agents to call (at most 3) **from this list only**:
  • WebSearchAgent
  • SiteCrawlerAgent

Pick concise 3–6 word queries, and include a website when relevant.

Only output valid JSON matching exactly this schema—no extra keys, no commentary, no markdown fences:

{{
  "tasks": [
    {{
      "gap": "Describe the specific knowledge gap here",
      "agent": "WebSearchAgent",
      "query": "3–6 word query",
      "entity_website": "https://optional.domain.com"
    }},
    {{
      "gap": "Another gap if needed",
      "agent": "SiteCrawlerAgent",
      "query": "short query",
      "entity_website": "https://another.site"
    }}
  ]
}}
"""

def init_tool_selector_agent(config: LLMConfig) -> ResearchAgent:
    selected_model = config.reasoning_model

    return ResearchAgent(
        name="ToolSelectorAgent",
        instructions=INSTRUCTIONS,
        model=selected_model,
        output_type=AgentSelectionPlan if model_supports_structured_output(selected_model) else None,
        output_parser=create_type_parser(AgentSelectionPlan) if not model_supports_structured_output(selected_model) else None
    )
