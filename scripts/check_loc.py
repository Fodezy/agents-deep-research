#!/usr/bin/env python3
"""Simple script to check lines of code in TokenChunker"""

import sys
from pathlib import Path

def count_loc(file_path: Path) -> int:
    """Count non-empty lines in a Python file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line for line in f.readlines() if line.strip()]
    return len(lines)

def main():
    token_chunker_path = Path("deep_researcher/agents/utils/token_chunker.py")
    
    if not token_chunker_path.exists():
        print(f"Error: {token_chunker_path} not found")
        sys.exit(1)
    
    loc = count_loc(token_chunker_path)
    max_loc = 150
    
    print(f"TokenChunker lines of code: {loc}")
    print(f"Maximum allowed: {max_loc}")
    
    if loc <= max_loc:
        print("[OK] PASS: Under LoC limit")
        sys.exit(0)
    else:
        print("[FAIL] FAIL: Exceeds LoC limit")
        sys.exit(1)

if __name__ == "__main__":
    main()