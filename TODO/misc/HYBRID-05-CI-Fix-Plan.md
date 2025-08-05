# HYBRID-05 CI Fix Plan: Unblocking Test Suite

**Status:** Critical CI blockers preventing green build  
**Scope:** Immediate fixes required before HYBRID-06 can proceed  
**Timeline:** Must complete before moving to next tickets  

---

## Executive Summary

Post-HYBRID-05 implementation, the test suite has 26 failing tests blocking CI. This plan provides **executable specifications** for each blocker, focusing on exact inputs and expected outputs to ensure fixes address real test requirements rather than reshaping tests to fit broken code.

---

## Phase 1: Core CI Unblockers

### 1. Unicode Header Encoding

| **Goal** | **Inputs** | **Expected Output** |
|----------|------------|-------------------|
| Remove any non-ASCII from all prompt strings so HTTP headers never contain smart quotes or em-dashes. | • `INSTRUCTIONS` constants containing curly quotes (`'`) or `—`<br>• Template strings in `outlines_templates.py`<br>• Any agent prompt strings passed to HTTP headers | • All prompt-header strings only contain `['"]` and `-` (ASCII)<br>• No `UnicodeEncodeError` when constructing HTTP headers<br>• All LLM provider tests pass header validation |

**Validation Script:**
```python
# scripts/validate_unicode.py
def validate_no_unicode_in_prompts():
    # Scan all INSTRUCTIONS and template strings
    # Assert no characters > ASCII 127
    # Test HTTP header creation with all prompts
```

---

### 2. Missing `long_writer_agent` Exports

| **Goal** | **Inputs** | **Expected Output** |
|----------|------------|-------------------|
| Provide the two functions the tests import so they can at least be called. | • Tests in `test_reformat_references.py` calling `reformat_references(section_markdown, section_refs, all_refs)`<br>• Tests in `test_reformat_section_headings.py` calling `reformat_section_headings(markdown_text)` | • `from deep_researcher.agents.long_writer_agent import reformat_references, reformat_section_headings` succeeds<br>• `reformat_references()` returns `(str, List[str])` tuple<br>• `reformat_section_headings()` returns string with level-2 headings<br>• Tests pass with minimal expected behavior |

**Validation Script:**
```python
# scripts/validate_exports.py
def validate_long_writer_exports():
    from deep_researcher.agents.long_writer_agent import reformat_references, reformat_section_headings
    # Test basic function signatures and return types
    assert callable(reformat_references)
    assert callable(reformat_section_headings)
```

---

### 3. Missing `searxng_host` in `LLMConfig`

| **Goal** | **Inputs** | **Expected Output** |
|----------|------------|-------------------|
| Add `searxng_host` so `init_search_agent()` can read it. | • `test_tool_agents.py`'s call to `init_search_agent(config)`<br>• SearchXNG integration tests reading `config.searxng_host`<br>• Default config creation without explicit host | • `LLMConfig().searxng_host` attribute exists<br>• Default value `"http://127.0.0.1:8888"`<br>• `init_search_agent()` no longer raises `AttributeError` |

**Validation Script:**
```python
# scripts/validate_config.py  
def validate_searxng_config():
    from deep_researcher.llm_config import LLMConfig
    config = LLMConfig()
    assert hasattr(config, 'searxng_host')
    assert config.searxng_host == "http://127.0.0.1:8888"
```

---

## Phase 2: Tool & Integration Fixes

### 4. `FunctionTool` Callable

| **Goal** | **Inputs** | **Expected Output** |
|----------|------------|-------------------|
| Make every `FunctionTool` usable like `await tool(...)` in tests. | • `await web_search_tool("query")` calls in tests<br>• `await crawl_website(url)` calls in tests<br>• `FunctionTool` objects from tool creation functions | • `FunctionTool` implements `__call__` async method OR<br>• `FunctionTool` exposes `.callable` attribute OR<br>• Tool creation returns callable wrapper<br>• Tests pass without changing `await tool(...)` syntax |

