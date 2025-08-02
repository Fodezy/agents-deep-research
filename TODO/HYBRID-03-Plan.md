# 🎫 HYBRID-03: Token Chunker Utility - Implementation Plan

Based on SL-X specification and guardrails, here's the focused plan for HYBRID-03.

## Scope Definition (Per Guardrails)

**✅ Must Deliver:**

* `TokenChunker` utility class (≤150 LoC with automated check)
* True memory safety: handles 25k+ tokens without OOM via string-slicing approach
* Preserves sentence boundaries across chunks
* Configurable chunk size (~800 tokens with overlap)
* Dual API: List and Generator versions
* Empty-text guards in both APIs
* Unit tests with 100% coverage + memory smoke test
* **NO integration with agents yet** (that's HYBRID-04)

**Success Gate:** Handle 25k+ token documents without memory spikes, 100% test coverage

---

**❌ Out of Scope:**
- Agent integration (HYBRID-04 dependency)
- Performance optimization 
- Custom tokenizer implementation
- Advanced chunking strategies (semantic, etc.)

**📏 Budget Constraints:**
- `token_chunker.py` ≤ 150 LoC
- 2-day delivery timeline (per guardrails)
- Reuse existing tokenizer from project

## Implementation Tasks

### Day 1: Core TokenChunker Implementation

**File:** `deep_researcher/agents/utils/chunker_config.py`

```python
# Configuration constants for easy tuning
DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP_TOKENS = 100
```

**File:** `deep_researcher/agents/utils/token_chunker.py`

```python
import re
from typing import List, Iterator
from .chunker_config import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP_TOKENS
from .chunk_info import ChunkInfo

class TokenChunker:
    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP_TOKENS):
        self.tokenizer = self._get_consistent_tokenizer()
        self.chunk_size = chunk_size  
        self.overlap = overlap
        
    def _get_consistent_tokenizer(self):
        """Get exact same tokenizer used by summariser models"""
        from deep_researcher.llm_config import get_summariser_tokenizer
        return get_summariser_tokenizer()
        
    def chunk_text(self, text: str) -> List[ChunkInfo]:
        """Split text into overlapping chunks with sentence boundary preservation"""
        if not text.strip():
            return []
            
        return list(self.chunk_text_generator(text))
    
    def chunk_text_generator(self, text: str) -> Iterator[ChunkInfo]:
        """Memory-efficient generator with true memory safety"""
        if not text.strip():
            return
            
        # Memory-safe approach: slice raw string first, then tokenize windows
        char_window_size = self.chunk_size * 4  # rough chars per chunk estimate
        overlap_chars = self.overlap * 4
        
        chunk_id = 0
        char_offset = 0
        
        while char_offset < len(text):
            # Extract character window
            window_end = min(char_offset + char_window_size, len(text))
            raw_window = text[char_offset:window_end]
            
            # Expand to nearest sentence boundary to preserve context
            if window_end < len(text):
                sentence_end = self._find_sentence_boundary(raw_window)
                if sentence_end > 0:
                    raw_window = raw_window[:sentence_end]
            
            # Now tokenize just this window (memory-safe)
            tokens = self.tokenizer.encode(raw_window)
            
            # Handle case where window exceeds chunk_size
            if len(tokens) > self.chunk_size:
                tokens = tokens[:self.chunk_size]
                raw_window = self.tokenizer.decode(tokens)
            
            yield ChunkInfo(
                text=raw_window,
                token_count=len(tokens),
                start_offset=char_offset,
                end_offset=char_offset + len(raw_window),
                chunk_id=chunk_id
            )
            
            # Move to next window with overlap
            char_offset += len(raw_window) - overlap_chars
            if char_offset >= len(text):
                break
                
            chunk_id += 1
    
    def _find_sentence_boundary(self, text: str) -> int:
        """Find the last sentence boundary in text to preserve complete thoughts"""
        # Look for sentence endings in reverse order
        for match in re.finditer(r'[.!?]\s+', text):
            boundary_pos = match.end()
        
        # Return the last found boundary, or full text if no boundary found
        try:
            return boundary_pos
        except UnboundLocalError:
            return len(text)
        
    def estimate_chunks(self, text: str) -> int:
        """Refined estimation using realistic char/token ratio"""
        if not text.strip():
            return 0
        # Use 3.5 chars per token (more realistic than 4)
        estimated_tokens = len(text) / 3.5
        return max(1, int(estimated_tokens / (self.chunk_size - self.overlap)))
```

**Core Logic Flow:**
1. Guard against empty text in both APIs
2. Memory-safe approach: slice raw string into char windows first
3. Expand windows to sentence boundaries to preserve context
4. Tokenize only small windows (not entire document)
5. Handle token count limits and overlaps
6. Maintain offset mapping for reconstruction

### Day 1-2: ChunkInfo Data Structure

**File:** `deep_researcher/agents/utils/chunk_info.py`

```python
@dataclass
class ChunkInfo:
    text: str
    token_count: int
    start_offset: int
    end_offset: int
    chunk_id: int
    
    def __post_init__(self):
        if self.token_count <= 0:
            raise ValueError("Token count must be positive")
        if self.start_offset < 0:
            raise ValueError("Start offset cannot be negative")
        if self.end_offset <= self.start_offset:
            raise ValueError("End offset must be greater than start offset")
        if self.chunk_id < 0:
            raise ValueError("Chunk ID cannot be negative")
```

### Day 2: Unit Tests & Edge Cases

**File:** `tests/test_token_chunker.py`

```python
# Core functionality tests
def test_chunk_small_text()           # <800 tokens
def test_chunk_exactly_chunk_size()   # =800 tokens  
def test_chunk_large_text()           # >25k tokens
def test_overlap_handling()           # overlap logic
def test_empty_text()                 # edge case
def test_offset_mapping()             # reconstruction
def test_estimate_chunks()            # estimation accuracy

# API tests
def test_chunk_text_list_api()        # returns List[ChunkInfo]
def test_chunk_text_generator_api()   # yields ChunkInfo
def test_generator_memory_efficiency() # large text doesn't OOM

# Configuration tests  
def test_custom_chunk_size()          # non-default sizes
def test_custom_overlap()             # non-default overlap

# Memory safety tests
def test_memory_usage_smoke_test()    # RSS memory check on large text
def test_sentence_boundary_preservation() # complete thoughts preserved

# Validation tests
def test_chunk_info_validation()      # all __post_init__ checks
def test_tokenizer_consistency()      # same as summariser models
```

**Success Gate:** All tests pass, 100% coverage

### Day 2: Integration Preparation

**File:** `deep_researcher/agents/utils/__init__.py`

```python
from .token_chunker import TokenChunker
from .chunk_info import ChunkInfo
from .chunker_config import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP_TOKENS
```

**File:** `deep_researcher/llm_config.py` (update)

```python
def get_summariser_tokenizer():
    """Get exact same tokenizer used by summariser models"""
    # Return tokenizer instance that will be used by HYBRID-04 summariser
    # This ensures byte-for-byte consistency between chunking and summarisation
    pass
```

## Implementation Details

### Tokenizer Consistency
```python
# Ensure exact same tokenizer as summariser models
from deep_researcher.llm_config import get_summariser_tokenizer

class TokenChunker:
    def _get_consistent_tokenizer(self):
        """Critical: Must match HYBRID-04 summariser tokenizer exactly"""
        return get_summariser_tokenizer()  # Byte-for-byte consistency
```


### Memory Safety Implementation
```python
def test_memory_usage_smoke_test():
    """Simple RSS memory check without heavy dependencies"""
    import psutil, os
    
    # Create large text (25k+ tokens worth)
    large_text = "This is a test sentence. " * 10000  # ~25k tokens
    
    proc = psutil.Process(os.getpid())
    before_rss = proc.memory_info().rss
    
    chunker = TokenChunker()
    # Process with generator (should not spike memory)
    chunks = list(chunker.chunk_text_generator(large_text))
    
    after_rss = proc.memory_info().rss
    memory_delta = after_rss - before_rss
    
    # Assert memory increase is reasonable (< 50MB)
    assert memory_delta < 50 * 1024 * 1024, f"Memory spike too large: {memory_delta} bytes"
    assert len(chunks) > 1, "Should create multiple chunks"
```

## Success Criteria

**Must Pass CI:**
- `pytest tests/test_token_chunker.py` → Green
- 100% test coverage on TokenChunker and ChunkInfo
- Handle 25k+ token documents without memory issues
- Overlap logic maintains continuity between chunks

**Demo Checkpoints:**
- **Day 1:** TokenChunker class chunks text correctly
- **Day 2:** All edge cases tested, 100% coverage achieved

## Files to Create/Modify

```
deep_researcher/
├── agents/utils/
│   ├── token_chunker.py     # New - Core chunking logic with dual API
│   ├── chunk_info.py        # New - Data structure with validation
│   ├── chunker_config.py    # New - Configuration constants
│   └── __init__.py          # Modified - Add exports
└── llm_config.py            # Modified - Add get_summariser_tokenizer()

tests/
└── test_token_chunker.py    # New - Comprehensive unit tests
```

## Risk Mitigation

1. **Tokenizer Dependency Risk:** Use exact same tokenizer as summariser models for consistency
2. **Memory Risk:** String-slicing approach + RSS smoke test ensures true memory safety
3. **Context Preservation Risk:** Sentence boundary detection prevents mid-thought splits
4. **Code Bloat Risk:** Automated LoC check enforces 150-line limit
5. **Integration Risk:** Dual API provides flexibility for HYBRID-04 usage

## Testing Strategy

1. **Unit Tests:** All public methods, edge cases, empty text guards
2. **Memory Safety Tests:** RSS monitoring with psutil on 25k+ token documents
3. **Boundary Preservation Tests:** Verify sentences aren't split mid-thought
4. **Automated LoC Check:** CI pipeline enforces 150-line limit
5. **Integration Tests:** Tokenizer consistency with summariser models

## Definition of Done

- [ ] TokenChunker class implemented (≤150 LoC with automated check)
- [ ] ChunkInfo dataclass with enhanced validation
- [ ] Empty text guards in both APIs
- [ ] True memory safety via string-slicing approach
- [ ] Sentence boundary preservation implemented
- [ ] Unit tests achieve 100% coverage
- [ ] Memory smoke test passes (RSS delta < 50MB)
- [ ] Handles 25k+ token documents without OOM
- [ ] Tokenizer consistency with summariser models
- [ ] CI pipeline green with LoC enforcement
- [ ] Refined estimation algorithm (3.5 chars/token)

**Ready for HYBRID-04 Integration:** This utility provides the foundation for hierarchical summarization in the next ticket.

## Interface Contract for HYBRID-04

```python
# Option 1: List API (for smaller documents)
chunker = TokenChunker(chunk_size=800, overlap=100)
chunks = chunker.chunk_text(webpage_text)

summaries = []
for chunk in chunks:
    summary = fast_model.summarize(chunk.text)
    summaries.append(summary)

# Option 2: Generator API (for memory efficiency on large documents)
chunker = TokenChunker(chunk_size=1000, overlap=150)  # Custom sizing
for chunk in chunker.chunk_text_generator(large_webpage_text):
    summary = fast_model.summarize(chunk.text)
    # Process immediately without storing all chunks

# Option 3: Custom configuration for different use cases
chunker = TokenChunker(chunk_size=1200, overlap=200)  # Larger chunks for better context
```

## 🛠 Pre-Coding Checklist (Final Validation)

✅ **Memory Safety:** String-slicing approach prevents OOM on 25k+ tokens  
✅ **Context Preservation:** Sentence boundary detection maintains complete thoughts  
✅ **Empty Text Guards:** Both APIs handle blank inputs gracefully  
✅ **Simplified Config:** Removed redundant percentage helpers  
✅ **Refined Estimation:** 3.5 chars/token ratio for realistic estimates  
✅ **Automated LoC Check:** CI enforces 150-line limit  
✅ **Memory Smoke Test:** RSS monitoring with psutil  
✅ **Dual API:** List and Generator for maximum flexibility  

**Ready to start HYBRID-03?** This battle-tested plan delivers true memory safety and context preservation within the 2-day guardrail.