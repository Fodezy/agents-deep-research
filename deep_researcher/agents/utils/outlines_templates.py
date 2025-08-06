"""Optimized template system for Outlines-based agents"""
from typing import List, Dict, Any, Union
from datetime import datetime
import re

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

# Planning templates for PlannerAgent
def render_planning_prompt(research_question: str, context: str = "") -> str:
    """Render prompt for Outlines structured planning generation"""
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    context_section = f"\n\nBackground Context:\n{context}" if context.strip() else ""
    
    return f"""You are the Report Planner for a research project. Today's date is {current_date}.

Your task is to create a comprehensive research plan that breaks down the research question into manageable sections.

Research Question: {research_question}{context_section}

Create a research plan with:
1. A concise, descriptive report title (10-100 characters)
2. Background context summarizing what we know (50-1000 characters)
3. An outline of 2-5 research sections, each with:
   - A clear section title (5-80 characters)
   - A specific key question to investigate (10-200 characters)

Focus on creating sections that can be researched independently while building toward a comprehensive answer to the research question."""

def render_legacy_planning_prompt(research_question: str, context: str = "") -> str:
    """Render legacy planning prompt with explicit JSON format"""
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    context_section = f"\n\nBackground Context:\n{context}" if context.strip() else ""
    
    return f"""You are the Report Planner for a research project. Today's date is {current_date}.

Your task is to create a comprehensive research plan that breaks down the research question into manageable sections.

Research Question: {research_question}{context_section}

You MUST respond with a JSON object in exactly this format - no extra keys, no commentary:

{{
  "schema_version": 1,
  "report_title": "A concise, descriptive title for the report (10-100 chars)",
  "background_context": "1-2 paragraphs of background context that summarizes what we know about this topic (50-1000 chars).",
  "report_outline": [
    {{
      "title": "Section 1 Title (5-80 chars)",
      "key_question": "The specific question this section answers (10-200 chars)"
    }},
    {{
      "title": "Section 2 Title (5-80 chars)", 
      "key_question": "Another specific question for this section (10-200 chars)"
    }}
  ]
}}

Create 2-5 sections that can be researched independently while building toward a comprehensive answer. Each section should focus on a specific aspect of the research question."""

# Knowledge gap analysis templates for KnowledgeGapAgent
def render_knowledge_gap_prompt(
    research_context: str, 
    background_context: str = "", 
    findings_history: str = "",
    iteration_context: Dict[str, Any] = None
) -> str:
    """Render knowledge gap analysis prompt for structured output"""
    current_date = datetime.now().strftime('%Y-%m-%d')  # Runtime injection
    
    background_section = f"\n\nBackground Context:\n{background_context}" if background_context.strip() else ""
    history_section = f"\n\nResearch History:\n{findings_history}" if findings_history.strip() else ""
    
    iteration_info = ""
    if iteration_context:
        iteration = iteration_context.get("iteration", 0)
        time_elapsed = iteration_context.get("time_elapsed", 0)
        max_time = iteration_context.get("max_time", 0)
        if iteration > 0:
            iteration_info += f"\n\nIteration: {iteration}"
        if time_elapsed > 0:
            time_info = f" (Time Elapsed: {time_elapsed:.1f}"
            if max_time > 0:
                time_info += f" of {max_time} minutes)"
            else:
                time_info += " minutes)"
            iteration_info += time_info
    
    return f"""You are the Knowledge Gap Analyzer for a research project. Today's date is {current_date}.

Your task is to analyze the current research progress and identify remaining knowledge gaps that need to be addressed.

Research Context: {research_context}{background_section}{history_section}{iteration_info}

Analyze the research state and provide:
1. Assessment of research completeness with confidence level (0.0-1.0)
2. Identification of specific knowledge gaps with priority levels (high/medium/low)
3. Research approach suggestions for each identified gap (10-200 characters)
4. Confidence scores for gap identification accuracy (0.0-1.0)
5. Overall analysis summary

Focus on gaps that can be addressed through additional research tools and methods. Provide actionable gaps with clear research approaches."""

def render_legacy_knowledge_gap_prompt(
    research_context: str, 
    background_context: str = "", 
    findings_history: str = "",
    iteration_context: Dict[str, Any] = None
) -> str:
    """Render legacy knowledge gap analysis prompt with explicit JSON format"""
    current_date = datetime.now().strftime('%Y-%m-%d')  # Runtime injection
    
    # Same parameter handling as structured template
    background_section = f"\n\nBackground Context:\n{background_context}" if background_context.strip() else ""
    history_section = f"\n\nResearch History:\n{findings_history}" if findings_history.strip() else ""
    
    iteration_info = ""
    if iteration_context:
        iteration = iteration_context.get("iteration", 0)
        time_elapsed = iteration_context.get("time_elapsed", 0)
        if iteration > 0:
            iteration_info += f"\n\nIteration: {iteration}"
        if time_elapsed > 0:
            iteration_info += f" (Time Elapsed: {time_elapsed:.1f} minutes)"
    
    return f"""You are the Knowledge Gap Analyzer for a research project. Today's date is {current_date}.

Research Context: {research_context}{background_section}{history_section}{iteration_info}

You MUST respond with a JSON object in exactly this format - no extra keys, no commentary:

{{
  "schema_version": 1,
  "research_complete": false,
  "research_completeness_confidence": 0.8,
  "research_context": "Brief summary of research context (20-1000 chars)",
  "gaps_identified": [
    {{
      "gap_id": "gap_1",
      "description": "Specific knowledge gap description (10-500 chars)",
      "priority": "high",
      "research_approach": "Suggested approach to address this gap (10-200 chars)",
      "confidence": 0.9,
      "category": "optional_category"
    }}
  ],
  "analysis_summary": "Comprehensive analysis of current research state and identified gaps (50-2000 chars)",
  "total_gaps": 1
}}

Analyze the research progress and identify 0-10 specific, actionable knowledge gaps that can be addressed through additional research. Set research_complete to true only if no significant gaps remain."""

