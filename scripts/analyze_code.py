#!/usr/bin/env python3
"""
Main code analysis script that orchestrates LLM-based code review.
Sends code diffs to Databricks Model Serving with appropriate rules and prompts.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional
import yaml

from databricks_client import DatabricksModelClient
from detect_language import detect_language_from_content


def load_rules(rules_path: str) -> dict:
    """Load rules from YAML file."""
    with open(rules_path, 'r') as f:
        return yaml.safe_load(f)


def load_prompt(prompt_path: str) -> str:
    """Load prompt template from markdown file."""
    with open(prompt_path, 'r') as f:
        return f.read()


def build_system_prompt(
    base_prompt: str,
    rules: dict,
    language: Optional[str] = None,
    language_prompt: Optional[str] = None,
    strictness: str = "normal"
) -> str:
    """
    Build the complete system prompt combining:
    - Base instructions
    - Rules (formatted)
    - Language-specific guidance
    - Strictness level
    """
    
    # Format rules into readable structure
    rules_text = format_rules_for_prompt(rules)
    
    # Build strictness instruction
    strictness_instruction = {
        "low": "Focus only on critical issues. Be lenient with style preferences.",
        "normal": "Balance between catching issues and avoiding false positives.",
        "high": "Be thorough. Flag any potential violations, even minor ones. This code is from an external contractor and requires careful review."
    }.get(strictness, "normal")
    
    prompt = f"""{base_prompt}

## Strictness Level: {strictness.upper()}
{strictness_instruction}

## Rules to Enforce

{rules_text}
"""
    
    if language and language_prompt:
        prompt += f"""
## Language-Specific Guidelines ({language.title()})

{language_prompt}
"""
    
    prompt += """
## Output Format

You MUST respond with valid JSON only. No markdown, no explanation outside JSON.

```json
{
  "summary": "Brief overall assessment",
  "violations": [
    {
      "severity": "critical|high|medium|low|info",
      "rule_id": "RULE-XXX",
      "rule_name": "Name of violated rule",
      "file": "path/to/file.ext",
      "line": 42,
      "line_end": 45,
      "code_snippet": "the problematic code",
      "explanation": "Why this violates the rule",
      "suggestion": "How to fix it",
      "confidence": 0.95
    }
  ],
  "passed_checks": ["List of rules that passed"],
  "recommendations": ["General improvement suggestions"],
  "metrics": {
    "files_analyzed": 5,
    "total_lines": 234,
    "violation_density": 0.02
  }
}
```

Be precise about line numbers. Only report violations you are confident about (>0.7 confidence).
"""
    
    return prompt


def format_rules_for_prompt(rules: dict) -> str:
    """Convert rules dict into LLM-friendly format."""
    lines = []
    
    for category, category_rules in rules.get('rules', {}).items():
        lines.append(f"### {category.replace('_', ' ').title()}")
        lines.append("")
        
        for rule in category_rules:
            rule_id = rule.get('id', 'UNKNOWN')
            name = rule.get('name', 'Unnamed Rule')
            description = rule.get('description', '')
            severity = rule.get('severity', 'medium')
            
            lines.append(f"**[{rule_id}] {name}** (Severity: {severity})")
            lines.append(f"  {description}")
            
            if 'good_example' in rule:
                lines.append(f"  ✅ Good: `{rule['good_example']}`")
            if 'bad_example' in rule:
                lines.append(f"  ❌ Bad: `{rule['bad_example']}`")
            
            lines.append("")
    
    return "\n".join(lines)


def chunk_diff(diff_content: str, max_tokens: int = 6000) -> list[str]:
    """
    Split large diffs into chunks that fit within token limits.
    Tries to split on file boundaries.
    """
    # Rough estimate: 1 token ≈ 4 characters
    max_chars = max_tokens * 4
    
    if len(diff_content) <= max_chars:
        return [diff_content]
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    # Split by file (diff sections start with 'diff --git')
    file_diffs = diff_content.split('diff --git ')
    
    for i, file_diff in enumerate(file_diffs):
        if i == 0 and not file_diff.strip():
            continue
        
        section = ('diff --git ' + file_diff) if i > 0 else file_diff
        section_size = len(section)
        
        if current_size + section_size > max_chars and current_chunk:
            chunks.append('\n'.join(current_chunk))
            current_chunk = []
            current_size = 0
        
        current_chunk.append(section)
        current_size += section_size
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks


def analyze_with_llm(
    client: DatabricksModelClient,
    diff_content: str,
    system_prompt: str,
    language: Optional[str] = None
) -> dict:
    """Send diff to LLM and get analysis results."""
    
    user_message = f"""Please analyze the following code diff for rule violations:

```diff
{diff_content}
```

