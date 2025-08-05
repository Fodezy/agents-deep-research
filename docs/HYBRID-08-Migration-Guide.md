# HYBRID-08: 4-Model Architecture Migration Guide

## Overview

This guide walks you through migrating from the legacy 3-model configuration to the new validated 4-model architecture that ensures reliable function calling and structured agent outputs.

## Why Migrate?

The 4-model architecture fixes critical issues discovered in HYBRID-05:
- **Tool Execution Failures**: Models like `hermes3:8b` don't support function calling
- **OutputParserError Incidents**: Wrong models for specific roles cause parsing failures  
- **Unreliable Structured Output**: Mixed-purpose models produce inconsistent results

## 4-Model Role Architecture

| Role | Purpose | Model Requirements | Recommended Model |
|------|---------|-------------------|------------------|
| **PLANNER** | Planning and strategy | Reasoning, analysis | `hermes3:8b` |
| **TOOL_CALLING** | Function calling | Function calling capability | `hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M` |
| **SUMMARISER** | Content summarization | Text processing, context | `qwen2.5-coder:latest` |
| **WRITER** | Final report writing | Text generation, formatting | `llama3.2:latest` |

## Migration Steps

### Step 1: Update Environment Variables

**Legacy 3-Model Configuration:**
```bash
# OLD - Remove these
REASONING_MODEL_PROVIDER=local
REASONING_MODEL=hermes3:8b
MAIN_MODEL_PROVIDER=local  
MAIN_MODEL=qwen2.5-coder:latest
FAST_MODEL_PROVIDER=local
FAST_MODEL=llama3.2:latest
```

**New 4-Model Configuration:**
```bash
# NEW - Add these
PLANNER_MODEL_PROVIDER=local
PLANNER_MODEL=hermes3:8b

TOOL_CALLING_MODEL_PROVIDER=local
TOOL_CALLING_MODEL=hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M

SUMMARISER_MODEL_PROVIDER=local
SUMMARISER_MODEL=qwen2.5-coder:latest

WRITER_MODEL_PROVIDER=local
WRITER_MODEL=llama3.2:latest

# Required for all configurations
SEARCH_PROVIDER=searxng
SEARXNG_HOST=http://127.0.0.1:8888
LOCAL_MODEL_URL=http://127.0.0.1:11434/v1
```

### Step 2: Install Required Models

Download the specialized function calling model:
```bash
ollama pull hf.co/tensorblock/Salesforce_Llama-xLAM-2-8b-fc-r-GGUF:Q4_K_M
```

Verify other models are available:
```bash
ollama list
# Should show: hermes3:8b, qwen2.5-coder:latest, llama3.2:latest
```

### Step 3: Validate Configuration

Run the configuration validator:
```python
from deep_researcher.config_validator import ConfigurationValidator, ConfigurationMode

# Production mode - strict validation
validator = ConfigurationValidator(ConfigurationMode.PRODUCTION)
is_valid = validator.validate_environment()

if not is_valid:
    print(validator.get_validation_report())
```

### Step 4: Test Agent Integration

Verify agents use correct models:
```python
from deep_researcher.llm_config import create_default_config
from deep_researcher.agents.tool_selector_agent import init_tool_selector_agent
from deep_researcher.agents.planner_agent import init_planner_agent

config = create_default_config()

# These should now use role-appropriate models
tool_selector = init_tool_selector_agent(config)  # Uses TOOL_CALLING model
planner = init_planner_agent(config)             # Uses PLANNER model
```

## Troubleshooting

### Common Issues

**1. "Missing configuration for TOOL_CALLING_MODEL"**
- Solution: Add `TOOL_CALLING_MODEL_PROVIDER` and `TOOL_CALLING_MODEL` environment variables
- Ensure the xLAM model is downloaded in Ollama

**2. "Model not suitable for function calling"** 
- Solution: Verify you're using the recommended xLAM model for TOOL_CALLING role
- Check model is properly downloaded: `ollama list | grep xlam`

**3. "Legacy configuration detected"**
- Solution: Remove old `REASONING_MODEL`, `MAIN_MODEL`, `FAST_MODEL` variables
- Add the 4 new role-specific model variables

**4. "Runtime assertion failed"**
- Solution: Check model role compatibility with the Model Role Registry
- Ensure models support their assigned role capabilities

### Development Mode

For development with limited models:
```python
from deep_researcher.config_validator import ConfigurationMode

# Relaxed validation for development
validator = ConfigurationValidator(ConfigurationMode.DEVELOPMENT)
```

### Performance Optimization

Expected performance impact:
- Model role validation: <100ms additional startup time
- Configuration validation: <50ms 
- Total overhead: <5% of normal operation

## Backward Compatibility

The system maintains backward compatibility:
- Legacy 3-model configurations continue to work with warnings
- Gradual migration is supported
- Existing research workflows are preserved

## Validation Commands

Check your setup:
```bash
# Test configuration
python -c "from deep_researcher.config_validator import ConfigurationValidator; ConfigurationValidator().validate_environment()"

# Test model registry
python -c "from deep_researcher.agents.utils.model_role_registry import get_model_registry; print('Registry OK')"

# Test runtime assertions
python -c "from deep_researcher.agents.utils.runtime_assertions import get_assertion_framework; print('Assertions OK')"
```

## Support

For issues with migration:
1. Check this troubleshooting guide
2. Review error messages for specific configuration problems
3. Verify all required models are downloaded
4. Test with `ConfigurationMode.DEVELOPMENT` first

The 4-model architecture provides the foundation for reliable structured agent outputs and successful tool execution in your research workflows.