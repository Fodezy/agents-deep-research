"""End-to-end integration tests for PlannerAgent workflow validation"""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from deep_researcher.agents.planner_agent import init_planner_agent, ReportPlan, ReportPlanSection
from deep_researcher.agents.utils.outlines_schemas import PlanningResult, ResearchStep
from deep_researcher.llm_config import create_default_config


class MockPlannerModel:
    """Mock PLANNER model for end-to-end testing"""
    def __init__(self, structured_response=None):
        self.structured_response = structured_response or PlanningResult(
            report_title="End-to-End AI Research Report",
            background_context="Artificial intelligence is transforming multiple industries through automation, data analysis, and decision-making capabilities.",
            report_outline=[
                ResearchStep(
                    title="AI Fundamentals", 
                    key_question="What are the core principles and technologies behind modern AI systems?"
                ),
                ResearchStep(
                    title="Industry Applications", 
                    key_question="How is AI being implemented across different business sectors?"
                ),
                ResearchStep(
                    title="Future Implications", 
                    key_question="What are the potential long-term impacts of AI adoption?"
                )
            ]
        )
    
    def __call__(self, prompt: str) -> PlanningResult:
        return self.structured_response
    
    async def chat(self, prompt: str):
        class MockResponse:
            def __init__(self, text):
                self.text = text
        
        # Return JSON string for legacy path
        return MockResponse(self.structured_response.model_dump_json())


@pytest.fixture
def mock_config_with_planner():
    """Mock config with PLANNER model role"""
    config = create_default_config()
    # Mock the get_model_for_role method to return our mock model
    mock_model = MockPlannerModel()
    config.get_model_for_role = lambda role: mock_model
    return config


