#!/usr/bin/env python3
"""
Language detection utilities for code analysis.
Detects programming languages from file extensions and content.
"""

import re
from pathlib import Path
from typing import Optional


# File extension to language mapping
EXTENSION_MAP = {
    # Python
    'py': 'python',
    'pyi': 'python',
    'pyx': 'python',
    
    # Java
    'java': 'java',
    
    # JavaScript/TypeScript
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'javascript',
    'tsx': 'javascript',
    'mjs': 'javascript',
    'cjs': 'javascript',
    
    # Go
    'go': 'go',
    
    # Rust
    'rs': 'rust',
    
    # C/C++
    'c': 'c',
    'h': 'c',
    'cpp': 'cpp',
    'hpp': 'cpp',
    'cc': 'cpp',
    'cxx': 'cpp',
    
    # Ruby
    'rb': 'ruby',
    
    # PHP
    'php': 'php',
    
    # Shell
    'sh': 'shell',
    'bash': 'shell',
    'zsh': 'shell',
    
    # Infrastructure
    'tf': 'terraform',
    'hcl': 'terraform',
    
    # Configuration
    'yaml': 'yaml',
    'yml': 'yaml',
    'json': 'json',
    'toml': 'toml',
    
    # Web
    'html': 'html',
    'css': 'css',
    'scss': 'css',
    'sass': 'css',
    'less': 'css',
    
    # SQL
    'sql': 'sql',
    
    # Kotlin
    'kt': 'kotlin',
    'kts': 'kotlin',
    
    # Swift
    'swift': 'swift',
    
    # Scala
    'scala': 'scala',
    'sc': 'scala',
}

# Content patterns for additional detection
CONTENT_PATTERNS = {
    'python': [
        r'^#!/usr/bin/env python',
        r'^#!/usr/bin/python',
        r'^import\s+\w+',
        r'^from\s+\w+\s+import',
        r'^def\s+\w+\s*\(',
        r'^class\s+\w+(\s*\(.*\))?\s*:',
    ],
    'javascript': [
        r'^import\s+.*\s+from\s+["\']',
        r'^const\s+\w+\s*=',
        r'^let\s+\w+\s*=',
        r'^export\s+(default\s+)?(function|class|const)',
        r'^\s*function\s+\w+\s*\(',
        r'^\s*class\s+\w+\s*(extends|{)',
    ],
    'java': [
        r'^package\s+[\w.]+;',
        r'^import\s+[\w.]+;',
        r'^public\s+(class|interface|enum)\s+\w+',
        r'^@\w+(\(.*\))?$',
    ],
    'go': [
        r'^package\s+\w+',
        r'^import\s+\(',
        r'^func\s+(\(\w+\s+\*?\w+\)\s+)?\w+\(',
        r'^type\s+\w+\s+(struct|interface)\s*{',
    ],
    'terraform': [
        r'^resource\s+"[\w_]+"',
        r'^provider\s+"[\w_]+"',
        r'^variable\s+"[\w_]+"',
        r'^module\s+"[\w_]+"',
        r'^terraform\s*{',
    ],
    'kubernetes': [
        r'^apiVersion:\s*',
        r'^kind:\s*(Deployment|Service|ConfigMap|Pod|Ingress)',
        r'^metadata:\s*$',
        r'^spec:\s*$',
    ],
    'shell': [
        r'^#!/bin/(ba)?sh',
        r'^#!/usr/bin/env\s+(ba)?sh',
        r'^\s*if\s+\[\[?\s+',
        r'^\s*for\s+\w+\s+in\s+',
    ],
}


def detect_language_from_extension(file_path: str) -> Optional[str]:
    """Detect language from file extension."""
    ext = Path(file_path).suffix.lstrip('.').lower()
    return EXTENSION_MAP.get(ext)


def detect_language_from_content(content: str) -> Optional[str]:
    """Detect language from file content patterns."""
    lines = content.split('\n')[:50]  # Check first 50 lines
    
    scores = {}
    
    for language, patterns in CONTENT_PATTERNS.items():
        for pattern in patterns:
            for line in lines:
                if re.search(pattern, line.strip()):
                    scores[language] = scores.get(language, 0) + 1
    
    if not scores:
        return None
    
    # Return language with highest score
    return max(scores, key=scores.get)


def detect_language(file_path: str, content: Optional[str] = None) -> str:
    """
    Detect programming language from file path and optionally content.
    
    Args:
        file_path: Path to the file
        content: Optional file content for deeper analysis
        
    Returns:
        Detected language or 'unknown'
    """
    # Try extension first
    lang = detect_language_from_extension(file_path)
    if lang:
        # Special case: YAML might be Kubernetes
        if lang == 'yaml' and content:
            content_lang = detect_language_from_content(content)
            if content_lang == 'kubernetes':
                return 'kubernetes'
        return lang
    
    # Try content patterns
    if content:
        lang = detect_language_from_content(content)
        if lang:
            return lang
    
    return 'unknown'


def categorize_files(file_list: list[str]) -> dict[str, list[str]]:
    """
    Categorize a list of files by programming language.
    
    Args:
        file_list: List of file paths
        
    Returns:
        Dict mapping language to list of file paths
    """
    categories = {}
    
    for file_path in file_list:
        lang = detect_language(file_path)
        if lang not in categories:
            categories[lang] = []
        categories[lang].append(file_path)
    
    return categories


def get_supported_languages() -> list[str]:
    """Return list of languages we have rules for."""
    return ['python', 'java', 'javascript', 'go', 'terraform', 'kubernetes', 'shell']


def is_code_file(file_path: str) -> bool:
    """Check if a file is a code file we should analyze."""
    ext = Path(file_path).suffix.lstrip('.').lower()
    
    # Skip common non-code files
    skip_extensions = {
        'md', 'txt', 'rst', 'lock', 'sum',
        'png', 'jpg', 'jpeg', 'gif', 'svg', 'ico',
        'woff', 'woff2', 'ttf', 'eot',
        'zip', 'tar', 'gz', 'bz2',
        'pdf', 'doc', 'docx',
    }
    
    if ext in skip_extensions:
        return False
    
    # Check if it's in our extension map
    return ext in EXTENSION_MAP


# Main for testing
if __name__ == '__main__':
    # Test detection
    test_files = [
        'src/main.py',
        'services/UserService.java',
        'components/Button.tsx',
        'main.go',
        'terraform/main.tf',
        'deploy/k8s/deployment.yaml',
        'scripts/build.sh',
        'README.md',
        'package-lock.json',
    ]
    
    print("File language detection test:")
    for f in test_files:
        lang = detect_language(f)
        is_code = is_code_file(f)
        print(f"  {f}: {lang} (analyze: {is_code})")
    
    print("\nCategorized:")
    categories = categorize_files(test_files)
    for lang, files in categories.items():
        print(f"  {lang}: {files}")
