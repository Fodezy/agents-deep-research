# HYBRID-07 Implementation Plan: KnowledgeGapAgent Outlines Refactor

**Date:** August 6, 2025  
**Ticket:** HYBRID-07 - Outlines refactor — KnowledgeGap  
**Status:** 🚧 PLANNED  
**Timeline:** 1 sprint (1 week implementation)  

---

## 1. Executive Summary & Core Objective

Implement complete Outlines refactor for KnowledgeGapAgent to achieve 98%+ valid structured knowledge gap analysis outputs with zero OutputParserError incidents. This builds directly on the proven patterns established in HYBRID-05 (ToolSelector) and HYBRID-06 (PlannerAgent), leveraging the validated 4-model architecture (HYBRID-08) to enable reliable knowledge gap identification through structured generation.

**Core Objective:** Transform KnowledgeGapAgent from legacy JSON parsing to Outlines-based structured generation, ensuring gap analysis outputs pass schema validation and integrate seamlessly with the research pipeline while maintaining perfect backward compatibility.

**Business Value:**
- **Gap Analysis Reliability:** 98%+ valid structured gap identification (vs current parsing failures)
- **Zero Parse Errors:** Eliminate OutputParserError incidents in knowledge gap analysis phase
- **Research Pipeline Integrity:** Ensure reliable gap-to-tool mapping for comprehensive research
- **Foundation for HYBRID-09:** Complete structured agent ecosystem enabling WriterAgent guardrails

**Strategic Impact:** Completes the core structured agent triad (ToolSelector → Planner → KnowledgeGap) that forms the backbone of the research pipeline, enabling reliable automated research workflows with structured data flow throughout.

---

## 2. Key Questions, Risks, and Assumptions

### Key Questions (To be Answered in Discovery)

#### Product/UX Questions
- **Q1:** Should knowledge gaps include confidence scores to indicate certainty of gap identification?
- **Q2:** How should overlapping or duplicate gaps be handled in the structured output?
- **Q3:** Should gap prioritization be automated based on research context or remain manual?
- **Q4:** How should knowledge gaps be grouped or categorized for downstream tool selection?

#### Technical Questions  
- **Q5:** Will the existing gap analysis logic work with structured schemas or need redesign?
- **Q6:** Can the KNOWLEDGE_GAP model (from 4-model architecture) handle complex gap reasoning within context limits?
- **Q7:** How should the schema handle dynamic gap types discovered during research?
- **Q8:** Should gap analysis support iterative refinement as research progresses?

### Potential Risks

#### Technical Risks
- **R1:** KNOWLEDGE_GAP model may struggle with complex contextual gap reasoning → Mitigation: Use proven schema patterns from HYBRID-05/06, implement iterative gap refinement
- **R2:** Gap analysis may become too rigid for evolving research contexts → Mitigation: Design flexible schema with extensible gap categories
- **R3:** Context window limits may prevent comprehensive gap analysis for large research topics → Mitigation: Implement gap chunking and incremental analysis patterns

#### Product Risks
- **R4:** Structured gap analysis may miss nuanced gaps that human researchers would identify → Mitigation: Include gap confidence scoring and human review integration points
- **R5:** Gap categorization may not align with researcher mental models → Mitigation: Design intuitive gap taxonomy based on existing usage patterns
- **R6:** Integration complexity may introduce latency in research workflow → Mitigation: Maintain performance parity with legacy implementation

### Core Assumptions

- **A1:** Current KnowledgeGapAgent failures are primarily due to malformed JSON parsing, not logical gap analysis errors
- **A2:** The 4-model architecture's KNOWLEDGE_GAP model can effectively handle structured gap analysis schemas
- **A3:** Existing gap analysis prompts can be adapted to structured output without loss of quality
- **A4:** Researchers value gap analysis reliability over minor workflow changes
- **A5:** Downstream tool selection can effectively utilize structured gap data for improved research targeting

---

## 3. Proposed MVP (Minimum Viable Product)

### Core Functionality

