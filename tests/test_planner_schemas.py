"""Tests for planning schemas validation"""
import pytest
import json
from pydantic import ValidationError
from deep_researcher.agents.utils.outlines_schemas import ResearchStep, PlanningResult


class TestResearchStepValidation:
    """Test ResearchStep schema validation"""
    
    def test_valid_research_step(self):
        """Test valid ResearchStep creation"""
        step = ResearchStep(
            title="Introduction to AI",
            key_question="What are the foundational concepts of artificial intelligence?"
        )
        
        assert step.title == "Introduction to AI"
        assert step.key_question == "What are the foundational concepts of artificial intelligence?"
    
    def test_title_length_validation(self):
        """Test title length constraints"""
        # Too short (< 5 chars)
        with pytest.raises(ValidationError) as exc_info:
            ResearchStep(
                title="AI",
                key_question="What is artificial intelligence?"
            )
        assert "at least 5 characters" in str(exc_info.value)
        
        # Too long (> 80 chars)
        long_title = "A" * 81
        with pytest.raises(ValidationError) as exc_info:
            ResearchStep(
                title=long_title,
                key_question="What is artificial intelligence?"
            )
        assert "at most 80 characters" in str(exc_info.value)
    
    def test_key_question_length_validation(self):
        """Test key_question length constraints"""
        # Too short (< 10 chars)
        with pytest.raises(ValidationError) as exc_info:
            ResearchStep(
                title="AI Introduction",
                key_question="What?"  # Only 5 characters
            )
        assert "at least 10 characters" in str(exc_info.value)
        
        # Too long (> 200 chars)
        long_question = "What is " + "very " * 40 + "artificial intelligence?"
        with pytest.raises(ValidationError) as exc_info:
            ResearchStep(
                title="AI Introduction", 
                key_question=long_question
            )
        assert "at most 200 characters" in str(exc_info.value)
    
    def test_edge_case_lengths(self):
        """Test boundary values for length validation"""
        # Minimum valid lengths
        step = ResearchStep(
            title="A" * 5,  # Exactly 5 chars
            key_question="A" * 10  # Exactly 10 chars
        )
        assert len(step.title) == 5
        assert len(step.key_question) == 10
        
        # Maximum valid lengths
        step = ResearchStep(
            title="A" * 80,  # Exactly 80 chars
            key_question="A" * 200  # Exactly 200 chars
        )
        assert len(step.title) == 80
        assert len(step.key_question) == 200


