# 🎫 HYBRID-05: Outlines Refactor - ToolSelector Implementation Plan

Based on SL-X specification and analysis of the current ToolSelectorAgent implementation.

## Scope Definition (Per Guardrails)

**✅ Must Deliver:**

* Replace f-string prompting with Outlines `select_tools` function
* Achieve 98% valid JSON in tests with structured output validation
* Eliminate complex parsing fallback logic for ToolSelector
* Implement template-based dynamic content injection (date)
* Maintain backward compatibility with existing agent initialization
* **NO breaking changes** to existing ResearchRunner or agent workflows

**Success Gate:** 98% valid JSON output in comprehensive test suite

---

**❌ Out of Scope:**
- PlannerAgent refactor (HYBRID-06)
- KnowledgeGapAgent refactor (HYBRID-07)
- WriterAgent guardrails (HYBRID-09)
- ValidationWrapper integration (handled by HYBRID-02)

**📏 Budget Constraints:**
- Core refactor ≤ 100 LoC changes in tool_selector_agent.py
- New Outlines integration utilities ≤ 150 LoC total
- 1-day delivery timeline (per guardrails)

## Current State Analysis

### Existing Implementation Issues

1. **F-String Date Injection**
   ```python
   # Current problematic approach
   INSTRUCTIONS = f"""
   You are the Tool Selector. Today's date is {datetime.now():%Y-%m-%d}.
   ...
   """
   ```

2. **Hardcoded JSON Schema in Prompt**
   ```python
   # Manual schema definition - error-prone
   """
   {
     "tasks": [
       {
         "gap": "Describe the specific knowledge gap here",
         "agent": "WebSearchAgent",
         "query": "3–6 word query",
         "entity_website": "https://optional.domain.com"
       }
     ]
   }
   """
   ```

3. **Complex Fallback Parsing Logic**
   - 200+ lines of regex-based JSON fixing in `parse_output.py`
   - Special handling for bare task lists vs. wrapped format
   - Multiple parsing strategies with various fallbacks

4. **Dual Output Mode Complexity**
   ```python
   # Current complex conditional logic
   output_type=AgentSelectionPlan if model_supports_structured_output(selected_model) else None,
   output_parser=create_type_parser(AgentSelectionPlan) if not model_supports_structured_output(selected_model) else None
   ```

## Implementation Tasks

### Day 1: Core Outlines Integration

#### **Task 1: Create Outlines Function Schema**

**File:** `deep_researcher/agents/utils/outlines_schemas.py` (NEW)

```python
"""Outlines function schemas for structured agent output"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class AgentTask(BaseModel):
    gap: Optional[str] = Field(description="The knowledge gap being addressed", default=None)
    agent: str = Field(description="The name of the agent to use")
    query: str = Field(description="The specific query for the agent")
    entity_website: Optional[str] = Field(description="The website of the entity being researched, if known", default=None)

class AgentSelectionPlan(BaseModel):
    tasks: List[AgentTask] = Field(description="List of agent tasks to address knowledge gaps")

def select_tools(
    research_context: str,
    knowledge_gaps: List[str],
    available_agents: List[str],
    current_date: str = None
) -> AgentSelectionPlan:
    """
    Select appropriate research tools and create agent tasks to address knowledge gaps.
    
    Args:
        research_context: The overall research question or topic
        knowledge_gaps: List of specific information gaps to fill
        available_agents: List of available agent names (WebSearchAgent, SiteCrawlerAgent, etc.)
        current_date: Current date in YYYY-MM-DD format for context
        
    Returns:
        AgentSelectionPlan with list of agent tasks
    """
    pass  # Implementation will be handled by Outlines
```

#### **Task 2: Create Outlines Template System**

**File:** `deep_researcher/agents/utils/outlines_templates.py` (NEW)

