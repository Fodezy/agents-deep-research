# HYBRID-08: Model-Role Registry & Tag Checker - Kickoff Plan

## 1. Executive Summary & Core Objective

**Project Name**: Model-Role Registry & Tag Checker (HYBRID-08)

**Core Objective**: Formalize and enforce the validated 4-model architecture (PLANNER/TOOL_CALLING/SUMMARISER/WRITER) through runtime assertions, configuration validation, and role-based model assignment to eliminate tool execution failures and establish a reliable foundation for structured agent outputs.

**Business Impact**: This slice directly addresses the critical pipeline breakdown discovered during HYBRID-05 investigation, where local models like `hermes3:8b` fail at function calling while dedicated models like `Salesforce_Llama-xLAM-2-8b-fc-r-GGUF` succeed. By enforcing proper role-to-model assignments at runtime, we prevent configuration errors that lead to zero tool execution and OutputParserError incidents.

**Success Metrics**:
- Runtime assertions pass for all 4 model roles
- Configuration validation prevents invalid model assignments
- Tool execution success rate increases from current failure state to >95%
- Zero deployment incidents due to model misconfiguration

**Strategic Value**: This becomes the foundational infrastructure enabling all subsequent structured agent work (HYBRID-05, 06, 07, 04a) by ensuring each agent gets a model capable of its specific role requirements.

## 2. Key Questions, Risks, and Assumptions

### Key Questions (To be Answered in Discovery)

**Product/UX Questions:**
- How should researchers be notified when model role mismatches are detected?
- Should the system auto-correct invalid configurations or fail fast with clear error messages?
- What level of model role visibility do researchers need in debug scenarios?
- Should model switching be allowed at runtime or only at configuration time?

**Technical Questions:**
- Will HuggingFace model tag validation work reliably across all target model formats (GGUF, safetensors)?
- Can we implement role assertions without breaking existing async ResearchRunner workflows?
- What's the performance impact of runtime model capability checking on agent startup?
- How do we handle model role validation in Docker environments with limited model access?
- Will the current LLMConfig structure support role-based model selection without major refactoring?

**Configuration Questions:**
- Should role validation happen at config creation time or first model usage?
- How do we handle development environments where not all 4 models are available?
- What's the fallback strategy when a required model role is unavailable?

### Potential Risks

**Technical Risks:**
- HuggingFace API rate limits during model tag validation could slow startup
- Runtime assertions might introduce deadlocks in the current async agent pipeline
- Model capability checking could add significant latency to agent initialization
- Docker networking issues might prevent HuggingFace model metadata access

**Product Risks:**
- Overly strict validation might break existing research workflows that use non-standard model assignments
- Researchers might be confused by new role-based configuration requirements
- Error messages for role validation failures might not provide clear remediation steps

**Operational Risks:**
- New dependencies (HuggingFace Hub) could break CI/Docker builds
- Model tag APIs might be unreliable in production environments
- Configuration migration might require manual updates to existing research setups

### Core Assumptions

- The 4-model architecture (PLANNER/TOOL_CALLING/SUMMARISER/WRITER) is the optimal separation of concerns based on validation testing
- HuggingFace model tags accurately reflect model capabilities for role assignment
- Researchers value reliability over flexibility in model role assignments
- The current LLMConfig structure can be extended without breaking existing integrations
- Runtime validation overhead is acceptable if it prevents pipeline failures

## 3. Proposed MVP (Minimum Viable Product)

### Core Functionality

1. **Model-Role Registry System**
   - Define role specifications with required capabilities
   - Map model identifiers to supported roles based on HuggingFace tags
   - Runtime role validation with clear error reporting

2. **LLMConfig Enhancement**
   - Role-aware model assignment validation
   - Configuration validation at instantiation time
   - Support for 4-model role enforcement (PLANNER/TOOL_CALLING/SUMMARISER/WRITER)

3. **Runtime Assertion Framework**
   - Pre-execution checks that verify model-role compatibility
   - Fail-fast behavior with actionable error messages
   - Integration with existing ResearchRunner workflow

4. **Configuration Validation**
   - Environment variable validation for 4-model setup
   - Development mode support with role requirement relaxation
   - Migration path from current 3-model configuration

5. **HuggingFace Integration**
   - Model metadata fetching and caching
   - Tag-based capability detection
   - Offline/fallback support for air-gapped environments

### Out of Scope (for MVP)

- Dynamic model switching based on workload
- Advanced role optimization or recommendation systems
- UI/dashboard for model role management
- Performance profiling or model benchmarking
- Integration with external model registries beyond HuggingFace
- Automatic model downloading or deployment

## 4. Phased Implementation Plan

### Phase 1: Discovery & Design (3 days)
- Research HuggingFace model tag APIs and reliability
- Design role specification schema and validation rules
- Create technical design document for LLMConfig integration
- Define error handling and messaging strategy

### Phase 2: Core Registry Implementation (5 days)
- Implement ModelRoleRegistry class with tag-based validation
- Create role specification definitions for 4-model architecture
- Add HuggingFace model metadata integration with caching
- Build runtime assertion framework

