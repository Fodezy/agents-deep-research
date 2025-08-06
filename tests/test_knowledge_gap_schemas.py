"""Tests for knowledge gap analysis schemas validation"""
import pytest
import json
from pydantic import ValidationError
from deep_researcher.agents.utils.outlines_schemas import (
    KnowledgeGap, 
    KnowledgeGapResult, 
    KnowledgeGapOutput
)


class TestKnowledgeGapValidation:
    """Test KnowledgeGap schema validation"""
    
    def test_valid_knowledge_gap(self):
        """Test valid KnowledgeGap creation"""
        gap = KnowledgeGap(
            gap_id="gap_1",
            description="Recent developments in AI healthcare applications need investigation",
            priority="high",
            research_approach="Search recent papers and clinical trial databases",
            confidence=0.8,
            category="healthcare"
        )
        
        assert gap.gap_id == "gap_1"
        assert gap.description == "Recent developments in AI healthcare applications need investigation"
        assert gap.priority == "high"
        assert gap.research_approach == "Search recent papers and clinical trial databases"
        assert gap.confidence == 0.8
        assert gap.category == "healthcare"
    
    def test_gap_id_validation(self):
        """Test gap_id validation constraints"""
        # Valid alphanumeric with underscores and dashes
        valid_ids = ["gap_1", "gap-2", "gap123", "research_gap_ai", "ml-applications"]
        for gap_id in valid_ids:
            gap = KnowledgeGap(
                gap_id=gap_id,
                description="Valid gap description for testing purposes",
                priority="medium",
                research_approach="Standard research methodology"
            )
            assert gap.gap_id == gap_id
        
        # Invalid characters
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGap(
                gap_id="gap@1",  # Contains invalid character
                description="Gap description",
                priority="high",
                research_approach="Research approach"
            )
        assert "must be alphanumeric with optional underscores or dashes" in str(exc_info.value)
        
        # Too short (< 3 chars)
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGap(
                gap_id="g1",
                description="Gap description",
                priority="high", 
                research_approach="Research approach"
            )
        assert "at least 3 characters" in str(exc_info.value)
        
        # Too long (> 50 chars)
        long_id = "gap_" + "very_long_identifier_" * 3 + "exceeds_limit"
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGap(
                gap_id=long_id,
                description="Gap description",
                priority="high",
                research_approach="Research approach"
            )
        assert "at most 50 characters" in str(exc_info.value)
    
    def test_description_length_validation(self):
        """Test description length constraints"""
        # Too short (< 10 chars)
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGap(
                gap_id="gap_1",
                description="Short",
                priority="high",
                research_approach="Research approach"
            )
        assert "at least 10 characters" in str(exc_info.value)
        
        # Too long (> 500 chars)
        long_description = "A" * 501
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGap(
                gap_id="gap_1",
                description=long_description,
                priority="high",
                research_approach="Research approach"
            )
        assert "at most 500 characters" in str(exc_info.value)
    
    def test_priority_validation(self):
        """Test priority literal validation"""
        valid_priorities = ["high", "medium", "low"]
        for priority in valid_priorities:
            gap = KnowledgeGap(
                gap_id="gap_1",
                description="Valid gap description",
                priority=priority,
                research_approach="Research approach"
            )
            assert gap.priority == priority
        
        # Invalid priority
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGap(
                gap_id="gap_1",
                description="Gap description",
                priority="urgent",  # Invalid priority
                research_approach="Research approach"
            )
        assert "Input should be 'high', 'medium' or 'low'" in str(exc_info.value)
    
    def test_research_approach_length_validation(self):
        """Test research_approach length constraints"""
        # Too short (< 10 chars)
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGap(
                gap_id="gap_1",
                description="Valid gap description",
                priority="high",
                research_approach="Search"
            )
        assert "at least 10 characters" in str(exc_info.value)
        
        # Too long (> 200 chars)
        long_approach = "A" * 201
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGap(
                gap_id="gap_1",
                description="Valid gap description", 
                priority="high",
                research_approach=long_approach
            )
        assert "at most 200 characters" in str(exc_info.value)
    
    def test_confidence_validation(self):
        """Test confidence range validation"""
        # Valid confidence values
        valid_confidences = [0.0, 0.5, 1.0, 0.123, 0.999]
        for confidence in valid_confidences:
            gap = KnowledgeGap(
                gap_id="gap_1",
                description="Valid gap description",
                priority="high",
                research_approach="Research approach",
                confidence=confidence
            )
            assert gap.confidence == confidence
        
        # Invalid confidence (< 0.0)
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGap(
                gap_id="gap_1",
                description="Valid gap description",
                priority="high",
                research_approach="Research approach",
                confidence=-0.1
            )
        assert "greater than or equal to 0" in str(exc_info.value)
        
        # Invalid confidence (> 1.0)
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGap(
                gap_id="gap_1",
                description="Valid gap description",
                priority="high",
                research_approach="Research approach",
                confidence=1.1
            )
        assert "less than or equal to 1" in str(exc_info.value)
    
    def test_category_optional_validation(self):
        """Test category field optional validation"""
        # Without category (should work)
        gap = KnowledgeGap(
            gap_id="gap_1",
            description="Valid gap description",
            priority="high",
            research_approach="Research approach"
        )
        assert gap.category is None
        
        # With category (should work)
        gap = KnowledgeGap(
            gap_id="gap_1",
            description="Valid gap description",
            priority="high",
            research_approach="Research approach",
            category="technology"
        )
        assert gap.category == "technology"
        
        # Too long category (> 50 chars)
        long_category = "A" * 51
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGap(
                gap_id="gap_1",
                description="Valid gap description",
                priority="high",
                research_approach="Research approach",
                category=long_category
            )
        assert "at most 50 characters" in str(exc_info.value)
    
    def test_default_confidence_value(self):
        """Test default confidence value"""
        gap = KnowledgeGap(
            gap_id="gap_1",
            description="Valid gap description",
            priority="high",
            research_approach="Research approach"
        )
        assert gap.confidence == 1.0  # Default value


