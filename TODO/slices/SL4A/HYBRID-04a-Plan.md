# HYBRID-04a Implementation Plan: Outlines-based Summariser

**Date:** January 6, 2025  
**Slice:** HYBRID-04a - Outlines-based Summariser (Structured Output)  
**Priority:** HIGH  
**Dependencies:** HYBRID-08 (Model-Role Registry) ✅ COMPLETED  

---

## 1. Executive Summary & Core Objective

**Core Objective:** Convert SearchAgent and CrawlAgent from legacy parsing to Outlines structured generation, completing the 5-model architecture's summarisation pipeline with 98%+ valid JSON output.

**Current Problem:** 
- SearchAgent and CrawlAgent use legacy `ToolAgentOutput` parsing instead of Outlines structured generation
- Inconsistent with HYBRID-05/06/07 proven patterns
- Missing dual-path architecture for reliability
- No enhanced schema validation with metadata

**Business Value:**
- **Structured Summarisation:** Reliable `{output, sources}` JSON from all tool agents
- **Pipeline Consistency:** All core agents (Planner, ToolSelector, KnowledgeGap, Summariser) use Outlines
- **Zero Parser Errors:** Eliminates `OutputParserError` incidents from search/crawl operations
- **5-Model Architecture:** Completes dedicated `ModelRole.SUMMARISER` integration

**Success Criteria:**
- SearchAgent and CrawlAgent produce 98%+ valid structured JSON via Outlines
- Dual-path architecture with graceful fallback to legacy parsing
- Backward compatibility: existing `ToolAgentOutput` interface preserved
- Performance: <20% latency increase vs current implementation
- Integration: Works seamlessly with HierarchicalSummariser pipeline

---

## 2. Key Questions, Risks, and Assumptions

### Key Questions (To be Answered in Discovery)

| Type | Question |
|------|----------|
| **Technical** | Will ModelRole.SUMMARISER (hermes3:8b) support Outlines structured generation reliably? |
| **Technical** | How should HierarchicalSummariser integrate with Outlines dual-path architecture? |
| **Technical** | Should ToolAgentOutput schema be enhanced with metadata (confidence, processing time)? |
| **Product/UX** | Do downstream consumers need visibility into summarisation method (structured vs legacy)? |
| **Technical** | How will template system handle different search provider result formats? |
| **Performance** | What's the latency impact of Outlines generation on high-volume search/crawl bursts? |

### Potential Risks

| Type | Risk | Mitigation |
|------|------|------------|
| **Technical** | hermes3:8b model doesn't support structured output → falls back to legacy parsing | Implement dual-path architecture; measure fallback rates |
| **Performance** | Outlines generation adds >50% latency to search operations | Benchmark both paths; optimize template rendering |
| **Integration** | Breaking changes to ToolAgentOutput affect downstream agents | Maintain backward compatibility via schema aliases |
| **Quality** | Structured generation produces lower quality summaries than prose | A/B test structured vs legacy output quality |
| **Technical** | HierarchicalSummariser chunking conflicts with Outlines constraints | Design templates to handle chunked content properly |

### Core Assumptions

- **Structured Output Quality:** JSON-formatted summaries will maintain same factual accuracy as prose summaries
- **Model Compatibility:** hermes3:8b (SUMMARISER model) can generate valid JSON when prompted appropriately  
- **Template Flexibility:** Single template system can handle diverse search result formats (Serper, SearXNG, etc.)
- **Performance Acceptable:** 20-30% latency increase is acceptable for reliability gains
- **Backward Compatibility:** Existing consumers can transition to enhanced ToolAgentOutput seamlessly

---

## 3. Proposed MVP (Minimum Viable Product)

### Core Functionality

1. **Outlines Integration for SearchAgent**
   - `outlines.Generator(model, schema)` with ToolAgentOutput JSON schema
   - Dual-path architecture: structured generation + legacy fallback
   - Template system with search provider result formatting

2. **Outlines Integration for CrawlAgent**  
   - Same dual-path architecture pattern as SearchAgent
   - Template system optimized for crawled content summarisation
   - Integration with existing site crawling pipeline

3. **Enhanced ToolAgentOutput Schema**
   - Maintain existing `{output, sources}` structure for backward compatibility
   - Add optional metadata fields (processing_method, confidence, etc.)
   - Pydantic validation with field constraints matching search result patterns

4. **Template System for Summariser Agents**
   - `render_search_summary_prompt()` for structured path
   - `render_legacy_search_summary_prompt()` for fallback path
   - Dynamic content formatting based on search provider results
   - Runtime date injection following HYBRID-07 patterns

5. **Integration Testing**
   - End-to-end search workflow with Outlines generation
   - Crawl workflow with structured summarisation
   - HierarchicalSummariser compatibility validation

### Out of Scope

- **WriterAgent Outlines Integration:** Deferred to future slice
- **Advanced Summarisation Features:** Rich metadata, confidence scoring, multi-model validation
- **Search Provider Optimization:** Provider-specific template customization
- **Performance Optimization:** Advanced caching, streaming generation
- **UI/Debug Surfaces:** Summarisation method visibility in research interface

---

