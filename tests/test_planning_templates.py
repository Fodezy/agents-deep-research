"""Tests for planning template system"""
import pytest
import re
import time
from deep_researcher.agents.utils.outlines_templates import (
    render_planning_prompt, 
    render_legacy_planning_prompt,
    extract_planner_params
)


class TestPlanningTemplateRendering:
    """Test planning template rendering without placeholders"""
    
    def test_structured_planning_template_no_placeholders(self):
        """Test that structured planning template has no literal placeholders"""
        research_question = "What are the applications of machine learning?"
        context = "Focus on 2024 developments"
        
        prompt = render_planning_prompt(research_question, context)
        
        # Should not contain literal placeholders
        assert "{research_question}" not in prompt
        assert "{context}" not in prompt
        assert "{current_date}" not in prompt
        assert "{context_section}" not in prompt
        
        # Should contain actual values
        assert "machine learning" in prompt
        assert "2024 developments" in prompt
        assert "2025-08-0" in prompt  # Current date should be injected
        assert "Background Context:" in prompt
    
    def test_legacy_planning_template_no_placeholders(self):
        """Test that legacy planning template has no literal placeholders"""
        research_question = "How does artificial intelligence impact healthcare?"
        context = "Consider recent regulatory changes"
        
        prompt = render_legacy_planning_prompt(research_question, context)
        
        # Should not contain literal placeholders
        assert "{research_question}" not in prompt
        assert "{context}" not in prompt
        assert "{current_date}" not in prompt
        assert "{context_section}" not in prompt
        
        # Should contain actual values and JSON schema
        assert "artificial intelligence" in prompt
        assert "healthcare" in prompt
        assert "regulatory changes" in prompt
        assert '"schema_version": 1' in prompt
        assert '"report_title"' in prompt
        assert '"background_context"' in prompt
        assert '"report_outline"' in prompt
        assert "2025-08-0" in prompt
    
    def test_structured_planning_template_without_context(self):
        """Test structured template handles empty context gracefully"""
        research_question = "What is quantum computing?"
        
        # Test with empty string
        prompt1 = render_planning_prompt(research_question, "")
        assert "Background Context:" not in prompt1
        assert "quantum computing" in prompt1
        
        # Test without context parameter (default)
        prompt2 = render_planning_prompt(research_question)
        assert "Background Context:" not in prompt2
        assert "quantum computing" in prompt2
        
        # Both should be equivalent
        assert prompt1 == prompt2
    
    def test_legacy_planning_template_without_context(self):
        """Test legacy template handles empty context gracefully"""
        research_question = "What is blockchain technology?"
        
        # Test with empty string
        prompt1 = render_legacy_planning_prompt(research_question, "")
        assert "Background Context:" not in prompt1
        assert "blockchain technology" in prompt1
        assert '"schema_version": 1' in prompt1
        
        # Test without context parameter (default)
        prompt2 = render_legacy_planning_prompt(research_question)
        assert "Background Context:" not in prompt2
        assert "blockchain technology" in prompt2
        
        # Both should be equivalent
        assert prompt1 == prompt2
    
    def test_context_formatting(self):
        """Test that context is properly formatted when provided"""
        research_question = "AI in education"
        context = "Recent studies show increased adoption"
        
        structured_prompt = render_planning_prompt(research_question, context)
        legacy_prompt = render_legacy_planning_prompt(research_question, context)
        
        # Both should include the context section
        assert "Background Context:" in structured_prompt
        assert "Recent studies show increased adoption" in structured_prompt
        
        assert "Background Context:" in legacy_prompt
        assert "Recent studies show increased adoption" in legacy_prompt


