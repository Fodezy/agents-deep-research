# Tool Execution Pipeline Debugging Progress

## Problem Statement

**Critical Issue**: Search agent test fails because tool execution pipeline is completely broken. Function calls are generated as text but never executed, causing `OutputParserError: Failed to parse and validate output as ToolAgentOutput`.

**Test Failing**: `tests/test_searxng_integration_real.py::TestSearchAgentReal::test_search_agent_execution`

## Root Cause Confirmed

### Hypothesis Validated ✅
Through diagnostic logging, we confirmed the exact pipeline breakdown:

**Expected Flow:**
```
Model → ResponseFunctionToolCall → Tool Execution → ToolAgentOutput → Success
```

**Actual Broken Flow:**
```
Model → ResponseOutputMessage (text) → No Tool Execution → Function Call JSON Only → Parser Error
```

### Key Evidence from Diagnostics

1. **Model Response Format Issue**:
   ```
   Output 0: type=ResponseOutputMessage
     content: [ResponseOutputText(..., text='{\n  "name": "web_search",\n  "arguments": {...
   ```
   - Function call is returned as **plain text** instead of structured `ResponseFunctionToolCall`

2. **Pipeline Completely Bypassed**:
   ```
   functions count: 0  # ← NO FUNCTION TOOLS DETECTED
   execute_function_tool_calls called with 0 tool_runs  # ← NO TOOLS TO EXECUTE
   ```

3. **Agent Configuration Correct**:
   ```
   ENABLE_FUNCTION_CALLING: true
   Tool #0: FunctionTool(name='web_search', ...)
   ```

## Implementation Progress

### Phase 1: Diagnostic Confirmation ✅ COMPLETED
**Status**: Successfully confirmed hypothesis

**What We Added**:
- Enhanced logging in `ResearchRunner.run()` to capture raw model responses
- Monkey patched `RunImpl.process_model_response` to see function call detection
- Monkey patched `RunImpl.execute_function_tool_calls` to confirm no tools executed

**Key Files Modified**:
- `deep_researcher/agents/baseclass.py` - Added response debugging
- `deep_researcher/llm_config.py` - Added RunImpl monkey patches

### Phase 2: Fix Model Response Translation ⚠️ IN PROGRESS
**Status**: Identified the issue but fix not yet working

**Root Cause Identified**: 
The agents framework expects `tools` parameter (modern OpenAI API format) but our `call_with_functions` method was passing legacy `functions` format.

**Attempted Fix**:
- Modified `call_with_functions` in `llm_config.py` to convert `functions` → `tools` format
- Added tool_choice parameter handling
- **Result**: Still not working - `call_with_functions` method may not be used by agents framework

**Next Investigation Step**:
Need to check if agents framework uses its own tool calling mechanism and doesn't use our `call_with_functions` method at all.

## Technical Architecture Understanding

### Agents Framework Tool Flow
1. **Agent Creation**: `ResearchAgent` with `tools=[web_search_tool]`
2. **Model Client**: `OpenAIChatCompletionsModel` handles API calls
3. **Tool Conversion**: `ToolConverter.to_openai(tool)` converts `FunctionTool` → OpenAI format
4. **API Call**: Direct OpenAI API call with `tools` parameter
5. **Response Processing**: `RunImpl.process_model_response` classifies response items

### The Disconnect
Our `call_with_functions` method is **not in the execution path**. The agents framework has its own complete tool calling pipeline that bypasses our custom function calling logic.

## Current Diagnostic Setup

### Monkey Patches in Place
**File**: `deep_researcher/llm_config.py`

1. **RunImpl.process_model_response**: Logs response classification
2. **RunImpl.execute_function_tool_calls**: Logs tool execution attempts
3. **Baseclass response logging**: Logs raw model responses

