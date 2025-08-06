"""Outlines function schemas for structured agent output"""
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator

class AgentTask(BaseModel):
    gap: Optional[str] = Field(description="The knowledge gap being addressed", default=None)
    agent: str = Field(description="The name of the agent to use")
    query: str = Field(description="The specific query for the agent")
    entity_website: Optional[str] = Field(description="The website of the entity being researched, if known", default=None)

class AgentSelectionPlan(BaseModel):
    tasks: List[AgentTask] = Field(description="List of agent tasks to address knowledge gaps")

# Planning schemas for PlannerAgent
class ResearchStep(BaseModel):
    """A research step in the planning process (matches ValidationWrapper expectations)"""
    title: str = Field(description="Title of the section", min_length=5, max_length=80)
    key_question: str = Field(description="Key question to address", min_length=10, max_length=200)

class PlanningResult(BaseModel):
    """Output from the Planner Agent (matches ValidationWrapper ReportPlan schema exactly)"""
    schema_version: int = Field(description="Schema version for compatibility", default=1)
    report_title: str = Field(description="The title of the report", min_length=10, max_length=100)
    background_context: str = Field(description="A summary of supporting context", min_length=50, max_length=1000)
    report_outline: List[ResearchStep] = Field(
        description="List of sections that need to be written in the report", 
        min_length=2, 
        max_length=5
    )
    
    @field_validator('schema_version')
    @classmethod
    def validate_schema_version(cls, v):
        if v != 1:
            raise ValueError('schema_version must be 1')
        return v

# Knowledge gap analysis schemas for KnowledgeGapAgent
class KnowledgeGap(BaseModel):
    """Individual knowledge gap with metadata"""
    gap_id: str = Field(description="Unique gap identifier", min_length=3, max_length=50)
    description: str = Field(description="Gap description", min_length=10, max_length=500)
    priority: Literal["high", "medium", "low"] = Field(description="Gap priority for research")
    research_approach: str = Field(description="Suggested research approach", min_length=10, max_length=200)
    confidence: float = Field(description="Gap identification confidence", ge=0.0, le=1.0, default=1.0)
    category: Optional[str] = Field(description="Gap category", max_length=50, default=None)

    @field_validator('gap_id')
    @classmethod
    def validate_gap_id(cls, v):
        # Ensure gap_id is alphanumeric with underscores/dashes
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('gap_id must be alphanumeric with optional underscores or dashes')
        return v

class KnowledgeGapResult(BaseModel):
    """Enhanced gap analysis output with metadata"""
    schema_version: int = Field(description="Schema version", default=1)
    research_complete: bool = Field(description="Whether research is complete")
    research_completeness_confidence: float = Field(description="Confidence in completeness assessment", ge=0.0, le=1.0, default=1.0)
    research_context: str = Field(description="Research context summary", min_length=20, max_length=1000)
    gaps_identified: List[KnowledgeGap] = Field(description="Identified knowledge gaps", min_length=0, max_length=10)
    analysis_summary: str = Field(description="Gap analysis summary", min_length=50, max_length=2000)
    total_gaps: int = Field(description="Total number of gaps identified", ge=0)
    iteration_context: Optional[Dict[str, Any]] = Field(description="Iteration metadata", default=None)

    @field_validator('total_gaps')
    @classmethod
    def validate_total_gaps(cls, v, info):
        if hasattr(info, 'data') and 'gaps_identified' in info.data:
            if v != len(info.data['gaps_identified']):
                raise ValueError('total_gaps must match length of gaps_identified')
        return v

    @field_validator('schema_version')
    @classmethod
    def validate_schema_version(cls, v):
        if v != 1:
            raise ValueError('schema_version must be 1')
        return v
    
    @property
    def outstanding_gaps(self) -> List[str]:
        """Backward compatibility property: convert gaps_identified to simple string list"""
        return [gap.description for gap in self.gaps_identified]

# Backward compatibility aliases (CRITICAL for zero breaking changes)
KnowledgeGapOutput = KnowledgeGapResult

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

def create_plan(
    research_question: str,
    context: str = ""
) -> PlanningResult:
    """
    Create a comprehensive research plan breaking down the question into manageable sections.
    
    This function is used by Outlines to generate structured planning results.
    
    Args:
        research_question: The main research question to investigate
        context: Optional background context to inform the planning
        
    Returns:
        PlanningResult with structured report plan including title, context, and outline
        
    Example:
        For research_question="quantum computing applications" and context="focus on 2024",
        returns plan with report title, background context, and 2-5 research sections
    """
    # This function signature is used by Outlines for structured generation
    # The actual implementation is handled by the LLM through Outlines
    pass

def analyze_knowledge_gaps(
    research_context: str,
    background_context: str = "",
    findings_history: str = "",
    iteration_context: Optional[Dict[str, Any]] = None
) -> KnowledgeGapResult:
    """
    Analyze research progress and identify remaining knowledge gaps that need to be addressed.
    
    This function is used by Outlines to generate structured knowledge gap analysis.
    
    Args:
        research_context: The main research question or topic being investigated
        background_context: Optional background context for the research
        findings_history: History of research findings and actions taken
        iteration_context: Optional metadata about the current research iteration
        
    Returns:
        KnowledgeGapResult with comprehensive gap analysis including identified gaps,
        completeness assessment, and research recommendations
        
    Example:
        For research_context="AI healthcare applications" with some findings_history,
        returns analysis with specific gaps like "recent clinical trial results" with
        priority levels and research approaches
    """
    # This function signature is used by Outlines for structured generation
    # The actual implementation is handled by the LLM through Outlines
    pass