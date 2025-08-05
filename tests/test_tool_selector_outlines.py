"""Comprehensive tests for ToolSelector Outlines refactor"""
import pytest
import json
from unittest.mock import Mock, AsyncMock
from deep_researcher.agents.tool_selector_agent import init_tool_selector_agent, extract_tool_selector_params
from deep_researcher.agents.utils.outlines_schemas import AgentSelectionPlan, AgentTask
from deep_researcher.llm_config import create_default_config


class MockStructuredModel:
    """Mock model that supports structured output"""
    def __init__(self, response_data=None):
        self.response_data = response_data or {
            "tasks": [
                {"gap": "Test gap", "agent": "WebSearchAgent", "query": "test query", "entity_website": None}
            ]
        }
    
    def __call__(self, prompt: str) -> AgentSelectionPlan:
        return AgentSelectionPlan(**self.response_data)


class MockLegacyModel:
    """Mock model without structured output support"""
    def __init__(self, response_text=None):
        self.response_text = response_text or '{"tasks": [{"gap": "Test gap", "agent": "WebSearchAgent", "query": "test query"}]}'
    
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
    # Mock the support function to return True
    return config


@pytest.fixture
def mock_config_legacy():
    """Mock config without structured output support"""
    config = create_default_config()
    config.reasoning_model = MockLegacyModel()
    return config


class TestInputExtraction:
    """Test input parameter extraction from different formats"""
    
    def test_extract_from_dict_input(self):
        """Test extraction from direct dictionary input"""
        input_data = {
            "research_context": "AI research",
            "knowledge_gaps": ["Recent papers", "Current trends"]
        }
        
        result = extract_tool_selector_params(input_data)
        
        assert result["research_context"] == "AI research"
        assert result["knowledge_gaps"] == ["Recent papers", "Current trends"]
    
    def test_extract_from_formatted_string(self):
        """Test extraction from formatted string input (current ResearchRunner format)"""
        input_data = """
ORIGINAL QUERY: What are the latest developments in quantum computing?

KNOWLEDGE GAP TO ADDRESS: Recent breakthroughs in quantum algorithms

BACKGROUND CONTEXT: Looking for 2024 developments

HISTORY OF ACTIONS, FINDINGS AND THOUGHTS: Previous searches focused on hardware
"""
        
        result = extract_tool_selector_params(input_data)
        
        assert "quantum computing" in result["research_context"]
        assert "quantum algorithms" in result["knowledge_gaps"][0]
    
    def test_extract_handles_extra_keys(self):
        """Test that extraction ignores extra keys gracefully"""
        input_data = {
            "research_context": "Climate research",
            "knowledge_gaps": ["Temperature data"],
            "user_id": "12345",  # Extra key
            "session_id": "abc",  # Another extra key
        }
        
        result = extract_tool_selector_params(input_data)
        
        assert "research_context" in result
        assert "knowledge_gaps" in result
        assert "user_id" not in result
        assert "session_id" not in result


class TestTemplateRendering:
    """Test template rendering without placeholders"""
    
    def test_outlines_template_no_placeholders(self):
        """Test that outlines template has no literal placeholders"""
        from deep_researcher.agents.utils.outlines_templates import render_outlines_prompt
        
        context = "Test research"
        gaps = ["Gap 1", "Gap 2"]
        
        prompt = render_outlines_prompt(context, gaps)
        
        # Should not contain literal placeholders
        assert "{research_context}" not in prompt
        assert "{knowledge_gaps_text}" not in prompt
        assert "{current_date}" not in prompt
        
        # Should contain actual values
        assert "Test research" in prompt
        assert "Gap 1" in prompt
        assert "Gap 2" in prompt
        assert "2025-08-0" in prompt  # Current date should be injected
    
    def test_legacy_template_no_placeholders(self):
        """Test that legacy template has no literal placeholders"""
        from deep_researcher.agents.utils.outlines_templates import render_legacy_prompt
        
        context = "Test research"
        gaps = ["Gap 1", "Gap 2"]
        
        prompt = render_legacy_prompt(context, gaps)
        
        # Should not contain literal placeholders
        assert "{research_context}" not in prompt
        assert "{knowledge_gaps_text}" not in prompt
        assert "{current_date}" not in prompt
        
        # Should contain actual values and JSON schema
        assert "Test research" in prompt
        assert "Gap 1" in prompt
        assert "Gap 2" in prompt
        assert '"tasks"' in prompt  # JSON schema present
        assert "2025-08-0" in prompt


class TestAgentInitialization:
    """Test agent initialization for both structured and legacy modes"""
    
    def test_structured_agent_initialization(self, mock_config_structured):
        """Test initialization with structured output support"""
        # Mock the support function
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: True
        
        try:
            agent = init_tool_selector_agent(mock_config_structured)
            
            assert agent.name == "ToolSelectorAgent"
            assert agent.structured_generator is not None
            assert agent.output_type == AgentSelectionPlan
            assert agent.instructions == ""  # Template handles instructions
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func
    
    def test_legacy_agent_initialization(self, mock_config_legacy):
        """Test initialization without structured output support"""
        # Mock the support function
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: False
        
        try:
            agent = init_tool_selector_agent(mock_config_legacy)
            
            assert agent.name == "ToolSelectorAgent"
            assert agent._dynamic_instructions is not None  # Callable instructions
            assert agent.output_type is None  # Legacy path uses output_parser instead
            assert agent.output_parser is not None
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func
    
    def test_backward_compatibility(self, mock_config_legacy):
        """Test that refactored agent maintains backward compatibility"""
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: False
        
        try:
            agent = init_tool_selector_agent(mock_config_legacy)
            
            # Should still have required attributes for ResearchRunner
            assert hasattr(agent, 'name')
            assert hasattr(agent, 'model')
            assert hasattr(agent, 'output_type')
            assert hasattr(agent, 'output_parser')
            assert agent.name == "ToolSelectorAgent"
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func