1. **Outlines Gap Analysis Schema** (`KnowledgeGapResult`, `KnowledgeGap`) with Pydantic validation
2. **Template-Based Gap Analysis Prompts** following HYBRID-05/06 patterns
3. **KNOWLEDGE_GAP Model Integration** using `config.get_model_for_role(ModelRole.KNOWLEDGE_GAP)`
4. **Graceful Fallback** to legacy parsing when Outlines unavailable
5. **Input Parameter Extraction** handling research context and current findings
6. **Comprehensive Test Coverage** following proven HYBRID-05/06 test patterns
7. **Backward Compatibility** via schema aliases preserving existing workflows

### Out of Scope

- **Advanced Gap Analytics** (gap trend analysis, research progress tracking)
- **Multi-Modal Gap Detection** (image, audio, or video content gap analysis)
- **Real-Time Gap Refinement** based on live research results
- **Gap Visualization Interfaces** for debugging and researcher interaction
- **Dynamic Schema Evolution** based on research domain specificity

---

## 4. Phased Implementation Plan

### Phase 1: Discovery & Design (1-2 days)
- Analyze existing KnowledgeGapAgent implementation and gap analysis patterns
- Design gap analysis schemas (`KnowledgeGapResult`, `KnowledgeGap`) based on current outputs
- Define input parameter extraction requirements for research context and findings
- Create template system for gap analysis prompts following HYBRID-06 patterns

### Phase 2: Backend Development (2-3 days)  
- Implement Outlines gap analysis schemas in `outlines_schemas.py`
- Create gap analysis templates in `outlines_templates.py`
- Refactor KnowledgeGapAgent with dual-path (structured/legacy) support
- Integrate with 4-model architecture using KNOWLEDGE_GAP role

### Phase 3: Testing & Validation (1-2 days)
- Comprehensive test suite covering all integration patterns (50+ tests target)
- Mock model validation for both structured and legacy paths
- End-to-end gap analysis workflow validation with research pipeline
- Performance benchmarking vs legacy implementation (<20% latency increase)

### Phase 4: QA & Documentation (1 day)
- Final integration testing with ResearchRunner and downstream agents
- Complete implementation documentation following HYBRID-05/06 patterns
- Performance validation and migration notes for future enhancements

---

## 5. Initial Backlog (Ticket-Ready Stories)

### Epic: HYBRID-07 KnowledgeGap Outlines Refactor

#### Ticket HYBRID-07-01: Discovery & Technical Design
**Type:** Story  
**Description:** Research and analyze existing KnowledgeGapAgent implementation, design gap analysis schemas, and create technical specification for Outlines integration following proven HYBRID-05/06 patterns.

**Acceptance Criteria:**
- [ ] Existing KnowledgeGapAgent patterns documented and analyzed
- [ ] Gap analysis schemas (`KnowledgeGapResult`, `KnowledgeGap`) designed and validated
- [ ] Template system architecture defined for gap analysis prompts
- [ ] Input parameter extraction patterns specified for research context and findings
- [ ] Technical design document created following HYBRID-06 implementation patterns

**Dependencies:** HYBRID-05 (completed), HYBRID-06 (completed), HYBRID-08 (4-model architecture)

#### Ticket HYBRID-07-02: Gap Analysis Schema Implementation
**Type:** Story  
**Description:** Implement Pydantic schemas for structured gap analysis output with Outlines integration support, following proven schema design patterns from HYBRID-05/06.

**Acceptance Criteria:**
- [ ] `KnowledgeGapResult` schema created with validation rules and field constraints
- [ ] `KnowledgeGap` schema supports all current gap analysis output types
- [ ] Schemas serialize to valid JSON for downstream tool selection consumption
- [ ] Schema validation handles edge cases and malformed gap analysis inputs
- [ ] Unit tests cover all schema validation scenarios (15+ tests minimum)

**Dependencies:** HYBRID-07-01

#### Ticket HYBRID-07-03: Gap Analysis Template System
**Type:** Story  
**Description:** Create template-based gap analysis prompt generation replacing f-string patterns, following HYBRID-06 template system architecture.

**Acceptance Criteria:**
- [ ] `render_gap_analysis_prompt()` function for structured output path
- [ ] `render_legacy_gap_analysis_prompt()` function for fallback path
- [ ] Dynamic date injection and runtime content population
- [ ] No placeholder tokens in rendered output
- [ ] Template tests verify no f-string injection issues (25+ tests minimum)

**Dependencies:** HYBRID-07-01

