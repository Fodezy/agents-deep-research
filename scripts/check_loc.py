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
    # Check multiple files with their limits
    files_to_check = [
        ("deep_researcher/agents/utils/token_chunker.py", 150),
        ("deep_researcher/agents/utils/hierarchical_summariser.py", 200)
    ]
    
    all_passed = True
    
    for file_path, max_loc in files_to_check:
        path = Path(file_path)
        
        if not path.exists():
            print(f"Error: {file_path} not found")
            all_passed = False
            continue
        
        loc = count_loc(path)
        status = "PASS" if loc <= max_loc else "FAIL"
        
        print(f"{path.name} lines of code: {loc}")
        print(f"Maximum allowed: {max_loc}")
        print(f"[{status}] {'Under' if loc <= max_loc else 'Exceeds'} LoC limit")
        print()
        
        if loc > max_loc:
            all_passed = False
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()