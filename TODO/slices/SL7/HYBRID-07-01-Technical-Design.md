# HYBRID-07-01: Discovery & Technical Design Report

**Date:** August 6, 2025  
**Ticket:** HYBRID-07-01 - Discovery & Technical Design  
**Status:** ✅ COMPLETED  
**Timeline:** Completed (discovery analysis)  

---

## Executive Summary

Completed comprehensive analysis of existing KnowledgeGapAgent implementation revealing **model role misalignment**, **f-string datetime injection issues**, and **limited schema flexibility** causing potential OutputParserError incidents. Designed robust knowledge gap analysis architecture following proven HYBRID-05/06 patterns to achieve reliable structured output with zero parsing failures.

**Key Discovery:** Current KnowledgeGapAgent incorrectly uses `ModelRole.PLANNER` instead of dedicated knowledge gap analysis role, and employs legacy f-string datetime patterns that create stale date injection issues.

**Solution Approach:** Implement dual-path Outlines integration with enhanced schemas, template system, and dedicated KNOWLEDGE_GAP model role following proven architectural patterns from HYBRID-05/06.

---

## 1. Current Implementation Analysis

### 1.1 Existing KnowledgeGapAgent Structure

**File:** `deep_researcher/agents/knowledge_gap_agent.py`

**Current Schema:**
```python
class KnowledgeGapOutput(BaseModel):
    """Output from the Knowledge Gap Agent"""
    research_complete: bool = Field(description="Whether the research and findings are complete enough to end the research loop")
    outstanding_gaps: List[str] = Field(description="List of knowledge gaps that still need to be addressed")
```

**Current Issues Identified:**

1. **Model Role Misalignment** (Line 59):
   ```python
   selected_model = config.get_model_for_role(ModelRole.PLANNER)
   ```
   - Uses PLANNER role instead of dedicated KNOWLEDGE_GAP role
   - Conflicts with PLANNER model allocation in research pipeline
   - May cause resource contention and suboptimal model selection

2. **F-String Datetime Injection** (Line 32-33):
   ```python
   INSTRUCTIONS = f"""
   You are the Knowledge-Gap Agent. Today's date is {datetime.now():%Y-%m-%d}.
   ```
   - Hardcoded at import time, creates stale date issues
   - Inconsistent with HYBRID-05/06 template pattern
   - Same anti-pattern identified and fixed in PlannerAgent

3. **Limited Schema Flexibility:**
   - Binary `research_complete` decision lacks confidence scoring
   - `outstanding_gaps` as simple strings lacks priority/categorization
   - No gap analysis metadata (confidence, research approach, etc.)
   - Missing backward compatibility considerations

4. **Inconsistent Architecture:**
   - Lacks dual-path structured/legacy approach from HYBRID-05/06
   - No template system for prompt generation
   - Missing input parameter extraction patterns
   - No graceful fallback handling for Outlines unavailability

### 1.2 Current Usage Pattern Analysis

**Integration Point:** `deep_researcher/iterative_research.py`

**Usage Method:** `_evaluate_gaps()`
```python
async def _evaluate_gaps(self, query: str, background_context: str = "") -> KnowledgeGapOutput:
    input_str = f"""
    Current Iteration Number: {self.iteration}
    Time Elapsed: {(time.time() - self.start_time) / 60:.2f} minutes of maximum {self.max_time_minutes} minutes

    ORIGINAL QUERY:
    {query}

    BACKGROUND CONTEXT:
    {background_context}

    HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
    {self.conversation.compile_conversation_history() or "No previous actions, findings or thoughts available."}        
    """

    result = await ResearchRunner.run(self.knowledge_gap_agent, input_str)
    evaluation = result.final_output_as(KnowledgeGapOutput)
```

**Input Format Requirements:**
- Multi-section structured input with iteration context
- Research query and background context
- Conversation history with findings and thoughts
- Time constraints and iteration metadata

**Output Requirements:**
- Boolean research completion indicator
- List of outstanding knowledge gaps for tool selection
- Integration with ResearchRunner workflow