```python
"""Template system for Outlines-based agents"""
from typing import Dict, Any, List
from datetime import datetime
import outlines

class OutlinesTemplate:
    """Base template class for dynamic content injection"""
    
    def __init__(self, base_prompt: str):
        self.base_prompt = base_prompt
    
    def render(self, **kwargs) -> str:
        """Render template with dynamic values"""
        # Handle datetime objects specially
        for key, value in kwargs.items():
            if isinstance(value, datetime):
                kwargs[key] = value.strftime('%Y-%m-%d')
        
        return self.base_prompt.format(**kwargs)

# ToolSelector-specific template
TOOL_SELECTOR_TEMPLATE = OutlinesTemplate("""
You are the Tool Selector for a research project. Today's date is {current_date}.

Your job is to analyze the research question and knowledge gaps, then select appropriate research agents and create specific tasks for each gap.

Available Research Agents:
- WebSearchAgent: Performs web searches for current information
- SiteCrawlerAgent: Crawls specific websites for detailed content
- DocumentAnalyzerAgent: Analyzes uploaded documents
- FactCheckerAgent: Verifies claims and checks accuracy

Research Context: {research_context}

Knowledge Gaps to Address:
{knowledge_gaps_text}

For each gap, create an agent task with:
- gap: Description of the specific knowledge gap
- agent: Most appropriate agent name from the available list
- query: Concise 3-6 word search query or task description
- entity_website: Optional website URL if relevant to the research

Select the most efficient combination of agents to fill all knowledge gaps without redundancy.
""")
```

#### **Task 3: Refactor ToolSelectorAgent with Outlines**

**File:** `deep_researcher/agents/tool_selector_agent.py` (MODIFIED)

```python
"""
Tool Selector Agent using Outlines for structured output generation
"""
from typing import List
from datetime import datetime
import outlines

from .baseclass import ResearchAgent  
from ..llm_config import LLMConfig, model_supports_structured_output
from .utils.outlines_schemas import select_tools, AgentSelectionPlan
from .utils.outlines_templates import TOOL_SELECTOR_TEMPLATE
from .utils.parse_output import create_type_parser

def init_tool_selector_agent(config: LLMConfig) -> ResearchAgent:
    """Initialize ToolSelectorAgent with Outlines structured output"""
    selected_model = config.main_model  # Use main model for planning tasks
    
    # Create Outlines-based structured generator
    if model_supports_structured_output(selected_model):
        # Use Outlines for guaranteed structured output
        generator = outlines.generate.json(selected_model, AgentSelectionPlan)
        
        def structured_call(research_context: str, knowledge_gaps: List[str]) -> AgentSelectionPlan:
            # Render template with dynamic content
            prompt = TOOL_SELECTOR_TEMPLATE.render(
                current_date=datetime.now(),
                research_context=research_context,
                knowledge_gaps_text="\n".join(f"- {gap}" for gap in knowledge_gaps)
            )
            
            # Generate structured output via Outlines
            return generator(prompt)
        
        return ResearchAgent(
            name="ToolSelectorAgent",
            instructions="",  # Instructions now in template
            model=selected_model,
            structured_generator=structured_call,  # New: Outlines generator
            output_type=AgentSelectionPlan
        )
    else:
        # Fallback for models without structured output support
        prompt = TOOL_SELECTOR_TEMPLATE.render(
            current_date=datetime.now(),
            research_context="{research_context}",  # Placeholder for runtime
            knowledge_gaps_text="{knowledge_gaps_text}"  # Placeholder for runtime
        )
        
        return ResearchAgent(
            name="ToolSelectorAgent", 
            instructions=prompt,
            model=selected_model,
            output_type=AgentSelectionPlan,
            output_parser=create_type_parser(AgentSelectionPlan)
        )
```

#### **Task 4: Enhance BaseClass for Outlines Support**

**File:** `deep_researcher/agents/baseclass.py` (MODIFIED)