class TestPlannerEndToEndIntegration:
    """End-to-end integration tests for complete planning workflows"""
    
    def test_structured_path_initialization_and_execution(self, mock_config_with_planner):
        """Test structured path can be initialized and execute planning"""
        with patch('deep_researcher.agents.planner_agent.llm_config.model_supports_structured_output', return_value=True):
            
            # Mock outlines
            import sys
            from unittest.mock import MagicMock
            
            mock_outlines = MagicMock()
            mock_outlines.json_schema.return_value = "mock_schema"
            mock_outlines.Generator.return_value = MockPlannerModel()
            sys.modules['outlines'] = mock_outlines
            
            try:
                # Initialize planner agent
                planner_agent = init_planner_agent(mock_config_with_planner)
                
                # Verify structured path initialization
                assert planner_agent.name == "PlannerAgent"
                assert planner_agent.output_type == PlanningResult
                assert hasattr(planner_agent, 'structured_generator')
                assert callable(planner_agent.structured_generator)
                
                # Test execution with various input formats
                test_inputs = [
                    "QUERY: What is the impact of artificial intelligence on healthcare?",
                    {
                        "research_question": "How does machine learning improve medical diagnostics?",
                        "context": "Focus on radiology and pathology applications"
                    },
                    """QUERY: AI ethics and bias in decision-making systems
                    
CONTEXT: Consider regulatory frameworks and industry standards"""
                ]
                
                for input_data in test_inputs:
                    result = planner_agent.structured_generator(input_data)
                    
                    # Validate complete schema compliance
                    assert isinstance(result, PlanningResult)
                    assert result.schema_version == 1
                    assert len(result.report_title) >= 10
                    assert len(result.background_context) >= 50
                    assert 2 <= len(result.report_outline) <= 5
                    
                    # Validate each research step
                    for step in result.report_outline:
                        assert isinstance(step, ResearchStep)
                        assert 5 <= len(step.title) <= 80
                        assert 10 <= len(step.key_question) <= 200
                    
                    # Validate JSON serialization
                    json_data = result.model_dump()
                    assert 'schema_version' in json_data
                    assert 'report_title' in json_data
                    assert 'background_context' in json_data
                    assert 'report_outline' in json_data
            
            finally:
                # Clean up mock
                if 'outlines' in sys.modules:
                    del sys.modules['outlines']
    
    def test_legacy_path_initialization_and_execution(self, mock_config_with_planner):
        """Test legacy path can be initialized and generate proper instructions"""
        with patch('deep_researcher.agents.planner_agent.llm_config.model_supports_structured_output', return_value=False):
            
            # Initialize planner agent (should use legacy path)
            planner_agent = init_planner_agent(mock_config_with_planner)
            
            # Verify legacy path initialization
            assert hasattr(planner_agent, '_dynamic_instructions')
            assert callable(planner_agent._dynamic_instructions)
            assert planner_agent.output_parser is not None
            
            # Test various input formats
            test_inputs = [
                "QUERY: Future of renewable energy technology",
                {
                    "research_question": "Blockchain applications in supply chain",
                    "context": "Focus on transparency and traceability"
                }
            ]
            
            for input_data in test_inputs:
                # Test dynamic instructions generation
                instructions = planner_agent._dynamic_instructions(input_data)
                
                # Validate instruction content
                assert len(instructions) > 0
                assert "Report Planner" in instructions
                assert "JSON object" in instructions
                assert "exactly this format" in instructions
                assert "schema_version" in instructions
                assert "2025-08-" in instructions  # Date injection
                
                # Validate research question content is included
                if isinstance(input_data, str) and "QUERY:" in input_data:
                    query_content = input_data.split("QUERY:")[1].split("\n")[0].strip()
                    if query_content:
                        assert query_content.lower() in instructions.lower()
                elif isinstance(input_data, dict) and "research_question" in input_data:
                    assert input_data["research_question"].lower() in instructions.lower()
    
    def test_planning_schema_compatibility_with_downstream(self):
        """Test that planning outputs are compatible with downstream agents"""
        # Create a planning result
        planning_result = PlanningResult(
            report_title="Downstream Compatibility Test Report",
            background_context="Testing compatibility between PlannerAgent output and downstream ToolSelector input formats.",
            report_outline=[
                ResearchStep(
                    title="Tool Integration",
                    key_question="How does planner output feed into tool selection?"
                ),
                ResearchStep(
                    title="Workflow Validation", 
                    key_question="Are all integration points working correctly?"
                )
            ]
        )
        
        # Validate JSON structure matches expected downstream format
        json_output = planning_result.model_dump()
        
        # Check structure expected by ToolSelector and other downstream agents
        assert 'report_outline' in json_output
        assert isinstance(json_output['report_outline'], list)
        
        for step in json_output['report_outline']:
            assert 'title' in step
            assert 'key_question' in step
            # These fields could be used by downstream agents for context
            assert isinstance(step['title'], str)
            assert isinstance(step['key_question'], str)
        
        # Validate compatibility with ResearchRunner expected formats
        assert 'schema_version' in json_output
        assert json_output['schema_version'] == 1
        
        # Test serialization round-trip (important for persistence)
        json_str = planning_result.model_dump_json()
        import json
        parsed_json = json.loads(json_str)
        reconstructed = PlanningResult(**parsed_json)
        
        assert reconstructed == planning_result
        assert reconstructed.report_title == planning_result.report_title
        assert len(reconstructed.report_outline) == len(planning_result.report_outline)
    
    def test_performance_characteristics_validation(self, mock_config_with_planner):
        """Test that planning performance meets acceptance criteria"""
        import time
        
        with patch('deep_researcher.agents.planner_agent.llm_config.model_supports_structured_output', return_value=True):
            
            # Mock outlines for performance test
            import sys
            from unittest.mock import MagicMock
            
            mock_outlines = MagicMock()
            mock_outlines.json_schema.return_value = "mock_schema"
            mock_outlines.Generator.return_value = MockPlannerModel()
            sys.modules['outlines'] = mock_outlines
            
            try:
                # Test structured path performance
                start_time = time.time()
                agent = init_planner_agent(mock_config_with_planner)
                result = agent.structured_generator("QUERY: Test performance question")
                structured_duration = time.time() - start_time
                
                # Validate result
                assert isinstance(result, PlanningResult)
                
                # Performance should be reasonable (< 100ms for mock)
                assert structured_duration < 0.1, f"Structured path too slow: {structured_duration}s"
                
            finally:
                if 'outlines' in sys.modules:
                    del sys.modules['outlines']
        
        # Test legacy path performance
        with patch('deep_researcher.agents.planner_agent.llm_config.model_supports_structured_output', return_value=False):
            
            start_time = time.time()
            agent = init_planner_agent(mock_config_with_planner)
            instructions = agent._dynamic_instructions("QUERY: Test performance question")
            legacy_duration = time.time() - start_time
            
            # Validate instructions generation
            assert len(instructions) > 0
            assert "Report Planner" in instructions
            
            # Performance should be reasonable (< 50ms for mock)
            assert legacy_duration < 0.05, f"Legacy path too slow: {legacy_duration}s"
    
    def test_error_resilience_and_recovery(self, mock_config_with_planner):
        """Test error handling and graceful degradation scenarios"""
        
        # Test 1: Outlines import failure handling
        with patch('deep_researcher.agents.planner_agent.llm_config.model_supports_structured_output', return_value=True):
            
            # Mock import error
            import builtins
            original_import = builtins.__import__
            
            def mock_import(name, *args, **kwargs):
                if name == 'outlines':
                    raise ImportError("Mock outlines import failure")
                return original_import(name, *args, **kwargs)
            
            builtins.__import__ = mock_import
            
            try:
                # Should gracefully fall back to legacy path
                agent = init_planner_agent(mock_config_with_planner)
                
                # Verify fallback worked
                assert hasattr(agent, '_dynamic_instructions')
                assert callable(agent._dynamic_instructions)
                assert agent.output_parser is not None
                
                # Should still generate valid instructions
                instructions = agent._dynamic_instructions("QUERY: Test fallback")
                assert "Report Planner" in instructions
                assert len(instructions) > 0
                
            finally:
                builtins.__import__ = original_import
        
        # Test 2: Generator creation failure handling
        with patch('deep_researcher.agents.planner_agent.llm_config.model_supports_structured_output', return_value=True):
            
            # Mock outlines that fails during generator creation
            import sys
            from unittest.mock import MagicMock
            
            mock_outlines = MagicMock()
            mock_outlines.json_schema.return_value = "mock_schema"
            mock_outlines.Generator.side_effect = Exception("Mock generator creation failure")
            sys.modules['outlines'] = mock_outlines
            
            try:
                # Should gracefully fall back to legacy path
                agent = init_planner_agent(mock_config_with_planner)
                
                # Verify fallback worked
                assert hasattr(agent, '_dynamic_instructions')
                assert callable(agent._dynamic_instructions)
                assert agent.output_parser is not None
                
            finally:
                if 'outlines' in sys.modules:
                    del sys.modules['outlines']
        
        # Test 3: Invalid input handling
        with patch('deep_researcher.agents.planner_agent.llm_config.model_supports_structured_output', return_value=False):
            
            agent = init_planner_agent(mock_config_with_planner)
            
            # Test various edge case inputs
            edge_case_inputs = [
                "",  # Empty string
                None,  # None value
                [],  # Empty list
                {},  # Empty dict
                {"unknown_key": "value"},  # Dict with unknown keys
                "No QUERY format",  # String without expected format
            ]
            
            for edge_input in edge_case_inputs:
                # Should not crash and should generate some instructions
                try:
                    instructions = agent._dynamic_instructions(edge_input)
                    assert isinstance(instructions, str)
                    assert len(instructions) > 0
                    assert "Report Planner" in instructions
                except Exception as e:
                    pytest.fail(f"Failed to handle edge case input {edge_input}: {e}")