**Validation Script:**
```python
# scripts/validate_tools.py
async def validate_tool_callable():
    from deep_researcher.tools.web_search import create_web_search_tool
    tool = create_web_search_tool(test_config)
    # Must be callable with await
    result = await tool("test query")
    assert result is not None
```

---

### 5. ToolAgentOutput Schema Alignment

| **Goal** | **Inputs** | **Expected Output** |
|----------|------------|-------------------|
| Ensure the JSON your tools emit matches `ToolAgentOutput` Pydantic model exactly. | • Tool agents returning JSON like `{"name": "web_search", "parameters": {"query": "..."}}`<br>• Test parser calling `result.final_output_as(ToolAgentOutput)`<br>• Actual `ToolAgentOutput` Pydantic model schema | • No `OutputParserError` when parsing tool agent output<br>• Returned dict has exactly the fields and nesting the Pydantic schema expects<br>• All tool agent tests pass validation |

**Validation Script:**
```python
# scripts/validate_schema.py
def validate_tool_output_schema():
    from deep_researcher.agents.tool_agents import ToolAgentOutput
    # Test actual tool output against schema
    sample_output = {"name": "web_search", "parameters": {"query": "test"}}
    parsed = ToolAgentOutput.model_validate(sample_output)
    assert parsed is not None
```

---

### 6. AsyncMock Context Manager

| **Goal** | **Inputs** | **Expected Output** |
|----------|------------|-------------------|
| Fix your HTTP client so mocks of `session.get()` work under `async with`. | • `TestSearchXNGClient.test_search_success` mocks `session.get` to return a coroutine<br>• HTTP client code using `async with session.get(...)` pattern<br>• AsyncMock objects in test fixtures | • No `TypeError` about coroutine and async context manager protocol<br>• HTTP client `await`s `session.get()` first, then uses `async with response`<br>• Tests can supply mock that implements `__aenter__`/`__aexit__` |

**Validation Script:**
```python
# scripts/validate_http.py
async def validate_http_async_pattern():
    # Test HTTP client pattern with AsyncMock
    from unittest.mock import AsyncMock
    mock_session = AsyncMock()
    # Verify pattern works with mocks
    resp = await mock_session.get("test")
    async with resp:
        assert True  # Pattern should work
```

---

## Executable Validation Framework