### Debug Output Pattern
```
[PIPELINE_DEBUG] process_model_response called:
  agent.name: WebSearchAgent
  all_tools: ['web_search']
  response.output length: 1
    Output 0: type=ResponseOutputMessage  # ← PROBLEM: Should be ResponseFunctionToolCall
      content: [ResponseOutputText(...function call JSON...)]
[PIPELINE_DEBUG] process_model_response result:
  functions count: 0  # ← NO TOOLS DETECTED
```

## Next Steps (Phase 2 Continuation)

### Immediate Actions Required
1. **Check Tool Conversion**: Add logging to see what `ToolConverter.to_openai()` produces from our `FunctionTool`
2. **Verify API Parameters**: Log actual parameters sent to OpenAI API (should include `tools` array)
3. **Response Analysis**: Check if OpenAI is returning `tool_calls` in message or just text content

### Implementation Plan
```python
# Add to llm_config.py monkey patches:
# 1. Log OpenAI model._get_response tool conversion
# 2. Log actual API call parameters 
# 3. Log raw OpenAI response format
```

### Hypothesis for Phase 2
**Most Likely Issue**: `ToolConverter.to_openai()` is not properly converting our `FunctionTool` objects, resulting in empty tools array sent to OpenAI API.

**Alternative Issues**:
- OpenAI API returning function calls as text instead of structured tool_calls
- Agents framework version incompatibility
- Model client configuration issue

## Files Modified So Far

### Core Changes
- `deep_researcher/agents/baseclass.py`: Added response debugging in ResearchRunner
- `deep_researcher/llm_config.py`: Added monkey patches + attempted tools format fix

### Test Files
- `tests/test_searxng_integration_real.py`: Enhanced with diagnostics (already had good logging)

## Working Components (Don't Break)

### ✅ What's Working
1. **Tool Creation**: `create_web_search_tool()` returns valid FunctionTool
2. **Agent Setup**: Tools properly attached to ResearchAgent
3. **Function Calling Config**: `ENABLE_FUNCTION_CALLING=true` properly set
4. **Manual Tool Execution**: Fallback mechanism works (tool.func() succeeds)
5. **Search Infrastructure**: SearchXNG server responding correctly

### ⚠️ What's Broken
1. **Agents Framework Pipeline**: Not executing tools during agent runs
2. **Response Format**: Function calls returned as text instead of structured objects

## Key Diagnostic Commands

### Run Failing Test with Full Diagnostics
```bash
cd "D:/projects/agents-deep-research" 
.venv/Scripts/activate
python -m pytest tests/test_searxng_integration_real.py::TestSearchAgentReal::test_search_agent_execution -v -s
```

### Test Tool Directly (Should Work)
```python
from deep_researcher.tools.web_search import create_web_search_tool
from deep_researcher.llm_config import create_default_config

config = create_default_config()
tool = create_web_search_tool(config)
result = await tool.func('test query')  # This works
```

## Success Criteria

### Phase 2 Complete When:
1. ✅ `ResponseFunctionToolCall` objects appear in model response instead of `ResponseOutputMessage`
2. ✅ `process_model_response result: functions count: 1` (instead of 0)
3. ✅ `execute_function_tool_calls called with 1 tool_runs` (instead of 0)

### Phase 3 Complete When:
1. ✅ Tool execution produces actual search results
2. ✅ Agent generates final ToolAgentOutput JSON
3. ✅ Test passes without fallback mechanism

## Environment Info

**Working Directory**: `D:\projects\agents-deep-research`
**Virtual Environment**: `.venv\Scripts\activate`
**Python**: 3.12.6
**Key Dependencies**: 
- `agents` package (OpenAI agents framework)
- `openai` client library
- `deep_researcher` (our code)

**SearchXNG**: Running on `http://127.0.0.1:8888` (verified working)

## Important Notes

1. **Don't disable monkey patches** - they provide critical debugging info
2. **Fallback mechanism works** - proves tools are correctly implemented
3. **Focus on agents framework integration** - not our tool implementation
4. **OpenAI API format changed** - `functions` → `tools` (handled in agents framework)
5. **Test isolation** - Only this specific integration is broken, core functionality works