## 4. Phased Implementation Plan

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **1: Discovery & Technical Design** | 0.5 days | Technical design document, schema specifications, template architecture |
| **2: Schema & Template System** | 1 day | Enhanced ToolAgentOutput schema, template rendering system, parameter extraction |
| **3: SearchAgent Outlines Integration** | 1 day | Dual-path SearchAgent with Outlines, comprehensive tests |
| **4: CrawlAgent Outlines Integration** | 1 day | Dual-path CrawlAgent with Outlines, integration tests |
| **5: QA & Performance Validation** | 0.5 days | End-to-end testing, performance benchmarks, regression validation |

**Total: 4 days implementation + comprehensive testing**

---

## 5. Initial Backlog (Ticket-Ready Stories)

### Epic: HYBRID-04a - Outlines-based Summariser

#### **HYBRID-04a-01: Discovery & Technical Design**
- **Type:** Story  
- **Description:** Research current SearchAgent/CrawlAgent architecture and design Outlines integration following HYBRID-07 patterns. Analyze ModelRole.SUMMARISER compatibility and template requirements.
- **Acceptance Criteria:**
  - Technical design document covers dual-path architecture for search/crawl agents
  - ToolAgentOutput schema enhancement plan with backward compatibility strategy  
  - Template system design for search provider result formatting
  - Performance impact analysis and optimization recommendations
- **Dependencies:** None

#### **HYBRID-04a-02: Enhanced Schema & Template System**
- **Type:** Story
- **Description:** Create enhanced ToolAgentOutput schema with validation constraints and implement template system for structured/legacy paths.
- **Acceptance Criteria:**
  - Enhanced ToolAgentOutput schema with optional metadata fields
  - `render_search_summary_prompt()` and `render_legacy_search_summary_prompt()` functions
  - Parameter extraction supporting search result formats
  - Backward compatibility validation via schema tests
- **Dependencies:** HYBRID-04a-01

#### **HYBRID-04a-03: SearchAgent Outlines Integration**
- **Type:** Story  
- **Description:** Refactor SearchAgent to use Outlines structured generation with dual-path architecture and graceful fallback.
- **Acceptance Criteria:**
  - SearchAgent uses `config.get_model_for_role(ModelRole.SUMMARISER)`
  - Outlines integration with `outlines.Generator(model, schema)`
  - Dual-path: structured generation + legacy parsing fallback
  - Template-based instruction generation with search result formatting
  - Comprehensive test suite (15+ tests)
- **Dependencies:** HYBRID-04a-02

#### **HYBRID-04a-04: CrawlAgent Outlines Integration**  
- **Type:** Story
- **Description:** Refactor CrawlAgent following same dual-path pattern as SearchAgent with crawled content optimization.
- **Acceptance Criteria:**
  - CrawlAgent dual-path architecture matching SearchAgent pattern
  - Template system optimized for crawled content summarisation
  - Integration with HierarchicalSummariser pipeline
  - Backward compatibility with existing crawl workflows
  - Comprehensive test suite (15+ tests)
- **Dependencies:** HYBRID-04a-03

#### **HYBRID-04a-05: Integration Testing & Performance Validation**
- **Type:** Story
- **Description:** End-to-end testing of search/crawl workflows with performance benchmarking and regression validation.
- **Acceptance Criteria:**
  - End-to-end search workflow produces valid ToolAgentOutput JSON
  - End-to-end crawl workflow with HierarchicalSummariser integration
  - Performance benchmarks: <20% latency increase vs legacy
  - Regression tests ensure no breaking changes to downstream consumers
  - Production readiness validation
- **Dependencies:** HYBRID-04a-04

---

## 6. Definition of Done (DoD)

### Technical Completion Criteria
- **Outlines Integration:** SearchAgent and CrawlAgent use `outlines.Generator()` for structured output
- **Dual-Path Architecture:** Both agents support structured generation with legacy fallback
- **Schema Validation:** Enhanced ToolAgentOutput produces 98%+ valid JSON
- **Model Integration:** Proper use of `ModelRole.SUMMARISER` (hermes3:8b) 
- **Template System:** Runtime content injection with search provider formatting

### Quality Assurance Criteria  
- **Test Coverage:** 30+ tests across schemas, templates, agents, and integration
- **Performance:** <20% latency increase vs current implementation
- **Backward Compatibility:** Zero breaking changes to existing ToolAgentOutput consumers
- **Error Handling:** Graceful fallback on Outlines import errors or generation failures

### Integration Criteria
- **HierarchicalSummariser:** Works seamlessly with both structured and legacy paths  
- **Search Providers:** Compatible with Serper, SearXNG, and other configured providers
- **ResearchRunner:** Standard agent initialization and execution patterns
- **Downstream Agents:** ToolSelector and other consumers work without modification

### Business Value Criteria
- **Reliability:** Zero `OutputParserError` incidents from search/crawl operations
- **Architecture Consistency:** All core agents (Planner, ToolSelector, KnowledgeGap, Summariser) use Outlines
- **Foundation Ready:** Pipeline prepared for HYBRID-02 ValidationWrapper integration
- **5-Model Complete:** ModelRole.SUMMARISER properly integrated in production workflows

---

**Next Action:** Kick off **HYBRID-04a-01** Discovery & Technical Design to analyze current architecture and plan Outlines integration following proven HYBRID-07 patterns.