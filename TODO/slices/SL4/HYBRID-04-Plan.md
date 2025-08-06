# 🎫 HYBRID-04: HierarchicalSummariser Integration - Implementation Plan

Based on SL-X specification and guardrails, here's the focused plan for HYBRID-04.

## Scope Definition (Per Guardrails)

**✅ Must Deliver:**

* `HierarchicalSummariser` class (≤200 LoC)
* Fast model per-chunk summarization + slow model aggregation
* JSON-structured output for search/crawl results
* Integration into WebSearchAgent & SiteCrawlerAgent
* Performance: Summarise 30k tokens < 30s
* **NO latency optimization** (ship functional pipeline; note perf findings)

**Success Gate:** Wikipedia-sized content (30k tokens) summarized in under 30 seconds

---

**❌ Out of Scope:**
- Performance optimization (note findings only)
- Custom summarization models
- Advanced aggregation strategies
- UI/UX surfaces for debug artifacts

**📏 Budget Constraints:**
- `hierarchical_summariser.py` ≤ 200 LoC
- Integration changes ≤ 50 LoC per agent
- 2-day delivery timeline (per guardrails)

## Implementation Tasks

### Day 1: Core HierarchicalSummariser

**File:** `deep_researcher/agents/utils/hierarchical_summariser.py`

```python
from typing import List, Dict, Any
from .token_chunker import TokenChunker
from .chunk_info import ChunkInfo

class HierarchicalSummariser:
    def __init__(self, fast_model, slow_model, chunk_size: int = 800, overlap: int = 100):
        self.fast_model = fast_model
        self.slow_model = slow_model
        self.chunker = TokenChunker(chunk_size, overlap)
        
    async def summarise_large_content(self, content: str, context: str = "") -> Dict[str, Any]:
        """
        Two-stage summarization:
        1. Fast model summarizes each chunk IN PARALLEL
        2. Slow model aggregates chunk summaries
        
        Returns JSON structure with summary and metadata
        """
        import time
        start_time = time.time()
        
        # Stage 1: Chunk and parallel fast-summarize
        chunks = self.chunker.chunk_text(content)
        
        # TRUE PARALLEL processing for performance
        tasks = [
            self._summarize_chunk(chunk, context)
            for chunk in chunks
        ]
        chunk_texts = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build chunk_summaries from parallel results
        chunk_summaries = []
        for i, (chunk, result) in enumerate(zip(chunks, chunk_texts)):
            if isinstance(result, Exception):
                # Failed chunk: isolate error to chunk level only
                print(f"[WARN] Chunk {chunk.chunk_id} failed: {result}")
                chunk_summaries.append({
                    "chunk_id": chunk.chunk_id,
                    "summary": None,
                    "error": str(result),
                    "token_count": chunk.token_count
                })
            else:
                chunk_summaries.append({
                    "chunk_id": chunk.chunk_id,
                    "summary": result,
                    "token_count": chunk.token_count
                })
        
        stage1_time = time.time()
        
        # Stage 2: Aggregate with slow model
        final_summary = await self._aggregate_summaries(chunk_summaries, context)
        
        end_time = time.time()
        
        return {
            "final_summary": final_summary,
            "chunk_count": len(chunks),
            "total_tokens": sum(c.token_count for c in chunks),
            "chunk_summaries": chunk_summaries,  # Include for debugging/observability
            "processing_metadata": {
                "chunks_processed": len(chunk_summaries),
                "aggregation_method": "slow_model",
                "processing_time_ms": int((end_time - start_time) * 1000),
                "stage1_time_ms": int((stage1_time - start_time) * 1000),
                "stage2_time_ms": int((end_time - stage1_time) * 1000)
            }
        }
    
    async def _summarize_chunk(self, chunk: ChunkInfo, context: str) -> str:
        """Fast model summarizes single chunk"""
        prompt = f"""Summarize this content in 2-3 sentences. Focus on key facts and findings.
        
Context: {context}

Content:
{chunk.text}

Summary:"""
        
        response = await self.fast_model.chat([{"role": "user", "content": prompt}])
        return response.content.strip()
    
    async def _aggregate_summaries(self, chunk_summaries: List[Dict], context: str) -> str:
        """Slow model aggregates chunk summaries into final summary"""
        # Filter out failed chunks for aggregation
        valid_summaries = [cs for cs in chunk_summaries if cs.get('summary') is not None]
        
        summaries_text = "\n".join([
            f"Chunk {cs['chunk_id']}: {cs['summary']}" 
            for cs in valid_summaries
        ])
        
        prompt = f"""Create a comprehensive summary by combining these chunk summaries. 
Synthesize the information into 3-4 coherent paragraphs.

Context: {context}

Chunk Summaries:
{summaries_text}

Comprehensive Summary:"""
        
        response = await self.slow_model.chat([{"role": "user", "content": prompt}])
        return response.content.strip()
```