class TestRuntimeDateInjection:
    """Test that templates inject date at runtime, not import time"""
    
    def test_templates_use_runtime_injection(self):
        """Test that templates populate date at runtime, not at import time"""
        research_question = "Test research question"
        context = "Test context"
        
        # Call templates twice with small delay
        prompt1 = render_planning_prompt(research_question, context)
        time.sleep(0.001)  # Small delay
        prompt2 = render_planning_prompt(research_question, context)
        
        # Both should contain current date (may be same if called quickly)
        assert "2025-08-0" in prompt1
        assert "2025-08-0" in prompt2
        
        # Same test for legacy template
        legacy_prompt1 = render_legacy_planning_prompt(research_question, context)
        time.sleep(0.001)
        legacy_prompt2 = render_legacy_planning_prompt(research_question, context)
        
        assert "2025-08-0" in legacy_prompt1
        assert "2025-08-0" in legacy_prompt2
    
    def test_date_format_consistency(self):
        """Test that date format is consistent across templates"""
        research_question = "Test question"
        
        structured_prompt = render_planning_prompt(research_question)
        legacy_prompt = render_legacy_planning_prompt(research_question)
        
        # Extract dates using regex
        date_pattern = r"Today's date is (\d{4}-\d{2}-\d{2})"
        
        structured_match = re.search(date_pattern, structured_prompt)
        legacy_match = re.search(date_pattern, legacy_prompt)
        
        assert structured_match is not None, "Date not found in structured prompt"
        assert legacy_match is not None, "Date not found in legacy prompt"
        
        # Dates should be the same (assuming called within same day)
        assert structured_match.group(1) == legacy_match.group(1)


class TestTemplateContentValidation:
    """Test template content structure and requirements"""
    
    def test_structured_template_includes_requirements(self):
        """Test that structured template includes all necessary requirements"""
        prompt = render_planning_prompt("AI research question")
        
        # Should include role definition
        assert "Report Planner" in prompt
        
        # Should include task description
        assert "comprehensive research plan" in prompt
        assert "manageable sections" in prompt
        
        # Should include requirements
        assert "report title" in prompt
        assert "10-100 characters" in prompt
        assert "Background context" in prompt
        assert "50-1000 characters" in prompt
        assert "2-5 research sections" in prompt
        assert "5-80 characters" in prompt
        assert "10-200 characters" in prompt
        
        # Should include guidance
        assert "independently" in prompt
        assert "comprehensive answer" in prompt
    
    def test_legacy_template_includes_json_schema(self):
        """Test that legacy template includes proper JSON schema"""
        prompt = render_legacy_planning_prompt("Blockchain research")
        
        # Should include JSON requirements
        assert "JSON object" in prompt
        assert "exactly this format" in prompt
        assert "no extra keys" in prompt
        assert "no commentary" in prompt
        
        # Should include schema structure
        assert '"schema_version": 1' in prompt
        assert '"report_title"' in prompt
        assert '"background_context"' in prompt
        assert '"report_outline"' in prompt
        
        # Should include field descriptions
        assert "10-100 chars" in prompt
        assert "50-1000 chars" in prompt
        assert "5-80 chars" in prompt
        assert "10-200 chars" in prompt
        
        # Should include guidance
        assert "2-5 sections" in prompt
        assert "independently" in prompt
    
    def test_parameter_injection_security(self):
        """Test that parameters are safely injected without code execution"""
        # Test with potentially problematic input
        malicious_question = "Test {eval('print(\"hack\")')}"
        malicious_context = "Context with {import os; os.system('echo hack')}"
        
        structured_prompt = render_planning_prompt(malicious_question, malicious_context)
        legacy_prompt = render_legacy_planning_prompt(malicious_question, malicious_context)
        
        # Should contain the literal text, not execute it
        assert "{eval" in structured_prompt
        assert "{import" in structured_prompt
        assert "{eval" in legacy_prompt
        assert "{import" in legacy_prompt
        
        # Should not contain executed results
        assert "hack" not in structured_prompt or "hack" in malicious_question or "hack" in malicious_context
        assert "hack" not in legacy_prompt or "hack" in malicious_question or "hack" in malicious_context


