"""Outlines function schemas for structured agent output"""
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

class AgentTask(BaseModel):
    model_config = ConfigDict(extra='forbid')
    gap: Optional[str] = Field(description="The knowledge gap being addressed", default=None)
    agent: str = Field(description="The name of the agent to use")
    query: str = Field(description="The specific query for the agent")
    entity_website: Optional[str] = Field(description="The website of the entity being researched, if known", default=None)

class AgentSelectionPlan(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: int = Field(description="Schema version for compatibility", default=1)
    tasks: List[AgentTask] = Field(description="List of agent tasks to address knowledge gaps")
    
    @field_validator('schema_version')
    @classmethod
    def validate_schema_version(cls, v):
        if v != 1:
            raise ValueError('schema_version must be 1')
        return v

# Planning schemas for PlannerAgent
class ResearchStep(BaseModel):
    """A research step in the planning process (matches ValidationWrapper expectations)"""
    model_config = ConfigDict(extra='forbid')
    title: str = Field(description="Title of the section", min_length=5, max_length=80)
    key_question: str = Field(description="Key question to address", min_length=10, max_length=200)

class PlanningResult(BaseModel):
    """Output from the Planner Agent (matches ValidationWrapper ReportPlan schema exactly)"""
    model_config = ConfigDict(extra='forbid')
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
    model_config = ConfigDict(extra='forbid')
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
    model_config = ConfigDict(extra='forbid')
    schema_version: int = Field(description="Schema version", default=1)
    research_complete: bool = Field(description="Whether research is complete")
    research_completeness_confidence: float = Field(description="Confidence in completeness assessment", ge=0.0, le=1.0, default=1.0)
    research_context: str = Field(description="Research context summary", min_length=20, max_length=1000)
    gaps_identified: List[KnowledgeGap] = Field(description="Identified knowledge gaps", min_length=0, max_length=10)
    analysis_summary: str = Field(description="Gap analysis summary", min_length=50, max_length=2000)
    total_gaps: int = Field(description="Total number of gaps identified", ge=0)
    iteration_context: Optional[Dict[str, str]] = Field(description="Iteration metadata", default=None)

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

# Tool agent output schemas for SearchAgent and CrawlAgent
class EnhancedToolAgentOutput(BaseModel):
    """Enhanced tool agent output with validation and metadata"""
    model_config = ConfigDict(extra='forbid')
    
    output: str = Field(
        description="Comprehensive summary addressing the knowledge gap",
        min_length=10,
        max_length=2000
    )
    
    sources: list[str] = Field(
        default_factory=list,
        description="Source URLs referenced in the summary",
        max_length=20
    )
    
    # Optional metadata for observability (HYBRID-02 integration)
    processing_method: Optional[str] = Field(
        default=None,
        description="Method used: 'structured' or 'legacy'"
    )
    
    confidence: Optional[float] = Field(
        default=None,
        description="Confidence score for the summary quality",
        ge=0.0,
        le=1.0
    )
    
    processing_time_ms: Optional[int] = Field(
        default=None,
        description="Processing time in milliseconds",
        ge=0
    )

# Backward compatibility alias for existing ToolAgentOutput consumers
ToolAgentOutput = EnhancedToolAgentOutput

# Structured summarization schemas
class StructuredSummary(BaseModel):
    """Structured summary output for hierarchical summarization"""
    model_config = ConfigDict(extra='forbid')
    output: str = Field(
        description="Comprehensive summary of the content", 
        min_length=50, 
        max_length=2000
    )
    key_findings: List[str] = Field(
        description="List of key findings or important points", 
        min_length=1, 
        max_length=10
    )
    sources: List[str] = Field(
        description="List of source URLs or references",
        default_factory=list
    )
    confidence: float = Field(
        description="Confidence score for the summary quality",
        ge=0.0,
        le=1.0,
        default=0.9
    )
    processing_metadata: Dict[str, str] = Field(
        description="Processing metadata including timing and chunk information",
        default_factory=dict
    )

    @field_validator('key_findings')
    @classmethod
    def validate_key_findings(cls, v):
        """Ensure all key findings are meaningful"""
        for finding in v:
            if not finding or len(finding.strip()) < 10:
                raise ValueError('Each key finding must be at least 10 characters long')
        return v

class ChunkSummaryItem(BaseModel):
    """Individual chunk summary for debugging and observability"""
    model_config = ConfigDict(extra='forbid')
    chunk_id: int = Field(description="Chunk identifier")
    summary: Optional[str] = Field(
        description="Summary of this chunk", 
        min_length=10, 
        max_length=500,
        default=None
    )
    key_points: List[str] = Field(
        description="Key points from this chunk",
        default_factory=list,
        max_length=5
    )
    token_count: int = Field(description="Token count for this chunk", ge=0)
    processing_time_ms: Optional[int] = Field(
        description="Processing time for this chunk in milliseconds", 
        ge=0, 
        default=None
    )
    error: Optional[str] = Field(description="Error message if processing failed", default=None)


def summarise_content_structured(
    content: str,
    context: str,
    sources: List[str] = None
) -> StructuredSummary:
    """
    Create a structured summary of content with key findings and metadata.
    
    This function is used by Outlines to generate structured summaries with
    consistent schema validation and rich metadata.
    
    Args:
        content: The content to summarize
        context: Context or purpose for the summarization
        sources: Optional list of source URLs or references
        
    Returns:
        StructuredSummary with output, key_findings, sources, and metadata
        
    Example:
        For research content about quantum computing, returns structured
        summary with key findings and confidence scoring.
    """
    # This function signature is used by Outlines for structured generation
    # The actual implementation is handled by the LLM through Outlines
    pass


def summarise_chunk_structured(
    chunk_content: str,
    chunk_id: int,
    context: str
) -> ChunkSummaryItem:
    """
    Create a structured summary of a content chunk.
    
    This function is used by Outlines for structured chunk summarization
    in hierarchical processing workflows.
    
    Args:
        chunk_content: The chunk content to summarize
        chunk_id: Identifier for the chunk
        context: Context for summarization
        
    Returns:
        ChunkSummaryItem with summary and key points
    """
    # This function signature is used by Outlines for structured generation
    # The actual implementation is handled by the LLM through Outlines
    pass


def summarise_search_results(
    knowledge_gap: str,
    search_query: str,
    search_results: str,
    entity_website: Optional[str] = None
) -> EnhancedToolAgentOutput:
    """
    Summarise web search results to address a specific knowledge gap.
    
    This function is used by Outlines to generate structured search summaries.
    
    Args:
        knowledge_gap: The specific knowledge gap being addressed
        search_query: The search query that was executed
        search_results: Raw search results from the web search tool
        entity_website: Optional specific website context for the research
        
    Returns:
        EnhancedToolAgentOutput with structured summary and source URLs
        
    Example:
        For knowledge_gap="recent quantum computing breakthroughs" and search results,
        returns structured output with comprehensive summary and source URLs
    """
    # This function signature is used by Outlines for structured generation
    # The actual implementation is handled by the LLM through Outlines
    pass

def summarise_crawled_content(
    knowledge_gap: str,
    target_website: str,
    crawled_content: str,
    search_query: Optional[str] = None
) -> EnhancedToolAgentOutput:
    """
    Summarise crawled website content to address a specific knowledge gap.
    
    This function is used by Outlines to generate structured crawl summaries.
    
    Args:
        knowledge_gap: The specific knowledge gap being addressed
        target_website: The website URL that was crawled
        crawled_content: Raw content from the website crawling tool
        search_query: Optional query context that led to this crawling
        
    Returns:
        EnhancedToolAgentOutput with structured summary and source URLs
        
    Example:
        For knowledge_gap="company financial performance" and crawled annual report,
        returns structured output with key financial insights and source URL
    """
    # This function signature is used by Outlines for structured generation
    # The actual implementation is handled by the LLM through Outlines
    pass

def analyze_knowledge_gaps(
    research_context: str,
    background_context: str = "",
    findings_history: str = "",
    iteration_context: Optional[Dict[str, str]] = None
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