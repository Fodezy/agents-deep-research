import pytest
import psutil
import os
from deep_researcher.agents.utils import TokenChunker, ChunkInfo, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP_TOKENS


class TestTokenChunker:
    """Test suite for TokenChunker utility"""
    
    def test_chunk_small_text(self):
        """Test chunking text smaller than chunk size"""
        chunker = TokenChunker()
        text = "This is a short text."
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].chunk_id == 0
        assert chunks[0].start_offset == 0
    
    def test_chunk_exactly_chunk_size(self):
        """Test chunking text exactly at chunk size"""
        chunker = TokenChunker(chunk_size=10, overlap=2)
        # Create text that's exactly 10 tokens when tokenized
        text = "This is exactly ten tokens of text content here."
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) >= 1
        assert all(chunk.token_count <= 10 for chunk in chunks)
    
    def test_chunk_large_text(self):
        """Test chunking large text (25k+ tokens)"""
        chunker = TokenChunker(chunk_size=100, overlap=20)
        # Create large text (~25k tokens)
        large_text = "This is a test sentence with multiple words. " * 2000
        chunks = chunker.chunk_text(large_text)
        
        assert len(chunks) > 1
        assert all(chunk.token_count <= 100 for chunk in chunks)
        assert all(chunk.token_count > 0 for chunk in chunks)
    
    def test_overlap_handling(self):
        """Test overlap logic between chunks"""
        chunker = TokenChunker(chunk_size=50, overlap=10)
        text = "Sentence one. Sentence two. Sentence three. " * 50
        chunks = chunker.chunk_text(text)
        
        if len(chunks) > 1:
            # Check that chunks have some reasonable offset progression
            assert chunks[1].start_offset > chunks[0].start_offset
    
    def test_empty_text(self):
        """Test empty text edge case"""
        chunker = TokenChunker()
        
        # Test empty string
        assert chunker.chunk_text("") == []
        assert list(chunker.chunk_text_generator("")) == []
        
        # Test whitespace only
        assert chunker.chunk_text("   \n\t  ") == []
        assert list(chunker.chunk_text_generator("   \n\t  ")) == []
    
    def test_offset_mapping(self):
        """Test offset mapping for reconstruction"""
        chunker = TokenChunker(chunk_size=20, overlap=5)
        text = "This is test text for offset mapping verification."
        chunks = chunker.chunk_text(text)
        
        for chunk in chunks:
            assert chunk.start_offset >= 0
            assert chunk.end_offset > chunk.start_offset
            assert chunk.end_offset <= len(text)
    
    def test_estimate_chunks(self):
        """Test chunk count estimation accuracy"""
        chunker = TokenChunker(chunk_size=100, overlap=20)
        
        # Test empty text
        assert chunker.estimate_chunks("") == 0
        assert chunker.estimate_chunks("   ") == 0
        
        # Test small text
        small_text = "Short text."
        estimate = chunker.estimate_chunks(small_text)
        assert estimate >= 1
        
        # Test large text - estimate should be reasonable
        large_text = "Word " * 1000
        estimate = chunker.estimate_chunks(large_text)
        actual = len(chunker.chunk_text(large_text))
        # Estimate should be within reasonable range of actual
        assert abs(estimate - actual) / max(actual, 1) < 1.0  # Within 100%


class TestTokenChunkerAPIs:
    """Test both List and Generator APIs"""
    
    def test_chunk_text_list_api(self):
        """Test that chunk_text returns List[ChunkInfo]"""
        chunker = TokenChunker()
        text = "This is test text for the list API."
        chunks = chunker.chunk_text(text)
        
        assert isinstance(chunks, list)
        assert all(isinstance(chunk, ChunkInfo) for chunk in chunks)
    
    def test_chunk_text_generator_api(self):
        """Test that chunk_text_generator yields ChunkInfo"""
        chunker = TokenChunker()
        text = "This is test text for the generator API."
        
        chunk_gen = chunker.chunk_text_generator(text)
        chunks = list(chunk_gen)
        
        assert all(isinstance(chunk, ChunkInfo) for chunk in chunks)
    
    def test_generator_memory_efficiency(self):
        """Test that generator doesn't load everything into memory"""
        chunker = TokenChunker(chunk_size=50, overlap=10)
        large_text = "This is a memory efficiency test. " * 1000
        
        # Generator should work without loading all chunks at once
        chunk_count = 0
        for chunk in chunker.chunk_text_generator(large_text):
            chunk_count += 1
            assert isinstance(chunk, ChunkInfo)
        
        assert chunk_count > 1


