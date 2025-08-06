"""Tests for HYBRID-04a enhanced schemas and templates"""
import pytest
from deep_researcher.agents.utils.outlines_schemas import (
    EnhancedToolAgentOutput, 
    ToolAgentOutput,
    summarise_search_results,
    summarise_crawled_content
)
from deep_researcher.agents.utils.outlines_templates import (
    render_search_summary_prompt,
    render_legacy_search_summary_prompt,
    render_crawl_summary_prompt, 
    render_legacy_crawl_summary_prompt,
    extract_search_params,
    extract_crawl_params
)


class TestEnhancedToolAgentOutput:
    """Test enhanced schema with validation and metadata"""
    
    def test_basic_output_creation(self):
        """Test creating basic tool agent output"""
        output = EnhancedToolAgentOutput(
            output="This is a comprehensive summary of quantum computing research findings.",
            sources=["https://example.com", "https://test.org"]
        )
        
        assert output.output == "This is a comprehensive summary of quantum computing research findings."
        assert output.sources == ["https://example.com", "https://test.org"]
        assert output.processing_method is None
        assert output.confidence is None
        assert output.processing_time_ms is None
    
    def test_enhanced_output_with_metadata(self):
        """Test creating output with observability metadata"""
        output = EnhancedToolAgentOutput(
            output="Detailed analysis of AI breakthroughs in healthcare applications.",
            sources=["https://nature.com/ai", "https://science.org/healthcare"],
            processing_method="structured",
            confidence=0.92,
            processing_time_ms=245
        )
        
        assert output.processing_method == "structured"
        assert output.confidence == 0.92
        assert output.processing_time_ms == 245
    
    def test_validation_constraints(self):
        """Test schema validation constraints"""
        # Test minimum length validation
        with pytest.raises(ValueError, match="String should have at least 10 characters"):
            EnhancedToolAgentOutput(output="Short", sources=[])
        
        # Test confidence range validation
        with pytest.raises(ValueError, match="Input should be less than or equal to 1"):
            EnhancedToolAgentOutput(
                output="Valid length output here", 
                confidence=1.5
            )
        
        # Test negative processing time
        with pytest.raises(ValueError, match="Input should be greater than or equal to 0"):
            EnhancedToolAgentOutput(
                output="Valid output content",
                processing_time_ms=-100
            )
    
    def test_backward_compatibility_alias(self):
        """Test that ToolAgentOutput alias works correctly"""
        # Create using alias
        output = ToolAgentOutput(
            output="Legacy compatibility test output",
            sources=["https://legacy.com"]
        )
        
        # Should be instance of enhanced class
        assert isinstance(output, EnhancedToolAgentOutput)
        assert output.output == "Legacy compatibility test output"
        assert output.sources == ["https://legacy.com"]
        assert output.processing_method is None
    
    def test_max_sources_validation(self):
        """Test maximum sources constraint"""
        # Should work with 20 sources
        many_sources = [f"https://source{i}.com" for i in range(20)]
        output = EnhancedToolAgentOutput(
            output="Valid output with many sources",
            sources=many_sources
        )
        assert len(output.sources) == 20
        
        # Should fail with 21 sources  
        too_many_sources = [f"https://source{i}.com" for i in range(21)]
        with pytest.raises(ValueError, match="List should have at most 20 items"):
            EnhancedToolAgentOutput(
                output="Valid output with too many sources",
                sources=too_many_sources
            )