class TestTemplateConsistency:
    """Test consistency between structured and legacy templates"""
    
    def test_role_definition_consistency(self):
        """Test that both templates define the same role"""
        research_question = "Test consistency"
        
        structured_prompt = render_planning_prompt(research_question)
        legacy_prompt = render_legacy_planning_prompt(research_question)
        
        # Both should define the same role
        assert "Report Planner" in structured_prompt
        assert "Report Planner" in legacy_prompt
        
        # Both should mention research project
        assert "research project" in structured_prompt
        assert "research project" in legacy_prompt
    
    def test_task_description_consistency(self):
        """Test that both templates describe the same task"""
        research_question = "Test task description"
        
        structured_prompt = render_planning_prompt(research_question)
        legacy_prompt = render_legacy_planning_prompt(research_question)
        
        # Core task elements should be present in both
        common_elements = [
            "comprehensive research plan",
            "manageable sections",
            "2-5",
            "independently"
        ]
        
        for element in common_elements:
            assert element in structured_prompt, f"Missing '{element}' in structured prompt"
            assert element in legacy_prompt, f"Missing '{element}' in legacy prompt"
    
    def test_field_constraints_consistency(self):
        """Test that both templates specify the same field constraints"""
        research_question = "Test constraints"
        
        structured_prompt = render_planning_prompt(research_question)
        legacy_prompt = render_legacy_planning_prompt(research_question)
        
        # Field constraints should match
        constraints = [
            "10-100 characters",
            "50-1000 characters", 
            "5-80 characters",
            "10-200 characters"
        ]
        
        for constraint in constraints:
            # Structured template should mention constraints (in descriptive form)
            assert any(constraint.replace("characters", "chars") in structured_prompt or 
                      constraint in structured_prompt 
                      for constraint in constraints)
            
            # Legacy template should mention constraints (in abbreviated form)
            constraint_abbrev = constraint.replace("characters", "chars")
            assert constraint_abbrev in legacy_prompt, f"Missing '{constraint_abbrev}' in legacy prompt"


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_research_question(self):
        """Test templates handle empty research question"""
        structured_prompt = render_planning_prompt("")
        legacy_prompt = render_legacy_planning_prompt("")
        
        # Templates should still render without error
        assert "Report Planner" in structured_prompt
        assert "Report Planner" in legacy_prompt
        assert "Research Question:" in structured_prompt
        assert "Research Question:" in legacy_prompt
    
    def test_very_long_inputs(self):
        """Test templates handle very long inputs"""
        long_question = "A" * 1000  # Very long question
        long_context = "B" * 2000   # Very long context
        
        structured_prompt = render_planning_prompt(long_question, long_context)
        legacy_prompt = render_legacy_planning_prompt(long_question, long_context)
        
        # Should include the inputs
        assert "A" in structured_prompt
        assert "B" in structured_prompt
        assert "A" in legacy_prompt
        assert "B" in legacy_prompt
        
        # Should still have proper structure
        assert "Report Planner" in structured_prompt
        assert "JSON object" in legacy_prompt
    
    def test_special_characters_in_inputs(self):
        """Test templates handle special characters properly"""
        special_question = 'Question with "quotes" and \'apostrophes\' and {braces}'
        special_context = 'Context with <tags> and [brackets] and (parentheses)'
        
        structured_prompt = render_planning_prompt(special_question, special_context)
        legacy_prompt = render_legacy_planning_prompt(special_question, special_context)
        
        # Should preserve special characters
        assert '"quotes"' in structured_prompt
        assert "'apostrophes'" in structured_prompt
        assert "{braces}" in structured_prompt
        assert "<tags>" in structured_prompt
        assert "[brackets]" in structured_prompt
        assert "(parentheses)" in structured_prompt
        
        # Same for legacy
        assert '"quotes"' in legacy_prompt
        assert "'apostrophes'" in legacy_prompt
        assert "{braces}" in legacy_prompt
        assert "<tags>" in legacy_prompt


