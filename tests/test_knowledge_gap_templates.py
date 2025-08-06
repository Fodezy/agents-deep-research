"""Tests for knowledge gap analysis template system"""
import pytest
import re
from datetime import datetime
from deep_researcher.agents.utils.outlines_templates import (
    render_knowledge_gap_prompt,
    render_legacy_knowledge_gap_prompt,
    extract_knowledge_gap_params
)


class TestKnowledgeGapPromptRendering:
    """Test knowledge gap prompt rendering functions"""
    
    def test_basic_structured_prompt_rendering(self):
        """Test basic structured prompt rendering with minimal input"""
        research_context = "AI applications in healthcare"
        
        prompt = render_knowledge_gap_prompt(research_context)
        
        # Verify basic structure
        assert "Knowledge Gap Analyzer" in prompt
        assert "AI applications in healthcare" in prompt
        assert "Today's date is" in prompt
        assert "research progress" in prompt
        assert "Assessment of research completeness" in prompt
        assert "Identification of specific knowledge gaps" in prompt
        assert "Research approach suggestions" in prompt
        
        # Verify no placeholder tokens
        assert "{" not in prompt
        assert "}" not in prompt
        assert "placeholder" not in prompt.lower()
        
        # Verify date injection worked
        current_date = datetime.now().strftime('%Y-%m-%d')
        assert current_date in prompt
    
    def test_structured_prompt_with_background_context(self):
        """Test structured prompt with background context"""
        research_context = "AI applications in healthcare"
        background_context = "Focus on regulatory compliance and FDA guidelines"
        
        prompt = render_knowledge_gap_prompt(research_context, background_context)
        
        assert "AI applications in healthcare" in prompt
        assert "Background Context:" in prompt
        assert "regulatory compliance and FDA guidelines" in prompt
    
    def test_structured_prompt_with_findings_history(self):
        """Test structured prompt with findings history"""
        research_context = "AI applications in healthcare"
        findings_history = "Previous research covered basic AI concepts and machine learning fundamentals"
        
        prompt = render_knowledge_gap_prompt(research_context, findings_history=findings_history)
        
        assert "Research History:" in prompt
        assert "Previous research covered basic AI concepts" in prompt
    
    def test_structured_prompt_with_iteration_context(self):
        """Test structured prompt with iteration context"""
        research_context = "AI applications in healthcare"
        iteration_context = {
            "iteration": 3,
            "time_elapsed": 45.7,
            "max_time": 60
        }
        
        prompt = render_knowledge_gap_prompt(research_context, iteration_context=iteration_context)
        
        assert "Iteration: 3" in prompt
        assert "Time Elapsed: 45.7 of 60 minutes" in prompt
    
    def test_structured_prompt_with_all_parameters(self):
        """Test structured prompt with all parameters"""
        research_context = "AI applications in healthcare"
        background_context = "Focus on regulatory frameworks"
        findings_history = "Covered basic concepts, need specific applications"
        iteration_context = {"iteration": 2, "time_elapsed": 30.5}
        
        prompt = render_knowledge_gap_prompt(
            research_context, 
            background_context, 
            findings_history, 
            iteration_context
        )
        
        # All sections should be present
        assert "AI applications in healthcare" in prompt
        assert "Background Context:" in prompt
        assert "regulatory frameworks" in prompt
        assert "Research History:" in prompt
        assert "specific applications" in prompt
        assert "Iteration: 2" in prompt
        assert "30.5 minutes" in prompt
        
        # Verify structure
        assert "Assessment of research completeness" in prompt
        assert "confidence level (0.0-1.0)" in prompt
        assert "priority levels (high/medium/low)" in prompt
        assert "10-200 characters" in prompt
    
    def test_empty_optional_parameters(self):
        """Test structured prompt with empty optional parameters"""
        research_context = "AI applications in healthcare"
        
        # Empty strings should not create sections
        prompt = render_knowledge_gap_prompt(
            research_context, 
            background_context="", 
            findings_history="   ", 
            iteration_context={}
        )
        
        assert "Background Context:" not in prompt
        assert "Research History:" not in prompt
        assert "Iteration:" not in prompt
        assert research_context in prompt


