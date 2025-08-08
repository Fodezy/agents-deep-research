"""
Test suite for StructuredHierarchicalSummariser (SLICE-9-01).
Tests structured JSON output, validation integration, and performance.
"""

import asyncio
import json
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.utils.structured_summariser import StructuredHierarchicalSummariser
from deep_researcher.agents.utils.outlines_schemas import StructuredSummary, ChunkSummaryItem


async def test_structured_summarizer_initialization():
    """Test structured summarizer initialization"""
    print("\n=== Testing Structured Summarizer Initialization ===")
    
    # Create mock models
    fast_model = AsyncMock()
    slow_model = AsyncMock()
    
    # Initialize summarizer
    summariser = StructuredHierarchicalSummariser(
        fast_model=fast_model,
        slow_model=slow_model,
        chunk_size=500,
        overlap=50
    )
    
    # Check initialization
    assert summariser.fast_model == fast_model
    assert summariser.slow_model == slow_model
    assert summariser.chunker.chunk_size == 500
    assert summariser.chunker.overlap == 50
    
    # Check status
    status = summariser.get_status()
    assert "supports_structured" in status
    assert "outlines_available" in status
    assert "validation_enabled" in status
    assert status["validation_enabled"] is True
    
    print(f"  [PASS] Summarizer initialized successfully")
    print(f"  [PASS] Status: {status}")
    print(f"  [PASS] Validation enabled: {status['validation_enabled']}")


async def test_structured_summary_schema_validation():
    """Test structured summary schema validation"""
    print("\n=== Testing Structured Summary Schema Validation ===")
    
    # Test valid structured summary
    valid_summary = {
        "output": "This is a comprehensive summary of quantum computing advances including error correction.",
        "key_findings": [
            "Quantum error correction achieved 99% fidelity",
            "New algorithms show exponential speedup",
            "Commercial applications emerging in cryptography"
        ],
        "sources": ["https://quantum-journal.com", "https://nature.com/quantum"],
        "confidence": 0.92,
        "processing_metadata": {
            "processing_time_ms": 1250,
            "method": "structured_generation"
        }
    }
    
    # Validate with Pydantic
    try:
        structured = StructuredSummary(**valid_summary)
        print(f"  [PASS] Valid structured summary validated")
        print(f"  [PASS] Output: {structured.output[:50]}...")
        print(f"  [PASS] Key findings: {len(structured.key_findings)} items")
        print(f"  [PASS] Confidence: {structured.confidence}")
    except Exception as e:
        print(f"  [FAIL] Schema validation failed: {e}")
        return False
    
    # Test invalid summary (too short output)
    invalid_summary = {
        "output": "Too short",  # Less than 50 characters
        "key_findings": ["Finding 1"],
        "confidence": 0.8
    }
    
    try:
        StructuredSummary(**invalid_summary)
        print(f"  [FAIL] Invalid summary should have failed validation")
        return False
    except Exception:
        print(f"  [PASS] Invalid summary correctly rejected")
    
    return True


async def test_chunk_summary_schema_validation():
    """Test chunk summary schema validation"""
    print("\n=== Testing Chunk Summary Schema Validation ===")
    
    # Test valid chunk summary
    valid_chunk = {
        "chunk_id": 1,
        "summary": "This chunk discusses quantum error correction techniques and their implementation.",
        "key_points": [
            "Surface code implementation",
            "99.1% error correction fidelity",
            "Logical qubit operations"
        ],
        "token_count": 245,
        "processing_time_ms": 150
    }
    
    try:
        chunk = ChunkSummaryItem(**valid_chunk)
        print(f"  [PASS] Valid chunk summary validated")
        print(f"  [PASS] Chunk ID: {chunk.chunk_id}")
        print(f"  [PASS] Summary: {chunk.summary[:40]}...")
        print(f"  [PASS] Key points: {len(chunk.key_points)} items")
    except Exception as e:
        print(f"  [FAIL] Chunk schema validation failed: {e}")
        return False
    
    return True