#### Ticket HYBRID-07-04: KnowledgeGapAgent Refactor
**Type:** Story  
**Description:** Refactor KnowledgeGapAgent with Outlines integration and 4-model architecture support, implementing dual-path architecture following HYBRID-05/06 patterns.

**Acceptance Criteria:**
- [ ] Outlines integration using `outlines.Generator(model, schema)`
- [ ] 4-model architecture integration with `ModelRole.KNOWLEDGE_GAP`
- [ ] Graceful fallback handling for Outlines import errors
- [ ] Input parameter extraction with graceful extra key handling
- [ ] Module-qualified imports for proper test mocking
- [ ] Backward compatibility aliases (`ReportGaps = KnowledgeGapResult`)

**Dependencies:** HYBRID-07-02, HYBRID-07-03

#### Ticket HYBRID-07-05: Gap Analysis Integration Testing
**Type:** Story  
**Description:** Comprehensive test suite for gap analysis workflows covering all integration patterns, following proven HYBRID-05/06 test architecture.

**Acceptance Criteria:**
- [ ] 50+ tests covering input extraction, template rendering, agent initialization, end-to-end workflows
- [ ] Mock model validation for structured and legacy paths
- [ ] End-to-end gap analysis workflow integration tests with research pipeline
- [ ] Schema validation and JSON serialization tests with edge cases
- [ ] Backward compatibility verification with existing research workflows

**Dependencies:** HYBRID-07-04

#### Ticket HYBRID-07-06: Performance & Documentation
**Type:** Story  
**Description:** Performance validation, implementation documentation, and preparation for HYBRID-09 WriterAgent integration.

**Acceptance Criteria:**
- [ ] Performance benchmarks show <20% latency increase vs legacy
- [ ] Implementation report documents actual working integration following HYBRID-06 format
- [ ] Gap analysis patterns documented for HYBRID-09 WriterAgent integration
- [ ] Integration points validated with research pipeline and tool selection
- [ ] Migration notes prepared for future gap analysis enhancements

**Dependencies:** HYBRID-07-05

---

## 6. Definition of Done (DoD)

### Technical Completion Criteria
- [ ] **Outlines Integration:** Actual `outlines.Generator` with JSON schema generation (not placeholder)
- [ ] **4-Model Architecture:** Uses `config.get_model_for_role(ModelRole.KNOWLEDGE_GAP)` for dedicated gap analysis model
- [ ] **Schema Validation:** Gap analysis output passes Pydantic validation with 98%+ success rate
- [ ] **Graceful Fallback:** Handles Outlines unavailability with legacy parsing path
- [ ] **Zero Parse Errors:** No `OutputParserError` incidents in gap analysis phase

### Integration Criteria  
- [ ] **ResearchRunner Compatibility:** Maintains exact same initialization signature and output contracts
- [ ] **Template Integration:** Dynamic content population eliminates all placeholder tokens
- [ ] **Backward Compatibility:** Zero breaking changes to existing gap analysis workflows
- [ ] **Pipeline Integration:** Seamless integration with ToolSelector and PlannerAgent outputs

### Quality Assurance Criteria
- [ ] **Test Coverage:** 100% pass rate across all test categories (50+ tests minimum)
- [ ] **Performance:** Gap analysis latency increase <20% vs legacy implementation
- [ ] **Documentation:** Implementation report reflects actual working integration with patterns for HYBRID-09
- [ ] **Code Quality:** Clean imports, no circular dependencies, consistent patterns with HYBRID-05/06

### Production Readiness Criteria
- [ ] **End-to-End Validation:** Planning → Gap Analysis → Tool Selection → Execution pipeline verified
- [ ] **Edge Case Handling:** Robust parameter extraction and error recovery for gap analysis scenarios
- [ ] **Monitoring Ready:** Integration points for future observability hooks and gap analysis metrics
- [ ] **Foundation Complete:** Patterns proven for HYBRID-09 WriterAgent guardrails integration

---

## Architecture Integration Points

### With HYBRID-05 (ToolSelector)
- **Schema Compatibility:** Gap analysis output feeds directly into ToolSelector structured input
- **Shared Patterns:** Template system, input extraction, dual-path architecture
- **Error Handling:** Consistent fallback mechanisms and validation patterns