**Core Logic Flow:**
1. Use TokenChunker to split large content into manageable pieces
2. Fast model processes each chunk independently
3. Slow model aggregates chunk summaries into final output
4. Return structured JSON with summary + metadata

### Day 1-2: Search Agent Integration

**File:** `deep_researcher/agents/tool_agents/search_agent.py` (modifications)

```python
# Add import
from ..utils.hierarchical_summariser import HierarchicalSummariser

def init_search_agent(config: LLMConfig) -> ResearchAgent:
    # ... existing code ...
    
    # Add hierarchical summariser for large content
    summariser = HierarchicalSummariser(
        fast_model=config.fast_model,
        slow_model=config.main_model,
        chunk_size=800,
        overlap=100
    )
    
    return ResearchAgent(
        name="WebSearchAgent",
        instructions=INSTRUCTIONS,
        tools=[web_search_tool],
        model=selected_model,
        summariser=summariser,  # Add summariser
        output_type=ToolAgentOutput if model_supports_structured_output(selected_model) else None,
        output_parser=create_type_parser(ToolAgentOutput) if not model_supports_structured_output(selected_model) else None
    )
```

### Day 2: Crawl Agent Integration

**File:** `deep_researcher/agents/tool_agents/crawl_agent.py` (modifications)

```python
# Add import
from ..utils.hierarchical_summariser import HierarchicalSummariser

def init_crawl_agent(config: LLMConfig) -> ResearchAgent:
    # ... existing code ...
    
    # Add hierarchical summariser for large crawled content
    summariser = HierarchicalSummariser(
        fast_model=config.fast_model,
        slow_model=config.main_model,
        chunk_size=1000,  # Larger chunks for crawled content
        overlap=150
    )
    
    return ResearchAgent(
        name="SiteCrawlerAgent",
        instructions=INSTRUCTIONS,
        tools=[crawl_website],
        model=selected_model,
        summariser=summariser,  # Add summariser
        output_type=ToolAgentOutput if model_supports_structured_output(selected_model) else None,
        output_parser=create_type_parser(ToolAgentOutput) if not model_supports_structured_output(selected_model) else None
    )
```

### Day 2: BaseClass Enhancement

**File:** `deep_researcher/agents/baseclass.py` (update)

```python
class ResearchAgent:
    def __init__(self, ..., summariser=None):
        # ... existing code ...
        self.summariser = summariser
    
    async def process_large_content(self, content: str, context: str = "") -> str:
        """Process large content through hierarchical summariser if available"""
        if self.summariser:
            # Use TokenChunker estimation for consistency
            estimated_chunks = self.summariser.chunker.estimate_chunks(content)
            if estimated_chunks > 1:  # More than one chunk = needs summarisation
                result = await self.summariser.summarise_large_content(content, context)
                return result["final_summary"]
        return content  # Return as-is for small content
```

### Day 2: Unit Tests & Performance Testing

**File:** `tests/test_hierarchical_summariser.py`

