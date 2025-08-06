# HYBRID-04a-01: Discovery & Technical Design

**Date:** August 6, 2025  
**Ticket:** HYBRID-04a-01 - Discovery & Technical Design  
**Epic:** HYBRID-04a - Outlines-based Summariser  
**Status:** COMPLETED  

---

## Executive Summary

Analysis of current SearchAgent and CrawlAgent architecture reveals legacy parsing patterns inconsistent with proven HYBRID-05/06/07 Outlines implementations. Both agents require refactoring to dual-path architecture with Outlines structured generation while maintaining backward compatibility.

**Key Finding:** Model selection inconsistency between agents - SearchAgent uses `ModelRole.SUMMARISER`, CrawlAgent uses `config.fast_model`.

---

## Current Architecture Analysis

### SearchAgent (search_agent.py:38-67)

**✅ Strengths:**
- Uses `ModelRole.SUMMARISER` from line 41 (consistent with 5-model architecture)
- Proper model selection via `config.get_model_for_role(ModelRole.SUMMARISER)`
- HierarchicalSummariser integration with correct model assignment
- Legacy dual-path pattern with `model_supports_structured_output()` check

**❌ Issues:**
- No Outlines integration - uses legacy `create_type_parser()` approach
- Basic `ToolAgentOutput` schema without enhanced validation
- Legacy instruction templates without dynamic content injection

**Current Pattern:**
```python
output_type=ToolAgentOutput if model_supports_structured_output(selected_model) else None,
output_parser=create_type_parser(ToolAgentOutput) if not model_supports_structured_output(selected_model) else None
```

### CrawlAgent (crawl_agent.py:41-74)

**✅ Strengths:**
- HierarchicalSummariser integration for large content processing
- Proper function tool decoration pattern
- Same legacy dual-path structure as SearchAgent

**❌ Issues:**
- **Model Inconsistency:** Uses `config.fast_model` (line 42) instead of `ModelRole.SUMMARISER`
- No Outlines integration
- Same legacy parsing limitations as SearchAgent

**Current Pattern:**
```python
selected_model = config.fast_model  # Should be ModelRole.SUMMARISER
```

### ToolAgentOutput Schema (__init__.py:3-6)

**Current Implementation:**
```python
class ToolAgentOutput(BaseModel):
    """Standard output for all tool agents"""
    output: str
    sources: list[str] = Field(default_factory=list)
```

**Analysis:**
- Basic schema without validation constraints
- No metadata fields for observability
- Missing field descriptions for Outlines generation
- No backward compatibility aliases

---

## Technical Design Recommendations

### 1. Dual-Path Architecture (Following HYBRID-07 Pattern)

**Structured Path with Outlines:**
```python
from deep_researcher.agents.utils.outlines_schemas import EnhancedToolAgentOutput
from deep_researcher.agents.utils.outlines_templates import render_search_summary_prompt
import outlines

# In agent initialization
if model_supports_structured_output(selected_model):
    schema = EnhancedToolAgentOutput.model_json_schema()
    generator = outlines.Generator(model, schema)
    
    # In execution
    prompt = render_search_summary_prompt(task_params, search_results)
    response = generator.generate(prompt)
else:
    # Legacy fallback path
    response = await agent.generate(legacy_prompt)
    parsed_response = legacy_parser.parse(response)
```

**Graceful Fallback:**
- Import error handling for Outlines dependency
- Model compatibility checking via `model_supports_structured_output()`
- Legacy parsing preservation for non-compatible models

### 2. Enhanced ToolAgentOutput Schema

**Location:** `deep_researcher/agents/utils/outlines_schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EnhancedToolAgentOutput(BaseModel):
    """Enhanced tool agent output with validation and metadata"""
    
    output: str = Field(
        description="Comprehensive summary addressing the knowledge gap",
        min_length=50,
        max_length=2000
    )
    
    sources: list[str] = Field(
        default_factory=list,
        description="Source URLs referenced in the summary",
        max_items=20
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
        description="Processing time in milliseconds"
    )

# Backward compatibility alias
ToolAgentOutput = EnhancedToolAgentOutput
```

### 3. Template System Design

**Location:** `deep_researcher/agents/utils/outlines_templates.py`

