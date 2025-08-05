"""Outlines function schemas for structured agent output"""
from typing import List, Optional
from pydantic import BaseModel, Field

class AgentTask(BaseModel):
    gap: Optional[str] = Field(description="The knowledge gap being addressed", default=None)
    agent: str = Field(description="The name of the agent to use")
    query: str = Field(description="The specific query for the agent")
    entity_website: Optional[str] = Field(description="The website of the entity being researched, if known", default=None)

class AgentSelectionPlan(BaseModel):
    tasks: List[AgentTask] = Field(description="List of agent tasks to address knowledge gaps")

def select_tools(
    research_context: str,
    knowledge_gaps: List[str]
) -> AgentSelectionPlan:
    """
    Select appropriate research tools and create agent tasks to address knowledge gaps.
    
    This function is used by Outlines to generate structured agent selection plans.
    
    Args:
        research_context: The overall research question or topic
        knowledge_gaps: List of specific information gaps to fill
        
    Returns:
        AgentSelectionPlan with list of agent tasks
        
    Example:
        For research_context="quantum computing" and knowledge_gaps=["recent breakthroughs"],
        returns plan with WebSearchAgent task for "quantum computing breakthroughs 2024"
    """
    # This function signature is used by Outlines for structured generation
    # The actual implementation is handled by the LLM through Outlines
    pass