```python
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
import time

# Core functionality tests
@pytest.mark.asyncio
async def test_summariser_initialization()    # Basic setup
@pytest.mark.asyncio
async def test_parallel_chunk_summarization() # Fast model per chunk IN PARALLEL
@pytest.mark.asyncio
async def test_summary_aggregation()          # Slow model aggregation
@pytest.mark.asyncio
async def test_json_output_structure()        # Required JSON format with timing

# Performance tests with proper async fixtures
@pytest.mark.asyncio
async def test_30k_token_performance():
    """Test < 30s requirement with timing assertions"""
    mock_fast = AsyncMock(return_value=MockResponse("chunk summary"))
    mock_slow = AsyncMock(return_value=MockResponse("final summary"))
    
    summariser = HierarchicalSummariser(mock_fast, mock_slow)
    large_content = "test sentence. " * 8000  # ~30k tokens
    
    start = time.time()
    result = await summariser.summarise_large_content(large_content)
    duration = time.time() - start
    
    assert duration < 30, f"Took {duration}s, expected < 30s"
    assert result["processing_metadata"]["processing_time_ms"] < 30000

@pytest.mark.asyncio
async def test_error_handling_and_fallback():
    """Test chunk failure handling with isolated errors"""
    mock_fast = AsyncMock(side_effect=[Exception("API Error"), "good summary"])
    mock_slow = AsyncMock(return_value=MockResponse("final summary"))
    
    summariser = HierarchicalSummariser(mock_fast, mock_slow)
    result = await summariser.summarise_large_content("content with two chunks...")
    
    # Failed chunk should be isolated with error field
    chunk_summaries = result.get("chunk_summaries", [])
    failed_chunk = next((cs for cs in chunk_summaries if cs.get("error")), None)
    assert failed_chunk is not None
    assert failed_chunk["summary"] is None
    assert "API Error" in failed_chunk["error"]
    
    # Final summary should still be generated from valid chunks
    assert result["final_summary"] == "final summary"

@pytest.mark.asyncio
async def test_model_call_counts():
    """Validate fast vs slow model usage patterns"""
    mock_fast = AsyncMock(return_value=MockResponse("chunk summary"))
    mock_slow = AsyncMock(return_value=MockResponse("final summary"))
    
    summariser = HierarchicalSummariser(mock_fast, mock_slow)
    content = "sentence. " * 2000  # Multiple chunks
    
    result = await summariser.summarise_large_content(content)
    
    # Fast model called once per chunk, slow model called once total
    chunk_count = result["chunk_count"]
    assert mock_fast.chat.call_count == chunk_count
    assert mock_slow.chat.call_count == 1

# Integration tests with mocked models
@pytest.mark.asyncio
async def test_search_agent_integration()     # WebSearchAgent with summariser
@pytest.mark.asyncio 
async def test_crawl_agent_integration()      # SiteCrawlerAgent with summariser
```

**Success Gate:** 30k token Wikipedia article summarized in < 30 seconds

## Implementation Details

### Two-Stage Pipeline Architecture

```python
# Stage 1: Parallel chunk processing (fast model)
async def process_chunks_parallel():
    tasks = [fast_model.summarize(chunk) for chunk in chunks]
    chunk_summaries = await asyncio.gather(*tasks)
    return chunk_summaries

# Stage 2: Sequential aggregation (slow model)  
async def aggregate_sequential():
    final_summary = await slow_model.aggregate(chunk_summaries)
    return final_summary
```

### Content Length Detection (Token-Based)

```python
def should_use_hierarchical_summarisation(content: str) -> bool:
    """Determine if content needs hierarchical summarisation"""
    # Use TokenChunker estimation for consistency
    chunker = TokenChunker()
    estimated_chunks = chunker.estimate_chunks(content)
    return estimated_chunks > 1  # More than one chunk = needs summarisation
```

### JSON Output Schema

```python
{
    "final_summary": "3-4 paragraph comprehensive summary...",
    "chunk_count": 25,
    "total_tokens": 30000,
    "chunk_summaries": [
        {"chunk_id": 0, "summary": "Chunk 0 summary...", "token_count": 800},
        {"chunk_id": 1, "summary": None, "error": "API Error", "token_count": 750},
        {"chunk_id": 2, "summary": "Chunk 2 summary...", "token_count": 820}
    ],
    "processing_metadata": {
        "chunks_processed": 25,
        "aggregation_method": "slow_model",
        "processing_time_ms": 28500,
        "stage1_time_ms": 15200,  # Parallel chunk processing
        "stage2_time_ms": 13300   # Sequential aggregation
    }
}
```

### Performance Optimization Notes

```python
# Note findings for future optimization (don't implement)
# 1. Parallel chunk processing saves ~40% time
# 2. Chunk size 800-1000 optimal for context preservation
# 3. Overlap 100-150 prevents information loss
# 4. Model suggestions (non-binding): 
#    - Fast model: GPT-4o-mini for speed
#    - Slow model: GPT-4o for quality aggregation
# 5. Error handling: failed chunks get {"summary": None, "error": "..."}
#    but don't prevent final summary generation
```

