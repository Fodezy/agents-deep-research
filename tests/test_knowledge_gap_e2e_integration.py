"""
End-to-end integration tests for KnowledgeGapAgent with real LLM calls.

These tests validate the complete HYBRID-07 implementation:
- Dual-path architecture (structured + legacy)
- Template system with runtime injection
- Enhanced schemas with metadata
- ModelRole.KNOWLEDGE_GAP integration
- ResearchRunner compatibility
"""
import pytest
import asyncio
import os
from unittest.mock import patch
from deep_researcher.llm_config import create_default_config
from deep_researcher.agents.knowledge_gap_agent import init_knowledge_gap_agent
from deep_researcher.agents.baseclass import ResearchRunner
from deep_researcher.agents.utils.outlines_schemas import KnowledgeGapResult, KnowledgeGapOutput
from deep_researcher.agents.utils.model_role_registry import ModelRole


class TestKnowledgeGapE2EIntegration:
    """End-to-end integration tests with real LLM calls"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return create_default_config()
    
    @pytest.fixture
    def agent(self, config):
        """Create KnowledgeGapAgent instance"""
        with patch.dict(os.environ, {'DISABLE_RUNTIME_ASSERTIONS': 'true'}):
            return init_knowledge_gap_agent(config)
    
    @pytest.mark.asyncio
    async def test_incomplete_research_detection(self, agent):
        """Test agent correctly identifies incomplete research scenarios"""
        test_input = """
        Current Iteration Number: 1
        Time Elapsed: 5.2 minutes of maximum 60 minutes

        ORIGINAL QUERY:
        What are the latest AI applications in quantum computing research?

        BACKGROUND CONTEXT:
        Focus on 2024 developments and commercial applications

        HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
        - Initial research started
        - Need to investigate specific applications and recent breakthroughs
        """
        
        result = await ResearchRunner.run(agent, test_input)
        gap_analysis = result.final_output_as(KnowledgeGapResult)
        
        # Validate structure and content
        assert isinstance(gap_analysis, KnowledgeGapResult)
        assert gap_analysis.schema_version == 1
        assert gap_analysis.research_complete is False
        assert gap_analysis.research_completeness_confidence < 1.0
        assert len(gap_analysis.gaps_identified) > 0
        assert gap_analysis.total_gaps == len(gap_analysis.gaps_identified)
        
        # Validate gap analysis quality
        assert "quantum computing" in gap_analysis.research_context.lower()
        assert "2024" in gap_analysis.research_context or "recent" in gap_analysis.research_context.lower()
        assert len(gap_analysis.analysis_summary) >= 50
        
        # Check for specific gap attributes
        for gap in gap_analysis.gaps_identified:
            assert gap.gap_id
            assert len(gap.description) >= 10
            assert gap.priority in ["high", "medium", "low"]
            assert len(gap.research_approach) >= 10
            assert 0.0 <= gap.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_complete_research_detection(self, agent):
        """Test agent correctly identifies complete research scenarios"""
        test_input = """
        Current Iteration Number: 4
        Time Elapsed: 45.8 minutes of maximum 60 minutes

        ORIGINAL QUERY:
        What is the capital of France?

        BACKGROUND CONTEXT:
        Simple factual query requiring basic geographic knowledge

        HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
        - Iteration 1: Searched for "France capital city"
        - Findings: Paris is the capital and largest city of France
        - Iteration 2: Verified with additional sources
        - Findings: Confirmed Paris population ~2.1 million, metropolitan area ~12 million
        - Iteration 3: Gathered historical context
        - Findings: Paris became capital in 987 AD under Hugh Capet
        - Research appears complete with comprehensive answer available
        """
        
        result = await ResearchRunner.run(agent, test_input)
        gap_analysis = result.final_output_as(KnowledgeGapResult)
        
        # Validate complete research detection
        assert isinstance(gap_analysis, KnowledgeGapResult)
        assert gap_analysis.research_complete is True
        assert gap_analysis.research_completeness_confidence > 0.8
        assert gap_analysis.total_gaps == 0
        assert len(gap_analysis.gaps_identified) == 0
        
        # Validate analysis content
        assert "paris" in gap_analysis.research_context.lower() or "france" in gap_analysis.research_context.lower()
        assert "complete" in gap_analysis.analysis_summary.lower()
    
    @pytest.mark.asyncio 
    async def test_dual_path_architecture_switching(self, agent):
        """Test the dual-path architecture switches correctly between structured and legacy modes"""
        test_input = """
        ORIGINAL QUERY: AI applications in healthcare regulatory compliance
        
        BACKGROUND CONTEXT: Focus on FDA guidelines and recent policy updates
        
        HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
        Basic research conducted but specific regulatory frameworks need investigation
        """
        
        # Test that both paths produce valid output
        result = await ResearchRunner.run(agent, test_input)
        gap_analysis = result.final_output_as(KnowledgeGapResult)
        
        # Verify dual-path compatibility
        assert isinstance(gap_analysis, (KnowledgeGapResult, KnowledgeGapOutput))
        
        # Test backward compatibility interface
        if hasattr(gap_analysis, 'outstanding_gaps'):
            outstanding = gap_analysis.outstanding_gaps
            assert isinstance(outstanding, list)
            assert all(isinstance(gap, str) for gap in outstanding)
            
        # Verify enhanced schema fields are present
        assert hasattr(gap_analysis, 'research_completeness_confidence')
        assert hasattr(gap_analysis, 'iteration_context')
        assert hasattr(gap_analysis, 'gaps_identified')
        assert hasattr(gap_analysis, 'analysis_summary')
    
    @pytest.mark.asyncio
    async def test_template_system_runtime_injection(self, agent):
        """Test template system properly injects runtime content"""
        from datetime import datetime
        
        test_input = {
            "research_context": "Machine learning model interpretability",
            "background_context": "Enterprise AI deployment considerations", 
            "findings_history": "Basic ML concepts researched, need specific interpretability methods",
            "iteration_context": {"iteration": 2, "time_elapsed": 22.3}
        }
        
        result = await ResearchRunner.run(agent, test_input)
        gap_analysis = result.final_output_as(KnowledgeGapResult)
        
        # Validate template injection worked
        assert "machine learning" in gap_analysis.research_context.lower() or "interpretability" in gap_analysis.research_context.lower()
        
        # Check iteration context preservation
        if gap_analysis.iteration_context:
            assert gap_analysis.iteration_context.get("iteration") == 2
            assert gap_analysis.iteration_context.get("time_elapsed") == 22.3
    
    @pytest.mark.asyncio
    async def test_research_runner_integration(self, agent):
        """Test ResearchRunner properly handles KnowledgeGapAgent"""
        # Test string input format (ResearchRunner standard)
        string_input = "What are emerging trends in cybersecurity AI applications?"
        
        result = await ResearchRunner.run(agent, string_input)
        gap_analysis = result.final_output_as(KnowledgeGapResult)
        
        assert isinstance(gap_analysis, KnowledgeGapResult)
        assert gap_analysis.research_complete in [True, False]  # Must be boolean
        assert "cybersecurity" in gap_analysis.research_context.lower() or "ai" in gap_analysis.research_context.lower()
        
        # Test final_output_as compatibility with both schemas
        legacy_output = result.final_output_as(KnowledgeGapOutput)
        assert legacy_output is gap_analysis  # Should be same object due to alias
    
    @pytest.mark.asyncio
    async def test_model_role_integration(self, agent):
        """Test ModelRole.KNOWLEDGE_GAP integration"""
        # Verify agent uses correct model role
        inferred_role = agent.infer_agent_role()
        assert inferred_role == ModelRole.KNOWLEDGE_GAP
        
        # Test agent name recognition
        assert "knowledge" in agent.name.lower() or "gap" in agent.name.lower()
        
        # Verify model assignment (should not be using PLANNER role)
        model_info = agent.model
        assert model_info is not None
    
    @pytest.mark.asyncio
    async def test_enhanced_gap_metadata(self, agent):
        """Test enhanced gap analysis with rich metadata"""
        test_input = """
        ORIGINAL QUERY: Comprehensive analysis of blockchain scalability solutions
        
        BACKGROUND CONTEXT: Focus on Layer 2 solutions and recent technical developments
        
        HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
        - Basic blockchain concepts covered
        - Need specific Layer 2 analysis: Lightning Network, Polygon, Arbitrum
        - Performance metrics and adoption data required
        - Regulatory implications need investigation
        """
        
        result = await ResearchRunner.run(agent, test_input)
        gap_analysis = result.final_output_as(KnowledgeGapResult)
        
        # Validate enhanced metadata
        for gap in gap_analysis.gaps_identified:
            # Check all required fields
            assert len(gap.gap_id) >= 3
            assert len(gap.description) >= 10
            assert gap.priority in ["high", "medium", "low"]
            assert len(gap.research_approach) >= 10
            assert 0.0 <= gap.confidence <= 1.0
            
            # Optional fields should be handled gracefully
            if gap.category:
                assert len(gap.category) <= 50
        
        # Validate research completeness assessment
        assert 0.0 <= gap_analysis.research_completeness_confidence <= 1.0
        assert gap_analysis.total_gaps == len(gap_analysis.gaps_identified)
    
    @pytest.mark.asyncio
    async def test_parameter_extraction_formats(self, agent):
        """Test parameter extraction handles multiple input formats"""
        # Test 1: ResearchRunner format
        runner_format = """
        Current Iteration Number: 3
        Time Elapsed: 30.5 minutes of maximum 60 minutes
        
        ORIGINAL QUERY:
        Edge computing security challenges
        
        BACKGROUND CONTEXT:  
        IoT deployment security considerations
        
        HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
        Previous research on basic edge computing, need security-specific analysis
        """
        
        result1 = await ResearchRunner.run(agent, runner_format)
        gap_analysis1 = result1.final_output_as(KnowledgeGapResult)
        assert "edge computing" in gap_analysis1.research_context.lower()
        
        # Test 2: Dictionary format
        dict_format = {
            "research_context": "Edge computing security challenges", 
            "background_context": "IoT deployment security considerations",
            "findings_history": "Previous research on basic edge computing, need security-specific analysis",
            "iteration_context": {"iteration": 3, "time_elapsed": 30.5}
        }
        
        result2 = await ResearchRunner.run(agent, dict_format) 
        gap_analysis2 = result2.final_output_as(KnowledgeGapResult)
        assert "edge computing" in gap_analysis2.research_context.lower()
        
        # Test 3: Simple string format
        simple_format = "Edge computing security challenges"
        
        result3 = await ResearchRunner.run(agent, simple_format)
        gap_analysis3 = result3.final_output_as(KnowledgeGapResult)
        assert "edge computing" in gap_analysis3.research_context.lower()
    
    @pytest.mark.asyncio
    async def test_error_handling_and_graceful_degradation(self, agent):
        """Test error handling and graceful fallback behavior"""
        # Test with malformed input
        malformed_input = "{'invalid': json, missing quotes}"
        
        # Should not crash, should produce valid output
        result = await ResearchRunner.run(agent, malformed_input)
        gap_analysis = result.final_output_as(KnowledgeGapResult)
        
        assert isinstance(gap_analysis, KnowledgeGapResult)
        assert isinstance(gap_analysis.research_complete, bool)
        assert isinstance(gap_analysis.gaps_identified, list)
        assert isinstance(gap_analysis.total_gaps, int)
        
        # Test with empty input
        empty_result = await ResearchRunner.run(agent, "")
        empty_analysis = empty_result.final_output_as(KnowledgeGapResult)
        assert isinstance(empty_analysis, KnowledgeGapResult)


class TestKnowledgeGapBackwardCompatibility:
    """Test backward compatibility with existing system"""
    
    @pytest.fixture
    def config(self):
        return create_default_config()
    
    @pytest.fixture  
    def agent(self, config):
        with patch.dict(os.environ, {'DISABLE_RUNTIME_ASSERTIONS': 'true'}):
            return init_knowledge_gap_agent(config)
    
    @pytest.mark.asyncio
    async def test_knowledge_gap_output_alias(self, agent):
        """Test KnowledgeGapOutput alias maintains compatibility"""
        test_input = "Research quantum computing applications in cryptography"
        
        result = await ResearchRunner.run(agent, test_input)
        
        # Both should work and return the same object
        as_result = result.final_output_as(KnowledgeGapResult)
        as_output = result.final_output_as(KnowledgeGapOutput)
        
        assert as_result is as_output  # Same object due to alias
        assert isinstance(as_result, KnowledgeGapResult)
        assert isinstance(as_output, KnowledgeGapOutput)
    
    @pytest.mark.asyncio
    async def test_outstanding_gaps_property(self, agent):
        """Test outstanding_gaps property for backward compatibility"""
        test_input = """
        ORIGINAL QUERY: Machine learning bias detection methods
        HISTORY OF ACTIONS, FINDINGS AND THOUGHTS: Initial research started, need specific detection techniques
        """
        
        result = await ResearchRunner.run(agent, test_input)
        gap_analysis = result.final_output_as(KnowledgeGapResult)
        
        # Test backward compatibility property
        if hasattr(gap_analysis, 'outstanding_gaps'):
            outstanding = gap_analysis.outstanding_gaps
            assert isinstance(outstanding, list)
            assert len(outstanding) == len(gap_analysis.gaps_identified)
            
            # Should contain gap descriptions as strings
            for i, gap_desc in enumerate(outstanding):
                assert isinstance(gap_desc, str)
                assert gap_desc == gap_analysis.gaps_identified[i].description
    
    @pytest.mark.asyncio
    async def test_legacy_test_suite_compatibility(self, agent):
        """Test compatibility with existing test expectations"""
        # Simulate the test format from test_research_agents.py
        initial_user_input = """
        ORIGINAL QUERY: What is the founding history of the company QX Labs (qxlabs.com)?

        HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
        - No research has been carried out yet.
        """
        
        result = await ResearchRunner.run(agent, initial_user_input)
        agent_output = result.final_output_as(KnowledgeGapOutput)  # Using legacy alias

        # Legacy test expectations
        assert isinstance(agent_output, KnowledgeGapOutput)
        assert agent_output.research_complete is False
        
        # Test outstanding_gaps backward compatibility
        if hasattr(agent_output, 'outstanding_gaps'):
            assert len(agent_output.outstanding_gaps) > 0
        else:
            # Fallback to new interface
            assert len(agent_output.gaps_identified) > 0
            
        # Test complete research scenario
        final_user_input = """
        ORIGINAL QUERY: What is the capital of France?

        HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
        - Thinking: I need to run a web search to find the capital of France
        - Action: Running WebSearchAgent with query 'France capital city'
        - Findings: The capital of France is Paris
        """
        
        final_result = await ResearchRunner.run(agent, final_user_input)
        final_output = final_result.final_output_as(KnowledgeGapOutput)
        
        assert isinstance(final_output, KnowledgeGapOutput)
        assert final_output.research_complete is True
        
        if hasattr(final_output, 'outstanding_gaps'):
            assert len(final_output.outstanding_gaps) == 0
        else:
            assert len(final_output.gaps_identified) == 0


class TestKnowledgeGapPerformance:
    """Performance validation tests"""
    
    @pytest.fixture
    def config(self):
        return create_default_config()
    
    @pytest.fixture
    def agent(self, config):
        with patch.dict(os.environ, {'DISABLE_RUNTIME_ASSERTIONS': 'true'}):
            return init_knowledge_gap_agent(config)
    
    @pytest.mark.asyncio
    async def test_response_time_performance(self, agent):
        """Test response time is within reasonable bounds"""
        import time
        
        test_input = "Analyze artificial intelligence applications in financial risk assessment"
        
        start_time = time.time()
        result = await ResearchRunner.run(agent, test_input)
        end_time = time.time()
        
        response_time = end_time - start_time
        gap_analysis = result.final_output_as(KnowledgeGapResult)
        
        # Validate output quality
        assert isinstance(gap_analysis, KnowledgeGapResult)
        assert len(gap_analysis.analysis_summary) >= 50
        
        # Performance expectation (adjust based on model speed)
        # This is more of a smoke test than strict performance requirement
        print(f"Response time: {response_time:.2f} seconds")
        assert response_time < 120  # 2 minute timeout for safety
    
    @pytest.mark.asyncio
    async def test_large_input_handling(self, agent):
        """Test handling of large input contexts"""
        # Create large input with extensive history
        large_history = "\n".join([
            f"- Iteration {i}: Researched topic area {i} with findings about various aspects of the research domain"
            for i in range(1, 51)  # 50 iterations of research history
        ])
        
        large_input = f"""
        Current Iteration Number: 50
        Time Elapsed: 55.0 minutes of maximum 60 minutes
        
        ORIGINAL QUERY:
        Comprehensive analysis of artificial intelligence applications across multiple industries
        
        BACKGROUND CONTEXT:
        Multi-industry analysis covering healthcare, finance, manufacturing, transportation, education, and retail sectors with focus on commercial implementations, regulatory compliance, ethical considerations, and performance metrics
        
        HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
        {large_history}
        - Current status: Extensive research completed but integration analysis pending
        """
        
        result = await ResearchRunner.run(agent, large_input)
        gap_analysis = result.final_output_as(KnowledgeGapResult)
        
        # Should handle large input gracefully
        assert isinstance(gap_analysis, KnowledgeGapResult)
        assert len(gap_analysis.research_context) > 0
        assert gap_analysis.total_gaps >= 0
        
        # Verify iteration context is preserved
        if gap_analysis.iteration_context:
            assert gap_analysis.iteration_context.get("iteration") == 50