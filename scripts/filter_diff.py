#!/usr/bin/env python3
"""
Filter a unified diff to include only specific files.
Used to extract language-specific portions of a PR diff.
"""

import argparse
import json
import re
from typing import Optional


def parse_diff_sections(diff_content: str) -> dict[str, str]:
    """
    Parse a unified diff into sections by file.
    
    Returns:
        Dict mapping file paths to their diff content
    """
    sections = {}
    current_file = None
    current_content = []
    
    for line in diff_content.split('\n'):
        # Match diff header: diff --git a/path/to/file b/path/to/file
        match = re.match(r'^diff --git a/(.+?) b/(.+)$', line)
        
        if match:
            # Save previous section
            if current_file is not None:
                sections[current_file] = '\n'.join(current_content)
            
            # Start new section
            current_file = match.group(2)  # Use the 'b' path (new file path)
            current_content = [line]
        elif current_file is not None:
            current_content.append(line)
    
    # Save last section
    if current_file is not None:
        sections[current_file] = '\n'.join(current_content)
    
    return sections


def filter_diff(
    diff_content: str,
    include_files: list[str],
    exclude_patterns: Optional[list[str]] = None
) -> str:
    """
    Filter diff to include only specified files.
    
    Args:
        diff_content: Full unified diff
        include_files: List of file paths to include
        exclude_patterns: Optional list of patterns to exclude
        
    Returns:
        Filtered diff containing only matching files
    """
    sections = parse_diff_sections(diff_content)
    
    # Normalize include files (handle potential path differences)
    include_set = set(include_files)
    # Also add versions without leading slashes
    include_set.update(f.lstrip('/') for f in include_files)
    
    filtered_sections = []
    
    for file_path, content in sections.items():
        # Check if file is in include list
        normalized_path = file_path.lstrip('/')
        
        if file_path in include_set or normalized_path in include_set:
            # Check exclusion patterns
            if exclude_patterns:
                excluded = any(
                    re.search(pattern, file_path) 
                    for pattern in exclude_patterns
                )
                if excluded:
                    continue
            
            filtered_sections.append(content)
    
    return '\n'.join(filtered_sections)


def main():
    parser = argparse.ArgumentParser(description='Filter diff to specific files')
    parser.add_argument('--diff', required=True, help='Path to diff file')
    parser.add_argument('--files', required=True, help='JSON array of files to include')
    parser.add_argument('--output', required=True, help='Output filtered diff file')
    parser.add_argument('--exclude', help='Comma-separated patterns to exclude')
    
    args = parser.parse_args()
    
    # Load diff
    with open(args.diff, 'r') as f:
        diff_content = f.read()
    
    # Parse files list
    try:
        include_files = json.loads(args.files)
    except json.JSONDecodeError:
        # Try as comma-separated
        include_files = [f.strip() for f in args.files.split(',')]
    
    # Parse exclude patterns
    exclude_patterns = None
    if args.exclude:
        exclude_patterns = [p.strip() for p in args.exclude.split(',')]
    
    # Filter
    filtered = filter_diff(
        diff_content=diff_content,
        include_files=include_files,
        exclude_patterns=exclude_patterns
    )
    
    # Write output
    with open(args.output, 'w') as f:
        f.write(filtered)
    
    # Report
    original_files = len(parse_diff_sections(diff_content))
    filtered_files = len(parse_diff_sections(filtered))
    print(f"Filtered {original_files} files down to {filtered_files} files")


if __name__ == '__main__':
    main()
