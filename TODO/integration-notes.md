# Schema Integration Notes

## Integration Points for HYBRID-02+

### 1. Outlines Function Definitions

For each schema, create Outlines function:

```python
import outlines
from schemas.validator import validator

# ToolSelector integration
def create_tool_selector_function(model):
    schema = validator.get_schema("select_tools")
    return outlines.generate.json(model, schema)

# Usage in agent
def init_tool_selector_agent(config: LLMConfig) -> ResearchAgent:
    model = config.reasoning_model
    generate_fn = create_tool_selector_function(model)
    
    return ResearchAgent(
        name="ToolSelectorAgent",
        generate_fn=generate_fn,  # New parameter
        # ... other config
    )
```

### 2. ValidationWrapper Integration

```python
from schemas.validator import validator
from schemas.models import SCHEMA_MODELS

class ValidationWrapper:
    def validate_schema(self, schema_name: str, data: dict) -> Tuple[bool, str, Optional[ValidationError]]:
        return validator.validate(schema_name, data)
    
    def get_expected_version(self, schema_name: str) -> int:
        return validator.get_latest_version(schema_name)
    
    def validate_with_pydantic(self, schema_name: str, data: dict) -> BaseModel:
        """Validate using Pydantic models for more detailed error reporting"""
        if schema_name not in SCHEMA_MODELS:
            raise ValueError(f"No Pydantic model for schema: {schema_name}")
        
        model_class = SCHEMA_MODELS[schema_name]
        return model_class.model_validate(data)
```

### 3. Agent Factory Updates

```python
# Update existing agent factories to use schema validation
def init_planner_agent(config: LLMConfig) -> ResearchAgent:
    if config.use_outlines:
        schema = validator.get_schema("create_plan")
        generate_fn = outlines.generate.json(config.reasoning_model, schema)
        return ResearchAgent(
            name="PlannerAgent",
            generate_fn=generate_fn,
            schema_name="create_plan"  # For validation
        )
    else:
        # Fallback to legacy approach
        return ResearchAgent(
            name="PlannerAgent", 
            instructions=INSTRUCTIONS,
            output_parser=create_type_parser(ReportPlan)
        )
```

## Migration Strategy

1. **HYBRID-02**: Add schema validation to ValidationWrapper
2. **HYBRID-05**: Replace ToolSelector with Outlines + schema
3. **HYBRID-06**: Replace Planner with Outlines + schema  
4. **HYBRID-07**: Replace KnowledgeGap with Outlines + schema
5. **HYBRID-04**: Add chunk_summary schema to HierarchicalSummariser

## Testing Requirements

- Unit tests for each schema with valid/invalid examples
- Integration tests verifying Outlines generates valid schema-compliant JSON
- Regression tests ensuring existing agent APIs unchanged