class TestLegacyKnowledgeGapPromptRendering:
    """Test legacy knowledge gap prompt rendering functions"""
    
    def test_basic_legacy_prompt_rendering(self):
        """Test basic legacy prompt rendering with JSON format"""
        research_context = "AI applications in healthcare"
        
        prompt = render_legacy_knowledge_gap_prompt(research_context)
        
        # Verify JSON structure requirement
        assert "You MUST respond with a JSON object" in prompt
        assert "exactly this format" in prompt
        assert "no extra keys, no commentary" in prompt
        
        # Verify schema structure
        assert '"schema_version": 1' in prompt
        assert '"research_complete": false' in prompt
        assert '"research_completeness_confidence": 0.8' in prompt
        assert '"gaps_identified": [' in prompt
        assert '"gap_id": "gap_1"' in prompt
        assert '"description":' in prompt
        assert '"priority": "high"' in prompt
        assert '"research_approach":' in prompt
        assert '"confidence": 0.9' in prompt
        assert '"total_gaps": 1' in prompt
        
        # Verify date injection
        current_date = datetime.now().strftime('%Y-%m-%d')
        assert current_date in prompt
        
        # Verify context
        assert "AI applications in healthcare" in prompt
    
    def test_legacy_prompt_with_background_and_history(self):
        """Test legacy prompt with background context and history"""
        research_context = "AI applications in healthcare"
        background_context = "Regulatory compliance focus"
        findings_history = "Basic concepts covered"
        
        prompt = render_legacy_knowledge_gap_prompt(
            research_context, 
            background_context, 
            findings_history
        )
        
        assert "Background Context:" in prompt
        assert "Regulatory compliance focus" in prompt
        assert "Research History:" in prompt
        assert "Basic concepts covered" in prompt
        assert '"schema_version": 1' in prompt  # JSON structure should remain
    
    def test_legacy_prompt_with_iteration_context(self):
        """Test legacy prompt with iteration context"""
        research_context = "AI applications in healthcare"
        iteration_context = {"iteration": 4, "time_elapsed": 55.3}
        
        prompt = render_legacy_knowledge_gap_prompt(
            research_context, 
            iteration_context=iteration_context
        )
        
        assert "Iteration: 4" in prompt
        assert "55.3 minutes" in prompt
        assert "0-10 specific, actionable knowledge gaps" in prompt
    
    def test_legacy_prompt_field_constraints(self):
        """Test legacy prompt includes field constraint information"""
        research_context = "AI applications in healthcare"
        
        prompt = render_legacy_knowledge_gap_prompt(research_context)
        
        # Verify field constraints are documented
        assert "20-1000 chars" in prompt  # research_context
        assert "10-500 chars" in prompt   # gap description  
        assert "10-200 chars" in prompt   # research_approach
        assert "50-2000 chars" in prompt  # analysis_summary
    
    def test_legacy_prompt_completion_guidance(self):
        """Test legacy prompt includes completion guidance"""
        research_context = "AI applications in healthcare"
        
        prompt = render_legacy_knowledge_gap_prompt(research_context)
        
        assert "Set research_complete to true only if no significant gaps remain" in prompt
        assert "0-10 specific, actionable knowledge gaps" in prompt


