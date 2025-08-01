# Hybrid Prompt System Overhaul Plan

## Role
You are a seasoned Product Manager and Lead Engineer, working in tandem. Your expertise lies in translating business goals and user needs into a practical, actionable engineering plan for migrating from brittle prompt-based systems to robust hybrid approaches.

## Objective
To create a comprehensive kickoff plan for overhauling the agents-deep-research pipeline from a prompt-only approach to a hybrid system (function-schema + auto-repair + few-shot) that eliminates parsing errors and improves reliability with local models.

---

## 1. Executive Summary & Core Objective

The agents-deep-research project currently suffers from brittle f-string based prompting that leads to frequent OutputParserError failures when using local models. The system needs migration to a hybrid approach combining OpenAI function calling with JSON Schema, programmatic validation with auto-repair mechanisms, and few-shot examples for edge cases. This will eliminate 90% of parsing errors while maintaining compatibility with smaller local models and improving overall system reliability.

## 2. Key Questions, Risks, and Assumptions

### Key Questions (To be Answered in Discovery)
- **Technical**: Does the current LLM provider wrapper support OpenAI function calling format?
- **Technical**: Which agents currently have the highest parsing failure rates and what are the common failure patterns?
- **Product/UX**: How will the migration affect response latency and token usage?
- **Technical**: Can we maintain backward compatibility during the migration?
- **Technical**: How reliably do our local models support function calling vs. fallback approaches?
- **Technical**: What observability do we need to track model drift and repair effectiveness?

### Potential Risks
- **Technical**: Local models may not support function calling as reliably as OpenAI models.
- **Technical**: JSON Schema validation overhead might impact performance.
- **Product**: Auto-repair mechanisms could mask underlying prompt quality issues.
- **Technical**: Migration could introduce new failure modes during transition period.
- **Technical**: Single retry strategy may be insufficient for persistent formatting issues.
- **Operational**: Without proper observability, we may not detect model drift affecting success rates.

### Core Assumptions
- Current OutputParserError issues are primarily due to malformed JSON rather than logical errors.
- The existing agent architecture can accommodate function calling without major restructuring.
- Local models will respond better to structured schemas than prose instructions.
- The performance overhead of validation and auto-repair is acceptable.

## 3. Proposed MVP (Minimum Viable Product)

### Core Functionality
- Convert ToolSelector agent to use JSON Schema function calling with schema versioning stub
- Implement central validation wrapper with single retry auto-repair and failure logging
- Add few-shot examples for the converted agent
- Maintain existing agent interfaces for seamless integration
- Basic observability (counters for validation failures, repair success rates)
- Fallback mechanism for local models that don't support function calling

### Out of Scope
- Migration of all agents (only ToolSelector for MVP)
- Advanced retry strategies (only single retry)
- Performance optimization beyond basic benchmarking
- Comprehensive metrics dashboard
- Full schema versioning system (only stub implementation)

## 4. Phased Implementation Plan

### Phase 1: Discovery & Design
- Analyze current parsing failure patterns
- Design JSON Schema structure for ToolSelector
- Create validation wrapper architecture
- Define few-shot example format

### Phase 2: Core Infrastructure Development
- Implement validation wrapper in baseclass.py
- Create JSON Schema definitions
- Build auto-repair mechanism
- Add error logging infrastructure

### Phase 3: Agent Migration (MVP)
- Convert ToolSelector agent to function calling
- Add few-shot examples
- Update LLM config for function support
- Integration testing

### Phase 4: Validation & Rollout
- Unit tests for validation and auto-repair
- End-to-end testing with problematic queries
- Performance benchmarking
- Documentation and deployment

## 5. Initial Backlog (Ticket-Ready Stories)

### Epic: Hybrid Prompt System Overhaul

#### HYBRID-01: Discovery & Technical Design
**Type**: Story  
**Description**: Analyze current parsing failures, design JSON Schema structure, and create technical architecture for validation wrapper and auto-repair mechanism.

**Acceptance Criteria**:
- Parsing failure analysis document with top 50 recent OutputParserError patterns and frequency data
- JSON Schema design for ToolSelector agent output with schema versioning stub ("schema_version": 1)
- Technical design document for validation wrapper architecture with observability hooks
- Auto-repair strategy and retry logic specification with failure reason logging
- Fallback strategy design for local models that don't support function calling

