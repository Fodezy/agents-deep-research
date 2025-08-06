"""Comprehensive integration tests for refactored PlannerAgent"""
import pytest
from unittest.mock import Mock
from deep_researcher.agents.planner_agent import init_planner_agent, ReportPlan, ReportPlanSection
from deep_researcher.agents.utils.outlines_schemas import PlanningResult, ResearchStep
from deep_researcher.llm_config import create_default_config


class MockStructuredModel:
    """Mock model that supports structured output"""
    def __init__(self, response_data=None):
        self.response_data = response_data or {
            "schema_version": 1,
            "report_title": "Test Report: Artificial Intelligence",
            "background_context": "Artificial intelligence has emerged as a transformative technology with applications across various industries and sectors.",
            "report_outline": [
                {"title": "AI Fundamentals", "key_question": "What are the core principles of artificial intelligence?"},
                {"title": "AI Applications", "key_question": "How is AI being applied in different industries?"}
            ]
        }
    
    def __call__(self, prompt: str) -> PlanningResult:
        return PlanningResult(**self.response_data)


class MockLegacyModel:
    """Mock model without structured output support"""
    def __init__(self, response_text=None):
        self.response_text = response_text or '''
        {
            "schema_version": 1,
            "report_title": "Machine Learning Research Report",
            "background_context": "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.",
            "report_outline": [
                {"title": "ML Basics", "key_question": "What are the fundamental concepts of machine learning?"},
                {"title": "ML Algorithms", "key_question": "What are the main types of machine learning algorithms?"}
            ]
        }
        '''
    
    async def chat(self, prompt: str):
        class MockResponse:
            def __init__(self, text):
                self.text = text
        return MockResponse(self.response_text)


@pytest.fixture
def mock_config_structured():
    """Mock config with structured output support"""
    config = create_default_config()
    config.reasoning_model = MockStructuredModel()
    return config


@pytest.fixture
def mock_config_legacy():
    """Mock config without structured output support"""
    config = create_default_config()
    config.reasoning_model = MockLegacyModel()
    return config


class TestPlannerAgentBackwardCompatibility:
    """Test backward compatibility with existing code"""
    
    def test_schema_aliases_work(self):
        """Test that ReportPlan and ReportPlanSection aliases work correctly"""
        # These should be the same as the new schemas
        assert ReportPlan == PlanningResult
        assert ReportPlanSection == ResearchStep
        
        # Should be able to create instances
        section = ReportPlanSection(
            title="Test Section",
            key_question="What is this test about?"
        )
        assert section.title == "Test Section"
        assert section.key_question == "What is this test about?"
        
        # Create a second section to meet minimum requirements
        section2 = ReportPlanSection(
            title="Another Test Section",
            key_question="What else should we test for compatibility?"
        )
        
        plan = ReportPlan(
            report_title="Test Backward Compatibility Report",
            background_context="This test verifies that backward compatibility is maintained for existing code using the old schema names.",
            report_outline=[section, section2]
        )
        assert plan.report_title == "Test Backward Compatibility Report"
        assert len(plan.report_outline) == 2
    
    def test_agent_initialization_maintains_interface(self, mock_config_legacy):
        """Test that agent initialization maintains the same interface"""
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: False
        
        try:
            agent = init_planner_agent(mock_config_legacy)
            
            # Should have all expected attributes for ResearchRunner
            assert hasattr(agent, 'name')
            assert hasattr(agent, 'model')
            assert hasattr(agent, 'output_parser')
            assert agent.name == "PlannerAgent"
            
            # Should have dynamic instructions for legacy path
            assert hasattr(agent, '_dynamic_instructions')
            assert callable(agent._dynamic_instructions)
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func


