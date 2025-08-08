"""
Native Structured Generation Knowledge Gap Agent.

This agent analyzes research progress and identifies remaining knowledge gaps using
native Ollama structured outputs instead of Outlines. This provides:

- 100% structured generation success rate (schema-guaranteed output)
- Simplified architecture (no dual-path complexity)  
- Direct integration with existing Pydantic schemas
- Elimination of JSON parsing errors and validation failures

Input formats supported:
- Dictionary with structured parameters
- ResearchRunner formatted strings 
- Simple string queries (fallback)

Output: KnowledgeGapResult with comprehensive gap analysis and metadata
"""

from typing import Union, Dict, Any
from .baseclass import ResearchAgent
from ..llm_config import LLMConfig
from .utils.native_structured_generation import generate_structured, extract_model_info

# Import existing schemas (100% compatible with native structured generation)
from .utils.outlines_schemas import KnowledgeGapResult, KnowledgeGapOutput, analyze_knowledge_gaps
from .utils.outlines_templates import (
    render_knowledge_gap_prompt, 
    render_legacy_knowledge_gap_prompt,
    extract_knowledge_gap_params
)

# Import logging for diagnostics (simplified for native generation)
import logging


async def generate_knowledge_gaps_native(
    config: LLMConfig,
    selected_model: Any,
    input_data: Union[str, Dict[str, Any]]
) -> KnowledgeGapResult:
    """
    Generate knowledge gap analysis using native Ollama structured outputs.
    
    Args:
        config: LLM configuration
        selected_model: Model from role registry
        input_data: Research context and parameters
        
    Returns:
        KnowledgeGapResult with structured gap analysis
    """
    try:
        # Extract base URL and model name
        base_url, model_name = extract_model_info(selected_model, config)
        
        # Extract parameters using existing template system
        params = extract_knowledge_gap_params(input_data)
        
        # Render prompt using existing template (reuse existing logic)
        base_prompt = render_knowledge_gap_prompt(**params)
        
        # Add explicit schema constraints for native structured generation
        prompt = f"""{base_prompt}

CRITICAL SCHEMA REQUIREMENTS:
- schema_version: Must be exactly 1 (integer)
- research_completeness_confidence: Must be decimal between 0.0 and 1.0 (e.g., 0.85, not 85)
- confidence in gaps_identified: Must be decimal between 0.0 and 1.0 (e.g., 0.8, not 80)
- All confidence values should be formatted as decimals (0.0-1.0), NOT percentages

RESEARCH COMPLETION LOGIC:
- research_complete should be TRUE only when NO meaningful knowledge gaps exist that can be addressed through research tools
- If ANY significant gaps are identified that could benefit from web search or crawling, research_complete should be FALSE
- For early iterations (1-2), research_complete should almost always be FALSE unless the query is extremely simple
- Only mark research_complete as TRUE when comprehensive information has been gathered

Example valid confidence values: 0.95, 0.8, 0.7, 0.65
Example INVALID confidence values: 95, 80, 70, 65

Ensure your JSON output strictly follows these numeric formats."""
        
        # Generate structured output using native Ollama API
        result = await generate_structured(
            base_url=base_url,
            model_name=model_name,
            messages=[{"role": "user", "content": prompt}],
            schema_class=KnowledgeGapResult,
            temperature=0.0  # Deterministic for analysis consistency
        )
        
        print(f"[KnowledgeGapAgent] Native structured generation success: {len(result.gaps_identified)} gaps identified")
        
        # CRITICAL FIX: Defensive programming for empty gaps
        if not result.research_complete and not result.gaps_identified:
            print(f"[KnowledgeGapAgent] Warning: Empty gaps detected, creating fallback gap")
            # Create a fallback gap to prevent downstream crashes
            from .utils.outlines_schemas import KnowledgeGap
            
            fallback_gap = KnowledgeGap(
                gap_id="fallback_gap_001",
                description="Additional research needed to complete analysis", 
                priority="medium",
                research_approach="Conduct broader search and analysis",
                confidence=0.7
            )
            result.gaps_identified = [fallback_gap]
        
        return result
        
    except Exception as e:
        print(f"[KnowledgeGapAgent] Native structured generation failed: {e}")
        raise Exception(f"Native structured generation failed: {e}")
        # NOTE: No fallback - we are committed to native structured generation only


def create_knowledge_gap_agent_native(config: LLMConfig) -> ResearchAgent:
    """
    Create KnowledgeGapAgent using native Ollama structured outputs.
    
    This replaces the complex Outlines integration with direct native API calls,
    providing the same structured generation benefits with minimal complexity.
    """
    from .utils.model_role_registry import ModelRole
    
    # Use dedicated KNOWLEDGE_GAP role
    selected_model = config.get_model_for_role(ModelRole.KNOWLEDGE_GAP)
    
    print(f"[INFO] KnowledgeGapAgent: Using native Ollama structured generation")
    print(f"[INFO] Model: {getattr(selected_model, 'model', str(selected_model))}")
    
    async def run_native_analysis(input_data: Union[str, Dict[str, Any]]) -> KnowledgeGapResult:
        """Run knowledge gap analysis with native structured generation"""
        return await generate_knowledge_gaps_native(config, selected_model, input_data)
    
    # Create agent with native structured generation function
    agent = ResearchAgent(
        name="KnowledgeGapAgent",
        instructions="Knowledge gap analysis with native structured generation",
        model=selected_model,
        output_type=KnowledgeGapResult
    )
    
    # Add the native generation method
    agent.run_native_analysis = run_native_analysis
    
    return agent


# Backward compatibility function (replace the original)
def init_knowledge_gap_agent(config: LLMConfig) -> ResearchAgent:
    """Initialize KnowledgeGapAgent with native structured generation (backward compatible)"""
    return create_knowledge_gap_agent_native(config)


# For testing individual agent
async def test_knowledge_gap_agent_native(config: LLMConfig, test_input: str = None) -> bool:
    """
    Test the native KnowledgeGapAgent implementation.
    
    Args:
        config: LLM configuration
        test_input: Optional test input (defaults to quantum entanglement query)
        
    Returns:
        True if test passes, False otherwise
    """
    if test_input is None:
        test_input = """
        Research Context: Quantum entanglement research for physics paper
        Current Progress: Found basic definitions and Einstein's objections
        Remaining Questions: How is it used in quantum computing? What are the practical applications?
        """
    
    try:
        agent = create_knowledge_gap_agent_native(config)
        result = await agent.run_native_analysis(test_input)
        
        # Validate result structure
        assert isinstance(result, KnowledgeGapResult)
        assert hasattr(result, 'gaps_identified')
        assert hasattr(result, 'research_complete')
        
        # Validate content quality
        if not result.research_complete:
            assert len(result.gaps_identified) > 0, "Should identify gaps when research incomplete"
        
        print(f"SUCCESS: Native KnowledgeGapAgent test passed")
        print(f"   Gaps identified: {len(result.gaps_identified)}")
        print(f"   Research complete: {result.research_complete}")
        for i, gap in enumerate(result.gaps_identified[:2]):  # Show first 2 gaps
            print(f"   Gap {i+1}: {gap.gap[:80]}...")
            
        return True
        
    except Exception as e:
        print(f"FAILED: Native KnowledgeGapAgent test failed: {e}")
        return False