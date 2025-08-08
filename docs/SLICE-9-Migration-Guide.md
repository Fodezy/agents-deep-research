# SLICE-9 Migration Guide: Structured Agents & Production Optimization

## Overview

This guide provides a comprehensive upgrade path from the legacy agent system to the new SLICE-9 structured agents architecture. The migration introduces production-ready guardrails, structured JSON outputs, and enhanced validation while maintaining backward compatibility.

## What's New in SLICE-9

### Core Improvements
- **Structured JSON Outputs**: All agents now produce validated JSON instead of raw text
- **ValidationWrapper Integration**: Auto-repair mechanisms for malformed outputs
- **Production Guardrails**: Length enforcement, quality controls, and performance optimization
- **Enhanced Error Handling**: Graceful fallbacks and comprehensive error recovery
- **Performance Monitoring**: Detailed metrics and observability

### Affected Components
1. **StructuredHierarchicalSummariser** (SLICE-9-01)
2. **KnowledgeGapAgent** (SLICE-9-02)  
3. **ProductionWriterAgent** (SLICE-9-03)

---

## Migration Steps

### Step 1: Update Dependencies

Ensure you have the required dependencies:

```bash
pip install outlines pydantic>=2.0
```

### Step 2: Migrate Structured Summarization

#### Before (Legacy)
```python
from deep_researcher.agents.utils.hierarchical_summariser import HierarchicalSummariser

# Legacy initialization
summariser = HierarchicalSummariser(fast_model, slow_model)
result = await summariser.summarise_large_content(content, context)

# Result was a dict with nested structure
final_summary = result["final_summary"]  # Raw text
```

#### After (SLICE-9-01)
```python
from deep_researcher.agents.utils.structured_summariser import StructuredHierarchicalSummariser

# New structured initialization
summariser = StructuredHierarchicalSummariser(fast_model, slow_model)
result = await summariser.summarise_large_content(content, context, sources)

# Result is structured JSON with validation
print(result["output"])                    # Structured summary text
print(result["key_findings"])              # List of key findings
print(result["confidence"])                # Quality confidence score
print(result["sources"])                   # Source URLs
print(result["processing_metadata"])       # Performance metrics
```

#### Migration Benefits
- **Structured Output**: Consistent JSON format with key findings extraction
- **Source Tracking**: Automatic URL reference management
- **Quality Scoring**: Confidence assessment for content reliability
- **Performance Metrics**: Built-in timing and processing metadata

### Step 3: Migrate Knowledge Gap Analysis

#### Before (Legacy)
```python
from deep_researcher.agents.knowledge_gap_agent import init_knowledge_gap_agent

agent = init_knowledge_gap_agent(config)
result = await ResearchRunner.run(agent, query)

# Raw text output requiring manual parsing
gaps = parse_gaps_manually(result.final_output)
```

#### After (SLICE-9-02)
```python
from deep_researcher.agents.knowledge_gap_agent import init_knowledge_gap_agent
from deep_researcher.agents.utils.outlines_schemas import KnowledgeGapResult

# Enhanced agent with validation
agent = init_knowledge_gap_agent(config)

# Input can be dict or string
structured_input = {
    "research_context": "quantum computing applications",
    "background_context": "recent developments in quantum algorithms", 
    "findings_history": "found IBM quantum research papers"
}

result = agent.output_parser(json.dumps(structured_input))

# Structured output with full validation
assert isinstance(result, KnowledgeGapResult)
print(f"Research complete: {result.research_complete}")
print(f"Confidence: {result.research_completeness_confidence}")

for gap in result.gaps_identified:
    print(f"Gap: {gap.description}")
    print(f"Priority: {gap.priority}") 
    print(f"Approach: {gap.research_approach}")
```

#### Migration Benefits
- **ValidationWrapper Integration**: Auto-repair for malformed JSON
- **Enhanced Schema**: Rich gap metadata with priority and confidence
- **Error Recovery**: Multiple fallback levels prevent failures
- **<2% Retry Rate**: Reliable parsing with graceful error handling

### Step 4: Migrate Report Writing

#### Before (Legacy)
```python
from deep_researcher.agents.long_writer_agent import init_long_writer_agent, write_next_section

writer = init_long_writer_agent(config)
result = await write_next_section(writer, query, draft, title, section)

# Raw markdown output
markdown = result  # String, no validation or metrics
```

#### After (SLICE-9-03)
```python
from deep_researcher.agents.long_writer_agent import (
    init_production_writer_agent, WriterConfig, WriterOutput
)

# Configure production guardrails
writer_config = WriterConfig(
    max_tokens=4000,
    min_tokens=200,
    quality_threshold=0.8,
    enable_length_enforcement=True,
    enable_quality_controls=True
)

writer = init_production_writer_agent(config, writer_config)
result = await writer.write_section_with_guardrails(
    original_query=query,
    report_draft=draft, 
    next_section_title=title,
    next_section_draft=section
)

# Structured output with quality metrics
assert isinstance(result, WriterOutput)
print(f"Content: {result.content}")                    # Validated markdown
print(f"Word count: {result.word_count}")              # Automatic counting
print(f"Estimated tokens: {result.estimated_tokens}") # Token estimation
print(f"Quality score: {result.quality_score}")       # Content quality
print(f"References: {result.references}")             # Extracted references
print(f"Processing time: {result.processing_metadata['processing_time_ms']}ms")
```

#### Migration Benefits
- **Length Enforcement**: Prevents token limit overruns
- **Quality Controls**: Maintains readability and coherence  
- **Automatic Metrics**: Word counts, token estimates, quality scores
- **Reference Extraction**: Automatic citation and reference handling
- **Performance Optimization**: Built-in timing and optimization