class TestPlannerAgentStructuredPath:
    """Test structured output path with Outlines integration"""
    
    def test_structured_agent_initialization(self, mock_config_structured):
        """Test initialization with structured output support"""
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: True
        
        try:
            # Mock outlines to avoid import issues
            import sys
            from unittest.mock import MagicMock
            
            mock_outlines = MagicMock()
            mock_outlines.json_schema.return_value = "mock_schema"
            mock_outlines.Generator.return_value = lambda prompt: PlanningResult(
                report_title="Structured Output Test Report",
                background_context="This is a test of the structured output path using mock Outlines integration.",
                report_outline=[
                    ResearchStep(title="Test Section", key_question="Does structured output work correctly?")
                ]
            )
            sys.modules['outlines'] = mock_outlines
            
            agent = init_planner_agent(mock_config_structured)
            
            assert agent.name == "PlannerAgent"
            assert agent.output_type == PlanningResult
            assert hasattr(agent, 'structured_generator')
            assert callable(agent.structured_generator)
            
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func
            # Clean up mock
            if 'outlines' in sys.modules:
                del sys.modules['outlines']
    
    def test_structured_generator_integration(self, mock_config_structured):
        """Test structured generator integration with parameter extraction"""
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: True
        
        try:
            # Mock outlines
            import sys
            from unittest.mock import MagicMock
            
            mock_outlines = MagicMock()
            mock_outlines.json_schema.return_value = "mock_schema"
            mock_generator = MagicMock()
            mock_generator.return_value = PlanningResult(
                report_title="AI Integration Test Report",
                background_context="Testing the integration between parameter extraction, template rendering, and structured generation.",
                report_outline=[
                    ResearchStep(title="Parameter Extraction", key_question="How are input parameters extracted correctly?"),
                    ResearchStep(title="Template Rendering", key_question="How are templates rendered without placeholders?")
                ]
            )
            mock_outlines.Generator.return_value = mock_generator
            sys.modules['outlines'] = mock_outlines
            
            agent = init_planner_agent(mock_config_structured)
            
            # Test with various input formats
            test_inputs = [
                {"research_question": "AI applications", "context": "Focus on healthcare"},
                "QUERY: What is machine learning?",
                """QUERY: Deep learning fundamentals

CONTEXT: Recent advances in neural networks"""
            ]
            
            for input_data in test_inputs:
                result = agent.structured_generator(input_data)
                assert isinstance(result, PlanningResult)
                assert result.report_title == "AI Integration Test Report"
                assert len(result.report_outline) == 2
                
                # Verify generator was called with rendered prompt
                mock_generator.assert_called()
                
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func
            if 'outlines' in sys.modules:
                del sys.modules['outlines']


class TestPlannerAgentLegacyPath:
    """Test legacy path with dynamic instructions"""
    
    def test_legacy_agent_initialization(self, mock_config_legacy):
        """Test initialization without structured output support"""
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: False
        
        try:
            agent = init_planner_agent(mock_config_legacy)
            
            assert agent.name == "PlannerAgent"
            assert hasattr(agent, '_dynamic_instructions')
            assert callable(agent._dynamic_instructions)
            assert agent.output_parser is not None
            
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func
    
    def test_dynamic_instructions_generation(self, mock_config_legacy):
        """Test dynamic instruction generation for various inputs"""
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: False
        
        try:
            agent = init_planner_agent(mock_config_legacy)
            
            test_inputs = [
                "QUERY: What are the benefits of renewable energy?",
                {"research_question": "Quantum computing applications", "context": "Commercial use cases"},
                """QUERY: Artificial intelligence in education

BACKGROUND: K-12 and higher education applications"""
            ]
            
            for input_data in test_inputs:
                instructions = agent._dynamic_instructions(input_data)
                
                # Should generate proper legacy prompt
                assert len(instructions) > 0
                assert "Report Planner" in instructions
                assert "JSON object" in instructions
                assert "exactly this format" in instructions
                assert "schema_version" in instructions
                assert "2025-08-" in instructions  # Date injection
                
                # Should contain research question content
                if isinstance(input_data, str) and "QUERY:" in input_data:
                    query_content = input_data.split("QUERY:")[1].split("\n")[0].strip()
                    if query_content:
                        assert query_content.lower() in instructions.lower()
                elif isinstance(input_data, dict) and "research_question" in input_data:
                    assert input_data["research_question"].lower() in instructions.lower()
                    
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func


class TestPlannerAgentFallbackHandling:
    """Test graceful fallback handling"""
    
    def test_outlines_import_error_fallback(self, mock_config_structured):
        """Test fallback when Outlines import fails"""
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: True
        
        try:
            # Ensure outlines is not importable
            import sys
            if 'outlines' in sys.modules:
                del sys.modules['outlines']
            
            # Mock import error
            import builtins
            original_import = builtins.__import__
            
            def mock_import(name, *args, **kwargs):
                if name == 'outlines':
                    raise ImportError("Mock outlines import error")
                return original_import(name, *args, **kwargs)
            
            builtins.__import__ = mock_import
            
            agent = init_planner_agent(mock_config_structured)
            
            # Should fall back to legacy path
            assert agent.name == "PlannerAgent"
            assert hasattr(agent, '_dynamic_instructions')
            assert callable(agent._dynamic_instructions)
            assert agent.output_parser is not None
            
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func
            builtins.__import__ = original_import
    
    def test_outlines_generator_error_fallback(self, mock_config_structured):
        """Test fallback when Outlines generator creation fails"""
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: True
        
        try:
            # Mock outlines that fails during generator creation
            import sys
            from unittest.mock import MagicMock
            
            mock_outlines = MagicMock()
            mock_outlines.json_schema.return_value = "mock_schema"
            mock_outlines.Generator.side_effect = Exception("Mock generator creation error")
            sys.modules['outlines'] = mock_outlines
            
            agent = init_planner_agent(mock_config_structured)
            
            # Should fall back to legacy path
            assert agent.name == "PlannerAgent" 
            assert hasattr(agent, '_dynamic_instructions')
            assert callable(agent._dynamic_instructions)
            assert agent.output_parser is not None
            
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func
            if 'outlines' in sys.modules:
                del sys.modules['outlines']


