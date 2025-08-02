import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock
from deep_researcher.agents.utils import HierarchicalSummariser


class MockResponse:
    """Mock response object for model.chat() calls"""
    def __init__(self, content: str):
        self.content = content


@pytest.fixture
def mock_fast_model():
    """Mock fast model for chunk summarization"""
    model = Mock()
    model.chat = AsyncMock(return_value=MockResponse("Fast model chunk summary"))
    return model


@pytest.fixture
def mock_slow_model():
    """Mock slow model for aggregation"""
    model = Mock()
    model.chat = AsyncMock(return_value=MockResponse("Slow model final summary"))
    return model


@pytest.fixture
def summariser(mock_fast_model, mock_slow_model):
    """Create HierarchicalSummariser with mocked models"""
    return HierarchicalSummariser(
        fast_model=mock_fast_model,
        slow_model=mock_slow_model,
        chunk_size=50,  # Small for testing
        overlap=10
    )


class TestHierarchicalSummariser:
    """Test core functionality of HierarchicalSummariser"""
    
    @pytest.mark.asyncio
    async def test_summariser_initialization(self, mock_fast_model, mock_slow_model):
        """Test basic setup and initialization"""
        summariser = HierarchicalSummariser(mock_fast_model, mock_slow_model)
        
        assert summariser.fast_model == mock_fast_model
        assert summariser.slow_model == mock_slow_model
        assert summariser.chunker is not None
        assert summariser.chunker.chunk_size == 800  # Default
    
    @pytest.mark.asyncio
    async def test_parallel_chunk_summarization(self, summariser, mock_fast_model):
        """Test that chunks are processed in parallel"""
        content = "This is test content. " * 100  # Multiple chunks
        
        result = await summariser.summarise_large_content(content, "test context")
        
        # Should have called fast model multiple times (once per chunk)
        assert mock_fast_model.chat.call_count > 1
        assert result["chunk_count"] > 1
        assert len(result["chunk_summaries"]) > 1
    
    @pytest.mark.asyncio
    async def test_summary_aggregation(self, summariser, mock_slow_model):
        """Test slow model aggregation"""
        content = "Test content for aggregation. " * 50
        
        result = await summariser.summarise_large_content(content, "test context")
        
        # Slow model should be called exactly once for aggregation
        assert mock_slow_model.chat.call_count == 1
        assert result["final_summary"] == "Slow model final summary"
    
    @pytest.mark.asyncio
    async def test_json_output_structure(self, summariser):
        """Test required JSON format with timing"""
        content = "Short test content."
        
        result = await summariser.summarise_large_content(content)
        
        # Verify required fields
        assert "final_summary" in result
        assert "chunk_count" in result
        assert "total_tokens" in result
        assert "chunk_summaries" in result
        assert "processing_metadata" in result
        
        # Verify metadata structure
        metadata = result["processing_metadata"]
        assert "processing_time_ms" in metadata
        assert "stage1_time_ms" in metadata
        assert "stage2_time_ms" in metadata
        assert "chunks_processed" in metadata
        assert "aggregation_method" in metadata
    
    @pytest.mark.asyncio
    async def test_30k_token_performance(self):
        """Test < 30s requirement with timing assertions"""
        # Create fast mock models for performance test
        mock_fast = Mock()
        mock_fast.chat = AsyncMock(return_value=MockResponse("chunk summary"))
        
        mock_slow = Mock()
        mock_slow.chat = AsyncMock(return_value=MockResponse("final summary"))
        
        summariser = HierarchicalSummariser(mock_fast, mock_slow)
        large_content = "This is a test sentence. " * 8000  # ~30k tokens
        
        start = time.time()
        result = await summariser.summarise_large_content(large_content)
        duration = time.time() - start
        
        assert duration < 30, f"Took {duration}s, expected < 30s"
        assert result["processing_metadata"]["processing_time_ms"] < 30000
    
    @pytest.mark.asyncio
    async def test_error_handling_and_fallback(self):
        """Test chunk failure handling with isolated errors"""
        # Mock fast model that fails on first call, succeeds on second
        mock_fast = Mock()
        mock_fast.chat = AsyncMock(side_effect=[Exception("API Error"), MockResponse("good summary")])
        
        mock_slow = Mock()
        mock_slow.chat = AsyncMock(return_value=MockResponse("final summary"))
        
        summariser = HierarchicalSummariser(mock_fast, mock_slow, chunk_size=20, overlap=5)
        content = "First chunk content. Second chunk content. " * 10  # Force 2 chunks
        
        result = await summariser.summarise_large_content(content)
        
        # Failed chunk should be isolated with error field
        chunk_summaries = result["chunk_summaries"]
        failed_chunk = next((cs for cs in chunk_summaries if cs.get("error")), None)
        assert failed_chunk is not None
        assert failed_chunk["summary"] is None
        assert "API Error" in failed_chunk["error"]
        
        # Final summary should still be generated from valid chunks
        assert result["final_summary"] == "final summary"
        assert mock_slow.chat.call_count == 1  # Aggregation still called
    
    @pytest.mark.asyncio
    async def test_model_call_counts(self):
        """Validate fast vs slow model usage patterns"""
        mock_fast = Mock()
        mock_fast.chat = AsyncMock(return_value=MockResponse("chunk summary"))
        
        mock_slow = Mock()
        mock_slow.chat = AsyncMock(return_value=MockResponse("final summary"))
        
        summariser = HierarchicalSummariser(mock_fast, mock_slow, chunk_size=30, overlap=5)
        content = "This creates multiple chunks of content. " * 20  # Multiple chunks
        
        result = await summariser.summarise_large_content(content)
        
        # Fast model called once per chunk, slow model called once total
        chunk_count = result["chunk_count"]
        assert mock_fast.chat.call_count == chunk_count
        assert mock_slow.chat.call_count == 1
    
    @pytest.mark.asyncio
    async def test_memory_efficiency(self, summariser):
        """Test that large content doesn't cause memory issues"""
        large_content = "Large content test. " * 5000  # Large but manageable
        
        result = await summariser.summarise_large_content(large_content)
        
        # Should complete without memory errors
        assert result["chunk_count"] > 0
        assert "final_summary" in result
    
    @pytest.mark.asyncio
    async def test_empty_content_handling(self, summariser):
        """Test handling of empty or very small content"""
        result = await summariser.summarise_large_content("")
        
        # Should handle gracefully
        assert result["chunk_count"] == 0
        assert result["total_tokens"] == 0


