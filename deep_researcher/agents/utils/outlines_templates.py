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

# Template system for SearchAgent and CrawlAgent
def render_search_summary_prompt(
    knowledge_gap: str,
    search_query: str,  
    search_results: str,
    entity_website: str = None
) -> str:
    """Render structured search summary prompt for Outlines generation"""
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    website_context = f"\n\nEntity Website Context: {entity_website}" if entity_website else ""
    
    return f"""You are the WebSearchAgent for a research project. Today's date is {current_date}.

Your task is to analyze web search results and create a comprehensive summary that addresses the specific knowledge gap.

Knowledge Gap to Address: {knowledge_gap}
Search Query Used: {search_query}{website_context}

Search Results:
{search_results}

Analyze the search results and provide:
1. A comprehensive summary (50-2000 characters) that directly addresses the knowledge gap
2. List of source URLs from the search results (up to 20 URLs)
3. Focus on factual accuracy and relevance to the knowledge gap

Extract key findings, facts, and insights that help fill the knowledge gap. Synthesize information from multiple sources when available."""

def render_legacy_search_summary_prompt(
    knowledge_gap: str,
    search_query: str,
    search_results: str, 
    entity_website: str = None
) -> str:
    """Render legacy search summary prompt with explicit JSON format"""
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    website_context = f"\n\nEntity Website Context: {entity_website}" if entity_website else ""
    
    return f"""You are the WebSearchAgent for a research project. Today's date is {current_date}.

Knowledge Gap to Address: {knowledge_gap}
Search Query Used: {search_query}{website_context}

Search Results:
{search_results}

You MUST respond with valid JSON in exactly this format:

{{
  "output": "A comprehensive summary of search findings that addresses the knowledge gap (50-2000 characters)",
  "sources": ["https://url1.com", "https://url2.com", "..."]
}}

Steps:
1. Analyze the search results for information relevant to the knowledge gap
2. Write a summary that directly addresses the gap with factual findings
3. Extract and list the source URLs from the search results
4. Format your response as the JSON above - no extra keys, no commentary"""

def render_crawl_summary_prompt(
    knowledge_gap: str,
    target_website: str,
    crawled_content: str,
    search_query: str = None
) -> str:
    """Render structured crawl summary prompt for Outlines generation"""
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    query_context = f"\n\nSearch Query Context: {search_query}" if search_query else ""
    
    return f"""You are the SiteCrawlerAgent for a research project. Today's date is {current_date}.

Your task is to analyze crawled website content and create a comprehensive summary that addresses the specific knowledge gap.

Knowledge Gap to Address: {knowledge_gap}
Target Website: {target_website}{query_context}

Crawled Content:
{crawled_content}

Analyze the crawled content and provide:
1. A comprehensive summary (50-2000 characters) that directly addresses the knowledge gap
2. Source URL (the target website that was crawled)
3. Focus on extracting relevant information that fills the knowledge gap

Extract key findings, facts, and insights from the website content. Synthesize information effectively while maintaining accuracy."""


def render_structured_summary_prompt(
    content: str,
    context: str,
    sources: List[str] = None,
    max_findings: int = 8
) -> str:
    """Render structured summarization prompt for Outlines generation"""
    sources_text = ""
    if sources:
        sources_text = f"\n\nSources: {', '.join(sources)}"
    
    return f"""Create a comprehensive structured summary of the following content.

Context: {context}

Content to summarize:
{content}{sources_text}

Provide a structured summary that includes:
1. A comprehensive summary (50-2000 characters)
2. Key findings (1-{max_findings} important points, each at least 10 characters)
3. Confidence score (0.0-1.0 based on content quality and completeness)

Focus on:
- Extracting the most important information relevant to the context
- Identifying key findings that directly address the research needs
- Providing accurate confidence assessment based on source quality
- Maintaining factual accuracy and avoiding speculation

Return the structured summary with all required fields."""


def render_structured_chunk_summary_prompt(
    chunk_content: str,
    chunk_id: int,
    context: str,
    max_key_points: int = 5
) -> str:
    """Render structured chunk summarization prompt"""
    return f"""Summarize this content chunk with structured output.

Chunk ID: {chunk_id}
Context: {context}

Chunk Content:
{chunk_content}

Provide a structured summary that includes:
1. A concise summary (10-500 characters) of the main points in this chunk
2. Key points (up to {max_key_points} specific points from this chunk)

Focus on:
- Extracting the most relevant information from this specific chunk
- Identifying concrete facts, findings, or insights
- Keeping summaries focused and avoiding redundancy
- Providing specific rather than generic key points

Return the structured chunk summary with all required fields."""


def render_structured_aggregation_prompt(
    chunk_summaries: List[Dict[str, Any]],
    context: str,
    sources: List[str] = None,
    max_findings: int = 10
) -> str:
    """Render structured aggregation prompt for final summary"""
    # Build chunk summaries text
    summaries_text = []
    all_key_points = []
    
    for cs in chunk_summaries:
        if cs.get('summary'):
            summaries_text.append(f"Chunk {cs['chunk_id']}: {cs['summary']}")
        if cs.get('key_points'):
            all_key_points.extend(cs['key_points'])
    
    sources_text = ""
    if sources:
        sources_text = f"\n\nSources: {', '.join(sources)}"
    
    key_points_text = ""
    if all_key_points:
        unique_points = list(set(all_key_points))[:20]  # Limit and deduplicate
        key_points_text = f"\n\nAll Key Points from Chunks:\n" + "\n".join([f"- {point}" for point in unique_points])
    
    return f"""Create a comprehensive structured summary by combining these chunk summaries.

Context: {context}

Chunk Summaries:
{chr(10).join(summaries_text)}{key_points_text}{sources_text}

Synthesize this information into a structured summary that includes:
1. A comprehensive summary (50-2000 characters) that combines and synthesizes all chunks
2. Refined key findings (1-{max_findings} most important findings across all chunks)
3. Confidence score (0.0-1.0) based on consistency and completeness of source material

Focus on:
- Synthesizing information across chunks rather than just concatenating
- Identifying the most important findings that span multiple chunks
- Resolving any conflicts or redundancies between chunks
- Providing a coherent narrative that addresses the research context
- Assessing confidence based on source consistency and completeness

Return the structured summary with all required fields."""


