# Tool Execution Pipeline Breakdown - Root Cause Analysis

## Executive Summary

**CRITICAL ISSUE**: The agents framework is producing function call JSON but **completely failing to execute tools**, causing a pipeline blockage that prevents any tool-based agents from working. This is not a configuration issue - it's a fundamental execution flow problem.

## Evidence of Pipeline Breakdown

### 1. **Symptom Pattern**
```
Model Output → Function Call JSON → [PIPELINE BREAK] → No Tool Execution → Parser Error
```

**What Should Happen:**
```
Model Output → Function Call JSON → Tool Execution → Tool Results → Final Agent Output → Success
```

**What Actually Happens:**
```
Model Output → Function Call JSON → ??? → Raw Output = Function Call JSON Only → Parser Error
```

### 2. **Key Evidence from Test Output**

#### ✅ **Working Components:**
- Function calling is enabled: `ENABLE_FUNCTION_CALLING: true`
- Tool properly registered: `FunctionTool(name='web_search', description=..., params_json_schema=...)`
- Model produces valid function call: `{"name": "web_search", "arguments": {"query": "..."}}`
- Fallback mechanism works: Manual tool invocation via `.func()` succeeds

#### ❌ **Broken Component:**
- **Agents framework execution pipeline completely skips tool execution**
- No tool invocation logs despite function call being produced
- Raw final_output contains only function call JSON, nothing else

## Root Cause Hypothesis

**The agents framework `RunImpl.execute_tools_and_side_effects` pipeline is not detecting or processing the function call JSON produced by the model.**

### Critical Questions to Investigate:

1. **Model Response Processing**: Is `RunImpl.process_model_response` correctly parsing the model output and detecting the `ResponseFunctionToolCall`?

2. **Tool Mapping**: Is the function call being mapped to the correct `FunctionTool` in the `function_map`?

3. **Execution Invocation**: Is `RunImpl.execute_function_tool_calls` actually being called with any `ToolRunFunction` objects?

4. **Agent Configuration**: Is there a mismatch between how we configure `ResearchAgent` vs what the agents framework expects?

## Detailed Pipeline Analysis

### Phase 1: Model Response → Internal Representation

**Location**: `RunImpl.process_model_response`

**Expected Flow:**
```python
response.output contains ResponseFunctionToolCall
→ Mapped to function_map["web_search"] 
→ Creates ToolRunFunction(tool_call=output, function_tool=web_search_tool)
→ Added to ProcessedResponse.functions list
```

**Investigation Needed:**
- What is the actual type and content of items in `response.output`?
- Is our function call JSON being converted to `ResponseFunctionToolCall`?
- Is the tool name lookup in `function_map` succeeding?

### Phase 2: Tool Execution Orchestration

**Location**: `RunImpl.execute_tools_and_side_effects`

**Expected Flow:**
```python
processed_response.functions contains ToolRunFunction objects
→ execute_function_tool_calls() called with tool_runs list
→ Each tool's on_invoke_tool() method invoked
→ Tool results added to new_step_items
```

**Investigation Needed:**
- Is `processed_response.functions` empty when it should contain our web_search tool?
- Is `execute_function_tool_calls` being called at all?
- If called, does it receive any `ToolRunFunction` objects?

### Phase 3: Continuation vs Final Output

**Location**: `RunImpl.execute_tools_and_side_effects` (second half)

**Expected Flow:**
```python
Tool execution completes
→ Agent continues with tool results
→ Produces final ToolAgentOutput JSON
→ Returns via execute_final_output()
```

**Current Broken Flow:**
```python
No tool execution occurs
→ Agent thinks it's done after function call
→ Returns function call JSON as final output
→ Parser error
```

## Technical Deep Dive Required

### 1. **Model Response Format Investigation**

**Critical Question**: What format is our OpenAI model actually returning for function calls?

The agents framework expects specific response types:
- `ResponseFunctionToolCall` for standard function calls
- `ResponseFunctionWebSearch` for web search (special case)
- `ResponseOutputMessage` for text content

**Our model might be producing**: Generic text content containing function call JSON instead of structured `ResponseFunctionToolCall` objects.

### 2. **Function Call Detection Logic**

**Code to Examine**: `RunImpl.process_model_response` lines ~300-350

```python
for output in response.output:
    # ... other cases ...
    elif not isinstance(output, ResponseFunctionToolCall):
        logger.warning(f"Unexpected output type, ignoring: {type(output)}")
        continue
    
    # At this point we know it's a function tool call
    if not isinstance(output, ResponseFunctionToolCall):
        continue
```

**Hypothesis**: Our function call JSON is being produced as `ResponseOutputMessage` (plain text) instead of `ResponseFunctionToolCall`, causing it to be ignored by the tool execution logic.