```python
class ResearchAgent:
    def __init__(self, 
                 name: str,
                 instructions: str,
                 model,
                 tools: List = None,
                 output_type=None,
                 output_parser=None,
                 summariser=None,
                 structured_generator=None):  # NEW: Outlines generator
        # ... existing initialization ...
        self.structured_generator = structured_generator
    
    async def run(self, input_data: str, **kwargs) -> Any:
        """Enhanced run method with Outlines support"""
        if self.structured_generator:
            # Use Outlines structured generation
            try:
                # Parse input for structured call
                if isinstance(input_data, dict):
                    return self.structured_generator(**input_data)
                else:
                    # For simple string inputs, wrap in context
                    return self.structured_generator(
                        research_context=input_data,
                        knowledge_gaps=kwargs.get('knowledge_gaps', [])
                    )
            except Exception as e:
                print(f"[WARN] Structured generation failed: {e}, falling back to standard parsing")
                # Fallback to existing logic
        
        # Existing logic for non-structured output
        return await super().run(input_data, **kwargs)
```

### Day 1: Comprehensive Testing

#### **Task 5: Outlines-Specific Test Suite**

**File:** `tests/test_tool_selector_outlines.py` (NEW)

```python
"""Comprehensive tests for ToolSelector Outlines refactor"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
import json

from deep_researcher.agents.tool_selector_agent import init_tool_selector_agent
from deep_researcher.agents.utils.outlines_schemas import AgentSelectionPlan, AgentTask
from deep_researcher.llm_config import create_default_config

class MockOutlinesModel:
    """Mock model that returns valid JSON structure"""
    def __init__(self, response_data):
        self.response_data = response_data
    
    def __call__(self, prompt: str) -> AgentSelectionPlan:
        return AgentSelectionPlan(**self.response_data)

@pytest.fixture
def mock_config():
    """Mock config with Outlines-compatible model"""
    config = create_default_config()
    config.main_model = MockOutlinesModel({
        "tasks": [
            {
                "gap": "Recent developments in quantum computing",
                "agent": "WebSearchAgent", 
                "query": "quantum computing 2024",
                "entity_website": None
            }
        ]
    })
    return config

class TestToolSelectorOutlines:
    """Test Outlines-based ToolSelector implementation"""
    
    def test_structured_output_format(self, mock_config):
        """Test that Outlines generates valid AgentSelectionPlan structure"""
        agent = init_tool_selector_agent(mock_config)
        
        result = agent.structured_generator(
            research_context="Quantum computing research",
            knowledge_gaps=["Recent developments", "Key researchers"]
        )
        
        # Validate structure
        assert isinstance(result, AgentSelectionPlan)
        assert len(result.tasks) > 0
        
        # Validate first task
        task = result.tasks[0]
        assert isinstance(task, AgentTask)
        assert task.agent in ["WebSearchAgent", "SiteCrawlerAgent"]
        assert task.query is not None
        assert len(task.query.split()) <= 6  # 3-6 word constraint
    
    def test_json_validity_rate(self, mock_config):
        """Test 98% JSON validity requirement"""
        agent = init_tool_selector_agent(mock_config)
        
        # Test with 100 different inputs
        test_cases = [
            ("AI research", ["Recent papers", "Key conferences"]),
            ("Climate change", ["Current data", "Policy updates"]),
            ("Cryptocurrency", ["Market trends", "Regulations"]),
            # ... add 97 more test cases
        ]
        
        valid_outputs = 0
        total_tests = len(test_cases)
        
        for context, gaps in test_cases:
            try:
                result = agent.structured_generator(
                    research_context=context,
                    knowledge_gaps=gaps
                )
                
                # Validate JSON serialization
                json_str = result.model_dump_json()
                parsed = json.loads(json_str)
                
                # Validate required fields
                assert "tasks" in parsed
                assert isinstance(parsed["tasks"], list)
                
                valid_outputs += 1
            except Exception as e:
                print(f"Failed for {context}: {e}")
        
        validity_rate = valid_outputs / total_tests
        assert validity_rate >= 0.98, f"Only {validity_rate:.1%} valid, need ≥98%"
    
    def test_template_rendering(self):
        """Test dynamic template rendering with dates"""
        from deep_researcher.agents.utils.outlines_templates import TOOL_SELECTOR_TEMPLATE
        
        rendered = TOOL_SELECTOR_TEMPLATE.render(
            current_date=datetime(2024, 8, 2),
            research_context="Test research",
            knowledge_gaps_text="- Gap 1\n- Gap 2"
        )
        
        assert "2024-08-02" in rendered
        assert "Test research" in rendered
        assert "Gap 1" in rendered
        assert "Gap 2" in rendered
    
    def test_backward_compatibility(self, mock_config):
        """Test that refactored agent works with existing ResearchRunner"""
        agent = init_tool_selector_agent(mock_config)
        
        # Should still have required attributes
        assert hasattr(agent, 'name')
        assert hasattr(agent, 'model')
        assert hasattr(agent, 'output_type')
        assert agent.name == "ToolSelectorAgent"
    
    def test_fallback_for_unsupported_models(self):
        """Test fallback to parsing for models without structured output"""
        config = create_default_config()
        # Mock unsupported model
        config.main_model = Mock()
        
        # Should create agent with parse-based fallback
        agent = init_tool_selector_agent(config)
        assert agent.output_parser is not None
        assert agent.structured_generator is None
    
    def test_no_f_string_injection(self):
        """Verify no f-string datetime injection in static code"""
        from deep_researcher.agents.tool_selector_agent import init_tool_selector_agent
        import inspect
        
        source = inspect.getsource(init_tool_selector_agent)
        
        # Should not contain f-string with datetime
        assert "f\"" not in source or "datetime.now()" not in source
        assert "Today's date is {datetime.now()" not in source
    
    @pytest.mark.asyncio
    async def test_integration_with_research_runner(self, mock_config):
        """Test integration with existing ResearchRunner workflows"""
        agent = init_tool_selector_agent(mock_config)
        
        # Mock ResearchRunner call pattern
        input_data = {
            "research_context": "Quantum computing breakthrough",
            "knowledge_gaps": ["Recent papers", "Industry adoption"]
        }
        
        result = await agent.run(json.dumps(input_data))
        
        assert isinstance(result, (AgentSelectionPlan, dict))
        if isinstance(result, dict):
            assert "tasks" in result
```

