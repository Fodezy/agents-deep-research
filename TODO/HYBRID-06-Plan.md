# HYBRID-06 Implementation Plan: Planner Outlines Refactor

**Date:** August 5, 2025  
**Ticket:** HYBRID-06 - Outlines refactor — Planner  
**Status:** 🚧 PLANNED  
**Timeline:** 1 sprint (1 week implementation)  

---

## 1. Executive Summary & Core Objective

Implement complete Outlines refactor for PlannerAgent to achieve 98%+ valid structured planning outputs with zero OutputParserError incidents. This builds directly on the validated 4-model architecture (HYBRID-08) and proven Outlines integration patterns (HYBRID-05), enabling reliable structured planning through the dedicated PLANNER model role.

**Core Objective:** Transform PlannerAgent from legacy JSON parsing to Outlines-based structured generation, ensuring planning outputs pass schema validation and integrate seamlessly with the validated 4-model architecture.

**Business Value:**
- **Planning Reliability:** 98%+ valid structured plans (vs current parsing failures)
- **Zero Parse Errors:** Eliminate OutputParserError incidents in planning phase
- **Foundation for HYBRID-07:** Proven patterns for KnowledgeGap agent refactor
- **4-Model Integration:** Leverage dedicated PLANNER model for optimal performance

---

## 2. Key Questions, Risks, and Assumptions

### Key Questions (To be Answered in Discovery)

#### Product/UX Questions
- **Q1:** Should planning output include confidence scores for each research step?
- **Q2:** Do researchers need visibility into the planning model's reasoning process?
- **Q3:** How should planning failures be communicated to users vs auto-recovery?

#### Technical Questions  
- **Q4:** Will the existing database schema support structured planning metadata?
- **Q5:** Can the PLANNER model handle complex multi-step research plans within context limits?
- **Q6:** Should planning schemas support extensible step types for future agent additions?

### Potential Risks

#### Technical Risks
- **R1:** PLANNER model may not respect complex nested planning schemas → Mitigation: Flatten schema design, use proven patterns from HYBRID-05
- **R2:** Planning context windows may be exceeded for complex research queries → Mitigation: Implement plan chunking and iterative planning
- **R3:** Outlines integration may add significant latency to planning phase → Mitigation: Benchmark against legacy, optimize schema complexity

#### Product Risks
- **R4:** Structured planning output may be too rigid for complex research scenarios → Mitigation: Design flexible schema with optional fields
- **R5:** Researchers may not trust automated planning vs manual step definition → Mitigation: Preserve planning transparency and explainability

### Core Assumptions

- **A1:** Malformed planning JSON, not logical planning errors, cause >90% of current planning failures
- **A2:** PLANNER model from 4-model architecture can handle structured planning schemas effectively  
- **A3:** Planning output validation can be performed synchronously without blocking research pipeline
- **A4:** Researchers value planning reliability over minor latency increases

---

## 3. Proposed MVP (Minimum Viable Product)

### Core Functionality

1. **Outlines Planning Schema** (`PlanningResult`, `ResearchStep`) with Pydantic validation
2. **Template-Based Planning Prompts** replacing f-string injection patterns  
3. **PLANNER Model Integration** using `config.get_model_for_role(ModelRole.PLANNER)`
4. **Graceful Fallback** to legacy parsing when Outlines unavailable
5. **Input Parameter Extraction** handling various planning input formats
6. **Comprehensive Test Coverage** following HYBRID-05 patterns

### Out of Scope

- **Advanced Planning Strategies** (multi-model planning, planning optimization)
- **Planning UI/UX Interfaces** for debugging and visualization  
- **Dynamic Schema Evolution** based on research domain
- **Planning Performance Optimization** beyond basic structured output

---

## 4. Phased Implementation Plan

### Phase 1: Discovery & Design (1-2 days)
- Analyze existing PlannerAgent implementation and usage patterns
- Design planning schemas (`PlanningResult`, `ResearchStep`) based on current outputs
- Define input parameter extraction requirements
- Create template system for planning prompts