class TestBackwardCompatibilityValidation:
    """Validate complete backward compatibility with existing workflows"""
    
    def test_import_structure_compatibility(self):
        """Test that all expected imports work as before"""
        # Test primary imports
        from deep_researcher.agents.planner_agent import init_planner_agent
        from deep_researcher.agents.planner_agent import ReportPlan, ReportPlanSection
        
        # Test schema imports
        from deep_researcher.agents.utils.outlines_schemas import PlanningResult, ResearchStep
        
        # Verify aliases work correctly
        assert ReportPlan == PlanningResult
        assert ReportPlanSection == ResearchStep
        
        # Test that instances can be created with old names
        section = ReportPlanSection(
            title="Compatibility Test",
            key_question="Does backward compatibility work correctly?"
        )
        assert section.title == "Compatibility Test"
        
        plan = ReportPlan(
            report_title="Backward Compatibility Validation Report",
            background_context="Testing that existing code continues to work with the refactored PlannerAgent implementation.",
            report_outline=[section, ReportPlanSection(
                title="Additional Validation",
                key_question="Are all usage patterns preserved?"
            )]
        )
        assert plan.report_title == "Backward Compatibility Validation Report"
        assert len(plan.report_outline) == 2
    
    def test_field_access_patterns_compatibility(self):
        """Test that all existing field access patterns continue to work"""
        # Create using new schema but access with old patterns
        plan = PlanningResult(
            report_title="Field Access Pattern Test Report",
            background_context="Validating that all existing field access patterns work correctly with the new schema implementation.",
            report_outline=[
                ResearchStep(title="Pattern 1", key_question="Does direct field access work?"),
                ResearchStep(title="Pattern 2", key_question="Do list iterations work correctly?"),
                ResearchStep(title="Pattern 3", key_question="Are nested field accesses preserved?")
            ]
        )
        
        # Test direct field access (common pattern)
        assert plan.report_title == "Field Access Pattern Test Report"
        assert plan.background_context.startswith("Validating that all")
        assert len(plan.report_outline) == 3
        
        # Test list iteration patterns (very common)
        titles = []
        questions = []
        for i, section in enumerate(plan.report_outline):
            titles.append(section.title)
            questions.append(section.key_question)
            # Test indexed access
            assert plan.report_outline[i].title == section.title
        
        assert "Pattern 1" in titles
        assert "Does direct field access work?" in questions
        
        # Test dictionary-style access after serialization
        json_data = plan.model_dump()
        assert json_data['report_title'] == plan.report_title
        assert len(json_data['report_outline']) == len(plan.report_outline)
        
        for i, outline_item in enumerate(json_data['report_outline']):
            assert outline_item['title'] == plan.report_outline[i].title
            assert outline_item['key_question'] == plan.report_outline[i].key_question
    
    def test_researchrunner_integration_compatibility(self, mock_config_with_planner):
        """Test compatibility with ResearchRunner usage patterns"""
        
        with patch('deep_researcher.agents.planner_agent.llm_config.model_supports_structured_output', return_value=False):
            
            # Initialize exactly as ResearchRunner would
            planner_agent = init_planner_agent(mock_config_with_planner)
            
            # Verify agent has expected attributes for ResearchRunner
            expected_attributes = ['name', 'model', 'output_parser', '_dynamic_instructions']
            for attr in expected_attributes:
                assert hasattr(planner_agent, attr), f"Missing expected attribute: {attr}"
            
            # Test name consistency
            assert planner_agent.name == "PlannerAgent"
            
            # Test that dynamic instructions function works
            assert callable(planner_agent._dynamic_instructions)
            
            # Test with typical ResearchRunner input format
            test_input = "QUERY: What are the environmental impacts of electric vehicles?"
            instructions = planner_agent._dynamic_instructions(test_input)
            
            # Verify instructions contain expected elements
            assert "electric vehicles" in instructions.lower()
            assert "environmental impacts" in instructions.lower()
            assert "Report Planner" in instructions
            assert "JSON object" in instructions
            assert "2025-08-" in instructions  # Current date
            
            # Verify output parser exists and is callable
            assert planner_agent.output_parser is not None
            assert hasattr(planner_agent.output_parser, '__call__') or callable(planner_agent.output_parser)


