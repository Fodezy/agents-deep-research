#!/usr/bin/env python3
"""Test deep research with disabled runtime assertions"""

import os
import asyncio

# Disable runtime assertions
os.environ['DISABLE_RUNTIME_ASSERTIONS'] = 'true'

from deep_researcher.main import main

async def test_with_disabled_assertions():
    # Mock sys.argv to simulate command line
    import sys
    original_argv = sys.argv
    try:
        sys.argv = [
            'main.py',
            '--mode', 'deep',
            '--query', 'What is quantum entanglement?',
            '--max-time', '2'
        ]
        
        await main()
        
    finally:
        sys.argv = original_argv

if __name__ == "__main__":
    asyncio.run(test_with_disabled_assertions())