### Day 1: Performance & Validation Testing

#### **Task 6: Performance Benchmark**

**File:** `tests/test_tool_selector_performance.py` (NEW)

```python
"""Performance tests for Outlines vs. traditional parsing"""
import pytest
import time
from deep_researcher.agents.tool_selector_agent import init_tool_selector_agent
from deep_researcher.llm_config import create_default_config

class TestPerformanceComparison:
    """Compare Outlines performance vs. traditional parsing"""
    
    @pytest.mark.benchmark
    def test_outlines_vs_parsing_latency(self):
        """Compare latency: Outlines vs. traditional parsing"""
        config = create_default_config()
        
        # Test with mock models for consistent timing
        test_input = {
            "research_context": "Climate change impacts",
            "knowledge_gaps": ["Temperature data", "Policy responses", "Economic effects"]
        }
        
        # Measure Outlines approach
        outlines_agent = init_tool_selector_agent(config)
        start = time.time()
        for _ in range(100):
            result = outlines_agent.structured_generator(**test_input)
        outlines_time = time.time() - start
        
        # Measure traditional parsing (if available for comparison)
        # ... comparison logic ...
        
        print(f"Outlines: {outlines_time:.3f}s for 100 calls")
        
        # Should meet latency requirements (≤ +20% per SL-X)
        assert outlines_time < 10.0  # Reasonable baseline
```

## Success Criteria

**Must Pass CI:**
- `pytest tests/test_tool_selector_outlines.py` → Green
- JSON validity rate ≥ 98% across test cases
- No f-string datetime injection in static code
- Backward compatibility with ResearchRunner maintained
- Performance impact ≤ +20% (per SL-X requirements)

**Demo Checkpoints:**
- **Mid-Day:** Outlines integration working with structured output
- **End-Day:** Full test suite green with 98% validity rate

## Files to Create/Modify