class TestPlanningResultValidation:
    """Test PlanningResult schema validation"""
    
    def test_valid_planning_result(self):
        """Test valid PlanningResult creation"""
        steps = [
            ResearchStep(
                title="Introduction to AI",
                key_question="What are the fundamental concepts of artificial intelligence?"
            ),
            ResearchStep(
                title="AI Applications",
                key_question="How is artificial intelligence being applied in different industries?"
            )
        ]
        
        plan = PlanningResult(
            report_title="Comprehensive Guide to Artificial Intelligence",
            background_context="Artificial intelligence has emerged as one of the most transformative technologies of the 21st century, revolutionizing industries from healthcare to finance through machine learning, natural language processing, and computer vision capabilities.",
            report_outline=steps
        )
        
        assert plan.schema_version == 1  # Default value
        assert plan.report_title == "Comprehensive Guide to Artificial Intelligence"
        assert len(plan.report_outline) == 2
        assert plan.report_outline[0].title == "Introduction to AI"
    
    def test_schema_version_validation(self):
        """Test schema_version validation"""
        steps = [
            ResearchStep(title="Test Section", key_question="What is this test about?"),
            ResearchStep(title="Another Section", key_question="What else should we test here?")
        ]
        
        # Invalid schema version
        with pytest.raises(ValidationError) as exc_info:
            PlanningResult(
                schema_version=2,
                report_title="Test Report Title",
                background_context="This is a test background context that meets the minimum length requirement for validation.",
                report_outline=steps
            )
        assert "schema_version must be 1" in str(exc_info.value)
    
    def test_report_title_length_validation(self):
        """Test report_title length constraints"""
        steps = [
            ResearchStep(title="Test Section", key_question="What is this test about?"),
            ResearchStep(title="Another Section", key_question="What else should we test here?")
        ]
        context = "This is a test background context that meets the minimum length requirement for validation."
        
        # Too short (< 10 chars)
        with pytest.raises(ValidationError) as exc_info:
            PlanningResult(
                report_title="AI",
                background_context=context,
                report_outline=steps
            )
        assert "at least 10 characters" in str(exc_info.value)
        
        # Too long (> 100 chars)
        long_title = "A" * 101
        with pytest.raises(ValidationError) as exc_info:
            PlanningResult(
                report_title=long_title,
                background_context=context,
                report_outline=steps
            )
        assert "at most 100 characters" in str(exc_info.value)
    
    def test_background_context_length_validation(self):
        """Test background_context length constraints"""
        steps = [
            ResearchStep(title="Test Section", key_question="What is this test about?"),
            ResearchStep(title="Another Section", key_question="What else should we test here?")
        ]
        
        # Too short (< 50 chars)
        with pytest.raises(ValidationError) as exc_info:
            PlanningResult(
                report_title="Test Report Title",
                background_context="Short context.",
                report_outline=steps
            )
        assert "at least 50 characters" in str(exc_info.value)
        
        # Too long (> 1000 chars)
        long_context = "A" * 1001
        with pytest.raises(ValidationError) as exc_info:
            PlanningResult(
                report_title="Test Report Title",
                background_context=long_context,
                report_outline=steps
            )
        assert "at most 1000 characters" in str(exc_info.value)
    
    def test_report_outline_size_validation(self):
        """Test report_outline size constraints"""
        context = "This is a test background context that meets the minimum length requirement for validation."
        
        # Too few items (< 2)
        with pytest.raises(ValidationError) as exc_info:
            PlanningResult(
                report_title="Test Report Title",
                background_context=context,
                report_outline=[
                    ResearchStep(title="Only Section", key_question="What is this single test about?")
                ]
            )
        assert "at least 2 items" in str(exc_info.value)
        
        # Too many items (> 5)
        many_steps = [
            ResearchStep(title=f"Section {i}", key_question=f"What should we test in section {i}?")
            for i in range(1, 7)  # 6 items
        ]
        with pytest.raises(ValidationError) as exc_info:
            PlanningResult(
                report_title="Test Report Title",
                background_context=context,
                report_outline=many_steps
            )
        assert "at most 5 items" in str(exc_info.value)
    
    def test_boundary_outline_sizes(self):
        """Test boundary values for outline size validation"""
        context = "This is a test background context that meets the minimum length requirement for validation."
        
        # Minimum valid size (exactly 2)
        plan = PlanningResult(
            report_title="Test Report Title",
            background_context=context,
            report_outline=[
                ResearchStep(title="First Section", key_question="What is the first test about?"),
                ResearchStep(title="Second Section", key_question="What is the second test about?")
            ]
        )
        assert len(plan.report_outline) == 2
        
        # Maximum valid size (exactly 5)
        plan = PlanningResult(
            report_title="Test Report Title",
            background_context=context,
            report_outline=[
                ResearchStep(title=f"Section {i}", key_question=f"What should we test in section {i}?")
                for i in range(1, 6)  # 5 items
            ]
        )
        assert len(plan.report_outline) == 5


