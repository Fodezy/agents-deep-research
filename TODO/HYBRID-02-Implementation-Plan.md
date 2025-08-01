# HYBRID-02: Core Infrastructure Implementation Plan

## Implementation Tasks from Feedback

### Immediate Spike Tasks

1. **Create `ValidationWrapper` Prototype** (100 lines max)
   - Hard-coded schema + Pydantic model  
   - Feed three malformed samples from analysis
   - Test auto-repair mechanism with system message prompts
   - Implement pluggable hooks for observability

2. **Instrument Basic Observability Handler**
   - Simple `print` counters first (wire Prometheus later)
   - Track validation failures, repair success/failure
   - Add `repair_roundtrip_ms` histogram placeholder
   - Log `function_ignored` when models don't return function calls

3. **Update `llm_config.py` for Function Support**
   - Add `call_chat()` method accepting optional `functions` parameter
   - Toggle function calling via environment flag
   - Maintain backward compatibility with existing agents
   - Handle both OpenAI and local model clients

4. **Create Test Malformed Samples**
   - Use patterns from HYBRID-01 analysis
   - Include JSON parsing errors and schema violations
   - Test validation wrapper with known failure cases

## Core Infrastructure Components

### ValidationWrapper Class Structure

```python
# Location: deep_researcher/agents/utils/validation_wrapper.py

class ValidationWrapper:
    """Handles function call validation, auto-repair, and fallback mechanisms"""
    
    def __init__(self, function_schema: dict, pydantic_model: BaseModel):
        self.function_schema = function_schema
        self.pydantic_model = pydantic_model
        self.observability = ObservabilityHandler()
        
    async def validate_and_repair(self, 
                                  llm_response: Any,
                                  model_client: Any,
                                  before_retry_hook: Callable = None,
                                  after_retry_hook: Callable = None) -> BaseModel:
        """Main validation workflow with auto-repair and timeout handling"""
        
    def _extract_function_call(self, response: Any) -> dict:
        """Extract function call arguments from LLM response"""
        
    def _validate_with_pydantic(self, arguments: dict) -> tuple[BaseModel, bool]:
        """Validate arguments against Pydantic model, return (result, needs_repair)"""
        
    def _check_schema_version(self, arguments: dict) -> None:
        """Validate schema version compatibility"""
        
    def _categorize_validation_errors(self, validation_error: ValidationError) -> dict:
        """Categorize validation errors by severity (required vs optional fields)"""
        
    async def _attempt_repair(self, 
                             model_client: Any,
                             validation_error: str,
                             original_response: str,
                             timeout_ms: int = 5000) -> Any:
        """Single retry with timeout and enhanced error message"""
        
    def _build_repair_prompt(self, validation_error: str) -> str:
        """Build system message for repair attempt"""
```

### ObservabilityHandler Class

```python
# Location: deep_researcher/agents/utils/observability.py

class ObservabilityHandler:
    """Basic observability for validation and repair metrics"""
    
    def __init__(self):
        self.counters = defaultdict(int)
        self.histograms = defaultdict(list)
        
    def increment(self, metric: str, tags: dict = None):
        """Increment counter with optional tags"""
        
    def record_time(self, metric: str, duration_ms: float, tags: dict = None):
        """Record timing for histogram metrics"""
        
    def log_validation_failure(self, model: str, error_type: str, details: dict, log_level: str = "INFO"):
        """Structured logging with sampling and log level control"""
        
    def should_log_verbose(self) -> bool:
        """Determine if verbose logging should occur based on sampling rate"""
        
    def log_aggregated_metrics(self):
        """Log aggregated metrics at INFO level for production monitoring"""
        
    def get_metrics_summary(self) -> dict:
        """Return current metrics for monitoring"""
```

### LLM Config Updates

```python
# Updates to: deep_researcher/llm_config.py

class LLMConfig:
    def __init__(self, ...):
        # Existing initialization
        self.enable_function_calling = get_env_with_prefix("ENABLE_FUNCTION_CALLING", "false").lower() == "true"
        
    async def call_chat(self, 
                       model: Union[OpenAIChatCompletionsModel, OpenAIResponsesModel],
                       messages: List[dict],
                       functions: Optional[List[dict]] = None,
                       **kwargs) -> Any:
        """Enhanced chat call supporting function calling"""
        
    def supports_function_calling(self, model: Union[OpenAIChatCompletionsModel, OpenAIResponsesModel]) -> bool:
        """Check if model reliably supports function calling"""
```

