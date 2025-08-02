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
            
        # For small text, just create one chunk
        if len(text) <= self.chunk_size * 4:
            tokens = self.tokenizer.encode(text)
            if len(tokens) <= self.chunk_size:
                yield ChunkInfo(
                    text=text,
                    token_count=len(tokens),
                    start_offset=0,
                    end_offset=len(text),
                    chunk_id=0
                )
                return
        
        # Memory-safe approach: slice raw string first, then tokenize windows
        char_window_size = self.chunk_size * 4  # rough chars per chunk estimate
        overlap_chars = min(self.overlap * 4, char_window_size // 2)  # Cap overlap
        
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
            advance = max(len(raw_window) - overlap_chars, 1)  # Ensure we always advance
            char_offset += advance
            if char_offset >= len(text):
                break
                
            chunk_id += 1
    
    def _find_sentence_boundary(self, text: str) -> int:
        """Find the last sentence boundary in text to preserve complete thoughts"""
        boundary_pos = len(text)  # Default to full text
        
        # Look for sentence endings in reverse order
        for match in re.finditer(r'[.!?]\s+', text):
            boundary_pos = match.end()
        
        return boundary_pos
        
    def estimate_chunks(self, text: str) -> int:
        """Refined estimation using realistic char/token ratio"""
        if not text.strip():
            return 0
        # Use 3.5 chars per token (more realistic than 4)
        estimated_tokens = len(text) / 3.5
        return max(1, int(estimated_tokens / (self.chunk_size - self.overlap)))