class TestPlannerParameterExtraction:
    """Test input parameter extraction for planning"""
    
    def test_extract_from_dict_input(self):
        """Test extraction from direct dictionary input"""
        input_data = {
            "research_question": "What is machine learning?",
            "context": "Focus on recent developments"
        }
        
        result = extract_planner_params(input_data)
        
        assert result["research_question"] == "What is machine learning?"
        assert result["context"] == "Focus on recent developments"
    
    def test_extract_from_dict_with_aliases(self):
        """Test extraction using field aliases"""
        input_data = {
            "query": "What is artificial intelligence?",
            "background_context": "Consider ethical implications"
        }
        
        result = extract_planner_params(input_data)
        
        assert result["research_question"] == "What is artificial intelligence?"
        assert result["context"] == "Consider ethical implications"
    
    def test_extract_handles_extra_keys(self):
        """Test that extraction ignores extra keys gracefully"""
        input_data = {
            "research_question": "Quantum computing applications",
            "context": "Focus on 2024 developments",
            "user_id": "12345",  # Extra key
            "session_id": "abc",  # Another extra key
            "available_agents": ["WebSearchAgent", "SiteCrawlerAgent"]  # Extra key
        }
        
        result = extract_planner_params(input_data)
        
        assert "research_question" in result
        assert "context" in result
        assert "user_id" not in result
        assert "session_id" not in result
        assert "available_agents" not in result
        assert result["research_question"] == "Quantum computing applications"
        assert result["context"] == "Focus on 2024 developments"
    
    def test_extract_from_simple_query_string(self):
        """Test extraction from simple QUERY format"""
        input_data = "QUERY: What are the benefits of renewable energy?"
        
        result = extract_planner_params(input_data)
        
        assert result["research_question"] == "What are the benefits of renewable energy?"
        assert result["context"] == ""
    
    def test_extract_from_query_with_whitespace(self):
        """Test extraction handles whitespace in QUERY format"""
        input_data = "  QUERY:   What is blockchain technology?  "
        
        result = extract_planner_params(input_data)
        
        assert result["research_question"] == "What is blockchain technology?"
        assert result["context"] == ""
    
    def test_extract_from_complex_formatted_string(self):
        """Test extraction from complex formatted string with context"""
        input_data = """QUERY: How does artificial intelligence impact healthcare?

CONTEXT: Consider recent FDA approvals and regulatory changes in 2024"""
        
        result = extract_planner_params(input_data)
        
        assert "artificial intelligence" in result["research_question"]
        assert "healthcare" in result["research_question"]
        assert "FDA approvals" in result["context"]
        assert "regulatory changes" in result["context"]
    
    def test_extract_from_background_formatted_string(self):
        """Test extraction recognizes BACKGROUND as alias for CONTEXT"""
        input_data = """QUERY: What are the latest developments in machine learning?

BACKGROUND: Focus on transformer architectures and large language models"""
        
        result = extract_planner_params(input_data)
        
        assert "machine learning" in result["research_question"]
        assert "transformer architectures" in result["context"]
        assert "large language models" in result["context"]
    
    def test_extract_fallback_string_handling(self):
        """Test fallback handling for unformatted strings"""
        input_data = "Research the impact of climate change on agriculture"
        
        result = extract_planner_params(input_data)
        
        assert result["research_question"] == "Research the impact of climate change on agriculture"
        assert result["context"] == ""
    
    def test_extract_from_non_string_types(self):
        """Test extraction from non-string, non-dict types"""
        # Test with number
        result1 = extract_planner_params(12345)
        assert result1["research_question"] == "12345"
        assert result1["context"] == ""
        
        # Test with None
        result2 = extract_planner_params(None)
        assert result2["research_question"] == "None"
        assert result2["context"] == ""
    
    def test_extract_empty_inputs(self):
        """Test extraction with empty inputs"""
        # Empty string
        result1 = extract_planner_params("")
        assert result1["research_question"] == ""
        assert result1["context"] == ""
        
        # Empty dict
        result2 = extract_planner_params({})
        assert result2["research_question"] == ""
        assert result2["context"] == ""
        
        # Dict with empty values
        result3 = extract_planner_params({"research_question": "", "context": ""})
        assert result3["research_question"] == ""
        assert result3["context"] == ""


class TestParameterExtractionIntegration:
    """Test parameter extraction integration with templates"""
    
    def test_extraction_with_structured_template(self):
        """Test parameter extraction works with structured template"""
        input_data = {
            "research_question": "AI in education",
            "context": "Focus on K-12 applications"
        }
        
        params = extract_planner_params(input_data)
        prompt = render_planning_prompt(**params)
        
        assert "AI in education" in prompt
        assert "K-12 applications" in prompt
        assert "Background Context:" in prompt
    
    def test_extraction_with_legacy_template(self):
        """Test parameter extraction works with legacy template"""
        input_data = "QUERY: What is the future of renewable energy?"
        
        params = extract_planner_params(input_data)
        prompt = render_legacy_planning_prompt(**params)
        
        assert "renewable energy" in prompt
        assert "JSON object" in prompt
        assert "Background Context:" not in prompt  # No context provided
    
    def test_end_to_end_parameter_flow(self):
        """Test complete parameter flow from input to template output"""
        # Test various input formats
        inputs = [
            {"research_question": "Quantum computing", "context": "Commercial applications"},
            "QUERY: Machine learning trends",
            """QUERY: Blockchain in finance

CONTEXT: Regulatory compliance and security concerns"""
        ]
        
        for input_data in inputs:
            params = extract_planner_params(input_data)
            
            # Both templates should work
            structured_prompt = render_planning_prompt(**params)
            legacy_prompt = render_legacy_planning_prompt(**params)
            
            # Should contain research question
            assert len(params["research_question"]) > 0
            assert params["research_question"] in structured_prompt
            assert params["research_question"] in legacy_prompt
            
            # Should handle context appropriately
            if params["context"]:
                assert params["context"] in structured_prompt
                assert params["context"] in legacy_prompt