"""
Outlines-based Structured Hierarchical Summarizer for SLICE-9-01.
Produces structured JSON outputs instead of prose, with full ValidationWrapper integration.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from .token_chunker import TokenChunker
from .chunk_info import ChunkInfo
from .outlines_schemas import StructuredSummary, ChunkSummaryItem, summarise_content_structured, summarise_chunk_structured
from .validation_wrapper import ValidationWrapper
from .validation_config import ValidationConfig
from .validation_logging import get_validation_logger, validation_context
from ...llm_config import model_supports_structured_output

# Graceful Outlines import for dual-path architecture
try:
    import outlines
    OUTLINES_AVAILABLE = True
except ImportError:
    outlines = None
    OUTLINES_AVAILABLE = False
    print("[StructuredSummariser] Outlines not available, using legacy mode only")


class StructuredHierarchicalSummariser:
    """
    Outlines-based hierarchical summarizer that produces structured JSON outputs.
    
    Two-stage process:
    1. Fast model summarizes each chunk with structured output (parallel)
    2. Slow model aggregates chunk summaries into final structured summary
    
    Provides ValidationWrapper integration for auto-repair and observability.
    """
    
    def __init__(self, fast_model, slow_model, chunk_size: int = 800, overlap: int = 100):
        self.fast_model = fast_model
        self.slow_model = slow_model
        self.chunker = TokenChunker(chunk_size, overlap)
        self.logger = get_validation_logger()
        
        # Initialize structured generation capabilities
        self.supports_structured = (
            model_supports_structured_output(fast_model) and 
            model_supports_structured_output(slow_model) and 
            OUTLINES_AVAILABLE
        )
        
        # Initialize Outlines generators if supported
        self.fast_generator = None
        self.slow_generator = None
        
        if self.supports_structured and OUTLINES_AVAILABLE:
            try:
                # Fast model generator for chunk summarization
                chunk_schema = ChunkSummaryItem.model_json_schema()
                self.fast_generator = outlines.Generator(fast_model, chunk_schema)
                
                # Slow model generator for final summarization
                summary_schema = StructuredSummary.model_json_schema()
                self.slow_generator = outlines.Generator(slow_model, summary_schema)
                
                print(f"[StructuredSummariser] Outlines generators initialized")
            except Exception as e:
                print(f"[StructuredSummariser] Outlines initialization failed: {e}, falling back to legacy")
                self.supports_structured = False
        
        # Initialize ValidationWrapper for structured outputs
        self.validation_config = ValidationConfig(
            enabled=True,
            max_retries=2,
            timeout_ms=30000
        )
        
        self.chunk_validator = ValidationWrapper(
            agent_name="StructuredSummariser_Chunk",
            schema=ChunkSummaryItem,
            config=self.validation_config
        )
        
        self.summary_validator = ValidationWrapper(
            agent_name="StructuredSummariser_Final",
            schema=StructuredSummary,
            config=self.validation_config
        )
    
    async def summarise_large_content(self, content: str, context: str = "", sources: List[str] = None) -> Dict[str, Any]:
        """
        Two-stage structured summarization with ValidationWrapper integration.
        
        Returns:
            Dict with StructuredSummary format including validation metadata
        """
        with validation_context("StructuredSummariser", "summarise_large_content") as logger:
            start_time = time.time()
            
            # Stage 1: Chunk and parallel structured summarization
            chunks = self.chunker.chunk_text(content)
            logger.logger.info("structured_summarization_start", extra={
                "chunk_count": len(chunks),
                "total_tokens": sum(c.token_count for c in chunks),
                "supports_structured": self.supports_structured
            })
            
            # Parallel chunk processing
            tasks = [
                self._summarize_chunk_structured(chunk, context)
                for chunk in chunks
            ]
            chunk_summaries = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process chunk results
            structured_chunks = []
            failed_chunks = 0
            
            for i, (chunk, result) in enumerate(zip(chunks, chunk_summaries)):
                if isinstance(result, Exception):
                    failed_chunks += 1
                    logger.logger.warning("chunk_summarization_failed", extra={
                        "chunk_id": chunk.chunk_id,
                        "error": str(result)
                    })
                    # Create error chunk summary
                    structured_chunks.append({
                        "chunk_id": chunk.chunk_id,
                        "summary": None,
                        "key_points": [],
                        "token_count": chunk.token_count,
                        "error": str(result)
                    })
                else:
                    structured_chunks.append(result)
            
            stage1_time = time.time()
            
            # Stage 2: Aggregate with structured final summary
            final_summary = await self._aggregate_structured_summaries(
                structured_chunks, context, sources or []
            )
            
            end_time = time.time()
            
            # Add processing metadata
            processing_metadata = {
                "chunks_processed": len(structured_chunks),
                "failed_chunks": failed_chunks,
                "aggregation_method": "structured_slow_model",
                "processing_time_ms": int((end_time - start_time) * 1000),
                "stage1_time_ms": int((stage1_time - start_time) * 1000),
                "stage2_time_ms": int((end_time - stage1_time) * 1000),
                "supports_structured": self.supports_structured,
                "validation_enabled": True
            }
            
            final_summary["processing_metadata"] = processing_metadata
            final_summary["chunk_summaries"] = structured_chunks  # For debugging
            
            logger.logger.info("structured_summarization_complete", extra={
                "processing_time_ms": processing_metadata["processing_time_ms"],
                "chunk_count": len(chunks),
                "failed_chunks": failed_chunks,
                "confidence": final_summary.get("confidence", 0.0)
            })
            
            return final_summary
    
    async def _summarize_chunk_structured(self, chunk: ChunkInfo, context: str) -> Dict[str, Any]:
        """Structured summarization of a single chunk with validation"""
        start_time = time.time()
        
        if self.supports_structured and self.fast_generator:
            return await self._chunk_structured_path(chunk, context, start_time)
        else:
            return await self._chunk_legacy_path(chunk, context, start_time)
    
    async def _chunk_structured_path(self, chunk: ChunkInfo, context: str, start_time: float) -> Dict[str, Any]:
        """Outlines-based structured chunk summarization"""
        try:
            # Generate structured prompt for chunk summarization
            prompt = f"""Summarize this content chunk with structured output. Extract key points and provide a concise summary.