class TestPlannerAgentInputHandling:
    """Test input parameter extraction and handling"""
    
    def test_input_extraction_integration(self, mock_config_legacy):
        """Test that input extraction works correctly with agent"""
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: False
        
        try:
            agent = init_planner_agent(mock_config_legacy)
            
            # Test complex input with context
            complex_input = """QUERY: How does artificial intelligence impact healthcare?

CONTEXT: Consider recent FDA approvals and regulatory changes"""
            
            instructions = agent._dynamic_instructions(complex_input)
            
            # Should extract and include both query and context
            assert "artificial intelligence" in instructions
            assert "healthcare" in instructions
            assert "FDA approvals" in instructions
            assert "regulatory changes" in instructions
            assert "Background Context:" in instructions
            
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func
    
    def test_extra_key_handling(self, mock_config_legacy):
        """Test that extra keys in input are handled gracefully"""
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: False
        
        try:
            agent = init_planner_agent(mock_config_legacy)
            
            # Input with extra keys that should be ignored
            input_with_extras = {
                "research_question": "Blockchain applications in finance",
                "context": "Focus on DeFi and smart contracts",
                "user_id": "12345",  # Extra key
                "session_data": {"timestamp": "2025-08-04"},  # Extra nested data
                "api_version": "v2"  # Another extra key
            }
            
            instructions = agent._dynamic_instructions(input_with_extras)
            
            # Should include research question and context
            assert "blockchain" in instructions.lower()
            assert "finance" in instructions.lower()
            assert "defi" in instructions.lower()
            assert "smart contracts" in instructions.lower()
            
            # Should not include extra keys
            assert "user_id" not in instructions.lower()
            assert "session_data" not in instructions.lower()
            assert "api_version" not in instructions.lower()
            
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func


class TestPlannerAgentSchemaCompatibility:
    """Test schema compatibility and validation"""
    
    def test_planning_result_compatibility(self):
        """Test that PlanningResult is compatible with expected usage"""
        # Should work exactly like the old ReportPlan
        result = PlanningResult(
            report_title="Compatibility Test Report", 
            background_context="Testing that the new PlanningResult schema works exactly like the old ReportPlan for all existing code.",
            report_outline=[
                ResearchStep(title="Schema Validation", key_question="Does the new schema validate correctly?"),
                ResearchStep(title="Compatibility Check", key_question="Is backward compatibility maintained?")
            ]
        )
        
        # Should have all expected fields
        assert result.schema_version == 1
        assert result.report_title == "Compatibility Test Report"
        assert result.background_context.startswith("Testing that the new")
        assert len(result.report_outline) == 2
        
        # Should serialize to expected JSON structure
        json_data = result.model_dump()
        assert "schema_version" in json_data
        assert "report_title" in json_data
        assert "background_context" in json_data
        assert "report_outline" in json_data
        
        # Outline should have expected structure
        outline = json_data["report_outline"]
        assert len(outline) == 2
        assert outline[0]["title"] == "Schema Validation"
        assert outline[0]["key_question"] == "Does the new schema validate correctly?"
    
    def test_research_step_compatibility(self):
        """Test that ResearchStep is compatible with expected usage"""
        # Should work exactly like the old ReportPlanSection
        step = ResearchStep(
            title="Test Research Step",
            key_question="How does this research step work in practice?"
        )
        
        # Should have expected fields
        assert step.title == "Test Research Step"
        assert step.key_question == "How does this research step work in practice?"
        
        # Should serialize correctly
        json_data = step.model_dump()
        assert "title" in json_data
        assert "key_question" in json_data
        assert json_data["title"] == "Test Research Step"