**Core Functions:**
```python
def render_search_summary_prompt(
    task_params: Union[dict, str, "ResearchRunner"],
    search_results: dict,
    current_date: str = None
) -> str:
    """Render structured search summary prompt"""
    
def render_crawl_summary_prompt(
    task_params: Union[dict, str, "ResearchRunner"], 
    crawled_content: dict,
    current_date: str = None
) -> str:
    """Render structured crawl summary prompt"""
    
def extract_summariser_params(task_input) -> dict:
    """Extract parameters from AgentTask/ResearchRunner/string input"""
```

**Template Features:**
- Runtime date injection following HYBRID-07 patterns
- Dynamic content formatting based on search provider results
- Parameter extraction from multiple input formats
- Search provider agnostic result formatting

### 4. Model Role Standardization

**Issue:** CrawlAgent uses `config.fast_model` vs SearchAgent's `ModelRole.SUMMARISER`

**Solution:**
```python
# Both agents should use:
from ..utils.model_role_registry import ModelRole
selected_model = config.get_model_for_role(ModelRole.SUMMARISER)
```

**Benefits:**
- Consistent model selection across tool agents
- Proper 5-model architecture compliance
- Centralized model role management

---

## Integration Points

### HierarchicalSummariser Compatibility

**Current Integration (search_agent.py:51-56):**
```python
summariser = HierarchicalSummariser(
    fast_model=config.fast_model,
    slow_model=config.main_model,
    chunk_size=800,
    overlap=100
)
```

**Analysis:** Works seamlessly with both structured and legacy paths. No changes required.

### ValidationWrapper Readiness (HYBRID-02)

**Available Infrastructure:**
- `validation_wrapper.py:8-137` - Complete validation/repair system
- `observability.py:6-50` - Metrics collection for validation events
- Schema validation with automatic retry on failure

**Integration Pattern:**
```python
wrapper = ValidationWrapper(
    schema_name="ToolAgentOutput",
    agent_name="SearchAgent", 
    call_with_functions=model.call_with_functions
)
validated_output = await wrapper.validate_and_repair(llm_response, model_client)
```

---

## Performance Impact Analysis

### Expected Latency Impact

**Structured Generation:**
- Template rendering: <1ms overhead
- Outlines generation: +15-25% vs legacy parsing
- Schema validation: <5ms overhead

**Mitigation Strategies:**
- Efficient template caching
- Optimized schema definitions
- Parallel processing where possible

### Memory Usage

**Additional Requirements:**
- Outlines model compilation: ~50MB per model
- Template cache: ~1MB for all templates
- Schema objects: Negligible overhead

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|---------|------------|
| hermes3:8b doesn't support Outlines | Medium | High | Dual-path with legacy fallback |
| Performance degradation >30% | Low | Medium | Benchmarking and optimization |
| Breaking changes to consumers | Low | High | Backward compatibility via aliases |
| HierarchicalSummariser conflicts | Very Low | Medium | Template design for chunked content |

---

## Implementation Approach

### Phase 1: Schema & Template Foundation
1. Create `outlines_schemas.py` with enhanced ToolAgentOutput
2. Implement template system in `outlines_templates.py`
3. Add backward compatibility aliases
4. Comprehensive schema validation tests

### Phase 2: SearchAgent Refactor
1. Model role standardization to `ModelRole.SUMMARISER`
2. Dual-path implementation with Outlines integration
3. Template-based prompt generation
4. Extensive testing (15+ test cases)

### Phase 3: CrawlAgent Refactor  
1. Follow proven SearchAgent patterns
2. Crawl-specific template optimization
3. HierarchicalSummariser integration validation
4. Performance benchmarking

---

## Acceptance Criteria Validation

**✅ Technical design document covers dual-path architecture**
- Structured path with Outlines generator
- Legacy fallback for non-compatible models
- Graceful error handling

**✅ ToolAgentOutput schema enhancement plan with backward compatibility**
- Enhanced schema with validation constraints
- Optional metadata fields for observability
- Backward compatibility via type aliases

**✅ Template system design for search provider result formatting**
- Provider-agnostic result formatting
- Runtime parameter extraction
- Dynamic content injection patterns

**✅ Performance impact analysis and optimization recommendations** 
- Expected 15-25% latency increase
- Memory usage projections
- Mitigation strategies identified

---

**Status:** COMPLETED ✅  
**Next Action:** Proceed to HYBRID-04a-02 Enhanced Schema & Template System implementation