Context: {context}

Chunk Content (ID: {chunk.chunk_id}):
{chunk.text}

Provide structured summary with key points:"""
            
            # Generate with Outlines
            response = self.fast_generator.generate(prompt)
            
            # Create structured chunk summary
            processing_time_ms = int((time.time() - start_time) * 1000)
            result = {
                "chunk_id": chunk.chunk_id,
                "summary": response.get("summary", ""),
                "key_points": response.get("key_points", []),
                "token_count": chunk.token_count,
                "processing_time_ms": processing_time_ms,
                "error": None
            }
            
            # Validate structured output
            validated_result = await self.chunk_validator.validate_and_repair(
                llm_response=str(result),
                model_client=self.fast_model
            )
            
            # Return validated result or original if validation failed
            if validated_result.get("processing_method") != "error_fallback":
                return validated_result
            else:
                return result
            
        except Exception as e:
            self.logger.logger.error("chunk_structured_path_failed", extra={
                "chunk_id": chunk.chunk_id,
                "error": str(e)
            })
            # Fallback to legacy path
            return await self._chunk_legacy_path(chunk, context, start_time)
    
    async def _chunk_legacy_path(self, chunk: ChunkInfo, context: str, start_time: float) -> Dict[str, Any]:
        """Legacy chunk summarization with structured output format"""
        try:
            prompt = f"""Summarize this content chunk and extract key points. Return in this JSON format:
{{
    "summary": "2-3 sentence summary",
    "key_points": ["point 1", "point 2", "point 3"]
}}

Context: {context}

Chunk Content:
{chunk.text}

JSON Response:"""
            
            response = await self.fast_model.chat([{"role": "user", "content": prompt}])
            raw_output = response.content.strip()
            
            # Parse JSON response
            import json
            try:
                parsed = json.loads(raw_output)
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                return {
                    "chunk_id": chunk.chunk_id,
                    "summary": parsed.get("summary", ""),
                    "key_points": parsed.get("key_points", []),
                    "token_count": chunk.token_count,
                    "processing_time_ms": processing_time_ms,
                    "error": None
                }
            except json.JSONDecodeError:
                # Fallback to simple string summary
                return {
                    "chunk_id": chunk.chunk_id,
                    "summary": raw_output[:500],  # Truncate if too long
                    "key_points": [],
                    "token_count": chunk.token_count,
                    "processing_time_ms": int((time.time() - start_time) * 1000),
                    "error": "json_parse_fallback"
                }
                
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            return {
                "chunk_id": chunk.chunk_id,
                "summary": None,
                "key_points": [],
                "token_count": chunk.token_count,
                "processing_time_ms": processing_time_ms,
                "error": str(e)
            }
    
    async def _aggregate_structured_summaries(self, chunk_summaries: List[Dict], 
                                            context: str, sources: List[str]) -> Dict[str, Any]:
        """Aggregate chunk summaries into final structured summary"""
        start_time = time.time()
        
        if self.supports_structured and self.slow_generator:
            return await self._aggregate_structured_path(chunk_summaries, context, sources, start_time)
        else:
            return await self._aggregate_legacy_path(chunk_summaries, context, sources, start_time)
    
    async def _aggregate_structured_path(self, chunk_summaries: List[Dict], 
                                       context: str, sources: List[str], start_time: float) -> Dict[str, Any]:
        """Outlines-based structured aggregation"""
        try:
            # Filter valid summaries
            valid_summaries = [cs for cs in chunk_summaries if cs.get('summary')]
            
            # Collect all key points
            all_key_points = []
            summaries_text = []
            
            for cs in valid_summaries:
                if cs.get('summary'):
                    summaries_text.append(f"Chunk {cs['chunk_id']}: {cs['summary']}")
                if cs.get('key_points'):
                    all_key_points.extend(cs['key_points'])
            
            prompt = f"""Create a comprehensive structured summary by combining these chunk summaries.

