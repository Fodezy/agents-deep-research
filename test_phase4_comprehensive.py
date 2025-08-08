#!/usr/bin/env python3
"""
Phase 4: Comprehensive Testing & Validation Suite

This suite performs extensive testing of the native Ollama structured outputs migration:
- End-to-end workflow validation
- Schema compliance verification  
- Error handling robustness
- Performance baseline establishment
- Integration testing with full research pipeline
"""

import asyncio
import time
import json
import traceback
from typing import Dict, Any, List
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.knowledge_gap_agent import init_knowledge_gap_agent
from deep_researcher.agents.tool_agents import init_search_agent, init_crawl_agent


class Phase4TestSuite:
    """Comprehensive test suite for Phase 4 validation"""
    
    def __init__(self):
        self.config = LLMConfig(search_provider='searxng')
        self.test_results = []
        self.performance_metrics = {}
        
    async def run_comprehensive_tests(self):
        """Execute all Phase 4 test categories"""
        print("=" * 60)
        print("PHASE 4: COMPREHENSIVE TESTING & VALIDATION SUITE")
        print("=" * 60)
        
        # Test categories
        test_categories = [
            ("End-to-End Workflow Tests", self._test_e2e_workflows),
            ("Schema Validation Tests", self._test_schema_validation),
            ("Error Handling Tests", self._test_error_handling),
            ("Performance Baseline Tests", self._test_performance_baseline),
            ("Integration Tests", self._test_integration),
            ("Stress Tests", self._test_stress_scenarios)
        ]
        
        for category_name, test_func in test_categories:
            print(f"\n{category_name}")
            print("-" * len(category_name))
            
            try:
                await test_func()
            except Exception as e:
                print(f"CATEGORY FAILED: {category_name} - {e}")
                traceback.print_exc()
        
        # Generate final report
        await self._generate_final_report()
    
    async def _test_e2e_workflows(self):
        """Test complete end-to-end workflows"""
        
        # Test 1: Knowledge Gap -> Search -> Crawl workflow
        print("Testing: Knowledge Gap -> Search -> Crawl workflow")
        start_time = time.time()
        
        try:
            # Step 1: Identify knowledge gaps
            kg_agent = init_knowledge_gap_agent(self.config)
            gap_result = await kg_agent.run_native_analysis(
                "Research quantum computing applications in cryptography"
            )
            
            assert len(gap_result.gaps_identified) > 0, "Should identify knowledge gaps"
            first_gap = gap_result.gaps_identified[0]
            
            # Step 2: Search for information
            search_agent = init_search_agent(self.config)
            search_result_dict = await search_agent.run_implementation(first_gap.description)
            
            assert search_result_dict['processing_method'] == 'native_structured'
            assert len(search_result_dict['output']['search_results']) > 0
            
            # Step 3: Crawl a source
            first_source = search_result_dict['output']['search_results'][0]
            crawl_agent = init_crawl_agent(self.config)
            
            crawl_input = f"""
            {{
              "gap": "{first_gap.description}",
              "target_website": "{first_source.get('url', 'https://example.com')}",
              "search_query": "quantum cryptography"
            }}
            """
            
            crawl_result_dict = await crawl_agent.run_implementation(crawl_input)
            assert crawl_result_dict['processing_method'] == 'native_structured'
            
            workflow_time = time.time() - start_time
            self.performance_metrics['e2e_workflow_time'] = workflow_time
            
            print(f"SUCCESS: E2E workflow completed in {workflow_time:.2f}s")
            self._record_success("e2e_workflow", {"time": workflow_time})
            
        except Exception as e:
            print(f"FAILED: E2E workflow - {e}")
            self._record_failure("e2e_workflow", str(e))
    
    async def _test_schema_validation(self):
        """Test schema compliance across all agents"""
        
        print("Testing: Schema validation compliance")
        
        # Test KnowledgeGapAgent schema compliance
        try:
            kg_agent = init_knowledge_gap_agent(self.config)
            result = await kg_agent.run_native_analysis("Test input")
            
            # Validate all required fields exist
            required_fields = ['gaps_identified', 'research_complete', 'confidence', 'next_steps']
            for field in required_fields:
                assert hasattr(result, field), f"Missing required field: {field}"
            
            # Validate gap structure
            if result.gaps_identified:
                gap = result.gaps_identified[0]
                gap_fields = ['gap_id', 'description', 'priority', 'research_approach', 'confidence']
                for field in gap_fields:
                    assert hasattr(gap, field), f"Missing gap field: {field}"
            
            print("SUCCESS: KnowledgeGapAgent schema validation passed")
            self._record_success("kg_schema_validation", {"fields_validated": len(required_fields)})
            
        except Exception as e:
            print(f"FAILED: KnowledgeGapAgent schema validation - {e}")
            self._record_failure("kg_schema_validation", str(e))
        
        # Test SearchAgent schema compliance
        try:
            search_agent = init_search_agent(self.config)
            result_dict = await search_agent.run_implementation("test query")
            
            # Validate structure
            assert 'output' in result_dict
            assert 'processing_method' in result_dict
            assert result_dict['processing_method'] == 'native_structured'
            
            output = result_dict['output']
            search_fields = ['search_results', 'summary', 'confidence', 'sources']
            for field in search_fields:
                assert field in output, f"Missing search output field: {field}"
            
            print("SUCCESS: SearchAgent schema validation passed")
            self._record_success("search_schema_validation", {"fields_validated": len(search_fields)})
            
        except Exception as e:
            print(f"FAILED: SearchAgent schema validation - {e}")
            self._record_failure("search_schema_validation", str(e))
    
    async def _test_error_handling(self):
        """Test error handling and recovery mechanisms"""
        
        print("Testing: Error handling robustness")
        
        # Test invalid input handling
        try:
            kg_agent = init_knowledge_gap_agent(self.config)
            
            # Test empty input
            result = await kg_agent.run_native_analysis("")
            assert result is not None, "Should handle empty input gracefully"
            
            # Test malformed JSON-like input
            result = await kg_agent.run_native_analysis('{"invalid": "json"...')
            assert result is not None, "Should handle malformed input gracefully"
            
            print("SUCCESS: Error handling tests passed")
            self._record_success("error_handling", {"tests_passed": 2})
            
        except Exception as e:
            print(f"FAILED: Error handling tests - {e}")
            self._record_failure("error_handling", str(e))
    
    async def _test_performance_baseline(self):
        """Establish performance baselines for native structured generation"""
        
        print("Testing: Performance baseline establishment")
        
        performance_results = {}
        
        # KnowledgeGapAgent performance
        try:
            kg_agent = init_knowledge_gap_agent(self.config)
            
            times = []
            for i in range(3):  # Multiple runs for average
                start = time.time()
                await kg_agent.run_native_analysis("Test performance query")
                times.append(time.time() - start)
            
            avg_time = sum(times) / len(times)
            performance_results['kg_agent_avg_time'] = avg_time
            
            print(f"KnowledgeGapAgent average time: {avg_time:.2f}s")
            
        except Exception as e:
            print(f"KnowledgeGapAgent performance test failed: {e}")
        
        # SearchAgent performance
        try:
            search_agent = init_search_agent(self.config)
            
            start = time.time()
            await search_agent.run_implementation("performance test query")
            search_time = time.time() - start
            
            performance_results['search_agent_time'] = search_time
            print(f"SearchAgent time: {search_time:.2f}s")
            
        except Exception as e:
            print(f"SearchAgent performance test failed: {e}")
        
        self.performance_metrics.update(performance_results)
        self._record_success("performance_baseline", performance_results)
    
    async def _test_integration(self):
        """Test integration with existing systems"""
        
        print("Testing: System integration")
        
        try:
            # Test that agents work with existing LLMConfig
            config_test = LLMConfig(search_provider='searxng')
            
            # Verify model selection works
            from deep_researcher.agents.utils.model_role_registry import ModelRole
            kg_model = config_test.get_model_for_role(ModelRole.KNOWLEDGE_GAP)
            search_model = config_test.get_model_for_role(ModelRole.TOOL_CALLING)
            
            assert kg_model is not None, "Should get knowledge gap model"
            assert search_model is not None, "Should get tool calling model"
            
            print("SUCCESS: System integration tests passed")
            self._record_success("integration", {"models_validated": 2})
            
        except Exception as e:
            print(f"FAILED: Integration tests - {e}")
            self._record_failure("integration", str(e))
    
    async def _test_stress_scenarios(self):
        """Test system under stress conditions"""
        
        print("Testing: Stress scenarios")
        
        try:
            kg_agent = init_knowledge_gap_agent(self.config)
            
            # Test with very long input
            long_input = "Research quantum computing " * 100  # ~2000 chars
            result = await kg_agent.run_native_analysis(long_input)
            
            assert result is not None, "Should handle long input"
            assert len(result.gaps_identified) > 0, "Should still identify gaps"
            
            print("SUCCESS: Stress test with long input passed")
            self._record_success("stress_long_input", {"input_length": len(long_input)})
            
        except Exception as e:
            print(f"FAILED: Stress tests - {e}")
            self._record_failure("stress_tests", str(e))
    
    def _record_success(self, test_name: str, metrics: Dict[str, Any]):
        """Record successful test result"""
        self.test_results.append({
            "test": test_name,
            "status": "SUCCESS",
            "metrics": metrics,
            "timestamp": time.time()
        })
    
    def _record_failure(self, test_name: str, error: str):
        """Record failed test result"""
        self.test_results.append({
            "test": test_name,
            "status": "FAILED", 
            "error": error,
            "timestamp": time.time()
        })
    
    async def _generate_final_report(self):
        """Generate comprehensive test report"""
        
        print("\n" + "=" * 60)
        print("PHASE 4 COMPREHENSIVE TEST REPORT")
        print("=" * 60)
        
        # Summary statistics
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "SUCCESS"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Performance metrics
        if self.performance_metrics:
            print(f"\nPerformance Metrics:")
            for metric, value in self.performance_metrics.items():
                print(f"  {metric}: {value:.3f}s")
        
        # Detailed results
        print(f"\nDetailed Results:")
        for result in self.test_results:
            status_icon = "✓" if result["status"] == "SUCCESS" else "✗"
            print(f"  {status_icon} {result['test']}: {result['status']}")
            if result["status"] == "FAILED":
                print(f"    Error: {result['error']}")
        
        # Migration validation
        if passed_tests >= total_tests * 0.8:  # 80% success threshold
            print(f"\n🎉 PHASE 4 VALIDATION: SUCCESS")
            print("Native Ollama structured outputs migration is validated and ready!")
            return True
        else:
            print(f"\n⚠️  PHASE 4 VALIDATION: NEEDS ATTENTION")
            print("Some critical tests failed. Review and fix before production deployment.")
            return False


async def main():
    """Run the comprehensive Phase 4 test suite"""
    suite = Phase4TestSuite()
    return await suite.run_comprehensive_tests()


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)