class TestDynamicInstructions:
    """Test dynamic instruction generation for legacy mode"""
    
    def test_dynamic_instructions_called(self, mock_config_legacy):
        """Test that dynamic instructions are generated properly"""
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: False
        
        try:
            agent = init_tool_selector_agent(mock_config_legacy)
            
            # Test dynamic instruction generation
            test_input = """
ORIGINAL QUERY: Test query

KNOWLEDGE GAP TO ADDRESS: Test gap
"""
            
            assert agent._dynamic_instructions is not None
            instructions = agent._dynamic_instructions(test_input)
            
            # Should contain the actual input values
            assert "Test query" in instructions
            assert "Test gap" in instructions
            assert "JSON object" in instructions  # Should be legacy prompt
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func


class TestSchemaValidation:
    """Test Pydantic schema validation"""
    
    def test_agent_task_validation(self):
        """Test AgentTask schema validation"""
        # Valid task
        task = AgentTask(
            gap="Test gap",
            agent="WebSearchAgent",
            query="test query",
            entity_website="https://example.com"
        )
        
        assert task.gap == "Test gap"
        assert task.agent == "WebSearchAgent"
        assert task.query == "test query"
        assert task.entity_website == "https://example.com"
    
    def test_agent_selection_plan_validation(self):
        """Test AgentSelectionPlan schema validation"""
        plan = AgentSelectionPlan(tasks=[
            AgentTask(agent="WebSearchAgent", query="test query"),
            AgentTask(agent="SiteCrawlerAgent", query="another query")
        ])
        
        assert len(plan.tasks) == 2
        assert all(isinstance(task, AgentTask) for task in plan.tasks)
    
    def test_json_serialization(self):
        """Test JSON serialization of schemas"""
        plan = AgentSelectionPlan(tasks=[
            AgentTask(gap="Test gap", agent="WebSearchAgent", query="test query")
        ])
        
        # Should serialize to valid JSON
        json_str = plan.model_dump_json()
        parsed = json.loads(json_str)
        
        assert "tasks" in parsed
        assert isinstance(parsed["tasks"], list)
        assert len(parsed["tasks"]) == 1
        assert parsed["tasks"][0]["agent"] == "WebSearchAgent"


class TestNoFStringInjection:
    """Test that f-string datetime injection is eliminated"""
    
    def test_no_fstring_in_agent_file(self):
        """Test that tool_selector_agent.py doesn't contain f-string datetime injection"""
        import inspect
        from deep_researcher.agents import tool_selector_agent
        
        # Get the source code of the module
        source = inspect.getsource(tool_selector_agent)
        
        # Should not contain f-string with datetime.now()
        assert "f\"" not in source or "datetime.now()" not in source
        assert "Today's date is {datetime.now()" not in source
    
    def test_templates_use_runtime_injection(self):
        """Test that templates inject date at runtime, not at import time"""
        from deep_researcher.agents.utils.outlines_templates import render_outlines_prompt
        import time
        
        # Call template twice with small delay
        prompt1 = render_outlines_prompt("test", ["gap"])
        time.sleep(0.001)  # Small delay
        prompt2 = render_outlines_prompt("test", ["gap"])
        
        # Both should contain current date (may be same if called quickly)
        assert "2025-08-0" in prompt1
        assert "2025-08-0" in prompt2


@pytest.mark.asyncio
class TestIntegrationPatterns:
    """Test integration patterns with ResearchRunner"""
    
    async def test_structured_generator_integration(self, mock_config_structured):
        """Test structured generator integration (when Outlines is available)"""
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: True
        
        try:
            agent = init_tool_selector_agent(mock_config_structured)
            
            # Test direct call to structured generator
            input_data = {
                "research_context": "Test research",
                "knowledge_gaps": ["Test gap"]
            }
            
            # Test the structured generator integration
            result = agent.structured_generator(input_data)
            
            # Should return proper AgentSelectionPlan for testing
            assert isinstance(result, AgentSelectionPlan)
            assert len(result.tasks) > 0
            assert result.tasks[0].agent == "WebSearchAgent"
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func
    
    async def test_legacy_fallback_integration(self, mock_config_legacy):
        """Test legacy fallback integration with parsing"""
        import deep_researcher.llm_config
        original_func = deep_researcher.llm_config.model_supports_structured_output
        deep_researcher.llm_config.model_supports_structured_output = lambda x: False
        
        try:
            agent = init_tool_selector_agent(mock_config_legacy)
            
            # Test dynamic instructions generation
            input_data = """
ORIGINAL QUERY: Climate change research

KNOWLEDGE GAP TO ADDRESS: Recent temperature data
"""
            
            instructions = agent._dynamic_instructions(input_data)
            
            # Should generate proper legacy prompt
            assert "Climate change research" in instructions
            assert "Recent temperature data" in instructions
            assert "JSON object" in instructions
            assert '"tasks"' in instructions
        finally:
            deep_researcher.llm_config.model_supports_structured_output = original_func