class TestSearchTemplates:
    """Test search agent template system"""
    
    def test_structured_search_prompt(self):
        """Test structured search prompt rendering"""
        prompt = render_search_summary_prompt(
            knowledge_gap="recent AI breakthroughs",
            search_query="AI breakthrough 2024",
            search_results="Mock search results with AI findings...",
            entity_website="https://ai.org"
        )
        
        assert "recent AI breakthroughs" in prompt
        assert "AI breakthrough 2024" in prompt
        assert "Mock search results with AI findings..." in prompt
        assert "Entity Website Context: https://ai.org" in prompt
        assert "Today's date is" in prompt
        
    def test_legacy_search_prompt(self):
        """Test legacy search prompt with JSON format"""
        prompt = render_legacy_search_summary_prompt(
            knowledge_gap="quantum computing applications",
            search_query="quantum apps 2024",
            search_results="Quantum research findings..."
        )
        
        assert "quantum computing applications" in prompt
        assert "quantum apps 2024" in prompt
        assert '"output":' in prompt
        assert '"sources":' in prompt
        assert "You MUST respond with valid JSON" in prompt
    
    def test_search_parameter_extraction_dict(self):
        """Test extracting search parameters from dictionary input"""
        task_dict = {
            "gap": "AI healthcare applications",
            "query": "AI health 2024",
            "entity_website": "https://healthcare.ai"
        }
        
        params = extract_search_params(task_dict)
        
        assert params["knowledge_gap"] == "AI healthcare applications"
        assert params["search_query"] == "AI health 2024"
        assert params["entity_website"] == "https://healthcare.ai"
    
    def test_search_parameter_extraction_string(self):
        """Test extracting parameters from string input"""
        # Structured string
        structured_input = "gap: quantum research\nquery: quantum 2024\nentity_website: https://quantum.org"
        params = extract_search_params(structured_input)
        
        assert params["knowledge_gap"] == "quantum research"
        assert params["search_query"] == "quantum 2024"
        assert params["entity_website"] == "https://quantum.org"
        
        # Simple string
        simple_input = "blockchain technology"
        params = extract_search_params(simple_input)
        
        assert params["knowledge_gap"] == "blockchain technology"
        assert params["search_query"] == "blockchain technology"
        assert params["entity_website"] is None


class TestCrawlTemplates:
    """Test crawl agent template system"""
    
    def test_structured_crawl_prompt(self):
        """Test structured crawl prompt rendering"""
        prompt = render_crawl_summary_prompt(
            knowledge_gap="company financial performance",
            target_website="https://company.com/annual-report",
            crawled_content="Financial data and revenue information...",
            search_query="company finances"
        )
        
        assert "company financial performance" in prompt
        assert "https://company.com/annual-report" in prompt
        assert "Financial data and revenue information..." in prompt
        assert "Search Query Context: company finances" in prompt
        assert "Today's date is" in prompt
    
    def test_legacy_crawl_prompt(self):
        """Test legacy crawl prompt with JSON format"""
        prompt = render_legacy_crawl_summary_prompt(
            knowledge_gap="product specifications",
            target_website="https://product.com/specs",
            crawled_content="Technical specifications content..."
        )
        
        assert "product specifications" in prompt
        assert "https://product.com/specs" in prompt
        assert '"output":' in prompt
        assert '"sources": ["https://product.com/specs"]' in prompt
        assert "You MUST respond with valid JSON" in prompt
    
    def test_crawl_parameter_extraction_dict(self):
        """Test extracting crawl parameters from dictionary input"""
        task_dict = {
            "gap": "market analysis",
            "entity_website": "https://market.com/report",
            "query": "market trends"
        }
        
        params = extract_crawl_params(task_dict)
        
        assert params["knowledge_gap"] == "market analysis"
        assert params["target_website"] == "https://market.com/report"
        assert params["search_query"] == "market trends"
    
    def test_crawl_parameter_extraction_string(self):
        """Test extracting parameters from string input"""
        # Structured string
        structured_input = "gap: tech analysis\nentity_website: https://tech.com\nquery: tech report"
        params = extract_crawl_params(structured_input)
        
        assert params["knowledge_gap"] == "tech analysis"
        assert params["target_website"] == "https://tech.com"
        assert params["search_query"] == "tech report"
        
        # Simple string (URL)
        url_input = "https://company.com"
        params = extract_crawl_params(url_input)
        
        assert params["knowledge_gap"] == "https://company.com"
        assert params["target_website"] == "https://company.com"
        assert params["search_query"] is None


class TestSchemaFunctions:
    """Test Outlines function schema definitions"""
    
    def test_search_function_signature(self):
        """Test search function has correct signature for Outlines"""
        import inspect
        
        sig = inspect.signature(summarise_search_results)
        params = list(sig.parameters.keys())
        
        assert "knowledge_gap" in params
        assert "search_query" in params
        assert "search_results" in params
        assert "entity_website" in params
        assert sig.return_annotation == EnhancedToolAgentOutput
    
    def test_crawl_function_signature(self):
        """Test crawl function has correct signature for Outlines"""
        import inspect
        
        sig = inspect.signature(summarise_crawled_content)
        params = list(sig.parameters.keys())
        
        assert "knowledge_gap" in params
        assert "target_website" in params
        assert "crawled_content" in params
        assert "search_query" in params
        assert sig.return_annotation == EnhancedToolAgentOutput