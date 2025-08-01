# HYBRID-01: Discovery & Technical Design Analysis

## Parsing Failure Analysis

### Current Architecture Issues

1. **Brittle F-String Prompting**: The current system relies on complex prompt instructions with JSON templates embedded in f-strings (lines 45-78 in `tool_selector_agent.py`).

2. **Complex Parser Logic**: The `parse_output.py` contains 168 lines of defensive parsing code that attempts to fix malformed JSON through regex patterns and normalization rules.

3. **Failure Points Identified**:
   - **Stray backticks**: Models add markdown fences around JSON (`````json`)
   - **Trailing commas**: Invalid JSON with extra commas after last elements  
   - **Unquoted values**: Models output unquoted strings in JSON values
   - **Inconsistent key naming**: Models use different field names than expected
   - **Nested structure variations**: Models wrap outputs in unexpected envelope structures

### Common Failure Patterns from Issue Log

**Pattern 1 - Malformed JSON Structure:**
From the provided error in `Issue.md`:
```json
{
  "gap": "Analyze superposition principle",
  "agent": "SiteCrawlerAgent,  // ← Trailing comma
  "query": "quantum mechanics - superposition definition",
  "entity_website": "https://scienceworld.com"" }  // ← Extra quote
```

**Pattern 2 - Schema Violations (Unknown Keys):**
```json
{
  "tasks": [
    {
      "knowledge_gap": "Review quantum theory",  // ← Wrong field name
      "tool": "WebSearchAgent",                  // ← Wrong field name  
      "search_query": "quantum entanglement",    // ← Wrong field name
      "website_url": "",                         // ← Wrong field name
      "priority": "high"                         // ← Additional property
    }
  ]
}
```

**Pattern Analysis**:
- Missing closing quotes on agent field
- Trailing commas in JSON objects  
- Extra quotes at end of values
- Wrong field names (schema validation failures)
- Additional properties not in schema
- Malformed JSON structure breaking parser

## JSON Schema Design for ToolSelector

### Schema with Versioning Stub

```json
{
  "name": "select_tools",
  "description": "Select specialized research agents to address knowledge gaps",
  "parameters": {
    "type": "object",
    "properties": {
      "schema_version": {
        "type": "integer",
        "enum": [1],
        "description": "Schema version for future compatibility"
      },
      "tasks": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "gap": {
              "type": "string",
              "description": "The knowledge gap being addressed"
            },
            "agent": {
              "type": "string",
              "enum": ["WebSearchAgent", "SiteCrawlerAgent"],
              "description": "The name of the agent to use"
            },
            "query": {
              "type": "string",
              "maxLength": 50,
              "description": "3-6 word query for the agent"
            },
            "entity_website": {
              "type": "string",
              "format": "uri",
              "description": "Optional website URL if researching specific entity"
            }
          },
          "required": ["gap", "agent", "query"],
          "additionalProperties": false
        },
        "maxItems": 3,
        "minItems": 1
      }
    },
    "required": ["schema_version", "tasks"],
    "additionalProperties": false
  }
}
```

### Key Schema Features

1. **Schema Versioning**: `schema_version: 1` for future migration support
2. **Enum Constraints**: Agent field limited to valid agent names
3. **Validation Rules**: Query length limits, URL format validation
4. **Required Fields**: Enforces mandatory fields at schema level
5. **Additional Properties**: Disabled to prevent unexpected fields

## Validation Wrapper Architecture

### Core Components

1. **Function Call Detection**: Check if model response contains `function_call`
2. **Schema Validation**: Use Pydantic to validate against expected schema
3. **Auto-Repair Logic**: Single retry with enhanced error message
4. **Fallback Mechanism**: Few-shot format guard for non-function-calling models
5. **Observability Hooks**: Counters for failures and repair success

### Validation Wrapper Design

```python
class ValidationWrapper:
    def __init__(self, 
                 function_schema: dict,
                 pydantic_model: BaseModel,
                 observability_handler: ObservabilityHandler):
        self.function_schema = function_schema
        self.pydantic_model = pydantic_model  
        self.observability = observability_handler
        
    async def validate_and_repair(self, 
                                  llm_response: Any, 
                                  model_client: Any,
                                  before_retry_hook: Callable = None,
                                  after_retry_hook: Callable = None) -> BaseModel:
        # 1. Extract function call arguments
        # 2. Validate with Pydantic
        # 3. On failure, call before_retry_hook(err, raw_json)
        # 4. Attempt single auto-repair with system message
        # 5. Call after_retry_hook(success) 
        # 6. Track metrics
        # 7. Return validated object or raise
        
        # TODO: Add pluggable observability hooks for custom metrics
```

