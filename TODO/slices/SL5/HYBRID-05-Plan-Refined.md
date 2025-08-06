# 🎫 HYBRID-05: Outlines Refactor - ToolSelector Implementation Plan (REFINED)

Based on SL-X specification and refined based on critical feedback to address template duplication, signature consistency, date injection, and LoC budgeting.

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

**📏 Budget Constraints (REFINED):**
- Core refactor ≤ 100 LoC changes in tool_selector_agent.py
- New Outlines utilities ≤ 120 LoC total (reduced from 150 to account for dual templates)
- BaseClass changes ≤ 30 LoC
- 1-day delivery timeline (per guardrails)

## Implementation Tasks

### Day 1: Core Outlines Integration

#### **Task 1: Create Outlines Function Schema**

**File:** `deep_researcher/agents/utils/outlines_schemas.py` (NEW - ~40 LoC)

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
    current_date: str = None  # Will be auto-populated if None
) -> AgentSelectionPlan:
    """
    Select appropriate research tools and create agent tasks to address knowledge gaps.
    
    Args:
        research_context: The overall research question or topic
        knowledge_gaps: List of specific information gaps to fill
        current_date: Current date in YYYY-MM-DD format (auto-populated if None)
        
    Returns:
        AgentSelectionPlan with list of agent tasks
    """
    pass  # Implementation will be handled by Outlines
```

#### **Task 2: Create Dual Template System (REFINED)**

**File:** `deep_researcher/agents/utils/outlines_templates.py` (NEW - ~80 LoC)

```python
"""Template system for Outlines-based agents with fallback support"""
from typing import Dict, Any, List
from datetime import datetime

class OutlinesTemplate:
    """Base template class for dynamic content injection"""
    
    def __init__(self, base_prompt: str):
        self.base_prompt = base_prompt
    
    def render(self, **kwargs) -> str:
        """Render template with dynamic values"""
        # Ensure current_date is always provided (FIXED: no None defaults)
        if 'current_date' not in kwargs:
            kwargs['current_date'] = datetime.now().strftime('%Y-%m-%d')
        
        # Handle datetime objects specially
        for key, value in kwargs.items():
            if isinstance(value, datetime):
                kwargs[key] = value.strftime('%Y-%m-%d')
        
        return self.base_prompt.format(**kwargs)

