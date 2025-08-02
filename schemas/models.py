"""
Pydantic models mirroring the JSON schemas for validation.
These models are used by ValidationWrapper for schema validation.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union


class AgentTask(BaseModel):
    """A task for a specific agent to address knowledge gaps"""
    gap: str = Field(description="The knowledge gap being addressed", min_length=10, max_length=200)
    agent: str = Field(description="The name of the agent to use")
    query: str = Field(description="The specific query for the agent", min_length=5, max_length=50)
    entity_website: Optional[str] = Field(description="The website of the entity being researched", default=None)
    
    @validator('agent')
    def validate_agent(cls, v):
        if v not in ["WebSearchAgent", "SiteCrawlerAgent"]:
            raise ValueError('agent must be "WebSearchAgent" or "SiteCrawlerAgent"')
        return v


class AgentSelectionPlan(BaseModel):
    """Plan for which agents to use for knowledge gaps"""
    schema_version: int = Field(description="Schema version for compatibility", default=1)
    tasks: List[AgentTask] = Field(description="List of agent tasks to address knowledge gaps", min_items=1, max_items=3)
    
    @validator('schema_version')
    def validate_schema_version(cls, v):
        if v != 1:
            raise ValueError('schema_version must be 1')
        return v


class KnowledgeGapOutput(BaseModel):
    """Output from the Knowledge Gap Agent"""
    schema_version: int = Field(description="Schema version for compatibility", default=1)
    research_complete: bool = Field(description="Whether the research is complete enough to end the research loop")
    outstanding_gaps: List[str] = Field(
        description="List of knowledge gaps that still need to be addressed", 
        max_items=3
    )
    
    @validator('schema_version')
    def validate_schema_version(cls, v):
        if v != 1:
            raise ValueError('schema_version must be 1')
        return v
    
    @validator('outstanding_gaps')
    def validate_gaps(cls, v):
        for gap in v:
            if len(gap) < 10 or len(gap) > 200:
                raise ValueError('each gap must be 10-200 characters')
        return v


class ReportPlanSection(BaseModel):
    """A section of the report that needs to be written"""
    title: str = Field(description="The title of the section", min_length=5, max_length=80)
    key_question: str = Field(description="The key question to be addressed in the section", min_length=10, max_length=200)


class ReportPlan(BaseModel):
    """Output from the Report Planner Agent"""
    schema_version: int = Field(description="Schema version for compatibility", default=1)
    report_title: str = Field(description="The title of the report", min_length=10, max_length=100)
    background_context: str = Field(description="A summary of supporting context", min_length=50, max_length=1000)
    report_outline: List[ReportPlanSection] = Field(
        description="List of sections that need to be written in the report", 
        min_items=2, 
        max_items=5
    )
    
    @validator('schema_version')
    def validate_schema_version(cls, v):
        if v != 1:
            raise ValueError('schema_version must be 1')
        return v


class ChunkSourceInfo(BaseModel):
    """Information about the source of a content chunk"""
    url: str = Field(description="Source URL of the content")
    chunk_index: int = Field(description="Index of this chunk within the source document", ge=0)
    total_chunks: int = Field(description="Total number of chunks from this source", ge=1)


class ChunkSummary(BaseModel):
    """Summary of a content chunk during hierarchical summarization"""
    schema_version: int = Field(description="Schema version for compatibility", default=1)
    source_info: ChunkSourceInfo = Field(description="Information about the source of this chunk")
    key_points: List[str] = Field(
        description="List of key points extracted from this chunk", 
        min_items=1, 
        max_items=5
    )
    relevance_score: float = Field(
        description="Relevance score of this chunk to the research query (0-1)", 
        ge=0.0, 
        le=1.0
    )
    
    @validator('schema_version')
    def validate_schema_version(cls, v):
        if v != 1:
            raise ValueError('schema_version must be 1')
        return v
    
    @validator('key_points')
    def validate_key_points(cls, v):
        for point in v:
            if len(point) < 5 or len(point) > 150:
                raise ValueError('each key point must be 5-150 characters')
        return v


# Schema name to model mapping for ValidationWrapper
SCHEMA_MODELS = {
    "select_tools": AgentSelectionPlan,
    "report_gaps": KnowledgeGapOutput,
    "create_plan": ReportPlan,
    "chunk_summary": ChunkSummary
}