---

## 2. Problem Statement & Critical Issues

### 2.1 Schema Compatibility Issues

**Current Schema Limitations:**
```python
# Current: Too simplistic for complex gap analysis
class KnowledgeGapOutput(BaseModel):
    research_complete: bool  # Binary decision lacks nuance
    outstanding_gaps: List[str]  # Simple strings lack metadata
```

**Required Enhancements:**
- Gap priority scoring (high/medium/low)
- Confidence levels for gap identification
- Research approach suggestions per gap
- Gap categorization and metadata
- Extensible schema for future gap types

### 2.2 Model Role Architecture Mismatch

**Issue:** KnowledgeGapAgent uses `ModelRole.PLANNER` 
- **Conflict:** PLANNER role already allocated to PlannerAgent
- **Performance:** No specialized model optimization for gap analysis
- **Scalability:** Resource contention in pipeline execution

**Solution Required:** Implement dedicated `ModelRole.KNOWLEDGE_GAP` role

### 2.3 Template System Inconsistency

**Current F-String Issues:**
- Stale datetime injection at import time
- No runtime content population
- Inconsistent with HYBRID-05/06 template patterns
- Missing parameter extraction flexibility

---

## 3. Schema Design (Following HYBRID-05/06 Patterns)

### 3.1 Enhanced Knowledge Gap Schemas

**Following HYBRID-06 Schema Architecture:**

```python
class KnowledgeGap(BaseModel):
    """Individual knowledge gap with metadata"""
    gap_id: str = Field(description="Unique gap identifier", min_length=3, max_length=50)
    description: str = Field(description="Gap description", min_length=10, max_length=500)
    priority: Literal["high", "medium", "low"] = Field(description="Gap priority for research")
    research_approach: str = Field(description="Suggested research approach", min_length=10, max_length=200)
    confidence: float = Field(description="Gap identification confidence", ge=0.0, le=1.0, default=1.0)
    category: Optional[str] = Field(description="Gap category", max_length=50, default=None)

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
        if 'gaps_identified' in info.data:
            if v != len(info.data['gaps_identified']):
                raise ValueError('total_gaps must match length of gaps_identified')
        return v

# Backward compatibility aliases (CRITICAL for zero breaking changes)
KnowledgeGapOutput = KnowledgeGapResult  # Preserve existing interface
```

**Schema Improvements:**
- ✅ Enhanced gap metadata with priority, confidence, research approach
- ✅ Research completeness confidence scoring
- ✅ Comprehensive analysis summary and context
- ✅ Schema versioning for future evolution
- ✅ Field constraints following HYBRID-06 validation patterns
- ✅ Backward compatibility via aliases (zero breaking changes)

### 3.2 Input Parameter Extraction (Following HYBRID-06 Pattern)

```python
def extract_knowledge_gap_params(input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Extract parameters for knowledge gap analysis following HYBRID-06 pattern"""
    if isinstance(input_data, dict):
        # Handle dictionary input with graceful extra key handling
        return {
            "research_context": input_data.get("research_context", input_data.get("query", "")),
            "background_context": input_data.get("background_context", ""),
            "findings_history": input_data.get("findings_history", input_data.get("history", "")),
            "iteration_context": input_data.get("iteration_context", {})
        }
    
    if isinstance(input_data, str):
        # Parse structured string input from ResearchRunner
        # Extract ORIGINAL QUERY, BACKGROUND CONTEXT, HISTORY sections
        patterns = {
            "query": r"ORIGINAL QUERY:\s*(.+?)(?=\n\n|\nBACKGROUND|\nHISTORY|$)",
            "background": r"BACKGROUND CONTEXT:\s*(.+?)(?=\n\n|\nHISTORY|$)", 
            "history": r"HISTORY OF ACTIONS.*?:\s*(.+?)(?=\n\n|$)"
        }
        
        result = {"research_context": "", "background_context": "", "findings_history": "", "iteration_context": {}}
        
        for key, pattern in patterns.items():
            match = re.search(pattern, input_data, re.DOTALL | re.IGNORECASE)
            if match:
                if key == "query":
                    result["research_context"] = match.group(1).strip()
                elif key == "background":
                    result["background_context"] = match.group(1).strip()
                elif key == "history":
                    result["findings_history"] = match.group(1).strip()
        
        # Extract iteration metadata if present
        iteration_match = re.search(r"Current Iteration Number:\s*(\d+)", input_data)
        if iteration_match:
            result["iteration_context"]["iteration"] = int(iteration_match.group(1))
            
        return result
    
    return {
        "research_context": str(input_data), 
        "background_context": "", 
        "findings_history": "",
        "iteration_context": {}
    }
```