class TestSchemaJsonSerialization:
    """Test JSON serialization of planning schemas"""
    
    def test_research_step_serialization(self):
        """Test ResearchStep JSON serialization"""
        step = ResearchStep(
            title="AI Applications",
            key_question="How is artificial intelligence being applied in different industries?"
        )
        
        # Test serialization
        json_str = step.model_dump_json()
        parsed = json.loads(json_str)
        
        assert "title" in parsed
        assert "key_question" in parsed
        assert parsed["title"] == "AI Applications"
        assert parsed["key_question"] == "How is artificial intelligence being applied in different industries?"
    
    def test_planning_result_serialization(self):
        """Test PlanningResult JSON serialization"""
        plan = PlanningResult(
            report_title="Comprehensive Guide to AI",
            background_context="AI has emerged as a transformative technology revolutionizing industries through machine learning and automation.",
            report_outline=[
                ResearchStep(
                    title="Introduction to AI",
                    key_question="What are the fundamental concepts of artificial intelligence?"
                ),
                ResearchStep(
                    title="AI Applications",
                    key_question="How is AI being applied across different industries?"
                )
            ]
        )
        
        # Test serialization
        json_str = plan.model_dump_json()
        parsed = json.loads(json_str)
        
        # Validate structure
        assert "schema_version" in parsed
        assert "report_title" in parsed
        assert "background_context" in parsed
        assert "report_outline" in parsed
        
        assert parsed["schema_version"] == 1
        assert parsed["report_title"] == "Comprehensive Guide to AI"
        assert isinstance(parsed["report_outline"], list)
        assert len(parsed["report_outline"]) == 2
        
        # Validate nested structure
        first_step = parsed["report_outline"][0]
        assert "title" in first_step
        assert "key_question" in first_step
        assert first_step["title"] == "Introduction to AI"
    
    def test_deserialization_from_json(self):
        """Test creating schemas from JSON data"""
        json_data = {
            "schema_version": 1,
            "report_title": "Test Report from JSON",
            "background_context": "This is a test background context created from JSON data to validate deserialization.",
            "report_outline": [
                {
                    "title": "First Section",
                    "key_question": "What should we test in the first section from JSON?"
                },
                {
                    "title": "Second Section", 
                    "key_question": "What should we test in the second section from JSON?"
                }
            ]
        }
        
        # Create from dict
        plan = PlanningResult(**json_data)
        
        assert plan.schema_version == 1
        assert plan.report_title == "Test Report from JSON"
        assert len(plan.report_outline) == 2
        assert plan.report_outline[0].title == "First Section"
        assert plan.report_outline[1].key_question == "What should we test in the second section from JSON?"


class TestSchemaCompatibility:
    """Test schema compatibility with ValidationWrapper expectations"""
    
    def test_matches_validation_wrapper_structure(self):
        """Test that PlanningResult matches ValidationWrapper ReportPlan exactly"""
        # This should match the structure expected by schemas/models.py
        plan = PlanningResult(
            schema_version=1,
            report_title="AI Research Report",
            background_context="Artificial intelligence research has accelerated dramatically in recent years with breakthroughs in deep learning.",
            report_outline=[
                ResearchStep(
                    title="Machine Learning Fundamentals",
                    key_question="What are the core principles of machine learning algorithms?"
                ),
                ResearchStep(
                    title="Deep Learning Applications",
                    key_question="How are deep neural networks being applied to solve real-world problems?"
                )
            ]
        )
        
        # Validate all required fields exist with correct names
        json_data = plan.model_dump()
        
        required_fields = ["schema_version", "report_title", "background_context", "report_outline"]
        for field in required_fields:
            assert field in json_data, f"Missing required field: {field}"
        
        # Validate outline structure
        outline = json_data["report_outline"]
        assert isinstance(outline, list)
        assert len(outline) >= 2
        
        for step in outline:
            assert "title" in step
            assert "key_question" in step
    
    def test_schema_registry_compatibility(self):
        """Test compatibility with SCHEMA_MODELS mapping"""
        # The create_plan function should work with ValidationWrapper
        plan = PlanningResult(
            report_title="Test Schema Registry",
            background_context="Testing compatibility with the schema registry used by ValidationWrapper components.",
            report_outline=[
                ResearchStep(title="Schema Testing", key_question="How do we test schema compatibility?"),
                ResearchStep(title="Registry Validation", key_question="What validation steps are needed?")
            ]
        )
        
        # Should serialize without errors
        json_str = plan.model_dump_json()
        parsed = json.loads(json_str)
        
        # Should be deserializable back to schema
        recreated = PlanningResult(**parsed)
        assert recreated.report_title == plan.report_title
        assert len(recreated.report_outline) == len(plan.report_outline)