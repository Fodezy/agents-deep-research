"""
Performance benchmark suite for ValidationWrapper system.
Measures latency, throughput, and resource usage under various conditions.
"""

import asyncio
import time
import json
import statistics
import psutil
import gc
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock

from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.utils.validation_wrapper import ValidationWrapper
from deep_researcher.agents.utils.validation_config import ValidationConfig
from deep_researcher.agents.utils.outlines_schemas import EnhancedToolAgentOutput
from deep_researcher.agents.utils.agent_factory import get_agent_factory


class PerformanceBenchmark:
    """Performance benchmarking suite for ValidationWrapper"""
    
    def __init__(self):
        self.results = {}
        self.config = LLMConfig(search_provider='searxng')
    
    async def benchmark_basic_validation(self, iterations: int = 1000) -> Dict[str, float]:
        """Benchmark basic validation performance"""
        print(f"\n=== Basic Validation Benchmark ({iterations} iterations) ===")
        
        config = ValidationConfig(enabled=True, max_retries=1)
        wrapper = ValidationWrapper(
            agent_name="BenchmarkAgent",
            schema=EnhancedToolAgentOutput,
            config=config
        )
        
        valid_json = json.dumps({
            "output": "Benchmark test output for performance validation",
            "sources": ["https://benchmark.com", "https://test.com"]
        })
        
        # Warm up
        for _ in range(10):
            await wrapper.validate_and_repair(valid_json)
        
        # Measure performance
        times = []
        start_total = time.perf_counter()
        
        for _ in range(iterations):
            start = time.perf_counter()
            result = await wrapper.validate_and_repair(valid_json)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        
        end_total = time.perf_counter()
        total_time = (end_total - start_total) * 1000
        
        stats = {
            "total_time_ms": total_time,
            "avg_latency_ms": statistics.mean(times),
            "median_latency_ms": statistics.median(times),
            "p95_latency_ms": statistics.quantiles(times, n=20)[18],  # 95th percentile
            "p99_latency_ms": statistics.quantiles(times, n=100)[98],  # 99th percentile
            "max_latency_ms": max(times),
            "min_latency_ms": min(times),
            "throughput_ops_per_sec": iterations / (total_time / 1000),
            "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0
        }
        
        print(f"  Average latency: {stats['avg_latency_ms']:.2f}ms")
        print(f"  P95 latency: {stats['p95_latency_ms']:.2f}ms")
        print(f"  P99 latency: {stats['p99_latency_ms']:.2f}ms")
        print(f"  Throughput: {stats['throughput_ops_per_sec']:.1f} ops/sec")
        
        return stats
    
    async def benchmark_repair_performance(self, iterations: int = 100) -> Dict[str, float]:
        """Benchmark repair mechanism performance"""
        print(f"\n=== Repair Performance Benchmark ({iterations} iterations) ===")
        
        config = ValidationConfig(enabled=True, max_retries=2)
        wrapper = ValidationWrapper(
            agent_name="RepairBenchmark",
            schema=EnhancedToolAgentOutput,
            config=config
        )
        
        # Various malformed JSON scenarios
        test_cases = [
            # Markdown fences
            '''```json
            {"output": "Test with markdown fences", "sources": []}
            ```''',
            
            # Trailing comma
            '{"output": "Test with trailing comma", "sources": [],}',
            
            # Single quotes
            "{'output': 'Single quotes test', 'sources': []}",
            
            # Missing quotes
            '{"output": Test missing quotes, "sources": []}',
            
            # Extra commas
            '{"output": "Extra commas test",, "sources": []}',
        ]
        
        all_times = []
        repair_methods = {}
        
        for test_case in test_cases:
            case_times = []
            
            for _ in range(iterations // len(test_cases)):
                start = time.perf_counter()
                result = await wrapper.validate_and_repair(test_case)
                end = time.perf_counter()
                
                duration = (end - start) * 1000
                case_times.append(duration)
                all_times.append(duration)
                
                # Track repair methods used
                method = result.get("processing_method", "unknown")
                repair_methods[method] = repair_methods.get(method, 0) + 1
        
        stats = {
            "avg_repair_latency_ms": statistics.mean(all_times),
            "median_repair_latency_ms": statistics.median(all_times),
            "p95_repair_latency_ms": statistics.quantiles(all_times, n=20)[18],
            "max_repair_latency_ms": max(all_times),
            "min_repair_latency_ms": min(all_times),
            "repair_methods_used": repair_methods
        }
        
        print(f"  Average repair latency: {stats['avg_repair_latency_ms']:.2f}ms")
        print(f"  P95 repair latency: {stats['p95_repair_latency_ms']:.2f}ms")
        print(f"  Repair methods: {repair_methods}")
        
        return stats
    
    async def benchmark_circuit_breaker_overhead(self, iterations: int = 1000) -> Dict[str, float]:
        """Benchmark circuit breaker overhead"""
        print(f"\n=== Circuit Breaker Overhead Benchmark ({iterations} iterations) ===")
        
        # Test with circuit breaker enabled
        config_with_cb = ValidationConfig(enabled=True, max_retries=1)
        wrapper_with_cb = ValidationWrapper(
            agent_name="CBBenchmark",
            schema=EnhancedToolAgentOutput,
            config=config_with_cb
        )
        
        # Test with validation disabled (baseline)
        config_disabled = ValidationConfig(enabled=False)
        wrapper_disabled = ValidationWrapper(
            agent_name="DisabledBenchmark",
            schema=EnhancedToolAgentOutput,
            config=config_disabled
        )
        
        valid_json = json.dumps({
            "output": "Circuit breaker overhead test",
            "sources": ["https://test.com"]
        })
        
        # Benchmark with circuit breaker
        cb_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await wrapper_with_cb.validate_and_repair(valid_json)
            end = time.perf_counter()
            cb_times.append((end - start) * 1000)
        
        # Benchmark with validation disabled
        disabled_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await wrapper_disabled.validate_and_repair(valid_json)
            end = time.perf_counter()
            disabled_times.append((end - start) * 1000)
        
        cb_avg = statistics.mean(cb_times)
        disabled_avg = statistics.mean(disabled_times)
        overhead_percent = ((cb_avg - disabled_avg) / disabled_avg) * 100
        
        stats = {
            "circuit_breaker_avg_ms": cb_avg,
            "disabled_avg_ms": disabled_avg,
            "overhead_ms": cb_avg - disabled_avg,
            "overhead_percent": overhead_percent
        }
        
        print(f"  Circuit breaker enabled: {cb_avg:.2f}ms")
        print(f"  Validation disabled: {disabled_avg:.2f}ms")
        print(f"  Overhead: {overhead_percent:.1f}%")
        
        return stats
    
    async def benchmark_agent_integration(self, iterations: int = 50) -> Dict[str, float]:
        """Benchmark full agent integration performance"""
        print(f"\n=== Agent Integration Benchmark ({iterations} iterations) ===")
        
        factory = get_agent_factory()
        
        # Test different agent types
        agent_types = ['search', 'crawl', 'planner']
        results = {}
        
        for agent_type in agent_types:
            print(f"  Testing {agent_type} agent...")
            
            try:
                # Create validated agent
                agent = factory.create_agent(
                    agent_type=agent_type,
                    config=self.config,
                    enable_validation=True
                )
                
                # Mock the underlying execution to avoid actual API calls
                if hasattr(agent, 'base_agent') and hasattr(agent.base_agent, 'run_implementation'):
                    original_method = agent.base_agent.run_implementation
                    
                    async def mock_implementation(*args, **kwargs):
                        return {
                            "output": f"Mock {agent_type} agent output with reasonable length content",
                            "sources": ["https://mock1.com", "https://mock2.com"]
                        }
                    
                    agent.base_agent.run_implementation = mock_implementation
                
                # Benchmark agent execution
                times = []
                for _ in range(iterations):
                    start = time.perf_counter()
                    result = await agent.run_implementation("test input")
                    end = time.perf_counter()
                    times.append((end - start) * 1000)
                
                results[agent_type] = {
                    "avg_latency_ms": statistics.mean(times),
                    "p95_latency_ms": statistics.quantiles(times, n=20)[18],
                    "max_latency_ms": max(times),
                    "validation_enabled": getattr(agent, 'validation_enabled', False)
                }
                
                print(f"    Average: {results[agent_type]['avg_latency_ms']:.2f}ms")
                
            except Exception as e:
                print(f"    Failed to benchmark {agent_type}: {e}")
                results[agent_type] = {"error": str(e)}
        
        return results
    
    def benchmark_memory_usage(self) -> Dict[str, float]:
        """Benchmark memory usage of ValidationWrapper"""
        print(f"\n=== Memory Usage Benchmark ===")
        
        process = psutil.Process()
        
        # Get baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create multiple ValidationWrappers
        wrappers = []
        num_wrappers = 100
        
        for i in range(num_wrappers):
            config = ValidationConfig(enabled=True)
            wrapper = ValidationWrapper(
                agent_name=f"MemoryTest_{i}",
                schema=EnhancedToolAgentOutput,
                config=config
            )
            wrappers.append(wrapper)
        
        after_creation = process.memory_info().rss / 1024 / 1024  # MB
        
        # Use the wrappers
        for wrapper in wrappers[:10]:  # Use subset to avoid too much processing
            wrapper.circuit_breaker.record_success()
            wrapper.circuit_breaker.record_failure("test")
        
        after_usage = process.memory_info().rss / 1024 / 1024  # MB
        
        # Clean up
        del wrappers
        gc.collect()
        after_cleanup = process.memory_info().rss / 1024 / 1024  # MB
        
        stats = {
            "baseline_memory_mb": baseline_memory,
            "after_creation_mb": after_creation,
            "after_usage_mb": after_usage,
            "after_cleanup_mb": after_cleanup,
            "memory_per_wrapper_kb": (after_creation - baseline_memory) * 1024 / num_wrappers,
            "memory_growth_mb": after_usage - baseline_memory,
            "memory_leak_mb": after_cleanup - baseline_memory
        }
        
        print(f"  Baseline memory: {baseline_memory:.1f}MB")
        print(f"  After creating {num_wrappers} wrappers: {after_creation:.1f}MB")
        print(f"  Memory per wrapper: {stats['memory_per_wrapper_kb']:.1f}KB")
        print(f"  Memory leak after cleanup: {stats['memory_leak_mb']:.1f}MB")
        
        return stats
    
    async def benchmark_concurrent_operations(self, concurrent_ops: int = 50) -> Dict[str, float]:
        """Benchmark concurrent validation operations"""
        print(f"\n=== Concurrent Operations Benchmark ({concurrent_ops} concurrent ops) ===")
        
        config = ValidationConfig(enabled=True, max_retries=1)
        wrapper = ValidationWrapper(
            agent_name="ConcurrentBenchmark",
            schema=EnhancedToolAgentOutput,
            config=config
        )
        
        valid_json = json.dumps({
            "output": "Concurrent operation test output",
            "sources": ["https://concurrent-test.com"]
        })
        
        async def single_operation():
            start = time.perf_counter()
            result = await wrapper.validate_and_repair(valid_json)
            end = time.perf_counter()
            return (end - start) * 1000, result
        
        # Run concurrent operations
        start_total = time.perf_counter()
        tasks = [single_operation() for _ in range(concurrent_ops)]
        results = await asyncio.gather(*tasks)
        end_total = time.perf_counter()
        
        times = [r[0] for r in results]
        total_time = (end_total - start_total) * 1000
        
        stats = {
            "concurrent_operations": concurrent_ops,
            "total_time_ms": total_time,
            "avg_operation_time_ms": statistics.mean(times),
            "max_operation_time_ms": max(times),
            "throughput_ops_per_sec": concurrent_ops / (total_time / 1000),
            "concurrency_efficiency": (statistics.mean(times) * concurrent_ops) / total_time
        }
        
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Average operation time: {stats['avg_operation_time_ms']:.2f}ms") 
        print(f"  Throughput: {stats['throughput_ops_per_sec']:.1f} ops/sec")
        print(f"  Concurrency efficiency: {stats['concurrency_efficiency']:.2f}")
        
        return stats
    
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all performance benchmarks"""
        print("ValidationWrapper Performance Benchmark Suite")
        print("=" * 50)
        
        all_results = {}
        
        try:
            all_results["basic_validation"] = await self.benchmark_basic_validation(1000)
            all_results["repair_performance"] = await self.benchmark_repair_performance(100)
            all_results["circuit_breaker_overhead"] = await self.benchmark_circuit_breaker_overhead(1000)
            all_results["agent_integration"] = await self.benchmark_agent_integration(50)
            all_results["memory_usage"] = self.benchmark_memory_usage()
            all_results["concurrent_operations"] = await self.benchmark_concurrent_operations(50)
            
        except Exception as e:
            print(f"Benchmark failed: {e}")
            import traceback
            traceback.print_exc()
        
        return all_results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print benchmark summary"""
        print(f"\n" + "=" * 50)
        print("PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 50)
        
        if "basic_validation" in results:
            basic = results["basic_validation"]
            print(f"Basic Validation:")
            print(f"  Average latency: {basic['avg_latency_ms']:.2f}ms")
            print(f"  P95 latency: {basic['p95_latency_ms']:.2f}ms")
            print(f"  Throughput: {basic['throughput_ops_per_sec']:.1f} ops/sec")
        
        if "repair_performance" in results:
            repair = results["repair_performance"] 
            print(f"\nRepair Performance:")
            print(f"  Average repair latency: {repair['avg_repair_latency_ms']:.2f}ms")
            print(f"  P95 repair latency: {repair['p95_repair_latency_ms']:.2f}ms")
        
        if "circuit_breaker_overhead" in results:
            cb = results["circuit_breaker_overhead"]
            print(f"\nCircuit Breaker Overhead:")
            print(f"  Overhead: {cb['overhead_percent']:.1f}%")
        
        if "memory_usage" in results:
            memory = results["memory_usage"]
            print(f"\nMemory Usage:")
            print(f"  Per wrapper: {memory['memory_per_wrapper_kb']:.1f}KB")
            print(f"  Memory leak: {memory['memory_leak_mb']:.1f}MB")
        
        if "concurrent_operations" in results:
            concurrent = results["concurrent_operations"]
            print(f"\nConcurrent Operations:")
            print(f"  Throughput: {concurrent['throughput_ops_per_sec']:.1f} ops/sec")
            print(f"  Efficiency: {concurrent['concurrency_efficiency']:.2f}")
        
        # Performance targets validation
        print(f"\n" + "=" * 30)
        print("PERFORMANCE TARGET VALIDATION")
        print("=" * 30)
        
        targets_met = []
        
        if "basic_validation" in results:
            basic = results["basic_validation"]
            if basic['avg_latency_ms'] < 50:
                targets_met.append("[PASS] Average latency < 50ms")
            else:
                targets_met.append(f"[FAIL] Average latency {basic['avg_latency_ms']:.2f}ms > 50ms")
            
            if basic['p95_latency_ms'] < 100:
                targets_met.append("[PASS] P95 latency < 100ms")
            else:
                targets_met.append(f"[FAIL] P95 latency {basic['p95_latency_ms']:.2f}ms > 100ms")
        
        if "circuit_breaker_overhead" in results:
            cb = results["circuit_breaker_overhead"]
            if cb['overhead_percent'] < 20:
                targets_met.append("[PASS] Circuit breaker overhead < 20%")
            else:
                targets_met.append(f"[FAIL] Circuit breaker overhead {cb['overhead_percent']:.1f}% > 20%")
        
        if "memory_usage" in results:
            memory = results["memory_usage"]
            if memory['memory_leak_mb'] < 5:
                targets_met.append("[PASS] Memory leak < 5MB")
            else:
                targets_met.append(f"[FAIL] Memory leak {memory['memory_leak_mb']:.1f}MB > 5MB")
        
        for target in targets_met:
            print(f"  {target}")
        
        pass_count = sum(1 for t in targets_met if "[PASS]" in t)
        total_count = len(targets_met)
        
        print(f"\nOverall: {pass_count}/{total_count} targets met ({pass_count/total_count*100:.1f}%)")


async def main():
    """Run performance benchmarks"""
    benchmark = PerformanceBenchmark()
    results = await benchmark.run_all_benchmarks()
    benchmark.print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())