### Auto-Repair Strategy with Failure Logging

**Single Retry Approach**:
1. **Capture Initial Failure**: Log exact validation error and raw output
2. **Generate Repair Prompt** (sent as system message): 
   ```
   Your last function call had validation errors: {specific_errors}
   Please provide only a corrected function call matching the schema.
   ```
   *Note: Repair prompt sent as system message to override conversation drift*
3. **Re-validate**: Apply same validation to retry response
4. **Log Outcomes**: Track repair success/failure with detailed context

**Failure Reason Categorization**:
- `malformed_json`: JSON parsing errors
- `missing_required_fields`: Required fields absent  
- `invalid_enum_values`: Agent name not in allowed list
- `type_mismatch`: Wrong data types for fields
- `schema_violation`: Additional properties or constraint violations

## Fallback Strategy for Local Models

### Problem: Function Calling Support Varies
Many local models don't reliably support OpenAI function calling format.

### Solution: Hybrid Detection + Fallback

1. **Function Support Detection**:
   ```python
   async def supports_function_calling(model_client) -> bool:
       # Test with simple function call
       # Return True if response contains function_call structure
   ```

2. **Few-Shot Format Guard**:
   When function calling fails, inject few-shot examples:
   ```python
   few_shot_examples = [
       {
           "role": "assistant", 
           "content": '{"name": "select_tools", "arguments": {"schema_version": 1, "tasks": [...]}}'
       }
   ]
   ```

3. **Graceful Degradation**:
   - Try function calling first
   - On failure, fall back to few-shot + current parser
   - Track which approach succeeded for model profiling
   - Track `function_ignored` counter when schema not returned

## Observability Infrastructure Design

### Metrics to Track

1. **Validation Counters**:
   - `validation_failed`: Failed initial validation attempts
   - `repair_success`: Successful auto-repair attempts  
   - `repair_failed`: Failed repair attempts requiring fallback
   - `repair_timeout`: Repair attempts that exceeded timeout
   - `repair_skipped`: Repairs skipped due to non-required field failures only
   - `function_calling_supported`: Models supporting function calls
   - `fallback_used`: Times fallback mechanism activated
   - `schema_version_rejected`: Requests with unsupported schema versions

2. **Performance Metrics**:
   - `validation_latency_ms`: Time spent on validation
   - `repair_latency_ms`: Additional time for repair attempts
   - `repair_roundtrip_ms`: Histogram for model round-trip including repair
   - `total_processing_time_ms`: End-to-end processing time

3. **Error Classification**:
   - Track failure reasons by category
   - Model-specific success rates
   - Schema version compatibility issues

### Implementation Approach

```python
class ObservabilityHandler:
    def __init__(self):
        self.counters = defaultdict(int)
        self.timers = {}
        
    def increment(self, metric: str, tags: dict = None):
        # Increment counter with optional tags
        
    def time_operation(self, operation: str):
        # Context manager for timing operations
        
    def log_validation_failure(self, 
                             model: str, 
                             error_type: str, 
                             raw_output: str,
                             validation_error: str):
        # Structured logging for debugging
```

## Migration Risk Assessment

### Technical Risks & Mitigations

1. **Local Model Function Support**: 
   - **Risk**: Models ignore function schemas
   - **Mitigation**: Fallback to enhanced few-shot prompting

2. **Performance Overhead**:
   - **Risk**: Validation adds latency
   - **Mitigation**: Async validation, caching, performance monitoring

3. **Schema Evolution**:
   - **Risk**: Breaking changes to function schemas
   - **Mitigation**: Schema versioning from day one

4. **Token Window Constraints**:
   - **Risk**: JSON schemas add tokens up front; tiny models with 4K context may choke for long queries
   - **Mitigation**: Trim background context when `functions` in use

### Implementation Dependencies

- Requires `agents` library support for function calling
- Pydantic for schema validation  
- Observability framework (basic counters + logging)
- Model client abstraction supporting both function calls and chat completion

## Next Steps

1. **Prototype validation wrapper** (100 lines max)
2. **Test with malformed samples** from current error logs
3. **Benchmark latency impact** on local models
4. **Design review** before Phase 2 implementation

---

**Status**: Analysis complete, ready for infrastructure development phase.