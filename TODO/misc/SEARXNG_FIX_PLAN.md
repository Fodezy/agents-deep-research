# SearchXNG Integration Fix Plan

## Phase 1: Fix Immediate Issues (Priority: Critical)

### 1.1 Fix Missing `_filter_results` Method
- **File**: `deep_researcher/tools/web_search.py`
- **Action**: Add the missing `_filter_results` method to `SearchXNGClient` class
- **Details**: Copy the method from `SerperClient` and adapt for SearchXNG response format

### 1.2 Fix Exception Handling
- **File**: `deep_researcher/tools/web_search.py` 
- **Action**: Improve error handling in `web_search` tool function
- **Details**: Log actual HTTP errors and SearchXNG API responses instead of generic error messages

## Phase 2: Enhanced Debugging (Priority: High)

### 2.1 Add Comprehensive Logging
- **File**: `deep_researcher/tools/web_search.py`
- **Action**: Add detailed logging throughout SearchXNG client
- **Details**: 
  - Log HTTP request/response details
  - Log SearchXNG API response structure
  - Log parsing steps and results
  - Add timing information

### 2.2 Add Response Validation
- **File**: `deep_researcher/tools/web_search.py`
- **Action**: Validate SearchXNG response format
- **Details**: Check for expected JSON structure and log discrepancies

## Phase 3: Isolated Testing (Priority: Medium)

### 3.1 Create SearchXNG Unit Tests
- **File**: `tests/test_searxng_integration.py` (new)
- **Action**: Create isolated tests for SearchXNG client
- **Details**:
  - Test SearchXNG client initialization
  - Test search method with mock responses
  - Test error handling scenarios
  - Test URL scraping functionality

### 3.2 Create Integration Test Script
- **File**: `test_searxng_standalone.py` (new, root level)
- **Action**: Create standalone test script
- **Details**:
  - Test direct SearchXNG API calls
  - Test with local Ollama models
  - Test end-to-end search + scrape workflow
  - Include curl command validation

### 3.3 Add Configuration Validation
- **File**: `tests/test_config_validation.py` (new)
- **Action**: Test SearchXNG configuration setup
- **Details**:
  - Validate SearchXNG host connectivity
  - Test environment variable loading
  - Test model compatibility

## Expected Outcomes

- **Phase 1**: SearchXNG integration works without silent failures
- **Phase 2**: Clear visibility into search execution and failures
- **Phase 3**: Reliable testing framework for future SearchXNG changes

## Files to be Modified/Created

### Modified:
- `deep_researcher/tools/web_search.py`

### Created:
- `tests/test_searxng_integration.py`
- `test_searxng_standalone.py`
- `tests/test_config_validation.py`
- `SEARXNG_FIX_PLAN.md` (this document)

This plan focuses on immediate fixes first, then provides debugging visibility, and finally ensures reliable testing for future maintenance.

## Root Cause Analysis

Based on analysis of the current code and log output, the primary issues identified are:

1. **Missing `_filter_results` method** in `SearchXNGClient` class (line 185 references it but doesn't exist)
2. **Silent failures** - tools show as executing but aren't actually calling SearchXNG
3. **Insufficient error logging** - HTTP response codes and SearchXNG API errors aren't captured
4. **Exception swallowing** - generic error messages hide actual failure causes

## Implementation Notes

- SearchXNG client initializes correctly with `http://127.0.0.1:8888/search`
- Tool registration succeeds but actual search execution fails silently
- Manual curl commands work, indicating SearchXNG docker container is functional
- The issue is in the Python client implementation, not the SearchXNG service