```
deep_researcher/
├── agents/
│   ├── utils/
│   │   ├── outlines_schemas.py        # New - Function schemas
│   │   ├── outlines_templates.py      # New - Template system
│   │   └── __init__.py                # Modified - Add exports
│   ├── tool_selector_agent.py         # Modified - Outlines integration
│   └── baseclass.py                   # Modified - Structured generator support

tests/
├── test_tool_selector_outlines.py     # New - Comprehensive Outlines tests
└── test_tool_selector_performance.py  # New - Performance benchmarks
```

## Risk Mitigation

1. **Outlines Integration Risk:** Start with simple cases, add fallback to existing parsing
2. **Performance Risk:** Benchmark against existing implementation, optimize if needed
3. **Model Compatibility Risk:** Test with multiple model types, maintain parser fallback
4. **Breaking Changes Risk:** Maintain existing agent interface, test ResearchRunner integration
5. **JSON Validity Risk:** Comprehensive test suite with edge cases and malformed inputs

## Implementation Details

### Outlines Function Schema Design

```python
# Function signature matches agent capabilities
def select_tools(
    research_context: str,           # Overall research question
    knowledge_gaps: List[str],       # Specific gaps to fill
    available_agents: List[str],     # Agent options
    current_date: str = None         # Dynamic date injection
) -> AgentSelectionPlan:            # Structured return type
```

### Template System Benefits

1. **No F-String Injection:** Templates rendered at runtime with proper escaping
2. **Dynamic Content:** Date, context, and gaps injected safely
3. **Reusable Patterns:** Template base class for other agents
4. **Type Safety:** Pydantic models ensure structure validity

### Structured Generator Pattern

```python
# Clean separation of concerns
structured_generator = lambda ctx, gaps: outlines.generate.json(
    model, 
    AgentSelectionPlan
)(TEMPLATE.render(context=ctx, gaps=gaps))
```

## Definition of Done

- [ ] F-string prompting eliminated from ToolSelectorAgent
- [ ] Outlines `select_tools` function schema implemented
- [ ] Template-based dynamic content injection working
- [ ] 98% JSON validity rate achieved in tests
- [ ] Backward compatibility maintained with ResearchRunner
- [ ] Performance impact ≤ +20% baseline
- [ ] Comprehensive test suite covering edge cases
- [ ] No breaking changes to existing agent workflows
- [ ] Fallback parsing for unsupported models
- [ ] Clean separation between Outlines and traditional approaches

**Ready for HYBRID-06:** This Outlines foundation enables the PlannerAgent refactor in the next ticket, demonstrating the template system and structured generation pattern for the broader agent overhaul.

## Interface Contract for Future Tickets

```python
# Expected usage pattern for other agent refactors
from deep_researcher.agents.utils.outlines_schemas import agent_function
from deep_researcher.agents.utils.outlines_templates import AGENT_TEMPLATE

# Template-based approach
prompt = AGENT_TEMPLATE.render(
    current_date=datetime.now(),
    **dynamic_context
)

# Structured generation
generator = outlines.generate.json(model, OutputSchema)
result = generator(prompt)

# Guaranteed JSON validity with Pydantic validation
assert isinstance(result, OutputSchema)
```

## 🛠 Key Design Decisions

### Major Design Choices ✅
1. **Template System over F-Strings:** Eliminates static datetime injection, enables runtime rendering
2. **Function Schema Approach:** `select_tools()` signature matches actual agent capabilities  
3. **Fallback Strategy:** Maintains parsing for models without structured output support
4. **BaseClass Enhancement:** Minimal changes to support both Outlines and traditional agents
5. **Comprehensive Testing:** 98% validity requirement enforced through extensive test cases

### Implementation Strategy ⚠️
6. **Backward Compatibility:** Existing ResearchRunner workflows continue unchanged
7. **Performance Focus:** Benchmark against baseline, ensure ≤ +20% latency impact
8. **Type Safety:** Pydantic models provide structure validation at Python level
9. **Clean Architecture:** Clear separation between Outlines and traditional parsing paths
10. **Future-Proof Design:** Template and schema patterns reusable for other agents

**Ready to start HYBRID-05?** This comprehensive plan delivers reliable JSON output through Outlines while maintaining full backward compatibility and establishing patterns for the broader agent overhaul.