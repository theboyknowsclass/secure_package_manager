#!/usr/bin/env python3
"""Quick script to fix test method signatures."""

import re
from pathlib import Path

def fix_test_file(file_path: Path) -> None:
    """Fix test method signatures in a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Fix test methods missing self parameter
    content = re.sub(
        r'def (test_\w+)\(\) -> None:',
        r'def \1(self) -> None:',
        content
    )
    
    # Fix setUp and tearDown methods
    content = re.sub(
        r'def (setUp|tearDown)\(\) -> None:',
        r'def \1(self) -> None:',
        content
    )
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Fixed {file_path.name}")

def main():
    """Fix all test files."""
    test_files = list(Path("tests").rglob("*.py"))
    
    for test_file in test_files:
        if test_file.name == "__init__.py":
            continue
        fix_test_file(test_file)

if __name__ == "__main__":
    main()
