"""
Enhanced Knowledge Gap Agent with Outlines integration and dual-path architecture.

This agent analyzes research progress and identifies remaining knowledge gaps using structured
generation for reliable output. Follows HYBRID-07 architecture with:

- Dual-path structured/legacy generation
- Enhanced gap analysis with metadata (priority, confidence, research approaches)  
- Template system with runtime date injection
- Dedicated ModelRole.KNOWLEDGE_GAP integration
- Backward compatibility with existing KnowledgeGapOutput interface

Input formats supported:
- Dictionary with structured parameters
- ResearchRunner formatted strings 
- Simple string queries (fallback)

Output: Enhanced KnowledgeGapResult with comprehensive gap analysis and metadata
"""

from typing import Union, Dict, Any
from .baseclass import ResearchAgent
from ..llm_config import LLMConfig, model_supports_structured_output
from .utils.parse_output import create_type_parser

# Import enhanced schemas with backward compatibility
from .utils.outlines_schemas import KnowledgeGapResult, KnowledgeGapOutput, analyze_knowledge_gaps
from .utils.outlines_templates import (
    render_knowledge_gap_prompt, 
    render_legacy_knowledge_gap_prompt,
    extract_knowledge_gap_params
)


def init_knowledge_gap_agent(config: LLMConfig) -> ResearchAgent:
    """Initialize KnowledgeGapAgent with dual-path Outlines integration following HYBRID-07 architecture"""
    from .utils.model_role_registry import ModelRole
    
    # CRITICAL: Use dedicated KNOWLEDGE_GAP role (not PLANNER)
    selected_model = config.get_model_for_role(ModelRole.KNOWLEDGE_GAP)
    
    # Check Outlines availability and model support for structured generation
    outlines_available = False
    generator = None
    
    try:
        import outlines
        if model_supports_structured_output(selected_model):
            # Create JSON schema and generator for structured output
            schema = outlines.json_schema(KnowledgeGapResult)
            generator = outlines.Generator(selected_model, schema)
            outlines_available = True
            print(f"[INFO] KnowledgeGapAgent: Using Outlines structured generation with {selected_model}")
        else:
            print(f"[INFO] KnowledgeGapAgent: Model {selected_model} doesn't support structured output, using legacy parsing")
            outlines_available = False
    except (ImportError, Exception) as e:
        print(f"[WARNING] KnowledgeGapAgent: Outlines not available ({e}), falling back to legacy parsing")
        outlines_available = False
        generator = None
    
    if outlines_available and generator:
        # Structured path with Outlines integration
        def structured_generator(input_data: Union[str, Dict[str, Any]]) -> KnowledgeGapResult:
            """Generate structured gap analysis using Outlines"""
            try:
                # Extract parameters using template system
                params = extract_knowledge_gap_params(input_data)
                
                # Render structured prompt with runtime content population
                prompt = render_knowledge_gap_prompt(**params)
                
                # Generate structured output using Outlines
                result = generator(prompt)
                
                return result
            except Exception as e:
                print(f"[ERROR] KnowledgeGapAgent structured generation failed: {e}")
                # Fallback to legacy path on error
                raise e
        
        return ResearchAgent(
            name="KnowledgeGapAgent", 
            instructions="",  # Template handles instructions
            model=selected_model,
            output_type=KnowledgeGapResult,
            structured_generator=structured_generator
        )
    else:
        # Legacy path with dynamic instructions and enhanced parsing
        def dynamic_instructions(input_data: Union[str, Dict[str, Any]]) -> str:
            """Generate dynamic instructions for legacy parsing using template system"""
            try:
                # Extract parameters and render legacy prompt
                params = extract_knowledge_gap_params(input_data)
                return render_legacy_knowledge_gap_prompt(**params)
            except Exception as e:
                print(f"[ERROR] KnowledgeGapAgent template rendering failed: {e}")
                # Ultimate fallback to basic prompt
                research_context = str(input_data) if isinstance(input_data, str) else input_data.get("research_context", "research query")
                return render_legacy_knowledge_gap_prompt(research_context)
        
        return ResearchAgent(
            name="KnowledgeGapAgent",
            instructions=dynamic_instructions,  # Function for dynamic instruction generation
            model=selected_model,
            output_type=None,  # Legacy parsing path
            output_parser=create_type_parser(KnowledgeGapResult)  # Enhanced parser
        )