---

## 4. Template System Architecture (Following HYBRID-06 Patterns)

### 4.1 Structured Output Template

```python
def render_knowledge_gap_prompt(
    research_context: str, 
    background_context: str = "", 
    findings_history: str = "",
    iteration_context: Dict[str, Any] = None
) -> str:
    """Render knowledge gap analysis prompt for structured output"""
    current_date = datetime.now().strftime('%Y-%m-%d')  # Runtime injection
    
    background_section = f"\n\nBackground Context:\n{background_context}" if background_context.strip() else ""
    history_section = f"\n\nResearch History:\n{findings_history}" if findings_history.strip() else ""
    
    iteration_info = ""
    if iteration_context:
        iteration = iteration_context.get("iteration", 0)
        iteration_info = f"\n\nIteration: {iteration}"
    
    return f"""You are the Knowledge Gap Analyzer for a research project. Today's date is {current_date}.

Your task is to analyze the current research progress and identify remaining knowledge gaps that need to be addressed.

Research Context: {research_context}{background_section}{history_section}{iteration_info}

Analyze the research state and provide:
1. Assessment of research completeness with confidence level
2. Identification of specific knowledge gaps with priority levels
3. Research approach suggestions for each identified gap
4. Overall analysis summary

Focus on gaps that can be addressed through additional research tools and methods."""
```

### 4.2 Legacy Parsing Template

```python
def render_legacy_knowledge_gap_prompt(
    research_context: str, 
    background_context: str = "", 
    findings_history: str = "",
    iteration_context: Dict[str, Any] = None
) -> str:
    """Render legacy prompt with explicit JSON format requirements"""
    current_date = datetime.now().strftime('%Y-%m-%d')  # Runtime injection
    
    # Same parameter handling as structured template
    background_section = f"\n\nBackground Context:\n{background_context}" if background_context.strip() else ""
    history_section = f"\n\nResearch History:\n{findings_history}" if findings_history.strip() else ""
    
    return f"""You are the Knowledge Gap Analyzer for a research project. Today's date is {current_date}.

Research Context: {research_context}{background_section}{history_section}

You MUST respond with a JSON object in exactly this format - no extra keys, no commentary:

{{
  "schema_version": 1,
  "research_complete": false,
  "research_completeness_confidence": 0.8,
  "research_context": "Brief summary of research context",
  "gaps_identified": [
    {{
      "gap_id": "gap_1",
      "description": "Specific knowledge gap description (10-500 chars)",
      "priority": "high",
      "research_approach": "Suggested approach to address this gap (10-200 chars)",
      "confidence": 0.9
    }}
  ],
  "analysis_summary": "Comprehensive analysis of current research state and identified gaps (50-2000 chars)",
  "total_gaps": 1
}}

Identify 0-10 specific, actionable knowledge gaps that can be addressed through additional research."""
```

---

## 5. Agent Architecture Design

### 5.1 Dual-Path Architecture (Following HYBRID-05/06)