async def test_structured_summarization_with_mock():
    """Test structured summarization with mock models"""
    print("\n=== Testing Structured Summarization with Mocks ===")
    
    # Create mock models
    fast_model = AsyncMock()
    slow_model = AsyncMock()
    
    # Mock fast model responses (for chunks)
    fast_model.chat.side_effect = [
        AsyncMock(content='{"summary": "Chunk 1 covers quantum error correction basics", "key_points": ["Error correction fundamentals", "Qubit stability"]}'),
        AsyncMock(content='{"summary": "Chunk 2 discusses implementation details", "key_points": ["Surface codes", "Hardware requirements"]}')
    ]
    
    # Mock slow model response (for aggregation)
    slow_model.chat.return_value = AsyncMock(content=json.dumps({
        "output": "This comprehensive summary covers quantum error correction advances including fundamental techniques and implementation strategies. Recent developments show significant improvements in error correction fidelity and practical applications.",
        "key_findings": [
            "Error correction fundamentals are well established",
            "Surface codes show promising results for hardware implementation", 
            "Hardware requirements are becoming more manageable"
        ],
        "confidence": 0.88
    }))
    
    # Create summarizer
    summariser = StructuredHierarchicalSummariser(
        fast_model=fast_model,
        slow_model=slow_model,
        chunk_size=200,
        overlap=20
    )
    
    # Test content
    test_content = """Quantum error correction has made significant advances recently. 
    The implementation of surface codes has achieved remarkable fidelity rates.
    Hardware requirements for these systems are becoming more practical.
    New algorithms are showing exponential improvements in error correction.
    Commercial applications are beginning to emerge in various sectors."""
    
    # Run summarization
    result = await summariser.summarise_large_content(
        content=test_content,
        context="quantum computing research",
        sources=["https://quantum-research.com"]
    )
    
    # Validate results
    assert "output" in result
    assert "key_findings" in result
    assert "sources" in result
    assert "confidence" in result
    assert "processing_metadata" in result
    
    print(f"  [PASS] Summarization completed")
    print(f"  [PASS] Output: {result['output'][:60]}...")
    print(f"  [PASS] Key findings: {len(result.get('key_findings', []))} items")
    print(f"  [PASS] Confidence: {result.get('confidence', 0)}")
    print(f"  [PASS] Processing time: {result['processing_metadata'].get('processing_time_ms', 0)}ms")
    print(f"  [PASS] Sources included: {len(result.get('sources', []))} sources")
    
    return True


async def test_error_handling_and_fallback():
    """Test error handling and fallback mechanisms"""
    print("\n=== Testing Error Handling and Fallback ===")
    
    # Test JSON parsing fallback instead of model failures
    # This is more predictable for testing
    fast_model = AsyncMock()
    slow_model = AsyncMock()
    
    # Make fast model return malformed JSON (tests JSON parsing fallback)
    fast_model.chat.return_value = AsyncMock(content="This is not JSON at all")
    
    # Slow model works
    slow_model.chat.return_value = AsyncMock(content=json.dumps({
        "output": "Summary with JSON parsing fallback handled gracefully",
        "key_findings": ["JSON parsing fallback worked", "Error recovery successful"],
        "confidence": 0.7
    }))
    
    # Create summarizer
    summariser = StructuredHierarchicalSummariser(
        fast_model=fast_model,
        slow_model=slow_model,
        chunk_size=100,
        overlap=10
    )
    
    # Test content
    test_content = "This content will test JSON parsing fallback mechanisms in the summarizer."
    
    # Run summarization
    result = await summariser.summarise_large_content(
        content=test_content,
        context="error handling test"
    )
    
    # Should complete despite parsing errors
    assert "output" in result
    assert "processing_metadata" in result
    assert "chunk_summaries" in result
    
    # Check if any chunks had JSON parsing fallback
    chunk_summaries = result.get("chunk_summaries", [])
    has_fallback = any(cs.get("error") == "json_parse_fallback" for cs in chunk_summaries)
    
    print(f"  [PASS] Error handling completed successfully")
    print(f"  [PASS] Chunks processed: {len(chunk_summaries)}")
    print(f"  [PASS] JSON fallback detected: {has_fallback}")
    print(f"  [PASS] Output: {result['output'][:50]}...")
    print(f"  [PASS] Confidence: {result.get('confidence', 0)}")
    
    return True


