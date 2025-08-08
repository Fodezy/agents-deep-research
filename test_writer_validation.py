#!/usr/bin/env python3
"""Test writer agent model validation specifically"""

import asyncio
from deep_researcher.llm_config import LLMConfig
from deep_researcher.agents.writer_agent import init_writer_agent

async def test_writer_validation():
    """Test if WriterAgent can be created without validation errors"""
    print("Testing WriterAgent creation...")
    
    try:
        config = LLMConfig(search_provider='searxng')
        writer_agent = init_writer_agent(config)
        print(f"[SUCCESS] WriterAgent created successfully")
        print(f"   Model: {getattr(writer_agent.model, 'model', str(writer_agent.model))}")
        
    except Exception as e:
        print(f"[FAILED] WriterAgent creation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_writer_validation())