"""Integration tests for the refactored KnowledgeGapAgent"""
import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from deep_researcher.llm_config import create_default_config
from deep_researcher.agents.knowledge_gap_agent import init_knowledge_gap_agent
from deep_researcher.agents.utils.outlines_schemas import KnowledgeGapResult, KnowledgeGapOutput, KnowledgeGap
from deep_researcher.agents.utils.outlines_templates import extract_knowledge_gap_params
from deep_researcher.agents.utils.model_role_registry import ModelRole


class TestKnowledgeGapAgentIntegration:
    """Test KnowledgeGapAgent integration with dual-path architecture"""
    
    def test_agent_initialization_legacy_path(self):
        """Test agent initializes correctly with legacy path"""
        # Disable runtime assertions for clean testing
        with patch.dict(os.environ, {'DISABLE_RUNTIME_ASSERTIONS': 'true'}):
            config = create_default_config()
            agent = init_knowledge_gap_agent(config)
            
            # Verify basic agent properties
            assert agent.name == "KnowledgeGapAgent"
            assert agent.model is not None
            assert agent.instructions == ""  # Placeholder in legacy path
            assert agent._dynamic_instructions is not None  # Dynamic instructions function
            assert callable(agent._dynamic_instructions)  # Should be callable
            assert agent.output_type is None  # Legacy path
            assert agent.output_parser is not None
            assert agent.structured_generator is None  # No Outlines
    
    def test_agent_role_inference(self):
        """Test that agent role is properly inferred as KNOWLEDGE_GAP"""
        with patch.dict(os.environ, {'DISABLE_RUNTIME_ASSERTIONS': 'true'}):
            config = create_default_config()
            agent = init_knowledge_gap_agent(config)
            
            inferred_role = agent.infer_agent_role()
            assert inferred_role == ModelRole.KNOWLEDGE_GAP
            assert inferred_role.value == "knowledge_gap"
    
    def test_dynamic_instructions_generation(self):
        """Test that dynamic instructions are generated properly"""
        with patch.dict(os.environ, {'DISABLE_RUNTIME_ASSERTIONS': 'true'}):
            config = create_default_config()
            agent = init_knowledge_gap_agent(config)
            
            # Test with simple string input
            test_input = "What are AI applications in healthcare?"
            instructions = agent._dynamic_instructions(test_input)
            
            assert isinstance(instructions, str)
            assert "Knowledge Gap Analyzer" in instructions
            assert "AI applications in healthcare" in instructions
            assert "JSON object" in instructions  # Legacy prompt format
            assert "schema_version" in instructions
            assert "research_complete" in instructions
            assert "gaps_identified" in instructions
            
            # Verify runtime date injection
            from datetime import datetime
            current_date = datetime.now().strftime('%Y-%m-%d')
            assert current_date in instructions
    
    def test_dynamic_instructions_with_structured_input(self):
        """Test dynamic instructions with ResearchRunner formatted input"""
        with patch.dict(os.environ, {'DISABLE_RUNTIME_ASSERTIONS': 'true'}):
            config = create_default_config()
            agent = init_knowledge_gap_agent(config)
            
            # Test with structured ResearchRunner format
            structured_input = """
            Current Iteration Number: 3
            Time Elapsed: 45.2 minutes of maximum 60 minutes
            
            ORIGINAL QUERY:
            What are the latest AI applications in healthcare?
            
            BACKGROUND CONTEXT:
            Focus on regulatory compliance and FDA guidelines
            
            HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
            Previous research covered basic AI concepts but needs specific healthcare applications
            """
            
            instructions = agent._dynamic_instructions(structured_input)
            
            assert "AI applications in healthcare" in instructions
            assert "regulatory compliance" in instructions
            assert "specific healthcare applications" in instructions
            assert "Iteration: 3" in instructions
            assert "45.2" in instructions
    
    def test_parameter_extraction_integration(self):
        """Test parameter extraction works with the agent"""
        test_input = """ORIGINAL QUERY:
AI healthcare applications research

BACKGROUND CONTEXT:
Focus on regulatory frameworks"""
        
        params = extract_knowledge_gap_params(test_input)
        
        assert params["research_context"] == "AI healthcare applications research"
        assert params["background_context"] == "Focus on regulatory frameworks"
        assert params["findings_history"] == ""
        assert params["iteration_context"] is None
    
    def test_backward_compatibility_schemas(self):
        """Test backward compatibility with existing schemas"""
        # Test that KnowledgeGapOutput is the correct alias
        assert KnowledgeGapOutput is KnowledgeGapResult
        
        # Test creating legacy compatible output
        legacy_output = KnowledgeGapOutput(
            research_complete=False,
            research_context="AI research testing backward compatibility",
            gaps_identified=[
                KnowledgeGap(
                    gap_id="gap_1",
                    description="Testing backward compatibility gap",
                    priority="high",
                    research_approach="Verify all legacy interfaces work correctly"
                )
            ],
            analysis_summary="This test verifies that legacy code can still create KnowledgeGapOutput objects",
            total_gaps=1
        )
        
        # Verify it has both old and new attributes
        assert hasattr(legacy_output, 'research_complete')  # Legacy
        assert hasattr(legacy_output, 'outstanding_gaps')   # Legacy via property/method (if implemented)
        assert hasattr(legacy_output, 'gaps_identified')    # New
        assert hasattr(legacy_output, 'analysis_summary')   # New
        assert hasattr(legacy_output, 'total_gaps')         # New
        assert hasattr(legacy_output, 'schema_version')     # New
        
        assert legacy_output.research_complete is False
        assert legacy_output.total_gaps == 1
        assert len(legacy_output.gaps_identified) == 1
    
    def test_model_role_mapping(self):
        """Test that KNOWLEDGE_GAP role maps to appropriate model"""
        config = create_default_config()
        
        # Test role mapping
        knowledge_gap_model = config.get_model_for_role(ModelRole.KNOWLEDGE_GAP)
        planner_model = config.get_model_for_role(ModelRole.PLANNER)
        
        # Should fallback to same model as planner for now (compatibility)
        assert knowledge_gap_model is not None
        assert type(knowledge_gap_model) == type(planner_model)
    
    def test_structured_path_initialization(self):
        """Test structured path initialization when Outlines is available"""
        # Mock the import and functionality
        mock_outlines = Mock()
        mock_generator = Mock()
        mock_outlines.json_schema.return_value = {"type": "object"}
        mock_outlines.Generator.return_value = mock_generator
        
        with patch.dict(os.environ, {'DISABLE_RUNTIME_ASSERTIONS': 'true'}):
            with patch('deep_researcher.agents.knowledge_gap_agent.model_supports_structured_output', return_value=True):
                with patch.dict('sys.modules', {'outlines': mock_outlines}):
                    config = create_default_config()
                    agent = init_knowledge_gap_agent(config)
                    
                    # Should use structured path
                    assert agent.output_type == KnowledgeGapResult
                    assert agent.structured_generator is not None
                    assert agent.instructions == ""  # Template handles instructions in structured path
                    
                    # Verify Outlines integration was attempted
                    mock_outlines.json_schema.assert_called_once_with(KnowledgeGapResult)
                    mock_outlines.Generator.assert_called_once()
    
    def test_enhanced_schema_validation(self):
        """Test enhanced schema validation works correctly"""
        # Test creating enhanced gap analysis result
        gaps = [
            KnowledgeGap(
                gap_id="healthcare_regulations",
                description="Recent FDA guidelines for AI medical devices need investigation",
                priority="high",
                research_approach="Review FDA guidance documents and recent policy updates",
                confidence=0.9,
                category="regulatory"
            ),
            KnowledgeGap(
                gap_id="clinical_trials",
                description="Current clinical trial results for AI diagnostic tools",
                priority="medium", 
                research_approach="Search PubMed and clinical trial databases",
                confidence=0.7,
                category="clinical"
            )
        ]
        
        result = KnowledgeGapResult(
            research_complete=False,
            research_completeness_confidence=0.6,
            research_context="AI applications in healthcare with regulatory compliance focus",
            gaps_identified=gaps,
            analysis_summary="Current research covers basic AI concepts but lacks specific regulatory framework analysis and recent clinical evidence. Two priority gaps identified requiring targeted research approaches.",
            total_gaps=2,
            iteration_context={"iteration": 2, "time_elapsed": 30.5}
        )
        
        # Verify all fields
        assert result.schema_version == 1
        assert result.research_complete is False
        assert result.research_completeness_confidence == 0.6
        assert len(result.gaps_identified) == 2
        assert result.total_gaps == 2
        assert result.iteration_context["iteration"] == 2
        
        # Verify gap details
        assert gaps[0].gap_id == "healthcare_regulations"
        assert gaps[0].priority == "high"
        assert gaps[0].confidence == 0.9
        assert gaps[0].category == "regulatory"
        
        # Test JSON serialization
        json_data = result.model_dump()
        assert "gaps_identified" in json_data
        assert len(json_data["gaps_identified"]) == 2
        assert json_data["total_gaps"] == 2