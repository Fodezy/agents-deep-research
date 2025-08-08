#!/usr/bin/env python
"""Run SLICE-9-04 End-to-End Regression Tests"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import and run the tests
from tests.test_slice9_end_to_end_regression import main
import asyncio

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)