---

## Configuration Updates

### LLMConfig Enhancements

The 4-model architecture now supports dedicated model roles:

```python
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.utils.model_role_registry import ModelRole

config = LLMConfig(
    search_provider="serper",
    # Dedicated model roles for structured agents
    planner_model_provider="openai",
    planner_model="gpt-4",
    tool_calling_model_provider="openai", 
    tool_calling_model="gpt-4",
    summariser_model_provider="openai",
    summariser_model="gpt-4",
    writer_model_provider="openai",
    writer_model="gpt-4",
    knowledge_gap_model_provider="openai",
    knowledge_gap_model="gpt-4"
)

# Agents automatically select appropriate model roles
```

### ValidationWrapper Configuration

```python
from deep_researcher.agents.utils.validation_config import ValidationConfig

# Configure validation behavior
validation_config = ValidationConfig(
    enabled=True,
    max_retries=3,
    timeout_ms=30000
)

# Used automatically by all structured agents
```

---

## Troubleshooting Common Issues

### Issue 1: "No module named 'outlines'"

**Problem**: Missing Outlines dependency
**Solution**: Install the required package
```bash
pip install outlines
```

### Issue 2: "ValidationError" on Pydantic schemas

**Problem**: Data doesn't meet schema validation requirements
**Solution**: Check field constraints in the schema:
```python
# For WriterOutput, content must be ≥100 characters
# For KnowledgeGapResult, analysis_summary must be ≥50 characters
# For StructuredSummary, each key_finding must be ≥10 characters
```

### Issue 3: Performance degradation

**Problem**: Structured validation adds processing time
**Solution**: Monitor performance metrics and adjust configuration:
```python
writer_config = WriterConfig(
    max_tokens=2000,  # Reduce for faster processing
    enable_quality_controls=False,  # Disable for speed
    performance_optimization=True   # Enable optimizations
)
```

### Issue 4: "OutputParserError" still occurring

**Problem**: ValidationWrapper not handling specific error case
**Solution**: Check error logs and add custom error handling:
```python
# ValidationWrapper provides multiple fallback levels
# Ultimate fallback always creates valid output structure
# Check processing_metadata for error details
```

---

## Testing Your Migration

### Basic Functionality Test

```python
import asyncio
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.knowledge_gap_agent import init_knowledge_gap_agent

async def test_migration():
    config = LLMConfig(search_provider="serper", reasoning_model="gpt-4")
    
    # Test structured agent
    agent = init_knowledge_gap_agent(config)
    test_input = json.dumps({
        "schema_version": 1,
        "research_complete": False,
        "research_completeness_confidence": 0.8,
        "research_context": "Testing migration functionality",
        "gaps_identified": [],
        "analysis_summary": "Migration test successfully validates structured output functionality",
        "total_gaps": 0
    })
    
    result = agent.output_parser(test_input)
    print(f"Migration test: {'PASS' if result.schema_version == 1 else 'FAIL'}")

# Run test
asyncio.run(test_migration())
```

### Performance Benchmark

```python
# Run the comprehensive test suite
python tests/test_slice9_end_to_end_regression.py

# Expected results:
# - All regression tests pass
# - Quantum entanglement query completes successfully  
# - Performance targets met (≤+20% latency increase)
# - Zero OutputParserError incidents
```

---

## Rollback Procedure

If you need to revert to the legacy system:

### 1. Disable Structured Features

```python
# Use legacy initialization functions
from deep_researcher.agents.long_writer_agent import init_long_writer_agent  # Legacy

# Avoid new structured functions
# from deep_researcher.agents.long_writer_agent import init_production_writer_agent  # SLICE-9
```

### 2. Update Code References

Replace structured output handling with legacy text parsing:

```python
# Change from:
result = await structured_summarizer.summarise_large_content(content)
summary = result["output"]

# Back to:
result = await legacy_summarizer.summarise_large_content(content) 
summary = result["final_summary"]
```

### 3. Remove Dependencies

```bash
pip uninstall outlines  # If not needed for other features
```

---

## Performance Optimization Tips

### 1. Model Role Assignment
- Use faster models for non-critical roles
- Reserve GPT-4 for complex reasoning tasks

### 2. Token Limits  
- Set appropriate max_tokens for your use case
- Use chunk_size optimization for large documents

### 3. Validation Configuration
- Reduce max_retries for faster processing
- Disable quality_controls for speed-critical paths

### 4. Caching Strategy
- Consider implementing response caching
- Use performance_optimization=True in WriterConfig

---

## Support and Resources

### Documentation
- **Schemas**: `deep_researcher/agents/utils/outlines_schemas.py`
- **Templates**: `deep_researcher/agents/utils/outlines_templates.py`  
- **Validation**: `deep_researcher/agents/utils/validation_wrapper.py`

### Test Examples
- **Unit Tests**: `tests/test_*_enhanced.py`
- **Integration Tests**: `tests/test_slice9_end_to_end_regression.py`
- **Performance Tests**: Individual agent test suites

### Migration Checklist

- [ ] Install required dependencies (outlines, pydantic>=2.0)
- [ ] Update StructuredHierarchicalSummariser usage
- [ ] Migrate KnowledgeGapAgent to structured output
- [ ] Update WriterAgent to ProductionWriterAgent  
- [ ] Configure ValidationWrapper settings
- [ ] Test with sample queries
- [ ] Run performance benchmarks
- [ ] Update error handling code
- [ ] Verify OutputParserError elimination
- [ ] Deploy and monitor

---

**Migration Complete**: Your system now benefits from structured outputs, enhanced validation, and production-ready guardrails while maintaining the reliability and performance of the original system.