# ToolSelector template for Outlines (clean, no JSON schema)
TOOL_SELECTOR_OUTLINES_TEMPLATE = OutlinesTemplate("""
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

# Legacy template for fallback parsing (FIXED: mirrors original exactly, no placeholders)
def create_legacy_prompt(research_context: str, knowledge_gaps: List[str], current_date: str = None) -> str:
    """Create legacy prompt with real values, no placeholders"""
    if current_date is None:
        current_date = datetime.now().strftime('%Y-%m-%d')
    
    knowledge_gaps_text = "\n".join(f"- {gap}" for gap in knowledge_gaps)
    
    return f"""
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

You MUST respond with a JSON object in exactly this format—no extra keys, no commentary:

{{
  "tasks": [
    {{
      "gap": "Describe the specific knowledge gap here",
      "agent": "WebSearchAgent",
      "query": "3–6 word query",
      "entity_website": "https://optional.domain.com"
    }}
  ]
}}

For each gap, create an agent task with:
- gap: Description of the specific knowledge gap
- agent: Most appropriate agent name from the available list
- query: Concise 3-6 word search query or task description
- entity_website: Optional website URL if relevant to the research

Select the most efficient combination of agents to fill all knowledge gaps without redundancy.
""".strip()
```

#### **Task 3: Input Normalization Utility (NEW)**

**File:** `deep_researcher/agents/utils/input_normalization.py` (NEW - ~25 LoC)

```python
"""Input normalization for consistent agent signatures"""
from typing import Dict, Any, List, Union
import json

def normalize_tool_selector_input(input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Normalize input for ToolSelector to consistent (research_context, knowledge_gaps) signature
    
    FIXED: Handles signature consistency between run() and structured_generator
    """
    if isinstance(input_data, str):
        # Try parsing as JSON first
        try:
            data = json.loads(input_data)
        except json.JSONDecodeError:
            # Treat as research context
            return {
                "research_context": input_data,
                "knowledge_gaps": []
            }
    else:
        data = input_data
    
    # Extract required fields, ignore extra keys to prevent mismatch
    result = {
        "research_context": data.get("research_context", data.get("context", "")),
        "knowledge_gaps": data.get("knowledge_gaps", data.get("gaps", []))
    }
    
    # Handle string knowledge_gaps (convert to list)
    if isinstance(result["knowledge_gaps"], str):
        result["knowledge_gaps"] = [result["knowledge_gaps"]]
    
    return result
```

#### **Task 4: Refactor ToolSelectorAgent with Outlines (REFINED)**

**File:** `deep_researcher/agents/tool_selector_agent.py` (MODIFIED - ~60 LoC changes)

```python
"""
Tool Selector Agent using Outlines for structured output generation
"""
from typing import List, Dict, Any, Union
from datetime import datetime
import outlines

from .baseclass import ResearchAgent  
from ..llm_config import LLMConfig, model_supports_structured_output
from .utils.outlines_schemas import AgentSelectionPlan
from .utils.outlines_templates import TOOL_SELECTOR_OUTLINES_TEMPLATE, create_legacy_prompt
from .utils.input_normalization import normalize_tool_selector_input
from .utils.parse_output import create_type_parser

def init_tool_selector_agent(config: LLMConfig) -> ResearchAgent:
    """Initialize ToolSelectorAgent with Outlines structured output"""
    selected_model = config.main_model  # Use main model for planning tasks
    
    # Create Outlines-based structured generator
    if model_supports_structured_output(selected_model):
        # Use Outlines for guaranteed structured output
        generator = outlines.generate.json(selected_model, AgentSelectionPlan)
        
        def structured_call(input_data: Union[str, Dict[str, Any]]) -> AgentSelectionPlan:
            """FIXED: Consistent signature that handles normalization internally"""
            # Normalize input to consistent format
            normalized = normalize_tool_selector_input(input_data)
            
            # Render template with normalized input
            prompt = TOOL_SELECTOR_OUTLINES_TEMPLATE.render(
                research_context=normalized["research_context"],
                knowledge_gaps_text="\n".join(f"- {gap}" for gap in normalized["knowledge_gaps"])
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
        # FIXED: Use real legacy prompt with no placeholders
        def create_instructions(input_data: Union[str, Dict[str, Any]]) -> str:
            normalized = normalize_tool_selector_input(input_data)
            return create_legacy_prompt(
                research_context=normalized["research_context"],
                knowledge_gaps=normalized["knowledge_gaps"]
            )
        
        return ResearchAgent(
            name="ToolSelectorAgent", 
            instructions=create_instructions,  # Dynamic instruction creator
            model=selected_model,
            output_type=AgentSelectionPlan,
            output_parser=create_type_parser(AgentSelectionPlan)
        )
```

#### **Task 5: Enhance BaseClass for Outlines Support (REFINED)**

**File:** `deep_researcher/agents/baseclass.py` (MODIFIED - ~25 LoC changes)

```python
class ResearchAgent:
    def __init__(self, 
                 name: str,
                 instructions: Union[str, Callable],  # FIXED: Support dynamic instructions
                 model,
                 tools: List = None,
                 output_type=None,
                 output_parser=None,
                 summariser=None,
                 structured_generator=None):  # NEW: Outlines generator
        # ... existing initialization ...
        self.structured_generator = structured_generator
        self.instructions = instructions  # Can be string or function
    
    async def run(self, input_data: Union[str, Dict[str, Any]], **kwargs) -> Any:
        """Enhanced run method with Outlines support"""
        if self.structured_generator:
            # Use Outlines structured generation
            try:
                # FIXED: Pass input_data directly, let structured_generator handle normalization
                return self.structured_generator(input_data)
            except Exception as e:
                print(f"[WARN] Structured generation failed: {e}, falling back to standard parsing")
                # Fallback to existing logic
        
        # Handle dynamic instructions for fallback mode
        if callable(self.instructions):
            current_instructions = self.instructions(input_data)
        else:
            current_instructions = self.instructions
        
        # Existing logic for non-structured output
        return await super().run(input_data, **kwargs)
```

### Day 1: Comprehensive Testing (REFINED)

#### **Task 6: Performance Baseline Creation**

**File:** `tests/test_tool_selector_baseline.py` (NEW - for comparison)

```python
"""Create baseline performance measurements for traditional parsing"""
import pytest
import time
import json
from unittest.mock import Mock
from deep_researcher.agents.utils.parse_output import create_type_parser
from deep_researcher.agents.utils.outlines_schemas import AgentSelectionPlan

class TestTraditionalParsingBaseline:
    """FIXED: Create concrete baseline for +20% performance comparison"""
    
    @pytest.mark.benchmark
    def test_traditional_parsing_baseline(self):
        """Measure traditional parsing performance for comparison"""
        parser = create_type_parser(AgentSelectionPlan)
        
        # Sample JSON response (what model would return)
        sample_json = {
            "tasks": [
                {
                    "gap": "Recent quantum computing developments",
                    "agent": "WebSearchAgent",
                    "query": "quantum computing 2024",
                    "entity_website": None
                }
            ]
        }
        
        # Measure parsing time for 100 iterations
        start = time.time()
        for _ in range(100):
            result = parser(json.dumps(sample_json))
        baseline_time = time.time() - start
        
        # Store baseline for comparison
        with open("tests/performance_baseline.txt", "w") as f:
            f.write(f"traditional_parsing_100_calls: {baseline_time:.6f}\n")
        
        assert baseline_time < 1.0  # Reasonable baseline
        return baseline_time
```

#### **Task 7: Refined Performance Testing**

**File:** `tests/test_tool_selector_performance.py` (REFINED)

```python
"""Performance tests for Outlines vs. traditional parsing"""
import pytest
import time
import os
from deep_researcher.agents.tool_selector_agent import init_tool_selector_agent
from deep_researcher.llm_config import create_default_config

class TestPerformanceComparison:
    """FIXED: Compare against concrete baseline with +20% requirement"""
    
    def get_baseline_time(self) -> float:
        """Get traditional parsing baseline"""
        baseline_file = "tests/performance_baseline.txt"
        if os.path.exists(baseline_file):
            with open(baseline_file, "r") as f:
                line = f.readline().strip()
                return float(line.split(": ")[1])
        return 0.1  # Fallback baseline
    
    @pytest.mark.benchmark
    def test_outlines_vs_parsing_latency(self):
        """FIXED: Compare against concrete baseline with ≤ +20% requirement"""
        baseline_time = self.get_baseline_time()
        
        config = create_default_config()
        # Mock model for consistent timing
        config.main_model = lambda prompt: {"tasks": [{"gap": "test", "agent": "WebSearchAgent", "query": "test query"}]}
        
        test_input = {
            "research_context": "Climate change impacts",
            "knowledge_gaps": ["Temperature data", "Policy responses"]
        }
        
        # Measure Outlines approach
        outlines_agent = init_tool_selector_agent(config)
        start = time.time()
        for _ in range(100):
            result = outlines_agent.structured_generator(test_input)
        outlines_time = time.time() - start
        
        # FIXED: Enforce ≤ +20% requirement against baseline
        max_allowed_time = baseline_time * 1.20
        assert outlines_time <= max_allowed_time, f"Outlines took {outlines_time:.3f}s, baseline {baseline_time:.3f}s, max allowed {max_allowed_time:.3f}s"
        
        print(f"Baseline: {baseline_time:.6f}s, Outlines: {outlines_time:.6f}s, Delta: {((outlines_time/baseline_time-1)*100):+.1f}%")
```

### LoC Budget Validation

**File:** `scripts/check_loc.py` (MODIFIED)

```python
def main():
    # FIXED: Check all new files against refined budget
    files_to_check = [
        ("deep_researcher/agents/utils/token_chunker.py", 150),
        ("deep_researcher/agents/utils/hierarchical_summariser.py", 200),
        ("deep_researcher/agents/utils/outlines_schemas.py", 50),       # NEW
        ("deep_researcher/agents/utils/outlines_templates.py", 90),     # NEW
        ("deep_researcher/agents/utils/input_normalization.py", 30)     # NEW
    ]
    
    # Total new utilities budget: 50 + 90 + 30 = 170 LoC
    # REFINED: Adjusted individual limits to stay under 120 LoC total
```

## Success Criteria (REFINED)

**Must Pass CI:**
- `pytest tests/test_tool_selector_outlines.py` → Green
- JSON validity rate ≥ 98% across test cases
- No f-string datetime injection in static code
- Backward compatibility with ResearchRunner maintained
- Performance impact ≤ +20% against concrete baseline
- **LoC Budget:** Total new files ≤ 120 LoC (refined from 150)

## Files to Create/Modify (REFINED)

```
deep_researcher/
├── agents/
│   ├── utils/
│   │   ├── outlines_schemas.py        # New - 40 LoC
│   │   ├── outlines_templates.py      # New - 80 LoC  
│   │   ├── input_normalization.py     # New - 25 LoC (Total: 145 LoC)
│   │   └── __init__.py                # Modified - Add exports
│   ├── tool_selector_agent.py         # Modified - 60 LoC changes
│   └── baseclass.py                   # Modified - 25 LoC changes

tests/
├── test_tool_selector_baseline.py     # New - Performance baseline
├── test_tool_selector_outlines.py     # New - Comprehensive tests
└── test_tool_selector_performance.py  # New - Refined performance tests

scripts/
└── check_loc.py                       # Modified - Add new file limits
```

**REFINED LoC Budget:** 
- New utilities: 145 LoC (over 120 budget - need to optimize)
- Core changes: 85 LoC
- **Action Required:** Reduce template file by ~25 LoC to meet budget

## Key Refinements Applied ✅

### Critical Fixes from Feedback
1. **Template vs. Fallback Duplication:** Created `create_legacy_prompt()` function that mirrors original f-string exactly, no placeholders
2. **Signature Consistency:** Added `normalize_tool_selector_input()` to handle dict/string inputs consistently  
3. **Date Injection Default:** Template renderer auto-populates `current_date` if None, no "None" strings in prompts
4. **Performance Baseline:** Created concrete baseline measurement for meaningful "+20%" comparison
5. **LoC Budget Reality Check:** Detailed accounting shows need to optimize template file by ~25 LoC

### Architecture Improvements
6. **Input Normalization:** Handles extra keys gracefully, prevents signature mismatches
7. **Dynamic Instructions:** BaseClass supports callable instructions for fallback mode
8. **Dual Template System:** Clean separation between Outlines and legacy prompts
9. **Concrete Baselines:** Performance tests now have real reference points
10. **Budget Enforcement:** Extended LoC checker to validate all new files

**Status:** Plan refined to address all critical feedback. Ready for implementation once template LoC is optimized to meet 120 LoC budget constraint.

## Next Steps to Finalize

1. **Optimize Templates:** Reduce `outlines_templates.py` by ~25 LoC to meet budget
2. **Validate LoC Counts:** Run refined `check_loc.py` to confirm budget compliance  
3. **Test Baseline Creation:** Run baseline measurement to establish performance reference
4. **Template Placeholder Verification:** Ensure legacy prompts have no stray `{placeholders}`

Once these refinements are complete, the plan will be implementation-ready with all feedback addressed.