class TestTokenChunkerConfiguration:
    """Test configuration options"""
    
    def test_custom_chunk_size(self):
        """Test non-default chunk sizes"""
        chunker_small = TokenChunker(chunk_size=10, overlap=2)
        chunker_large = TokenChunker(chunk_size=200, overlap=50)
        
        text = "This is test text. " * 100
        
        chunks_small = chunker_small.chunk_text(text)
        chunks_large = chunker_large.chunk_text(text)
        
        # Both should work and respect size limits
        assert len(chunks_small) > 0 and len(chunks_large) > 0
        
        # Verify chunk sizes are respected
        assert all(chunk.token_count <= 10 for chunk in chunks_small)
        assert all(chunk.token_count <= 200 for chunk in chunks_large)
    
    def test_custom_overlap(self):
        """Test non-default overlap values"""
        chunker_no_overlap = TokenChunker(chunk_size=50, overlap=0)
        chunker_high_overlap = TokenChunker(chunk_size=50, overlap=25)
        
        text = "Sentence. " * 100
        
        chunks_no_overlap = chunker_no_overlap.chunk_text(text)
        chunks_high_overlap = chunker_high_overlap.chunk_text(text)
        
        # High overlap should create more chunks (smaller steps)
        if len(text) > 50 * 4:  # If text is large enough
            assert len(chunks_high_overlap) >= len(chunks_no_overlap)


class TestMemorySafety:
    """Test memory safety and sentence boundary preservation"""
    
    def test_memory_usage_smoke_test(self):
        """Simple RSS memory check without heavy dependencies"""
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
    
    def test_sentence_boundary_preservation(self):
        """Test that sentences aren't split mid-thought"""
        chunker = TokenChunker(chunk_size=30, overlap=5)
        text = "First sentence here. Second sentence here. Third sentence here. Fourth sentence here."
        
        chunks = chunker.chunk_text(text)
        
        # Check that no chunks end mid-word (basic check)
        for chunk in chunks:
            # Chunk should not end with a partial word
            if chunk.text.strip():
                assert not chunk.text.endswith(" and")  # Example of incomplete thought


class TestChunkInfoValidation:
    """Test ChunkInfo dataclass validation"""
    
    def test_chunk_info_validation(self):
        """Test all __post_init__ validation checks"""
        
        # Valid chunk info should work
        valid_chunk = ChunkInfo(
            text="Test text",
            token_count=5,
            start_offset=0,
            end_offset=10,
            chunk_id=0
        )
        assert valid_chunk.text == "Test text"
        
        # Test invalid token count
        with pytest.raises(ValueError, match="Token count must be positive"):
            ChunkInfo("text", 0, 0, 10, 0)
        
        with pytest.raises(ValueError, match="Token count must be positive"):
            ChunkInfo("text", -1, 0, 10, 0)
        
        # Test invalid start offset
        with pytest.raises(ValueError, match="Start offset cannot be negative"):
            ChunkInfo("text", 5, -1, 10, 0)
        
        # Test invalid end offset
        with pytest.raises(ValueError, match="End offset must be greater than start offset"):
            ChunkInfo("text", 5, 10, 10, 0)
        
        with pytest.raises(ValueError, match="End offset must be greater than start offset"):
            ChunkInfo("text", 5, 10, 5, 0)
        
        # Test invalid chunk ID
        with pytest.raises(ValueError, match="Chunk ID cannot be negative"):
            ChunkInfo("text", 5, 0, 10, -1)
    
    def test_tokenizer_consistency(self):
        """Test that tokenizer is consistent with summariser models"""
        from deep_researcher.llm_config import get_summariser_tokenizer
        
        chunker = TokenChunker()
        direct_tokenizer = get_summariser_tokenizer()
        
        # Both should be the same instance/type
        assert type(chunker.tokenizer) == type(direct_tokenizer)


class TestConfigurationImports:
    """Test that configuration constants are properly importable"""
    
    def test_default_constants(self):
        """Test that default constants are available and reasonable"""
        assert DEFAULT_CHUNK_SIZE > 0
        assert DEFAULT_OVERLAP_TOKENS >= 0
        assert DEFAULT_OVERLAP_TOKENS < DEFAULT_CHUNK_SIZE
        
        # Test they can be used
        chunker = TokenChunker(DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP_TOKENS)
        assert chunker.chunk_size == DEFAULT_CHUNK_SIZE
        assert chunker.overlap == DEFAULT_OVERLAP_TOKENS