# Input parameter extraction for KnowledgeGapAgent
def extract_knowledge_gap_params(input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Extract parameters for knowledge gap analysis following HYBRID-06 pattern"""
    if isinstance(input_data, dict):
        # Handle dictionary input with graceful extra key handling
        iteration_context = input_data.get("iteration_context", {})
        
        # Extract time and iteration info if available
        if "iteration" in input_data:
            iteration_context["iteration"] = input_data["iteration"]
        if "time_elapsed" in input_data:
            iteration_context["time_elapsed"] = input_data["time_elapsed"]
        if "max_time" in input_data:
            iteration_context["max_time"] = input_data["max_time"]
            
        return {
            "research_context": input_data.get("research_context", input_data.get("query", "")),
            "background_context": input_data.get("background_context", ""),
            "findings_history": input_data.get("findings_history", input_data.get("history", "")),
            "iteration_context": iteration_context if iteration_context else None
        }
    
    if isinstance(input_data, str):
        # Parse structured string input from ResearchRunner
        # Extract ORIGINAL QUERY, BACKGROUND CONTEXT, HISTORY sections
        patterns = {
            "query": r"ORIGINAL QUERY:\s*(.+?)(?=\n\n|\nBACKGROUND|\nHISTORY|$)",
            "background": r"BACKGROUND CONTEXT:\s*(.+?)(?=\n\n|\nHISTORY|$)", 
            "history": r"HISTORY OF ACTIONS.*?:\s*(.+?)(?=\n\n|$)"
        }
        
        result = {"research_context": "", "background_context": "", "findings_history": "", "iteration_context": None}
        found_structured_format = False
        
        for key, pattern in patterns.items():
            match = re.search(pattern, input_data, re.DOTALL | re.IGNORECASE)
            if match:
                found_structured_format = True
                if key == "query":
                    result["research_context"] = match.group(1).strip()
                elif key == "background":
                    result["background_context"] = match.group(1).strip()
                elif key == "history":
                    result["findings_history"] = match.group(1).strip()
        
        # If no structured format found, treat entire string as research context
        if not found_structured_format:
            result["research_context"] = input_data.strip()
        
        # Extract iteration metadata if present
        iteration_context = {}
        iteration_match = re.search(r"Current Iteration Number:\s*(\d+)", input_data)
        if iteration_match:
            iteration_context["iteration"] = int(iteration_match.group(1))
            
        time_match = re.search(r"Time Elapsed:\s*([\d.]+)\s*minutes(?:\s+of\s+maximum\s+([\d.]+)\s*minutes)?", input_data)
        if time_match:
            iteration_context["time_elapsed"] = float(time_match.group(1))
            if time_match.group(2):
                iteration_context["max_time"] = float(time_match.group(2))
        
        if iteration_context:
            result["iteration_context"] = iteration_context
            
        return result
    
    return {
        "research_context": str(input_data), 
        "background_context": "", 
        "findings_history": "",
        "iteration_context": None
    }

# Input parameter extraction for PlannerAgent
def extract_planner_params(input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Extract planning parameters from various input formats"""
    if isinstance(input_data, dict):
        # Handle dictionary input with graceful extra key handling
        return {
            "research_question": input_data.get("research_question", input_data.get("query", "")),
            "context": input_data.get("context", input_data.get("background_context", ""))
        }
    
    # Handle string input
    if isinstance(input_data, str):
        # First try complex formatted input with context
        # Pattern: QUERY: <question>\n\nCONTEXT: <context>
        query_context_pattern = r"QUERY:\s*(.+?)(?:\n\n(?:CONTEXT|BACKGROUND):\s*(.+?))?(?:\n\n|$)"
        match = re.search(query_context_pattern, input_data, re.DOTALL | re.IGNORECASE)
        if match:
            query = match.group(1).strip()
            context = match.group(2).strip() if match.group(2) else ""
            return {"research_question": query, "context": context}
        
        # Simple QUERY format (current format: "QUERY: <question>")
        elif input_data.strip().startswith("QUERY:"):
            query = input_data.replace("QUERY:", "").strip()
            return {"research_question": query, "context": ""}
        
        # Fallback: treat entire string as research question
        else:
            return {"research_question": input_data.strip(), "context": ""}
    
    # Fallback for any other type
    return {"research_question": str(input_data), "context": ""}