"""
Quick test of current KnowledgeGap agent implementation for SLICE-9-02 analysis
"""

import asyncio
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.knowledge_gap_agent import init_knowledge_gap_agent

def test_knowledge_gap_agent_current():
    """Test current KnowledgeGap agent configuration and capabilities"""
    print("=== Testing Current KnowledgeGap Agent ===")
    
    # Create minimal config
    config = LLMConfig(
        search_provider="serper",  # Use valid search provider
        reasoning_model_provider="openai",
        reasoning_model="gpt-4"
    )
    
    # Initialize agent
    try:
        agent = init_knowledge_gap_agent(config)
        print(f"[PASS] Agent initialized successfully")
        print(f"  - Name: {agent.name}")
        print(f"  - Model: {agent.model}")
        print(f"  - Output type: {agent.output_type}")
        print(f"  - Has structured_generator: {hasattr(agent, 'structured_generator') and agent.structured_generator is not None}")
        print(f"  - Instructions type: {type(agent.instructions)}")
        
        # Test parameter extraction
        from deep_researcher.agents.utils.outlines_templates import extract_knowledge_gap_params
        
        # Test dictionary input
        dict_input = {
            "research_context": "quantum computing applications",
            "background_context": "Recent advances in quantum error correction",
            "findings_history": "Found information about IBM quantum processors",
            "iteration_context": {"iteration": 2, "time_elapsed": 5.5}
        }
        
        params = extract_knowledge_gap_params(dict_input)
        print(f"[PASS] Parameter extraction works for dict input")
        print(f"  - Research context: {params['research_context'][:50]}...")
        print(f"  - Has iteration context: {params['iteration_context'] is not None}")
        
        # Test string input
        string_input = """ORIGINAL QUERY: quantum computing applications in healthcare
        
BACKGROUND CONTEXT: Healthcare applications of quantum computing are emerging
        
HISTORY OF ACTIONS TAKEN: Searched for quantum algorithms, found IBM research"""
        
        params = extract_knowledge_gap_params(string_input)
        print(f"[PASS] Parameter extraction works for structured string input")
        print(f"  - Research context: {params['research_context'][:50]}...")
        print(f"  - Background context: {params['background_context'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Agent initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_knowledge_gap_agent_current()
    if success:
        print("\n[SUCCESS] Current KnowledgeGap agent is functional")
        print("Ready to implement ValidationWrapper integration for SLICE-9-02")
    else:
        print("\n[ERROR] Issues found with current implementation")