def render_legacy_crawl_summary_prompt(
    knowledge_gap: str,
    target_website: str,
    crawled_content: str,
    search_query: str = None  
) -> str:
    """Render legacy crawl summary prompt with explicit JSON format"""
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    query_context = f"\n\nSearch Query Context: {search_query}" if search_query else ""
    
    return f"""You are the SiteCrawlerAgent for a research project. Today's date is {current_date}.

Knowledge Gap to Address: {knowledge_gap}
Target Website: {target_website}{query_context}

Crawled Content:
{crawled_content}

You MUST respond with valid JSON in exactly this format:

{{
  "output": "A comprehensive summary of relevant information found on the website that addresses the knowledge gap (50-2000 characters)",
  "sources": ["{target_website}"]
}}

Steps:
1. Analyze the crawled content for information relevant to the knowledge gap
2. Write a summary that directly addresses the gap with factual findings
3. Include the target website URL as the source
4. Format your response as the JSON above - no extra keys, no commentary"""

# Parameter extraction for SearchAgent and CrawlAgent
def extract_search_params(input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Extract search parameters from AgentTask or other input formats"""
    if isinstance(input_data, dict):
        # Handle AgentTask dictionary or similar structured input
        return {
            "knowledge_gap": input_data.get("gap", input_data.get("knowledge_gap", "")),
            "search_query": input_data.get("query", input_data.get("search_query", "")),
            "entity_website": input_data.get("entity_website", input_data.get("website", None))
        }
    
    if isinstance(input_data, str):
        # Try to parse as JSON first (from task.model_dump_json())
        import json
        try:
            parsed_data = json.loads(input_data)
            if isinstance(parsed_data, dict):
                return {
                    "knowledge_gap": parsed_data.get("gap", parsed_data.get("knowledge_gap", "")),
                    "search_query": parsed_data.get("query", parsed_data.get("search_query", "")),
                    "entity_website": parsed_data.get("entity_website", parsed_data.get("website", None))
                }
        except (json.JSONDecodeError, TypeError):
            # Not JSON, continue with string parsing
            pass
        
        # Parse string input - could be simple query or structured format
        # Look for AgentTask-like patterns first
        if "gap:" in input_data or "query:" in input_data:
            # Extract structured information
            gap_match = re.search(r"gap:\s*(.+?)(?=\n|query:|entity_website:|$)", input_data)
            query_match = re.search(r"query:\s*(.+?)(?=\n|gap:|entity_website:|$)", input_data)
            website_match = re.search(r"entity_website:\s*(.+?)(?=\n|gap:|query:|$)", input_data)
            
            return {
                "knowledge_gap": gap_match.group(1).strip() if gap_match else "",
                "search_query": query_match.group(1).strip() if query_match else input_data.strip(),
                "entity_website": website_match.group(1).strip() if website_match else None
            }
        else:
            # Simple string - treat as search query
            return {
                "knowledge_gap": input_data.strip(),
                "search_query": input_data.strip(),
                "entity_website": None
            }
    
    # Fallback for other types
    return {
        "knowledge_gap": str(input_data),
        "search_query": str(input_data), 
        "entity_website": None
    }

def extract_crawl_params(input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Extract crawl parameters from AgentTask or other input formats"""
    if isinstance(input_data, dict):
        # Handle AgentTask dictionary or similar structured input
        return {
            "knowledge_gap": input_data.get("gap", input_data.get("knowledge_gap", "")),
            "target_website": input_data.get("entity_website", input_data.get("target_website", input_data.get("url", ""))),
            "search_query": input_data.get("query", input_data.get("search_query", None))
        }
    
    if isinstance(input_data, str):
        # Parse string input - look for structured patterns
        if "gap:" in input_data or "entity_website:" in input_data:
            # Extract structured information
            gap_match = re.search(r"gap:\s*(.+?)(?=\n|query:|entity_website:|$)", input_data)
            query_match = re.search(r"query:\s*(.+?)(?=\n|gap:|entity_website:|$)", input_data)
            website_match = re.search(r"entity_website:\s*(.+?)(?=\n|gap:|query:|$)", input_data)
            
            return {
                "knowledge_gap": gap_match.group(1).strip() if gap_match else "",
                "target_website": website_match.group(1).strip() if website_match else input_data.strip(),
                "search_query": query_match.group(1).strip() if query_match else None
            }
        else:
            # Simple string - treat as target website
            return {
                "knowledge_gap": input_data.strip(),
                "target_website": input_data.strip(),
                "search_query": None
            }
    
    # Fallback for other types  
    return {
        "knowledge_gap": str(input_data),
        "target_website": str(input_data),
        "search_query": None
    }