### Phase 3: LLMConfig Integration (4 days)
- Extend LLMConfig with role-aware model assignment
- Add configuration validation at instantiation
- Implement environment variable validation
- Create migration utilities for 3→4 model configs

### Phase 4: Testing & Integration (3 days)
- Integration testing with existing ResearchRunner
- Validation of error scenarios and edge cases
- Performance testing of role validation overhead
- Documentation and migration guide creation

**Total Duration**: 15 days (3 weeks)

## 5. Initial Backlog (Ticket-Ready Stories)

### Epic: Model-Role Registry & Tag Checker

#### **HYBRID-08.1: Model Role Registry Core**
- **Title**: Implement Model Role Registry with HuggingFace Integration
- **Type**: Story
- **Description**: Create the core ModelRoleRegistry class that defines role specifications and validates model capabilities using HuggingFace model tags. This registry will serve as the foundation for all role-based model validation.
- **Acceptance Criteria**:
  - ModelRoleRegistry class implemented with role specification schema
  - HuggingFace model tag fetching and caching functionality
  - Support for PLANNER, TOOL_CALLING, SUMMARISER, WRITER role definitions
  - Offline/fallback support when HuggingFace API unavailable
  - Unit tests covering role validation logic
- **Dependencies**: None

#### **HYBRID-08.2: Runtime Assertion Framework**
- **Title**: Build Runtime Model-Role Assertion System
- **Type**: Story  
- **Description**: Implement runtime assertions that verify model-role compatibility before agent execution, with fail-fast behavior and actionable error messages.
- **Acceptance Criteria**:
  - Runtime assertion framework integrated with ResearchRunner
  - Clear error messages when model-role mismatches detected
  - Assertions run without breaking existing async workflows
  - Performance impact <100ms additional startup time
  - Integration tests with mock model validation scenarios
- **Dependencies**: HYBRID-08.1

#### **HYBRID-08.3: LLMConfig Role-Aware Enhancement**
- **Title**: Extend LLMConfig with 4-Model Role Validation
- **Type**: Story
- **Description**: Enhance LLMConfig to support role-aware model assignment and validation, ensuring proper 4-model architecture enforcement at configuration time.
- **Acceptance Criteria**:
  - LLMConfig validates role assignments at instantiation
  - Support for 4-model configuration (PLANNER/TOOL_CALLING/SUMMARISER/WRITER)
  - Environment variable validation for model role setup
  - Backward compatibility with existing 3-model configurations
  - Configuration validation error messages provide clear remediation steps
- **Dependencies**: HYBRID-08.1

#### **HYBRID-08.4: Environment Variable Validation**
- **Title**: Implement Configuration Validation for 4-Model Setup
- **Type**: Story
- **Description**: Add comprehensive validation for environment variables and configuration files to ensure proper 4-model setup and prevent runtime failures.
- **Acceptance Criteria**:
  - Environment variable validation for all 4 model roles
  - Development mode support with relaxed requirements
  - Clear validation error messages with setup instructions
  - Migration utilities from 3-model to 4-model configuration
  - CI integration to catch configuration issues early
- **Dependencies**: HYBRID-08.3

#### **HYBRID-08.5: Integration Testing & Documentation**
- **Title**: End-to-End Testing and Migration Documentation
- **Type**: Story
- **Description**: Comprehensive testing of the model-role registry system with existing agents and creation of migration documentation for researchers.
- **Acceptance Criteria**:
  - Integration tests with ToolSelector, Planner, and other structured agents
  - Performance benchmarks showing <5% overhead from role validation
  - Migration guide for transitioning from 3-model to 4-model setup
  - Error troubleshooting documentation
  - All existing agents pass with properly configured 4-model setup
- **Dependencies**: HYBRID-08.4

## 6. Definition of Done (DoD)

### Technical Completion Criteria
- All 4 model roles (PLANNER/TOOL_CALLING/SUMMARISER/WRITER) have defined specifications and validation rules
- Runtime assertions successfully prevent model-role mismatches with <100ms overhead
- LLMConfig properly validates role assignments at instantiation time
- Environment variable validation catches configuration errors before agent execution
- Integration tests pass for all structured agents (ToolSelector, Planner, KnowledgeGap)

### Quality Assurance Criteria
- Unit test coverage >90% for all new model registry functionality
- Integration tests demonstrate successful tool execution with proper model assignments
- Performance tests show role validation adds <5% overhead to agent startup
- Error scenarios handled gracefully with actionable error messages
- Backward compatibility maintained for existing research workflows

### Documentation & Migration Criteria
- Technical documentation explains role specifications and validation logic
- Migration guide provides step-by-step transition from 3-model to 4-model setup
- Troubleshooting guide covers common configuration errors and solutions
- Code documentation includes examples of proper role-based model assignment

### Business Value Validation
- Tool execution success rate improves from current failure state to >95%
- Zero deployment incidents due to model role misconfiguration
- Research engineers can confidently deploy structured agents without pipeline failures
- Foundation established for successful completion of dependent tickets (HYBRID-05, 06, 07, 04a)

### Production Readiness
- Model registry system deployed and operational in development environment
- CI/CD pipeline includes model role validation checks
- Error monitoring and alerting configured for role validation failures
- Research team trained on new 4-model configuration requirements