class TestHierarchicalSummariserIntegration:
    """Integration tests for summariser with real components"""
    
    @pytest.mark.asyncio
    async def test_with_real_chunker(self, mock_fast_model, mock_slow_model):
        """Test integration with actual TokenChunker"""
        summariser = HierarchicalSummariser(mock_fast_model, mock_slow_model)
        content = "Real integration test content. " * 100
        
        result = await summariser.summarise_large_content(content, "integration test")
        
        # Should use actual chunker behavior
        assert result["chunk_count"] >= 1
        assert all(cs["token_count"] > 0 for cs in result["chunk_summaries"])
    
    @pytest.mark.asyncio
    async def test_context_passing(self, mock_fast_model, mock_slow_model):
        """Test that context is properly passed to models"""
        summariser = HierarchicalSummariser(mock_fast_model, mock_slow_model)
        content = "Test content for context passing."
        context = "Test research context"
        
        await summariser.summarise_large_content(content, context)
        
        # Verify context was passed in prompts
        fast_call_args = mock_fast_model.chat.call_args_list[0][0][0][0]["content"]
        slow_call_args = mock_slow_model.chat.call_args_list[0][0][0][0]["content"]
        
        assert context in fast_call_args
        assert context in slow_call_args


class TestConfigurationAndCustomization:
    """Test different configuration options"""
    
    @pytest.mark.asyncio
    async def test_custom_chunk_sizes(self, mock_fast_model, mock_slow_model):
        """Test custom chunk size and overlap"""
        summariser = HierarchicalSummariser(
            mock_fast_model, mock_slow_model,
            chunk_size=100, overlap=20
        )
        
        assert summariser.chunker.chunk_size == 100
        assert summariser.chunker.overlap == 20
    
    @pytest.mark.asyncio
    async def test_different_model_configurations(self):
        """Test with different model mock configurations"""
        fast_model = Mock()
        fast_model.chat = AsyncMock(return_value=MockResponse("fast response"))
        
        slow_model = Mock()
        slow_model.chat = AsyncMock(return_value=MockResponse("slow response"))
        
        summariser = HierarchicalSummariser(fast_model, slow_model)
        result = await summariser.summarise_large_content("test content")
        
        assert result["final_summary"] == "slow response"