Context: {context}

Chunk Summaries:
{chr(10).join(summaries_text)}

All Key Points:
{chr(10).join([f"- {point}" for point in all_key_points[:20]])}  # Limit to top 20

Provide a structured summary with comprehensive output and refined key findings:"""
            
            # Generate with Outlines
            response = self.slow_generator.generate(prompt)
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Create structured summary
            result = {
                "output": response.get("output", ""),
                "key_findings": response.get("key_findings", []),
                "sources": sources,
                "confidence": response.get("confidence", 0.9),
                "processing_metadata": {
                    "processing_time_ms": processing_time_ms,
                    "method": "structured_aggregation"
                }
            }
            
            # Validate final summary
            validated_result = await self.summary_validator.validate_and_repair(
                llm_response=str(result),
                model_client=self.slow_model
            )
            
            # Return validated result or fallback
            if validated_result.get("processing_method") != "error_fallback":
                return validated_result
            else:
                return result
                
        except Exception as e:
            self.logger.logger.error("aggregate_structured_path_failed", extra={
                "error": str(e),
                "context": context
            })
            return await self._aggregate_legacy_path(chunk_summaries, context, sources, start_time)
    
    async def _aggregate_legacy_path(self, chunk_summaries: List[Dict], 
                                   context: str, sources: List[str], start_time: float) -> Dict[str, Any]:
        """Legacy aggregation with structured output format"""
        try:
            # Filter valid summaries
            valid_summaries = [cs for cs in chunk_summaries if cs.get('summary')]
            
            summaries_text = "\n".join([
                f"Chunk {cs['chunk_id']}: {cs['summary']}" 
                for cs in valid_summaries
            ])
            
            # Collect key points
            all_key_points = []
            for cs in chunk_summaries:
                if cs.get('key_points'):
                    all_key_points.extend(cs['key_points'])
            
            prompt = f"""Create a comprehensive summary and extract key findings. Return in this JSON format:
{{
    "output": "3-4 paragraph comprehensive summary",
    "key_findings": ["finding 1", "finding 2", "finding 3"],
    "confidence": 0.9
}}

Context: {context}

Summaries to combine:
{summaries_text}

JSON Response:"""
            
            response = await self.slow_model.chat([{"role": "user", "content": prompt}])
            raw_output = response.content.strip()
            
            # Parse JSON response
            import json
            try:
                parsed = json.loads(raw_output)
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                return {
                    "output": parsed.get("output", "Summary processing completed"),
                    "key_findings": parsed.get("key_findings", all_key_points[:5]),  # Top 5 findings
                    "sources": sources,
                    "confidence": parsed.get("confidence", 0.8),
                    "processing_metadata": {
                        "processing_time_ms": processing_time_ms,
                        "method": "legacy_aggregation"
                    }
                }
                
            except json.JSONDecodeError:
                # Fallback to basic structure
                processing_time_ms = int((time.time() - start_time) * 1000)
                return {
                    "output": raw_output[:1500],  # Truncate if too long
                    "key_findings": all_key_points[:5] if all_key_points else ["Summary generated"],
                    "sources": sources,
                    "confidence": 0.7,  # Lower confidence for fallback
                    "processing_metadata": {
                        "processing_time_ms": processing_time_ms,
                        "method": "legacy_fallback"
                    }
                }
                
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            return {
                "output": f"Summary processing failed: {e}",
                "key_findings": ["Processing error occurred"],
                "sources": sources,
                "confidence": 0.1,
                "processing_metadata": {
                    "processing_time_ms": processing_time_ms,
                    "method": "error_fallback"
                }
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get summarizer status for monitoring"""
        return {
            "supports_structured": self.supports_structured,
            "outlines_available": OUTLINES_AVAILABLE,
            "fast_generator_initialized": self.fast_generator is not None,
            "slow_generator_initialized": self.slow_generator is not None,
            "validation_enabled": True,
            "chunk_size": self.chunker.chunk_size,
            "overlap": self.chunker.overlap
        }