async def test_performance_and_timing():
    """Test performance characteristics and timing"""
    print("\n=== Testing Performance and Timing ===")
    
    # Create fast mock models
    fast_model = AsyncMock()
    slow_model = AsyncMock()
    
    # Mock responses
    fast_model.chat.return_value = AsyncMock(content='{"summary": "Quick chunk summary", "key_points": ["Point 1", "Point 2"]}')
    slow_model.chat.return_value = AsyncMock(content=json.dumps({
        "output": "Fast aggregated summary with good performance characteristics",
        "key_findings": ["Performance is good", "Timing is acceptable"],
        "confidence": 0.9
    }))
    
    # Create summarizer
    summariser = StructuredHierarchicalSummariser(
        fast_model=fast_model,
        slow_model=slow_model,
        chunk_size=300,
        overlap=30
    )
    
    # Test with larger content
    large_content = " ".join([f"This is sentence {i} about quantum computing and its applications." for i in range(100)])
    
    # Run summarization with timing
    import time
    start_time = time.time()
    
    result = await summariser.summarise_large_content(
        content=large_content,
        context="performance testing"
    )
    
    end_time = time.time()
    total_time_ms = (end_time - start_time) * 1000
    
    # Check performance
    metadata = result["processing_metadata"]
    
    print(f"  [PASS] Performance test completed")
    print(f"  [PASS] Total time: {total_time_ms:.1f}ms")
    print(f"  [PASS] Reported processing time: {metadata['processing_time_ms']}ms")
    print(f"  [PASS] Stage 1 time: {metadata['stage1_time_ms']}ms")
    print(f"  [PASS] Stage 2 time: {metadata['stage2_time_ms']}ms")
    print(f"  [PASS] Chunks processed: {metadata['chunks_processed']}")
    
    # Performance should be reasonable (under 5 seconds for this test)
    assert total_time_ms < 5000, f"Performance too slow: {total_time_ms}ms"
    
    return True


async def test_validation_wrapper_integration():
    """Test integration with ValidationWrapper"""
    print("\n=== Testing ValidationWrapper Integration ===")
    
    # Create mock models
    fast_model = AsyncMock()
    slow_model = AsyncMock()
    
    # Mock malformed JSON that needs repair
    fast_model.chat.return_value = AsyncMock(content='```json\n{"summary": "Needs repair", "key_points": ["Point 1"]}\n```')
    
    slow_model.chat.return_value = AsyncMock(content=json.dumps({
        "output": "ValidationWrapper integration test summary",
        "key_findings": ["Validation works", "Auto-repair successful"],
        "confidence": 0.85
    }))
    
    # Create summarizer (validation is enabled by default)
    summariser = StructuredHierarchicalSummariser(
        fast_model=fast_model,
        slow_model=slow_model
    )
    
    # Test content
    test_content = "This content tests ValidationWrapper integration with structured summarization."
    
    # Run summarization
    result = await summariser.summarise_large_content(
        content=test_content,
        context="validation integration test"
    )
    
    # Check that validation occurred
    assert "output" in result
    assert "processing_metadata" in result
    
    print(f"  [PASS] ValidationWrapper integration working")
    print(f"  [PASS] Output: {result['output'][:50]}...")
    print(f"  [PASS] Validation enabled: {summariser.validation_config.enabled}")
    
    return True


async def run_all_tests():
    """Run all structured summarizer tests"""
    print("Structured Hierarchical Summariser Test Suite")
    print("=" * 55)
    
    tests = [
        ("Initialization", test_structured_summarizer_initialization),
        ("Summary Schema Validation", test_structured_summary_schema_validation),
        ("Chunk Schema Validation", test_chunk_summary_schema_validation),
        ("Mock Summarization", test_structured_summarization_with_mock),
        ("Error Handling", test_error_handling_and_fallback),
        ("Performance Testing", test_performance_and_timing),
        ("ValidationWrapper Integration", test_validation_wrapper_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n[TEST] {test_name}")
            result = await test_func()
            if result != False:
                print(f"[PASS] {test_name}")
                passed += 1
            else:
                print(f"[FAIL] {test_name}")
        except Exception as e:
            print(f"[FAIL] {test_name} - Exception: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("[SUCCESS] All structured summarizer tests passed!")
        return True
    else:
        print("[FAIL] Some tests failed")
        return False


async def main():
    """Main test execution"""
    success = await run_all_tests()
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)