Identify any violations of the rules specified in your instructions. Be thorough but avoid false positives.
{"Focus on " + language + " specific patterns." if language else ""}
"""
    
    response = client.query(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.1,  # Low temperature for consistent, factual responses
        max_tokens=4000
    )
    
    # Parse JSON response
    try:
        # Handle potential markdown code blocks in response
        response_text = response.strip()
        if response_text.startswith('```'):
            # Extract content between code fences
            lines = response_text.split('\n')
            json_lines = []
            in_json = False
            for line in lines:
                if line.startswith('```') and not in_json:
                    in_json = True
                    continue
                elif line.startswith('```') and in_json:
                    break
                elif in_json:
                    json_lines.append(line)
            response_text = '\n'.join(json_lines)
        
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse LLM response as JSON: {e}",
            "raw_response": response[:500],
            "violations": [],
            "summary": "Analysis failed due to response parsing error"
        }


def merge_chunk_results(results: list[dict]) -> dict:
    """Merge results from multiple diff chunks."""
    merged = {
        "summary": "",
        "violations": [],
        "passed_checks": set(),
        "recommendations": [],
        "metrics": {
            "files_analyzed": 0,
            "total_lines": 0,
            "violation_density": 0
        }
    }
    
    summaries = []
    total_lines = 0
    
    for result in results:
        if 'error' in result:
            continue
        
        summaries.append(result.get('summary', ''))
        merged['violations'].extend(result.get('violations', []))
        merged['passed_checks'].update(result.get('passed_checks', []))
        merged['recommendations'].extend(result.get('recommendations', []))
        
        metrics = result.get('metrics', {})
        merged['metrics']['files_analyzed'] += metrics.get('files_analyzed', 0)
        total_lines += metrics.get('total_lines', 0)
    
    # Deduplicate violations by file+line+rule
    seen = set()
    unique_violations = []
    for v in merged['violations']:
        key = (v.get('file'), v.get('line'), v.get('rule_id'))
        if key not in seen:
            seen.add(key)
            unique_violations.append(v)
    
    merged['violations'] = unique_violations
    merged['passed_checks'] = list(merged['passed_checks'])
    merged['recommendations'] = list(set(merged['recommendations']))
    merged['summary'] = ' '.join(summaries) if summaries else 'Analysis complete.'
    merged['metrics']['total_lines'] = total_lines
    
    if total_lines > 0:
        merged['metrics']['violation_density'] = len(unique_violations) / total_lines
    
    return merged


def main():
    parser = argparse.ArgumentParser(description='Analyze code diff for rule violations')
    parser.add_argument('--diff', required=True, help='Path to diff file')
    parser.add_argument('--rules', required=True, help='Path to rules YAML file')
    parser.add_argument('--prompt', required=True, help='Path to prompt template')
    parser.add_argument('--base-prompt', help='Path to base system prompt (optional)')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    parser.add_argument('--language', help='Programming language being analyzed')
    parser.add_argument('--strictness', default='normal', 
                       choices=['low', 'normal', 'high'],
                       help='Analysis strictness level')
    
    args = parser.parse_args()
    
    # Load inputs
    with open(args.diff, 'r') as f:
        diff_content = f.read()
    
    if not diff_content.strip():
        print("Empty diff, nothing to analyze")
        result = {"summary": "No changes to analyze", "violations": []}
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        return
    
    rules = load_rules(args.rules)
    
    # Load prompts
    if args.base_prompt:
        base_prompt = load_prompt(args.base_prompt)
        language_prompt = load_prompt(args.prompt)
    else:
        base_prompt = load_prompt(args.prompt)
        language_prompt = None
    
    # Build system prompt
    system_prompt = build_system_prompt(
        base_prompt=base_prompt,
        rules=rules,
        language=args.language,
        language_prompt=language_prompt,
        strictness=args.strictness
    )
    
    # Initialize Databricks client
    client = DatabricksModelClient(
        host=os.environ['DATABRICKS_HOST'],
        token=os.environ['DATABRICKS_TOKEN'],
        endpoint=os.environ.get('DATABRICKS_ENDPOINT', 'code-review-v1')
    )
    
    # Chunk large diffs
    chunks = chunk_diff(diff_content)
    print(f"Analyzing {len(chunks)} chunk(s)...")
    
    # Analyze each chunk
    results = []
    for i, chunk in enumerate(chunks):
        print(f"  Processing chunk {i+1}/{len(chunks)}...")
        result = analyze_with_llm(
            client=client,
            diff_content=chunk,
            system_prompt=system_prompt,
            language=args.language
        )
        results.append(result)
    
    # Merge results
    final_result = merge_chunk_results(results) if len(results) > 1 else results[0]
    
    # Add metadata
    final_result['metadata'] = {
        'language': args.language,
        'strictness': args.strictness,
        'rules_file': args.rules,
        'chunks_analyzed': len(chunks)
    }
    
    # Write output
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(final_result, f, indent=2)
    
    print(f"Analysis complete. Found {len(final_result.get('violations', []))} violation(s)")
    
    # Print summary to stdout for workflow logs
    for v in final_result.get('violations', [])[:5]:
        severity = v.get('severity', 'unknown').upper()
        rule = v.get('rule_id', 'UNKNOWN')
        file = v.get('file', 'unknown')
        line = v.get('line', '?')
        print(f"  [{severity}] {rule}: {file}:{line}")
    
    if len(final_result.get('violations', [])) > 5:
        print(f"  ... and {len(final_result['violations']) - 5} more")


if __name__ == '__main__':
    main()
