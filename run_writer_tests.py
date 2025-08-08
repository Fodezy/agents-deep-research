#!/usr/bin/env python
"""Run WriterAgent production guardrails tests for SLICE-9-03"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import and run the tests
from tests.test_writer_agent_production_guardrails import main
import asyncio

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)