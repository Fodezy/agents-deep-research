import asyncio
import time
from typing import List, Dict, Any
from .token_chunker import TokenChunker
from .chunk_info import ChunkInfo


class HierarchicalSummariser:
    """
    Two-stage hierarchical summarization for large content:
    1. Fast model summarizes each chunk in parallel
    2. Slow model aggregates chunk summaries into final output
    
    Provides structured JSON output with detailed timing and error handling.
    """
    
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