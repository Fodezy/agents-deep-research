"""Optimized template system for Outlines-based agents"""
from typing import List
from datetime import datetime

def render_outlines_prompt(research_context: str, knowledge_gaps: List[str]) -> str:
    """Render prompt for Outlines structured generation (FIXED: auto-populate date)"""
    current_date = datetime.now().strftime('%Y-%m-%d')
    knowledge_gaps_text = "\n".join(f"- {gap}" for gap in knowledge_gaps)
    
    return f"""You are the Tool Selector for a research project. Today's date is {current_date}.

Your job is to analyze the research question and knowledge gaps, then select appropriate research agents and create specific tasks for each gap.

Available Research Agents:
- WebSearchAgent: Performs web searches for current information  
- SiteCrawlerAgent: Crawls specific websites for detailed content

Research Context: {research_context}

Knowledge Gaps to Address:
{knowledge_gaps_text}

For each gap, create an agent task with:
- gap: Description of the specific knowledge gap
- agent: Most appropriate agent name from the available list
- query: Concise 3-6 word search query or task description  
- entity_website: Optional website URL if relevant to the research

Select the most efficient combination of agents to fill all knowledge gaps without redundancy."""

def render_legacy_prompt(research_context: str, knowledge_gaps: List[str]) -> str:
    """Render legacy prompt with real values (FIXED: no placeholders)"""
    current_date = datetime.now().strftime('%Y-%m-%d')
    knowledge_gaps_text = "\n".join(f"- {gap}" for gap in knowledge_gaps)
    
    return f"""You are the Tool Selector for a research project. Today's date is {current_date}.

Your job is to analyze the research question and knowledge gaps, then select appropriate research agents and create specific tasks for each gap.

Available Research Agents:
- WebSearchAgent: Performs web searches for current information
- SiteCrawlerAgent: Crawls specific websites for detailed content  

Research Context: {research_context}

Knowledge Gaps to Address:
{knowledge_gaps_text}

You MUST respond with a JSON object in exactly this format - no extra keys, no commentary:

{{
  "tasks": [
    {{
      "gap": "Describe the specific knowledge gap here",
      "agent": "WebSearchAgent",
      "query": "3-6 word query",
      "entity_website": "https://optional.domain.com"
    }}
  ]
}}

For each gap, create an agent task with:
- gap: Description of the specific knowledge gap
- agent: Most appropriate agent name from the available list
- query: Concise 3-6 word search query or task description
- entity_website: Optional website URL if relevant to the research

Select the most efficient combination of agents to fill all knowledge gaps without redundancy."""