class TestParameterExtraction:
    """Test input parameter extraction for knowledge gap analysis"""
    
    def test_extract_from_dictionary_input(self):
        """Test parameter extraction from dictionary input"""
        input_data = {
            "research_context": "AI in healthcare research",
            "background_context": "Regulatory focus",
            "findings_history": "Basic concepts covered",
            "iteration": 3,
            "time_elapsed": 45.2,
            "max_time": 60
        }
        
        params = extract_knowledge_gap_params(input_data)
        
        assert params["research_context"] == "AI in healthcare research"
        assert params["background_context"] == "Regulatory focus"
        assert params["findings_history"] == "Basic concepts covered"
        assert params["iteration_context"]["iteration"] == 3
        assert params["iteration_context"]["time_elapsed"] == 45.2
        assert params["iteration_context"]["max_time"] == 60
    
    def test_extract_with_query_fallback(self):
        """Test parameter extraction with query fallback"""
        input_data = {
            "query": "What are AI applications in healthcare?",
            "history": "Previous research on basic AI",
            "iteration_context": {"iteration": 2}
        }
        
        params = extract_knowledge_gap_params(input_data)
        
        assert params["research_context"] == "What are AI applications in healthcare?"
        assert params["findings_history"] == "Previous research on basic AI"
        assert params["iteration_context"]["iteration"] == 2
    
    def test_extract_from_structured_string(self):
        """Test parameter extraction from structured string input"""
        input_str = """Current Iteration Number: 3
Time Elapsed: 45.2 minutes of maximum 60 minutes

ORIGINAL QUERY:
What are the latest AI applications in healthcare?

BACKGROUND CONTEXT:
Focus on regulatory compliance and FDA guidelines for AI medical devices

HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
Previous research covered basic AI concepts but lacks specific healthcare applications and regulatory framework analysis."""
        
        params = extract_knowledge_gap_params(input_str)
        
        assert params["research_context"] == "What are the latest AI applications in healthcare?"
        assert params["background_context"] == "Focus on regulatory compliance and FDA guidelines for AI medical devices"
        assert "Previous research covered basic AI concepts" in params["findings_history"]
        assert params["iteration_context"]["iteration"] == 3
        assert params["iteration_context"]["time_elapsed"] == 45.2
        assert params["iteration_context"]["max_time"] == 60
    
    def test_extract_minimal_string_format(self):
        """Test parameter extraction from minimal string format"""
        input_str = """ORIGINAL QUERY:
AI healthcare applications

HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:
No previous actions available."""
        
        params = extract_knowledge_gap_params(input_str)
        
        assert params["research_context"] == "AI healthcare applications"
        assert params["background_context"] == ""
        assert params["findings_history"] == "No previous actions available."
        assert params["iteration_context"] is None
    
    def test_extract_with_only_query_section(self):
        """Test parameter extraction with only query section"""
        input_str = """ORIGINAL QUERY:
What are recent developments in AI for medical diagnosis?"""
        
        params = extract_knowledge_gap_params(input_str)
        
        assert params["research_context"] == "What are recent developments in AI for medical diagnosis?"
        assert params["background_context"] == ""
        assert params["findings_history"] == ""
        assert params["iteration_context"] is None
    
    def test_extract_time_without_maximum(self):
        """Test time extraction without maximum time specified"""
        input_str = """Current Iteration Number: 2
Time Elapsed: 30.5 minutes

ORIGINAL QUERY:
AI applications in healthcare"""
        
        params = extract_knowledge_gap_params(input_str)
        
        assert params["iteration_context"]["iteration"] == 2
        assert params["iteration_context"]["time_elapsed"] == 30.5
        assert "max_time" not in params["iteration_context"]
    
    def test_extract_fallback_string(self):
        """Test parameter extraction fallback for simple string"""
        input_str = "Simple research question about AI"
        
        params = extract_knowledge_gap_params(input_str)
        
        assert params["research_context"] == "Simple research question about AI"
        assert params["background_context"] == ""
        assert params["findings_history"] == ""
        assert params["iteration_context"] is None
    
    def test_extract_empty_iteration_context(self):
        """Test that empty iteration context returns None"""
        input_data = {
            "research_context": "AI research",
            "iteration_context": {}
        }
        
        params = extract_knowledge_gap_params(input_data)
        
        assert params["iteration_context"] is None
    
    def test_extract_graceful_extra_keys(self):
        """Test graceful handling of extra keys in dictionary input"""
        input_data = {
            "research_context": "AI research",
            "background_context": "Background info",
            "extra_key": "This should be ignored",
            "another_extra": 12345,
            "iteration": 1
        }
        
        params = extract_knowledge_gap_params(input_data)
        
        assert params["research_context"] == "AI research"
        assert params["background_context"] == "Background info"
        assert params["iteration_context"]["iteration"] == 1
        # Extra keys should not cause errors