### 3. **OpenAI Client Configuration**

**Critical Question**: How does our `OpenAIChatCompletionsModel` vs `OpenAIResponsesModel` handle function calling?

From the provider mapping:
```python
"openai": {
    "model": OpenAIResponsesModel,  # Uses responses API
}
```

But our test shows: `OpenAIChatCompletionsModel` - suggesting a mismatch in model type.

**Hypothesis**: We're using the wrong model type that doesn't properly handle function calling via the responses API.

## Diagnostic Plan

### Phase 1: Response Format Analysis
1. **Capture raw `ModelResponse` object** before any processing
2. **Log each item in `response.output`** with its exact type
3. **Verify function call detection logic** - is our JSON being classified correctly?

### Phase 2: Processing Pipeline Tracing  
1. **Instrument `process_model_response`** to log:
   - Input: Raw response items and their types
   - Processing: Which code paths are taken for each item
   - Output: Contents of `ProcessedResponse.functions` list

2. **Instrument `execute_function_tool_calls`** to log:
   - Input: Number and details of `ToolRunFunction` objects received
   - Execution: Each tool invocation attempt and result
   - Output: Tool results returned

### Phase 3: Agent Configuration Validation
1. **Verify model client type** - ensure we're using the correct OpenAI model class
2. **Check function schema passing** - confirm functions are actually sent to the OpenAI API
3. **Validate tool registration** - ensure tools are properly attached to agent

### Phase 4: Fallback Mechanism Analysis
1. **Trace why fallback mechanism works** while normal execution doesn't
2. **Compare execution paths** between normal agent run vs manual tool invocation

## Implementation Strategy

### Logging Instrumentation Points

**Priority 1 (Critical Path):**
```python
# In RunImpl.process_model_response
for output in response.output:
    logger.critical("PIPELINE_DEBUG: Processing output type=%s, content=%s", 
                   type(output).__name__, repr(output)[:200])

# In RunImpl.execute_tools_and_side_effects  
logger.critical("PIPELINE_DEBUG: execute_function_tool_calls called with %d tool_runs", 
               len(processed_response.functions))

# In execute_function_tool_calls
for tool_run in tool_runs:
    logger.critical("PIPELINE_DEBUG: Executing tool=%s with args=%s",
                   tool_run.function_tool.name, tool_run.tool_call.arguments)
```

**Priority 2 (Context):**
```python
# Before Runner.run call
logger.critical("PIPELINE_DEBUG: Starting agent run with tools=%s",
               [t.name for t in starting_agent.tools])

# In call_with_functions  
logger.critical("PIPELINE_DEBUG: Sending to API - functions=%s, enable_fc=%s",
               bool(functions), enable_fc)
```

### Hypothesis Testing Sequence

1. **Test A**: Does `response.output` contain `ResponseFunctionToolCall` objects?
   - **If Yes**: Issue is in tool mapping or execution
   - **If No**: Issue is in model response format or function calling setup

2. **Test B**: Does `processed_response.functions` contain any `ToolRunFunction` objects?
   - **If Yes**: Issue is in tool execution phase
   - **If No**: Issue is in response processing phase

3. **Test C**: Is `execute_function_tool_calls` being called at all?
   - **If Yes**: Issue is within tool execution logic
   - **If No**: Issue is in orchestration logic

## Expected Findings

**Most Likely Root Cause**: The OpenAI model is returning function calls as plain text content (`ResponseOutputMessage`) instead of structured function call objects (`ResponseFunctionToolCall`), causing the entire tool execution pipeline to be bypassed.

**Secondary Possibilities**:
- Model type mismatch (ChatCompletions vs Responses API)
- Function schema not being sent to OpenAI API
- Tool name mismatch in function_map lookup
- Agent framework version incompatibility

## Success Criteria

**Phase 1 Complete**: We can see exactly what type of objects are in `response.output` and why function calls aren't being detected.

**Phase 2 Complete**: We understand whether the issue is in response processing, tool mapping, or tool execution.

**Root Cause Identified**: We know the exact point where the pipeline breaks and why.

**Fix Implemented**: Tools execute properly and agents produce final ToolAgentOutput as expected.

## Next Steps (Awaiting Go-Ahead)

1. Implement critical logging at the 5 key pipeline points
2. Run instrumented test to capture detailed execution flow
3. Analyze logs to identify exact breakage point  
4. Develop targeted fix based on findings
5. Verify fix resolves the pipeline blockage

This is a **blocking issue** that prevents all tool-based functionality from working. Once identified and fixed, it should resolve not just the search agent test but all similar tool execution failures across the system.