**Dependencies**: None

#### HYBRID-02: Implement Core Validation Infrastructure
**Type**: Story  
**Description**: Create validation wrapper, auto-repair mechanism, and error logging infrastructure in the base agent class.

**Acceptance Criteria**:
- Validation wrapper integrated into baseclass.py or new utils module
- Auto-repair with single retry attempt implemented with detailed failure reason logging
- Observability infrastructure (counters for validation_failed, repair_success) integrated
- Fallback mechanism for models that ignore function calling (few-shot format guard)
- Unit tests for validation, repair logic, and fallback scenarios

**Dependencies**: HYBRID-01

#### HYBRID-03: Convert ToolSelector to Function Calling
**Type**: Story  
**Description**: Migrate ToolSelector agent from f-string prompts to JSON Schema function calling with few-shot examples.

**Acceptance Criteria**:
- ToolSelector uses JSON Schema function definition instead of prompt templates
- Few-shot examples added for edge cases
- System prompt simplified to focus on role rather than format
- Existing agent interface maintained for backward compatibility

**Dependencies**: HYBRID-02

#### HYBRID-04: Update LLM Configuration and Integration
**Type**: Story  
**Description**: Modify llm_config.py to support function calling and integrate with existing agent workflow.

**Acceptance Criteria**:
- LLM config supports passing functions parameter to chat completion
- Function calling integrated into ResearchRunner.run() workflow with fallback detection
- Maintains compatibility with existing non-function-calling agents
- Configuration tested with local models used in the project (with latency benchmarks)
- Observability hooks integrated into LLM config for tracking function calling success rates

**Dependencies**: HYBRID-03

#### HYBRID-05: End-to-End Testing and Validation
**Type**: Story  
**Description**: Comprehensive testing of the hybrid system with the problematic query that caused the original parsing error.

**Acceptance Criteria**:
- End-to-end test with quantum computing query runs without OutputParserError
- Performance benchmarks show acceptable latency increase
- Auto-repair metrics collected and analyzed
- Integration tests pass for ToolSelector in full pipeline

**Dependencies**: HYBRID-04

#### HYBRID-06: Documentation and Migration Guide
**Type**: Story  
**Description**: Create documentation for the hybrid approach and migration guide for remaining agents.

**Acceptance Criteria**:
- Technical documentation for validation wrapper and function calling approach
- Migration guide template for converting additional agents (including schema design best practices)
- Troubleshooting guide for common function calling issues and fallback scenarios
- Performance and reliability metrics documentation
- Team training material: "How to write function schemas & few-shot examples" guide

**Dependencies**: HYBRID-05

## 6. Definition of Done (DoD)

- ToolSelector agent successfully uses function calling with JSON Schema validation (including schema versioning)
- Auto-repair mechanism handles validation failures with single retry attempt and detailed logging
- Fallback mechanism works for local models that don't support function calling
- The problematic quantum computing query completes without OutputParserError
- Performance impact is within acceptable limits (< 20% latency increase)
- Unit and integration tests pass with >95% success rate
- Observability infrastructure tracks validation failures and repair success rates
- Migration guide and team training materials are ready for converting remaining agents
- System is deployed and monitored in production with acceptable performance

## 7. Next Concrete Steps (Pre-Implementation)

### Immediate Actions
1. **Catalog recent failures**: Analyze top 50 recent `OutputParserError` logs to identify explicit JSON failure patterns
2. **Draft `select_tools` schema**: Include enum constraints for `agent` field and schema versioning stub
3. **Spike validation wrapper**: Create 100-line prototype with auto-repair loop tested against malformed samples
4. **Latency benchmark**: Time-box test of local model function calling performance and context window requirements
5. **Schedule design review**: Plan review session before Phase 2 to align infrastructure with schema decisions

### Risk Mitigation Spikes
- Test function calling reliability across all local models in use
- Prototype observability hooks for tracking model drift
- Design fallback strategy for models that ignore function calling
- Validate schema versioning approach for future migrations