class TestTemplateContentValidation:
    """Test template content validation and security"""
    
    def test_no_sql_injection_patterns(self):
        """Test that templates don't contain SQL injection vulnerabilities"""
        research_context = "AI applications'; DROP TABLE users; --"
        
        structured_prompt = render_knowledge_gap_prompt(research_context)
        legacy_prompt = render_legacy_knowledge_gap_prompt(research_context)
        
        # Input should be safely included without modification
        assert "DROP TABLE users" in structured_prompt
        assert "DROP TABLE users" in legacy_prompt
        # No SQL execution should occur - these are just text templates
    
    def test_no_code_injection_patterns(self):
        """Test that templates handle code-like input safely"""
        research_context = "AI applications ${eval('malicious_code')}"
        
        structured_prompt = render_knowledge_gap_prompt(research_context)
        legacy_prompt = render_legacy_knowledge_gap_prompt(research_context)
        
        # Input should be included as literal text
        assert "${eval('malicious_code')}" in structured_prompt
        assert "${eval('malicious_code')}" in legacy_prompt
    
    def test_special_characters_handling(self):
        """Test handling of special characters in input"""
        research_context = "AI & ML applications <tag>content</tag> \"quotes\""
        background_context = "Background with {braces} and [brackets]"
        
        structured_prompt = render_knowledge_gap_prompt(research_context, background_context)
        
        assert "AI & ML applications" in structured_prompt
        assert "<tag>content</tag>" in structured_prompt
        assert "{braces}" in structured_prompt
        assert "[brackets]" in structured_prompt
        assert '"quotes"' in structured_prompt
    
    def test_unicode_character_support(self):
        """Test support for Unicode characters"""
        research_context = "AI applications in healthcare 中文 émojis 🤖"
        
        structured_prompt = render_knowledge_gap_prompt(research_context)
        legacy_prompt = render_legacy_knowledge_gap_prompt(research_context)
        
        assert "中文" in structured_prompt
        assert "émojis" in structured_prompt
        assert "🤖" in structured_prompt
        assert "中文" in legacy_prompt
    
    def test_very_long_input_handling(self):
        """Test handling of very long input strings"""
        research_context = "A" * 2000  # Very long string
        background_context = "B" * 1000
        
        structured_prompt = render_knowledge_gap_prompt(research_context, background_context)
        
        # Should handle long strings without truncation in templates
        assert "A" * 100 in structured_prompt  # Sample check
        assert "B" * 100 in structured_prompt


class TestRuntimeDateInjection:
    """Test runtime date injection functionality"""
    
    def test_date_injection_accuracy(self):
        """Test that injected date matches current date"""
        research_context = "AI research"
        
        structured_prompt = render_knowledge_gap_prompt(research_context)
        legacy_prompt = render_legacy_knowledge_gap_prompt(research_context)
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        assert f"Today's date is {current_date}" in structured_prompt
        assert f"Today's date is {current_date}" in legacy_prompt
    
    def test_date_format_consistency(self):
        """Test consistent date format across templates"""
        research_context = "AI research"
        
        structured_prompt = render_knowledge_gap_prompt(research_context)
        legacy_prompt = render_legacy_knowledge_gap_prompt(research_context)
        
        # Extract date from prompts
        date_pattern = r"Today's date is (\d{4}-\d{2}-\d{2})"
        structured_match = re.search(date_pattern, structured_prompt)
        legacy_match = re.search(date_pattern, legacy_prompt)
        
        assert structured_match is not None
        assert legacy_match is not None
        assert structured_match.group(1) == legacy_match.group(1)
        
        # Verify format
        date_str = structured_match.group(1)
        assert re.match(r"\d{4}-\d{2}-\d{2}", date_str)
    
    def test_no_stale_date_injection(self):
        """Test that date is injected at runtime, not at import"""
        import importlib
        from deep_researcher.agents.utils import outlines_templates
        
        # Re-import module to test fresh injection
        importlib.reload(outlines_templates)
        
        research_context = "AI research"
        prompt = outlines_templates.render_knowledge_gap_prompt(research_context)
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        assert current_date in prompt
    
    def test_multiple_calls_same_date(self):
        """Test multiple calls within same day return same date"""
        research_context = "AI research"
        
        prompt1 = render_knowledge_gap_prompt(research_context)
        prompt2 = render_knowledge_gap_prompt(research_context)
        
        date_pattern = r"Today's date is (\d{4}-\d{2}-\d{2})"
        date1 = re.search(date_pattern, prompt1).group(1)
        date2 = re.search(date_pattern, prompt2).group(1)
        
        assert date1 == date2