class TestPlannerComprehensiveIntegration:
    """Additional comprehensive integration tests to meet HYBRID-06-05 requirements"""
    
    def test_complete_planning_workflow_validation(self, mock_config_with_planner):
        """Test complete planning workflow with all validation points"""
        
        # Test both structured and legacy paths in one comprehensive test
        test_scenarios = [
            {"structured_support": True, "path_name": "structured"},
            {"structured_support": False, "path_name": "legacy"}
        ]
        
        for scenario in test_scenarios:
            with patch('deep_researcher.agents.planner_agent.llm_config.model_supports_structured_output', 
                      return_value=scenario["structured_support"]):
                
                if scenario["structured_support"]:
                    # Mock outlines for structured path
                    import sys
                    from unittest.mock import MagicMock
                    
                    mock_outlines = MagicMock()
                    mock_outlines.json_schema.return_value = "mock_schema"
                    mock_outlines.Generator.return_value = MockPlannerModel()
                    sys.modules['outlines'] = mock_outlines
                
                try:
                    # Initialize agent
                    agent = init_planner_agent(mock_config_with_planner)
                    
                    # Verify correct path initialization
                    if scenario["structured_support"]:
                        assert hasattr(agent, 'structured_generator')
                        assert agent.output_type == PlanningResult
                    else:
                        assert hasattr(agent, '_dynamic_instructions')
                        assert agent.output_parser is not None
                    
                    # Test with complex real-world input
                    complex_input = """QUERY: How is artificial intelligence transforming the financial services industry?
                    
CONTEXT: Focus on recent developments in algorithmic trading, fraud detection, and customer service automation. Consider regulatory implications and market adoption rates."""
                    
                    if scenario["structured_support"]:
                        # Test structured generation
                        result = agent.structured_generator(complex_input)
                        assert isinstance(result, PlanningResult)
                        
                        # Test that result can be used as ReportPlan (backward compatibility)
                        plan_alias = ReportPlan(**result.model_dump())
                        assert plan_alias.report_title == result.report_title
                        
                    else:
                        # Test legacy instructions generation
                        instructions = agent._dynamic_instructions(complex_input)
                        
                        # Verify all expected content is included
                        assert "artificial intelligence" in instructions.lower()
                        assert "financial services" in instructions.lower()
                        assert "algorithmic trading" in instructions.lower()
                        assert "fraud detection" in instructions.lower()
                        assert "customer service" in instructions.lower()
                        assert "regulatory implications" in instructions.lower()
                        
                        # Verify JSON schema structure
                        assert '"schema_version": 1' in instructions
                        assert '"report_title":' in instructions
                        assert '"background_context":' in instructions
                        assert '"report_outline":' in instructions
                    
                finally:
                    # Clean up outlines mock if it was set
                    if scenario["structured_support"] and 'outlines' in sys.modules:
                        del sys.modules['outlines']
    
    def test_schema_validation_edge_cases(self):
        """Test schema validation handles all edge cases correctly"""
        
        # Test boundary conditions for all fields
        test_cases = [
            {
                "name": "minimum_valid_lengths",
                "data": {
                    "report_title": "A" * 10,  # Minimum length
                    "background_context": "B" * 50,  # Minimum length
                    "report_outline": [
                        ResearchStep(title="C" * 5, key_question="D" * 10),  # Minimum lengths
                        ResearchStep(title="E" * 5, key_question="F" * 10)   # Two items minimum
                    ]
                },
                "should_pass": True
            },
            {
                "name": "maximum_valid_lengths",
                "data": {
                    "report_title": "G" * 100,  # Maximum length
                    "background_context": "H" * 1000,  # Maximum length
                    "report_outline": [
                        ResearchStep(title="I" * 80, key_question="J" * 200),  # Maximum lengths
                        ResearchStep(title="K" * 80, key_question="L" * 200),
                        ResearchStep(title="M" * 80, key_question="N" * 200),
                        ResearchStep(title="O" * 80, key_question="P" * 200),
                        ResearchStep(title="Q" * 80, key_question="R" * 200)   # Five items maximum
                    ]
                },
                "should_pass": True
            }
        ]
        
        for test_case in test_cases:
            if test_case["should_pass"]:
                # Should create successfully
                result = PlanningResult(**test_case["data"])
                assert result.schema_version == 1
                
                # Should serialize and deserialize correctly
                json_str = result.model_dump_json()
                reconstructed = PlanningResult.model_validate_json(json_str)
                assert reconstructed == result
                
                # Should work with backward compatibility aliases
                plan_alias = ReportPlan(**test_case["data"])
                assert plan_alias == result
            else:
                # Should raise validation error
                with pytest.raises(Exception):  # ValidationError or similar
                    PlanningResult(**test_case["data"])
    
    def test_end_to_end_json_compatibility(self):
        """Test end-to-end JSON compatibility with all downstream systems"""
        
        # Create a comprehensive planning result
        planning_result = PlanningResult(
            report_title="Comprehensive JSON Compatibility Test Report",
            background_context="This comprehensive test validates that the PlannerAgent output maintains perfect JSON compatibility with all downstream systems including ToolSelector, KnowledgeGap agents, and the ResearchRunner pipeline.",
            report_outline=[
                ResearchStep(
                    title="JSON Serialization",
                    key_question="Does the output serialize to valid JSON without data loss?"
                ),
                ResearchStep(
                    title="Schema Compatibility",
                    key_question="Are all field names and types compatible with existing systems?"
                ),
                ResearchStep(
                    title="Round-trip Validation",
                    key_question="Can the output be serialized and deserialized perfectly?"
                ),
                ResearchStep(
                    title="Backward Compatibility",
                    key_question="Do existing systems continue to work without modification?"
                )
            ]
        )
        
        # Test 1: Basic JSON serialization
        json_str = planning_result.model_dump_json()
        assert len(json_str) > 0
        
        # Test 2: JSON parsing validation
        import json
        parsed_json = json.loads(json_str)
        assert isinstance(parsed_json, dict)
        
        # Test 3: Schema field validation
        required_fields = ['schema_version', 'report_title', 'background_context', 'report_outline']
        for field in required_fields:
            assert field in parsed_json, f"Missing required field: {field}"
        
        # Test 4: Nested structure validation
        assert isinstance(parsed_json['report_outline'], list)
        assert len(parsed_json['report_outline']) == 4
        
        for step in parsed_json['report_outline']:
            assert isinstance(step, dict)
            assert 'title' in step
            assert 'key_question' in step
            assert isinstance(step['title'], str)
            assert isinstance(step['key_question'], str)
        
        # Test 5: Round-trip reconstruction
        reconstructed = PlanningResult.model_validate(parsed_json)
        assert reconstructed == planning_result
        
        # Test 6: Backward compatibility with aliases
        plan_alias = ReportPlan.model_validate(parsed_json)
        assert plan_alias == planning_result
        
        section_aliases = [ReportPlanSection.model_validate(step_data) 
                          for step_data in parsed_json['report_outline']]
        assert len(section_aliases) == 4
        assert all(isinstance(section, ResearchStep) for section in section_aliases)
        
        # Test 7: Field access patterns (common in downstream systems)
        assert planning_result.report_outline[0].title == "JSON Serialization"
        assert planning_result.report_outline[1].key_question.startswith("Are all field names")
        
        # Test 8: Dictionary-style access after model_dump()
        dict_output = planning_result.model_dump()
        assert dict_output['report_outline'][0]['title'] == "JSON Serialization"
        assert dict_output['report_outline'][1]['key_question'].startswith("Are all field names")