## Test Malformed Samples

### Sample 1: JSON Parsing Errors
```json
{
  "schema_version": 1,
  "tasks": [
    {
      "gap": "Research quantum theory",
      "agent": "WebSearchAgent",  // ← Trailing comma
      "query": "quantum entanglement basics",
      "entity_website": ""
    }
  }
}
```

### Sample 2: Schema Violations
```json
{
  "schema_version": 1,
  "tasks": [
    {
      "knowledge_gap": "Review quantum theory",  // ← Wrong field name
      "tool": "UnknownAgent",                    // ← Invalid enum value
      "search_query": "This is a very long query that exceeds the maximum length limit for queries",  // ← Too long
      "website_url": "not-a-valid-url",          // ← Invalid format
      "priority": "high"                         // ← Additional property
    }
  ]
}
```

### Sample 3: Missing Required Fields
```json
{
  "schema_version": 1,
  "tasks": [
    {
      "agent": "WebSearchAgent",
      "entity_website": "https://example.com"
      // Missing "gap" and "query" required fields
    }
  ]
}
```

## Environment Configuration

### New Environment Variables

```bash
# Function calling toggle
ENABLE_FUNCTION_CALLING=true

# Repair timeout and back-pressure
REPAIR_TIMEOUT_MS=5000
REPAIR_MAX_RETRIES=1

# Schema versioning
MIN_ACCEPTED_SCHEMA_VERSION=1
MAX_ACCEPTED_SCHEMA_VERSION=1

# Observability settings  
VALIDATION_METRICS_ENABLED=true
VALIDATION_LOG_LEVEL=INFO  # DEBUG for verbose, INFO for aggregated counts
VALIDATION_LOG_SAMPLE_RATE=0.1  # Sample 10% of failures for detailed logging

# Token management for small models
TRIM_CONTEXT_FOR_FUNCTIONS=true
MAX_CONTEXT_WITH_FUNCTIONS=3000
```

## Integration Points

### BaseClass Integration

```python
# Updates to: deep_researcher/agents/baseclass.py

class ResearchAgent(Agent[TContext]):
    def __init__(self, 
                 *args,
                 output_parser: Optional[Callable[[str], Any]] = None,
                 validation_wrapper: Optional[ValidationWrapper] = None,
                 **kwargs):
        self.output_parser = output_parser
        self.validation_wrapper = validation_wrapper
        # Existing initialization
        
    async def parse_output(self, run_result: RunResult) -> RunResult:
        """Enhanced output parsing with validation wrapper"""
        if self.validation_wrapper:
            # Use validation wrapper for function calling
            parsed_output = await self.validation_wrapper.validate_and_repair(
                run_result.final_output,
                self._get_model_client()
            )
        elif self.output_parser:
            # Fallback to existing parser
            parsed_output = self.output_parser(run_result.final_output)
        else:
            return run_result
            
        run_result.final_output = parsed_output
        return run_result
```

## Success Criteria for HYBRID-02

1. **ValidationWrapper** successfully validates good function calls
2. **Auto-repair** fixes at least 2 out of 3 malformed test samples
3. **Observability** tracks all defined metrics with print output
4. **LLM Config** supports function calling parameter
5. **Fallback detection** identifies when models ignore function schemas
6. **Unit tests** cover validation and repair scenarios

## File Structure After Implementation

```
deep_researcher/
├── agents/
│   ├── utils/
│   │   ├── validation_wrapper.py     # New
│   │   ├── observability.py          # New  
│   │   └── parse_output.py            # Existing (unchanged)
│   └── baseclass.py                   # Updated
├── llm_config.py                      # Updated
└── tests/
    ├── test_validation_wrapper.py     # New
    └── test_observability.py          # New
```

## Ready for Implementation

All design decisions are captured and concrete enough for development. The spike approach allows validation of core concepts before full integration.

**Next Step**: Begin ValidationWrapper prototype with malformed sample testing.