class TestKnowledgeGapResultValidation:
    """Test KnowledgeGapResult schema validation"""
    
    def test_valid_knowledge_gap_result(self):
        """Test valid KnowledgeGapResult creation"""
        gaps = [
            KnowledgeGap(
                gap_id="gap_1",
                description="AI healthcare applications research needed",
                priority="high",
                research_approach="Search recent medical journals",
                confidence=0.9
            ),
            KnowledgeGap(
                gap_id="gap_2",
                description="Regulatory compliance gaps in AI deployment",
                priority="medium",
                research_approach="Review current FDA guidelines",
                confidence=0.7
            )
        ]
        
        result = KnowledgeGapResult(
            research_complete=False,
            research_completeness_confidence=0.6,
            research_context="Investigating AI applications in healthcare with focus on regulatory compliance",
            gaps_identified=gaps,
            analysis_summary="Current research covers basic AI concepts but lacks specific healthcare applications and regulatory framework analysis. Two major gaps identified requiring targeted research.",
            total_gaps=2,
            iteration_context={"iteration": 3, "time_elapsed": 45.2}
        )
        
        assert result.schema_version == 1  # Default
        assert result.research_complete is False
        assert result.research_completeness_confidence == 0.6
        assert len(result.gaps_identified) == 2
        assert result.total_gaps == 2
        assert result.iteration_context["iteration"] == 3
    
    def test_schema_version_validation(self):
        """Test schema_version validation"""
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGapResult(
                schema_version=2,  # Invalid version
                research_complete=True,
                research_context="Valid research context for testing",
                gaps_identified=[],
                analysis_summary="Valid analysis summary that meets minimum length requirements",
                total_gaps=0
            )
        assert "schema_version must be 1" in str(exc_info.value)
    
    def test_research_completeness_confidence_validation(self):
        """Test research_completeness_confidence range validation"""
        # Valid range
        valid_confidences = [0.0, 0.5, 1.0]
        for confidence in valid_confidences:
            result = KnowledgeGapResult(
                research_complete=True,
                research_completeness_confidence=confidence,
                research_context="Valid research context",
                gaps_identified=[],
                analysis_summary="Valid analysis summary that meets minimum length requirements",
                total_gaps=0
            )
            assert result.research_completeness_confidence == confidence
        
        # Invalid range
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGapResult(
                research_complete=True,
                research_completeness_confidence=1.5,  # > 1.0
                research_context="Valid research context",
                gaps_identified=[],
                analysis_summary="Valid analysis summary",
                total_gaps=0
            )
        assert "less than or equal to 1" in str(exc_info.value)
    
    def test_research_context_length_validation(self):
        """Test research_context length constraints"""
        # Too short (< 20 chars)
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGapResult(
                research_complete=True,
                research_context="Short context",
                gaps_identified=[],
                analysis_summary="Valid analysis summary that meets minimum length requirements",
                total_gaps=0
            )
        assert "at least 20 characters" in str(exc_info.value)
        
        # Too long (> 1000 chars)
        long_context = "A" * 1001
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGapResult(
                research_complete=True,
                research_context=long_context,
                gaps_identified=[],
                analysis_summary="Valid analysis summary that meets minimum length requirements",
                total_gaps=0
            )
        assert "at most 1000 characters" in str(exc_info.value)
    
    def test_analysis_summary_length_validation(self):
        """Test analysis_summary length constraints"""
        # Too short (< 50 chars)
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGapResult(
                research_complete=True,
                research_context="Valid research context for testing",
                gaps_identified=[],
                analysis_summary="Short summary",
                total_gaps=0
            )
        assert "at least 50 characters" in str(exc_info.value)
        
        # Too long (> 2000 chars)
        long_summary = "A" * 2001
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGapResult(
                research_complete=True,
                research_context="Valid research context for testing",
                gaps_identified=[],
                analysis_summary=long_summary,
                total_gaps=0
            )
        assert "at most 2000 characters" in str(exc_info.value)
    
    def test_gaps_identified_size_validation(self):
        """Test gaps_identified size constraints"""
        context = "Valid research context for testing purposes"
        summary = "Valid analysis summary that meets minimum length requirements for testing"
        
        # Maximum valid size (exactly 10)
        gaps = [
            KnowledgeGap(
                gap_id=f"gap_{i}",
                description=f"Gap description number {i} for testing",
                priority="medium",
                research_approach="Standard research approach"
            )
            for i in range(1, 11)  # 10 gaps
        ]
        
        result = KnowledgeGapResult(
            research_complete=False,
            research_context=context,
            gaps_identified=gaps,
            analysis_summary=summary,
            total_gaps=10
        )
        assert len(result.gaps_identified) == 10
        
        # Too many gaps (> 10)
        too_many_gaps = [
            KnowledgeGap(
                gap_id=f"gap_{i}",
                description=f"Gap description number {i}",
                priority="low",
                research_approach="Research approach"
            )
            for i in range(1, 12)  # 11 gaps
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGapResult(
                research_complete=False,
                research_context=context,
                gaps_identified=too_many_gaps,
                analysis_summary=summary,
                total_gaps=11
            )
        assert "at most 10 items" in str(exc_info.value)
    
    def test_total_gaps_validation(self):
        """Test total_gaps matches gaps_identified length"""
        gaps = [
            KnowledgeGap(
                gap_id="gap_1",
                description="First gap description",
                priority="high",
                research_approach="Research approach 1"
            ),
            KnowledgeGap(
                gap_id="gap_2", 
                description="Second gap description",
                priority="medium",
                research_approach="Research approach 2"
            )
        ]
        
        # Matching counts (should work)
        result = KnowledgeGapResult(
            research_complete=False,
            research_context="Valid research context for testing",
            gaps_identified=gaps,
            analysis_summary="Valid analysis summary that meets minimum length requirements",
            total_gaps=2
        )
        assert result.total_gaps == len(result.gaps_identified)
        
        # Mismatched counts (should fail)
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGapResult(
                research_complete=False,
                research_context="Valid research context for testing",
                gaps_identified=gaps,
                analysis_summary="Valid analysis summary that meets minimum length requirements",
                total_gaps=3  # Doesn't match len(gaps_identified) = 2
            )
        assert "total_gaps must match length of gaps_identified" in str(exc_info.value)
    
    def test_total_gaps_range_validation(self):
        """Test total_gaps non-negative constraint"""
        with pytest.raises(ValidationError) as exc_info:
            KnowledgeGapResult(
                research_complete=True,
                research_context="Valid research context for testing",
                gaps_identified=[],
                analysis_summary="Valid analysis summary that meets minimum length requirements",
                total_gaps=-1  # Negative value
            )
        assert "greater than or equal to 0" in str(exc_info.value)
    
    def test_default_values(self):
        """Test default field values"""
        result = KnowledgeGapResult(
            research_complete=True,
            research_context="Valid research context for testing",
            gaps_identified=[],
            analysis_summary="Valid analysis summary that meets minimum length requirements",
            total_gaps=0
        )
        
        assert result.schema_version == 1  # Default
        assert result.research_completeness_confidence == 1.0  # Default
        assert result.iteration_context is None  # Default


class TestSchemaJsonSerialization:
    """Test JSON serialization of knowledge gap schemas"""
    
    def test_knowledge_gap_serialization(self):
        """Test KnowledgeGap JSON serialization"""
        gap = KnowledgeGap(
            gap_id="gap_healthcare_ai",
            description="Recent AI applications in healthcare diagnostics need investigation",
            priority="high",
            research_approach="Search PubMed and clinical trial databases",
            confidence=0.85,
            category="healthcare"
        )
        
        # Test serialization
        json_str = gap.model_dump_json()
        parsed = json.loads(json_str)
        
        assert parsed["gap_id"] == "gap_healthcare_ai"
        assert parsed["description"] == "Recent AI applications in healthcare diagnostics need investigation"
        assert parsed["priority"] == "high"
        assert parsed["research_approach"] == "Search PubMed and clinical trial databases"
        assert parsed["confidence"] == 0.85
        assert parsed["category"] == "healthcare"
    
    def test_knowledge_gap_result_serialization(self):
        """Test KnowledgeGapResult JSON serialization"""
        gaps = [
            KnowledgeGap(
                gap_id="gap_1",
                description="AI regulatory framework research needed",
                priority="high",
                research_approach="Review FDA guidelines and recent policy updates"
            )
        ]
        
        result = KnowledgeGapResult(
            research_complete=False,
            research_completeness_confidence=0.7,
            research_context="AI in healthcare with regulatory compliance focus",
            gaps_identified=gaps,
            analysis_summary="Research covers basic AI concepts but lacks regulatory compliance analysis",
            total_gaps=1,
            iteration_context={"iteration": 2, "time_elapsed": 30.5}
        )
        
        # Test serialization
        json_str = result.model_dump_json()
        parsed = json.loads(json_str)
        
        # Validate structure
        required_fields = [
            "schema_version", "research_complete", "research_completeness_confidence",
            "research_context", "gaps_identified", "analysis_summary", "total_gaps"
        ]
        for field in required_fields:
            assert field in parsed
        
        assert parsed["schema_version"] == 1
        assert parsed["research_complete"] is False
        assert parsed["research_completeness_confidence"] == 0.7
        assert len(parsed["gaps_identified"]) == 1
        assert parsed["total_gaps"] == 1
        
        # Validate nested gap structure
        gap = parsed["gaps_identified"][0]
        assert gap["gap_id"] == "gap_1"
        assert gap["priority"] == "high"
    
    def test_deserialization_from_json(self):
        """Test creating schemas from JSON data"""
        json_data = {
            "schema_version": 1,
            "research_complete": False,
            "research_completeness_confidence": 0.8,
            "research_context": "AI research with focus on machine learning applications",
            "gaps_identified": [
                {
                    "gap_id": "gap_ml_ethics",
                    "description": "Ethical considerations in machine learning deployment",
                    "priority": "high",
                    "research_approach": "Review ethics literature and case studies",
                    "confidence": 0.9,
                    "category": "ethics"
                }
            ],
            "analysis_summary": "Research covers technical aspects but lacks ethical framework analysis",
            "total_gaps": 1,
            "iteration_context": {"iteration": 1}
        }
        
        # Create from dict
        result = KnowledgeGapResult(**json_data)
        
        assert result.research_complete is False
        assert result.research_completeness_confidence == 0.8
        assert len(result.gaps_identified) == 1
        assert result.gaps_identified[0].gap_id == "gap_ml_ethics"
        assert result.gaps_identified[0].category == "ethics"
        assert result.iteration_context["iteration"] == 1


class TestBackwardCompatibility:
    """Test backward compatibility with legacy KnowledgeGapOutput"""
    
    def test_knowledge_gap_output_alias(self):
        """Test that KnowledgeGapOutput is an alias for KnowledgeGapResult"""
        assert KnowledgeGapOutput is KnowledgeGapResult
    
    def test_legacy_schema_compatibility(self):
        """Test compatibility with legacy usage patterns"""
        # Should work with the alias
        result = KnowledgeGapOutput(
            research_complete=True,
            research_context="Valid research context for legacy compatibility testing",
            gaps_identified=[],
            analysis_summary="Legacy compatibility test summary that meets minimum length requirements",
            total_gaps=0
        )
        
        assert isinstance(result, KnowledgeGapResult)
        assert result.research_complete is True
        assert result.total_gaps == 0
    
    def test_json_deserialization_compatibility(self):
        """Test JSON deserialization works with both names"""
        json_data = {
            "schema_version": 1,
            "research_complete": True,
            "research_context": "Legacy JSON compatibility testing context",
            "gaps_identified": [],
            "analysis_summary": "Legacy JSON deserialization test that meets minimum length requirements",
            "total_gaps": 0
        }
        
        # Both should work
        result1 = KnowledgeGapResult(**json_data)
        result2 = KnowledgeGapOutput(**json_data)
        
        assert result1.research_complete == result2.research_complete
        assert result1.total_gaps == result2.total_gaps
        assert type(result1) is type(result2)


class TestEdgeCasesAndBoundaryValues:
    """Test edge cases and boundary value validation"""
    
    def test_minimum_valid_values(self):
        """Test minimum valid field values"""
        # Minimum valid KnowledgeGap
        gap = KnowledgeGap(
            gap_id="abc",  # Exactly 3 chars
            description="A" * 10,  # Exactly 10 chars
            priority="low",
            research_approach="B" * 10,  # Exactly 10 chars
            confidence=0.0  # Minimum confidence
        )
        assert gap.gap_id == "abc"
        assert len(gap.description) == 10
        assert gap.confidence == 0.0
        
        # Minimum valid KnowledgeGapResult
        result = KnowledgeGapResult(
            research_complete=True,
            research_context="C" * 20,  # Exactly 20 chars
            gaps_identified=[],  # Minimum length (0)
            analysis_summary="D" * 50,  # Exactly 50 chars
            total_gaps=0  # Minimum value
        )
        assert len(result.research_context) == 20
        assert len(result.analysis_summary) == 50
        assert result.total_gaps == 0
    
    def test_maximum_valid_values(self):
        """Test maximum valid field values"""
        # Maximum valid KnowledgeGap
        gap = KnowledgeGap(
            gap_id="a" * 50,  # Exactly 50 chars
            description="b" * 500,  # Exactly 500 chars
            priority="high",
            research_approach="c" * 200,  # Exactly 200 chars
            confidence=1.0,  # Maximum confidence
            category="d" * 50  # Exactly 50 chars
        )
        assert len(gap.gap_id) == 50
        assert len(gap.description) == 500
        assert len(gap.research_approach) == 200
        assert len(gap.category) == 50
        assert gap.confidence == 1.0
        
        # Maximum valid KnowledgeGapResult with maximum gaps
        gaps = [
            KnowledgeGap(
                gap_id=f"gap{i}",
                description="Valid gap description",
                priority="medium",
                research_approach="Valid research approach"
            )
            for i in range(10)  # Exactly 10 gaps
        ]
        
        result = KnowledgeGapResult(
            research_complete=False,
            research_context="e" * 1000,  # Exactly 1000 chars
            gaps_identified=gaps,
            analysis_summary="f" * 2000,  # Exactly 2000 chars
            total_gaps=10  # Maximum gaps
        )
        assert len(result.research_context) == 1000
        assert len(result.analysis_summary) == 2000
        assert len(result.gaps_identified) == 10
        assert result.total_gaps == 10