### Phase 2: Backend Development (2-3 days)  
- Implement Outlines planning schemas in `outlines_schemas.py`
- Create planning templates in `outlines_templates.py`
- Refactor PlannerAgent with dual-path (structured/legacy) support
- Integrate with 4-model architecture using PLANNER role

### Phase 3: Testing & Validation (1-2 days)
- Comprehensive test suite covering all integration patterns
- Mock model validation for both structured and legacy paths
- End-to-end planning workflow validation
- Performance benchmarking vs legacy implementation

### Phase 4: QA & Documentation (1 day)
- Final integration testing with ResearchRunner
- Update implementation documentation
- Prepare for HYBRID-07 (KnowledgeGap) integration

---

## 5. Initial Backlog (Ticket-Ready Stories)

### Epic: HYBRID-06 Planner Outlines Refactor

#### Ticket HYBRID-06-01: Discovery & Technical Design
**Type:** Story  
**Description:** Research and analyze existing PlannerAgent implementation, design planning schemas, and create technical specification for Outlines integration.

**Acceptance Criteria:**
- [ ] Existing PlannerAgent patterns documented and analyzed
- [ ] Planning schemas (`PlanningResult`, `ResearchStep`) designed and validated
- [ ] Template system architecture defined for planning prompts
- [ ] Input parameter extraction patterns specified
- [ ] Technical design document created and reviewed

**Dependencies:** HYBRID-05 (completed), HYBRID-08 (4-model architecture)

#### Ticket HYBRID-06-02: Planning Schema Implementation
**Type:** Story  
**Description:** Implement Pydantic schemas for structured planning output with Outlines integration support.

**Acceptance Criteria:**
- [ ] `PlanningResult` schema created with validation rules
- [ ] `ResearchStep` schema supports all current planning step types
- [ ] Schemas serialize to valid JSON for downstream consumption
- [ ] Schema validation handles edge cases and malformed inputs
- [ ] Unit tests cover all schema validation scenarios

**Dependencies:** HYBRID-06-01

#### Ticket HYBRID-06-03: Planning Template System
**Type:** Story  
**Description:** Create template-based planning prompt generation replacing f-string patterns.

**Acceptance Criteria:**
- [ ] `render_planning_prompt()` function for structured output path
- [ ] `render_legacy_planning_prompt()` function for fallback path
- [ ] Dynamic date injection and runtime content population
- [ ] No placeholder tokens in rendered output
- [ ] Template tests verify no f-string injection

**Dependencies:** HYBRID-06-01

#### Ticket HYBRID-06-04: PlannerAgent Refactor
**Type:** Story  
**Description:** Refactor PlannerAgent with Outlines integration and 4-model architecture support.

**Acceptance Criteria:**
- [ ] Outlines integration using `outlines.Generator(model, schema)`
- [ ] 4-model architecture integration with `ModelRole.PLANNER`
- [ ] Graceful fallback handling for Outlines import errors
- [ ] Input parameter extraction with extra key handling
- [ ] Module-qualified imports for proper test mocking

**Dependencies:** HYBRID-06-02, HYBRID-06-03

#### Ticket HYBRID-06-05: Planning Integration Testing
**Type:** Story  
**Description:** Comprehensive test suite for planning workflows covering all integration patterns.

**Acceptance Criteria:**
- [ ] 15+ tests covering input extraction, template rendering, agent initialization
- [ ] Mock model validation for structured and legacy paths
- [ ] End-to-end planning workflow integration tests
- [ ] Schema validation and JSON serialization tests
- [ ] Backward compatibility verification with ResearchRunner

**Dependencies:** HYBRID-06-04

#### Ticket HYBRID-06-06: Performance & Documentation
**Type:** Story  
**Description:** Performance validation, implementation documentation, and preparation for HYBRID-07.