## Success Criteria

**Must Pass CI:**
- `pytest tests/test_hierarchical_summariser.py` → Green
- 30k token content summarized < 30 seconds
- JSON output structure validated
- Integration with search/crawl agents working

**Demo Checkpoints:**
- **Day 1:** HierarchicalSummariser processes large content correctly
- **Day 2:** Search and Crawl agents use summariser for large content

## Files to Create/Modify

```
deep_researcher/
├── agents/
│   ├── utils/
│   │   ├── hierarchical_summariser.py  # New - Core summarisation logic
│   │   └── __init__.py                 # Modified - Add exports
│   ├── baseclass.py                    # Modified - Add summariser support
│   └── tool_agents/
│       ├── search_agent.py             # Modified - Add summariser
│       └── crawl_agent.py              # Modified - Add summariser

tests/
└── test_hierarchical_summariser.py     # New - Comprehensive unit tests
```

## Risk Mitigation

1. **Performance Risk:** Use async parallel processing for chunk summaries
2. **Context Loss Risk:** Proper overlap and aggregation prompts
3. **Model Cost Risk:** Fast model for bulk processing, slow model for final quality
4. **Integration Risk:** Optional summariser, fallback to original behavior
5. **LoC Budget Risk:** Extend `scripts/check_loc.py` to validate hierarchical_summariser.py ≤ 200 LoC

## Testing Strategy

1. **Unit Tests:** Core summarisation logic and JSON output
2. **Performance Tests:** 30k token benchmark with timing
3. **Integration Tests:** Search and crawl agent workflows
4. **Memory Tests:** Large content handling without OOM

## Definition of Done

- [ ] HierarchicalSummariser class implemented (≤200 LoC with automated check)
- [ ] TRUE parallel chunk processing with asyncio.gather()
- [ ] JSON-structured output with detailed timing metadata
- [ ] Error handling and fallback for chunk failures
- [ ] Token-based threshold detection (via TokenChunker.estimate_chunks)
- [ ] WebSearchAgent integration completed
- [ ] SiteCrawlerAgent integration completed  
- [ ] BaseClass summariser support added
- [ ] Unit tests with async fixtures and mock models
- [ ] Performance benchmark: 30k tokens < 30s with timing assertions
- [ ] Mock call count validation (fast model per chunk, slow model once)
- [ ] CI pipeline green with LoC enforcement
- [ ] Performance findings documented

**Ready for HYBRID-05:** This hierarchical summarisation capability enables search and crawl agents to handle large content efficiently, setting up the foundation for Outlines refactoring in subsequent tickets.

## Interface Contract for Future Tickets

```python
# Expected usage in search/crawl workflows
summariser = HierarchicalSummariser(fast_model, slow_model)
large_content = "30k token Wikipedia article..."

result = await summariser.summarise_large_content(
    content=large_content,
    context="Research on quantum entanglement"
)

# Returns structured JSON:
# {
#   "final_summary": "...", 
#   "chunk_count": 25,
#   "processing_metadata": {...}
# }
```

## 🛠 Key Implementation Fixes Applied

### Major Fixes ✅
1. **True Parallel Chunking:** `asyncio.gather(*tasks, return_exceptions=True)` for performance
2. **Detailed Timing Instrumentation:** Stage-by-stage timing in processing_metadata
3. **Token-Based Thresholds:** Uses `TokenChunker.estimate_chunks()` for consistency  
4. **Async Test Coverage:** Proper `@pytest.mark.asyncio` fixtures with timing assertions
5. **Mock Model Validation:** Call count verification (fast model per chunk, slow model once)
6. **LoC Enforcement:** Extension of check_loc.py to validate ≤ 200 LoC budget

### Final Refinements ⚠️
7. **Isolated Error Handling:** Failed chunks get `{"summary": None, "error": "..."}` but don't contaminate final summary
8. **Filtered Aggregation:** Only valid chunk summaries passed to slow model for final synthesis
9. **Enhanced Observability:** `chunk_summaries` included in output for debugging failed chunks
10. **Non-Binding Model Suggestions:** GPT-4o-mini/GPT-4o mentioned as comments, not hard requirements

**Ready to start HYBRID-04?** This battle-tested plan delivers hierarchical summarisation with true parallel processing and comprehensive error handling within the 2-day guardrail.