```python
def init_knowledge_gap_agent(config: LLMConfig) -> ResearchAgent:
    """Initialize KnowledgeGapAgent with dual-path Outlines integration"""
    from .utils.model_role_registry import ModelRole
    
    # CRITICAL: Use dedicated KNOWLEDGE_GAP role (not PLANNER)
    selected_model = config.get_model_for_role(ModelRole.KNOWLEDGE_GAP)
    
    # Check Outlines availability and model support
    outlines_available = False
    generator = None
    
    try:
        import outlines
        if llm_config.model_supports_structured_output(selected_model):
            # Create JSON schema and generator for structured output
            schema = outlines.json_schema(KnowledgeGapResult)
            generator = outlines.Generator(selected_model, schema)
            outlines_available = True
    except (ImportError, Exception) as e:
        print(f"[WARNING] Outlines not available ({e}), falling back to legacy parsing")
        outlines_available = False
        generator = None
    
    if outlines_available:
        # Structured path with Outlines integration
        def structured_generator(input_data: Union[str, Dict[str, Any]]) -> KnowledgeGapResult:
            """Generate structured gap analysis using Outlines"""
            params = extract_knowledge_gap_params(input_data)
            prompt = render_knowledge_gap_prompt(**params)
            return generator(prompt)
        
        return ResearchAgent(
            name="KnowledgeGapAgent",
            instructions="",  # Template handles instructions
            model=selected_model,
            output_type=KnowledgeGapResult,
            structured_generator=structured_generator
        )
    else:
        # Legacy path with dynamic instructions and parsing
        def dynamic_instructions(input_data: Union[str, Dict[str, Any]]) -> str:
            """Generate dynamic instructions for legacy parsing"""
            params = extract_knowledge_gap_params(input_data)
            return render_legacy_knowledge_gap_prompt(**params)
        
        return ResearchAgent(
            name="KnowledgeGapAgent",
            instructions=dynamic_instructions,  # Function for dynamic instructions
            model=selected_model,
            output_parser=create_type_parser(KnowledgeGapResult)
        )
```

### 5.2 Model Role Registry Enhancement

**Required Addition to ModelRole enum:**
```python
class ModelRole(Enum):
    """Defines the 4 model roles in the architecture."""
    PLANNER = "planner"
    TOOL_CALLING = "tool_calling" 
    SUMMARISER = "summariser"
    WRITER = "writer"
    KNOWLEDGE_GAP = "knowledge_gap"  # NEW: Dedicated gap analysis role
```

**Role Specification:**
```python
ModelRole.KNOWLEDGE_GAP: RoleSpecification(
    role=ModelRole.KNOWLEDGE_GAP,
    required_capabilities={'text-generation', 'reasoning', 'analysis'},
    preferred_tags={'reasoning', 'analysis', 'instruction-following', 'evaluation'},
    min_context_length=8192,  # Needs longer context for research history analysis
    supports_function_calling=False,
    description="Analyzes research progress and identifies knowledge gaps"
)
```

---

## 6. Test Architecture (Following HYBRID-05/06 Patterns)

### 6.1 Comprehensive Test Coverage Plan

**Following HYBRID-06 Test Categories:**

1. **Schema Validation Tests** (`tests/test_knowledge_gap_schemas.py`) - **15+ tests**
   - `KnowledgeGap` field validation and constraints
   - `KnowledgeGapResult` schema validation and edge cases
   - JSON serialization and deserialization
   - Backward compatibility with `KnowledgeGapOutput` alias

2. **Template System Tests** (`tests/test_knowledge_gap_templates.py`) - **25+ tests**
   - Structured and legacy template rendering
   - Runtime date injection validation
   - Parameter extraction with various input formats
   - Template content validation and security

3. **Agent Integration Tests** (`tests/test_knowledge_gap_integration.py`) - **12+ tests**
   - Dual-path agent initialization
   - Structured and legacy path execution
   - Fallback handling and error recovery
   - Backward compatibility verification

4. **End-to-End Workflow Tests** (`tests/test_knowledge_gap_end_to_end.py`) - **10+ tests**
   - Complete gap analysis workflow validation
   - ResearchRunner integration patterns
   - Performance characteristics validation
   - Pipeline integration with ToolSelector

**Total: 60+ tests** (exceeding HYBRID-05/06 standards)