**Acceptance Criteria:**
- [ ] Performance benchmarks show <20% latency increase vs legacy
- [ ] Implementation report documents actual working integration
- [ ] Planning patterns documented for HYBRID-07 reuse
- [ ] Integration points validated with existing codebase
- [ ] Migration notes prepared for future planning enhancements

**Dependencies:** HYBRID-06-05

---

## 6. Definition of Done (DoD)

### Technical Completion Criteria
- [ ] **Outlines Integration:** Actual `outlines.Generator` with JSON schema generation (not placeholder)
- [ ] **4-Model Architecture:** Uses `config.get_model_for_role(ModelRole.PLANNER)` for dedicated planning model
- [ ] **Schema Validation:** Planning output passes Pydantic validation with 98%+ success rate
- [ ] **Graceful Fallback:** Handles Outlines unavailability with legacy parsing path
- [ ] **Zero Parse Errors:** No `OutputParserError` incidents in planning phase

### Integration Criteria  
- [ ] **ResearchRunner Compatibility:** Maintains exact same initialization signature and output contracts
- [ ] **Template Integration:** Dynamic content population eliminates all placeholder tokens
- [ ] **Backward Compatibility:** Zero breaking changes to existing planning workflows
- [ ] **Error Handling:** Integrates with established error reporting mechanisms

### Quality Assurance Criteria
- [ ] **Test Coverage:** 100% pass rate across all test categories (15+ tests)
- [ ] **Performance:** Planning latency increase <20% vs legacy implementation
- [ ] **Documentation:** Implementation report reflects actual working integration
- [ ] **Code Quality:** Clean imports, no circular dependencies, consistent patterns

### Production Readiness Criteria
- [ ] **End-to-End Validation:** Planning → Tool Selection → Execution pipeline verified
- [ ] **Edge Case Handling:** Robust parameter extraction and error recovery
- [ ] **Monitoring Ready:** Integration points for future observability hooks
- [ ] **Foundation Complete:** Patterns proven for HYBRID-07 KnowledgeGap refactor

---

## Architecture Integration Points

### With HYBRID-05 (ToolSelector)
- **Shared Patterns:** Template system, input extraction, dual-path architecture
- **Schema Compatibility:** Planning output feeds into ToolSelector input requirements
- **Error Handling:** Consistent fallback mechanisms and validation patterns

### With HYBRID-08 (4-Model Architecture)  
- **Model Role:** Dedicated PLANNER model for optimal planning performance
- **Runtime Assertions:** Planning model validation and role enforcement
- **Config Integration:** Seamless integration with model role registry

### With Future HYBRID-07 (KnowledgeGap)
- **Proven Patterns:** Template-based prompts, schema design, test coverage
- **Consistent Architecture:** Same dual-path approach and integration points
- **Knowledge Transfer:** Clear implementation patterns for rapid development

---

## Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **Planning JSON Validity** | ≥98% | Schema validation pass rate |
| **OutputParserError Incidents** | 0 | Error monitoring in planning phase |
| **Latency Impact** | <20% increase | Performance benchmarks vs legacy |
| **Test Coverage** | 100% pass rate | Automated test suite execution |
| **Integration Success** | Zero breaking changes | ResearchRunner compatibility tests |

---

## Technical Foundation

### Schema Design Principles
```python
# Planning result structure
class ResearchStep(BaseModel):
    step_id: str
    description: str
    agent_type: str
    expected_output: str
    dependencies: List[str] = []

class PlanningResult(BaseModel):
    research_question: str
    steps: List[ResearchStep]
    estimated_complexity: Literal["low", "medium", "high"]
    expected_duration: Optional[str] = None
```

### Integration Pattern
```python
# PLANNER model integration
selected_model = config.get_model_for_role(ModelRole.PLANNER)

# Outlines structured generation
schema = outlines.json_schema(PlanningResult)
generator = outlines.Generator(selected_model, schema)
result = generator(planning_prompt)
```

---

**Next Action:** Begin HYBRID-06-01 Discovery & Technical Design phase to analyze existing PlannerAgent and design schema architecture.