### With HYBRID-06 (PlannerAgent)  
- **Workflow Integration:** Gap analysis consumes planning output to identify research gaps
- **Template Consistency:** Same runtime injection and parameter extraction patterns
- **Schema Evolution:** Consistent versioning and backward compatibility approach

### With HYBRID-08 (4-Model Architecture)
- **Model Role:** Dedicated KNOWLEDGE_GAP model for optimal gap analysis performance
- **Runtime Assertions:** Gap analysis model validation and role enforcement
- **Config Integration:** Seamless integration with model role registry

### With Future HYBRID-09 (WriterAgent)
- **Gap-Driven Writing:** Structured gap data enables targeted writing instructions
- **Quality Assurance:** Gap analysis validates completeness before final writing
- **Structured Pipeline:** Complete structured data flow from planning through writing

---

## Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Gap Analysis JSON Validity** | ≥98% | Schema validation pass rate |
| **OutputParserError Incidents** | 0 | Error monitoring in gap analysis phase |
| **Latency Impact** | <20% increase | Performance benchmarks vs legacy |
| **Test Coverage** | 100% pass rate | Automated test suite execution (50+ tests) |
| **Integration Success** | Zero breaking changes | Research pipeline compatibility tests |
| **Gap-to-Tool Accuracy** | Maintain current levels | Downstream ToolSelector effectiveness |

---

## Technical Foundation

### Schema Design Principles
```python
# Gap analysis result structure following HYBRID-05/06 patterns
class KnowledgeGap(BaseModel):
    gap_id: str = Field(description="Unique gap identifier", min_length=3, max_length=50)
    description: str = Field(description="Gap description", min_length=10, max_length=500)
    priority: Literal["high", "medium", "low"] = Field(description="Gap priority")
    research_approach: str = Field(description="Suggested research approach", min_length=10, max_length=200)
    confidence: float = Field(description="Gap identification confidence", ge=0.0, le=1.0, default=1.0)

class KnowledgeGapResult(BaseModel):
    schema_version: int = Field(description="Schema version", default=1)
    research_context: str = Field(description="Research context summary", min_length=20, max_length=1000)
    gaps_identified: List[KnowledgeGap] = Field(description="Identified knowledge gaps", min_length=0, max_length=10)
    analysis_summary: str = Field(description="Gap analysis summary", min_length=50, max_length=2000)
    total_gaps: int = Field(description="Total number of gaps identified", ge=0)

# Backward compatibility aliases
ReportGaps = KnowledgeGapResult
ReportGapItem = KnowledgeGap
```

### Integration Pattern
```python
# KNOWLEDGE_GAP model integration following HYBRID-06 pattern
selected_model = config.get_model_for_role(ModelRole.KNOWLEDGE_GAP)

# Outlines structured generation
schema = outlines.json_schema(KnowledgeGapResult)
generator = outlines.Generator(selected_model, schema)
result = generator(gap_analysis_prompt)
```

### Template System Architecture
```python
# Gap analysis template following HYBRID-06 patterns
def render_gap_analysis_prompt(research_context: str, current_findings: str = "") -> str:
    current_date = datetime.now().strftime('%Y-%m-%d')  # Runtime injection
    findings_section = f"\n\nCurrent Findings:\n{current_findings}" if current_findings.strip() else ""
    
    return f"""You are the Knowledge Gap Analyzer for a research project. Today's date is {current_date}.

Your task is to analyze the research progress and identify remaining knowledge gaps that need to be addressed.

Research Context: {research_context}{findings_section}

Analyze the current state and identify specific knowledge gaps with:
1. Clear gap descriptions (10-500 characters each)
2. Priority levels (high/medium/low) based on research importance
3. Suggested research approaches for addressing each gap
4. Confidence scores for gap identification accuracy

Focus on gaps that can be addressed through additional research, not fundamental limitations."""
```

---

**Next Action:** Begin HYBRID-07-01 Discovery & Technical Design phase to analyze existing KnowledgeGapAgent and design comprehensive gap analysis schema architecture following proven HYBRID-05/06 patterns.

**Strategic Positioning:** HYBRID-07 completes the structured agent triad (ToolSelector → Planner → KnowledgeGap) enabling reliable end-to-end research workflows with structured data throughout, positioning for HYBRID-09 WriterAgent guardrails and complete pipeline automation.