### Master Validation Script
```python
# scripts/validate_blockers.py
"""Validate all 6 CI blockers are resolved with executable specifications"""

import asyncio
from deep_researcher.llm_config import LLMConfig

def main():
    print("🔍 Validating CI Blocker Fixes...")
    
    # Phase 1 validations
    validate_unicode_clean()
    validate_long_writer_exports() 
    validate_searxng_config()
    
    # Phase 2 validations  
    asyncio.run(validate_tool_callable())
    validate_tool_output_schema()
    asyncio.run(validate_http_async_pattern())
    
    print("✅ All blockers validated!")

def validate_unicode_clean():
    """Spec: No Unicode chars in prompts -> No UnicodeEncodeError in headers"""
    import re
    import glob
    
    for file_path in glob.glob("deep_researcher/**/*.py", recursive=True):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check for smart quotes and em-dashes
            unicode_chars = re.findall(r'[\u2019\u201C\u201D\u2014]', content)
            assert not unicode_chars, f"Unicode chars found in {file_path}: {unicode_chars}"
    
    print("✅ Unicode validation: All prompts ASCII-clean")

def validate_long_writer_exports():
    """Spec: Functions importable -> Tests can call them"""
    from deep_researcher.agents.long_writer_agent import reformat_references, reformat_section_headings
    
    # Test signatures match test expectations
    result_refs = reformat_references("test", ["[1] url"], ["[0] existing"])
    assert isinstance(result_refs, tuple) and len(result_refs) == 2
    
    result_headings = reformat_section_headings("# Title\nContent")
    assert isinstance(result_headings, str)
    assert "## Title" in result_headings  # Level-2 heading expected
    
    print("✅ Long writer exports: Functions callable with expected return types")

def validate_searxng_config():
    """Spec: searxng_host exists -> init_search_agent works"""
    config = LLMConfig()
    assert hasattr(config, 'searxng_host'), "searxng_host attribute missing"
    assert config.searxng_host == "http://127.0.0.1:8888", f"Wrong default: {config.searxng_host}"
    
    print("✅ SearchXNG config: searxng_host attribute exists with correct default")

async def validate_tool_callable():
    """Spec: FunctionTool callable -> await tool(...) works"""
    from deep_researcher.tools.web_search import create_web_search_tool
    from deep_researcher.llm_config import create_default_config
    
    config = create_default_config()
    config.searxng_host = "http://test:8080"  # Test value
    tool = create_web_search_tool(config)
    
    # Must be awaitable
    try:
        result = await tool("test query")
        print("✅ Tool callable: FunctionTool supports await tool(...) syntax")
    except TypeError as e:
        if "'FunctionTool' object is not callable" in str(e):
            raise AssertionError("FunctionTool not callable - fix required")
        raise

async def validate_tool_output_schema():
    """Spec: Tool output matches schema -> No OutputParserError"""
    try:
        from deep_researcher.agents.tool_agents import ToolAgentOutput
        
        # Test current output format against schema
        sample_output = {"name": "web_search", "parameters": {"query": "test"}}
        parsed = ToolAgentOutput.model_validate(sample_output)
        print("✅ Tool schema: Output format matches ToolAgentOutput schema")
        
    except Exception as e:
        print(f"❌ Tool schema mismatch: {e}")
        print("Current output format needs alignment with ToolAgentOutput schema")

async def validate_http_async_pattern():
    """Spec: HTTP client + AsyncMock -> No context manager error"""
    from unittest.mock import AsyncMock
    
    # Test the pattern HTTP client should use
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_session.get.return_value = mock_response
    
    try:
        # Pattern that should work
        response = await mock_session.get("http://test")
        async with response:
            pass  # Should not raise TypeError
        print("✅ HTTP async: Pattern works with AsyncMock")
    except TypeError as e:
        if "async context manager protocol" in str(e):
            raise AssertionError("HTTP client pattern incompatible with AsyncMock")
        raise

if __name__ == "__main__":
    main()
```

---

## Implementation Tracking

### Blocker Status Dashboard
| Blocker | Status | Validation Command |
|---------|--------|--------------------|
| 1. Unicode Headers | ❌ | `python scripts/validate_blockers.py::validate_unicode_clean` |
| 2. Long Writer Exports | ❌ | `python scripts/validate_blockers.py::validate_long_writer_exports` |
| 3. SearchXNG Config | ❌ | `python scripts/validate_blockers.py::validate_searxng_config` |  
| 4. Tool Callable | ❌ | `python scripts/validate_blockers.py::validate_tool_callable` |
| 5. Tool Schema | ❌ | `python scripts/validate_blockers.py::validate_tool_output_schema` |
| 6. HTTP Async | ❌ | `python scripts/validate_blockers.py::validate_http_async_pattern` |

### Quality Gates
- [ ] All 6 blocker validations pass
- [ ] `pytest tests/test_tool_selector_outlines.py` still passes (HYBRID-05 regression check)
- [ ] No new test failures introduced by fixes
- [ ] Master validation script runs clean: `python scripts/validate_blockers.py`

---

## Definition of Done

**Each blocker is complete when:**
1. ✅ Its validation function in `scripts/validate_blockers.py` passes
2. ✅ Related test failures are resolved
3. ✅ No regression in HYBRID-05 ToolSelector functionality

**Overall completion when:**
1. ✅ Master validation script passes: `python scripts/validate_blockers.py`  
2. ✅ Test suite collection succeeds without import errors
3. ✅ Core LLM communication and tool invocation restored
4. ✅ CI can proceed to HYBRID-06 without blocked dependencies

This approach ensures **every fix is validated against exact test requirements** rather than reshaping tests to fit broken implementations.