### 6.2 Mock Model Patterns

```python
class MockKnowledgeGapModel:
    """Mock KNOWLEDGE_GAP model for testing"""
    def __init__(self, structured_response=None):
        self.structured_response = structured_response or KnowledgeGapResult(
            research_complete=False,
            research_completeness_confidence=0.7,
            research_context="AI applications research context",
            gaps_identified=[
                KnowledgeGap(
                    gap_id="gap_1",
                    description="Recent developments in AI healthcare applications",
                    priority="high",
                    research_approach="Search recent papers and clinical trials",
                    confidence=0.8
                )
            ],
            analysis_summary="Research shows good coverage of fundamentals but lacks recent developments",
            total_gaps=1
        )
    
    def __call__(self, prompt: str) -> KnowledgeGapResult:
        return self.structured_response
```

---

## 7. Success Criteria (HYBRID-07-01 Acceptance)

### 7.1 Technical Design Validation

- ✅ **Schema Design:** Enhanced `KnowledgeGapResult` with comprehensive gap metadata
- ✅ **Template System:** Runtime injection patterns following HYBRID-06 architecture  
- ✅ **Dual-Path Architecture:** Structured and legacy paths with graceful fallback
- ✅ **Model Role:** Dedicated `KNOWLEDGE_GAP` role specification defined
- ✅ **Input Extraction:** Robust parameter extraction for complex research contexts
- ✅ **Backward Compatibility:** Alias mapping preserves existing `KnowledgeGapOutput` interface

### 7.2 Integration Design Validation

- ✅ **ResearchRunner Integration:** Maintains existing initialization and usage patterns
- ✅ **Pipeline Compatibility:** Seamless integration with ToolSelector and PlannerAgent
- ✅ **Error Handling:** Comprehensive fallback and recovery mechanisms
- ✅ **Performance Planning:** <20% latency increase target vs legacy implementation

### 7.3 Test Strategy Validation

- ✅ **Test Coverage Plan:** 60+ tests across all integration patterns
- ✅ **Mock Architecture:** Comprehensive model mocking for reliable testing
- ✅ **Edge Case Coverage:** Complex input formats and error scenarios
- ✅ **Performance Testing:** Benchmark validation framework defined

---

## 8. Next Steps (HYBRID-07-02)

### 8.1 Implementation Priority Order

1. **HYBRID-07-02:** Implement enhanced schemas in `outlines_schemas.py`
2. **HYBRID-07-03:** Create template system in `outlines_templates.py`  
3. **HYBRID-07-04:** Refactor KnowledgeGapAgent with dual-path architecture
4. **HYBRID-07-05:** Comprehensive test suite implementation
5. **HYBRID-07-06:** Performance validation and documentation

### 8.2 Critical Dependencies

**Dependencies:** HYBRID-05 (completed), HYBRID-06 (completed), HYBRID-08 (4-model architecture)  
**Blocks:** HYBRID-09 (WriterAgent guardrails)  
**Model Role:** Requires `ModelRole.KNOWLEDGE_GAP` addition to registry

---

## Conclusion

Discovery phase completed successfully, revealing critical model role misalignment and f-string anti-patterns causing potential pipeline failures. Designed comprehensive solution following proven HYBRID-05/06 patterns ensuring:

- **Enhanced Schema:** Rich gap metadata with priority, confidence, and research approaches
- **Dual-Path Architecture:** Reliable structured generation with comprehensive fallback
- **Template System:** Runtime injection eliminating stale date issues
- **Model Role Separation:** Dedicated KNOWLEDGE_GAP role preventing resource conflicts
- **Zero Breaking Changes:** Backward compatibility via schema aliases
- **Comprehensive Testing:** 60+ tests exceeding previous implementation standards

**Technical Foundation:** Established complete architecture for reliable knowledge gap analysis with structured output, enabling seamless integration with research pipeline and foundation for HYBRID-09 WriterAgent integration.

**Ready for HYBRID-07-02 implementation phase.**