class TestTemplateStructureValidation:
    """Test template structure and completeness"""
    
    def test_structured_template_required_sections(self):
        """Test that structured template contains all required sections"""
        research_context = "AI research"
        prompt = render_knowledge_gap_prompt(research_context)
        
        required_sections = [
            "Knowledge Gap Analyzer",
            "analyze the current research progress",
            "Assessment of research completeness",
            "Identification of specific knowledge gaps",
            "Research approach suggestions",
            "Confidence scores",
            "Overall analysis summary",
            "additional research tools and methods"
        ]
        
        for section in required_sections:
            assert section in prompt, f"Missing required section: {section}"
    
    def test_legacy_template_json_structure(self):
        """Test that legacy template includes proper JSON structure"""
        research_context = "AI research"
        prompt = render_legacy_knowledge_gap_prompt(research_context)
        
        # Verify JSON template structure
        json_fields = [
            "schema_version",
            "research_complete",
            "research_completeness_confidence", 
            "research_context",
            "gaps_identified",
            "analysis_summary",
            "total_gaps"
        ]
        
        for field in json_fields:
            assert f'"{field}":' in prompt, f"Missing JSON field: {field}"
        
        # Verify nested gap structure
        gap_fields = ["gap_id", "description", "priority", "research_approach", "confidence"]
        for field in gap_fields:
            assert f'"{field}":' in prompt, f"Missing gap field: {field}"
    
    def test_consistent_parameter_handling(self):
        """Test that both templates handle parameters consistently"""
        research_context = "AI research"
        background_context = "Background info"
        findings_history = "Previous findings"
        iteration_context = {"iteration": 2}
        
        structured_prompt = render_knowledge_gap_prompt(
            research_context, background_context, findings_history, iteration_context
        )
        legacy_prompt = render_legacy_knowledge_gap_prompt(
            research_context, background_context, findings_history, iteration_context
        )
        
        # Both should include the same input content
        assert research_context in structured_prompt
        assert research_context in legacy_prompt
        assert background_context in structured_prompt
        assert background_context in legacy_prompt
        assert findings_history in structured_prompt
        assert findings_history in legacy_prompt
        assert "Iteration: 2" in structured_prompt
        assert "Iteration: 2" in legacy_prompt
    
    def test_no_placeholder_tokens_remain(self):
        """Test that no placeholder tokens remain in rendered prompts"""
        research_context = "AI research"
        
        structured_prompt = render_knowledge_gap_prompt(research_context)
        legacy_prompt = render_legacy_knowledge_gap_prompt(research_context)
        
        # Common placeholder patterns that should not appear
        forbidden_patterns = [
            r"\$\{[^}]*\}",  # ${placeholder}
            r"TODO",
            r"PLACEHOLDER", 
            r"FIXME"
        ]
        
        for pattern in forbidden_patterns:
            matches = re.findall(pattern, structured_prompt, re.IGNORECASE)
            assert len(matches) == 0, f"Found placeholder pattern {pattern} in structured prompt: {matches}"
            
            matches = re.findall(pattern, legacy_prompt, re.IGNORECASE)
            assert len(matches) == 0, f"Found placeholder pattern {pattern} in legacy prompt: {matches}"
        
        # Check for specific problematic placeholders (but allow JSON structure in legacy)
        problematic_placeholders = [
            r"\{placeholder[^}]*\}",  # {placeholder...}
            r"\{[^}]*placeholder[^}]*\}",  # {...placeholder...}
            r"<placeholder[^>]*>",  # <placeholder>
        ]
        
        for pattern in problematic_placeholders:
            matches = re.findall(pattern, structured_prompt, re.IGNORECASE)
            assert len(matches) == 0, f"Found problematic placeholder {pattern} in structured prompt: {matches}"
            
            matches = re.findall(pattern, legacy_prompt, re.IGNORECASE) 
            assert len(matches) == 0, f"Found problematic placeholder {pattern} in legacy prompt: {matches}"