#!/usr/bin/env python3
"""
Format analysis results into GitHub PR review comments.
Aggregates results from multiple language analyzers and creates
readable, actionable feedback.
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Optional


# Severity configuration
SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info']
SEVERITY_EMOJI = {
    'critical': '🚨',
    'high': '❌',
    'medium': '⚠️',
    'low': '💡',
    'info': 'ℹ️'
}
SEVERITY_COLORS = {
    'critical': '#d73a49',
    'high': '#cb2431',
    'medium': '#f66a0a',
    'low': '#0366d6',
    'info': '#6a737d'
}


def load_all_results(results_dir: str) -> list[dict]:
    """Load all JSON result files from directory."""
    results = []
    results_path = Path(results_dir)
    
    for json_file in results_path.glob('*.json'):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                data['_source_file'] = json_file.name
                results.append(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load {json_file}: {e}")
    
    return results


def aggregate_violations(results: list[dict]) -> list[dict]:
    """Combine violations from all results, sorted by severity."""
    all_violations = []
    
    for result in results:
        source = result.get('_source_file', 'unknown')
        language = result.get('metadata', {}).get('language', 'common')
        
        for violation in result.get('violations', []):
            violation['_source'] = source
            violation['_language'] = language
            all_violations.append(violation)
    
    # Sort by severity
    def severity_key(v):
        sev = v.get('severity', 'medium').lower()
        return SEVERITY_ORDER.index(sev) if sev in SEVERITY_ORDER else 99
    
    return sorted(all_violations, key=severity_key)


def get_max_severity(violations: list[dict]) -> str:
    """Get the highest severity from all violations."""
    if not violations:
        return 'none'
    
    severities = [v.get('severity', 'medium').lower() for v in violations]
    for sev in SEVERITY_ORDER:
        if sev in severities:
            return sev
    return 'medium'


def format_violation_markdown(violation: dict) -> str:
    """Format a single violation as markdown."""
    severity = violation.get('severity', 'medium').lower()
    emoji = SEVERITY_EMOJI.get(severity, '❓')
    
    rule_id = violation.get('rule_id', 'UNKNOWN')
    rule_name = violation.get('rule_name', 'Unnamed Rule')
    file_path = violation.get('file', 'unknown')
    line = violation.get('line', '?')
    line_end = violation.get('line_end')
    explanation = violation.get('explanation', 'No explanation provided')
    suggestion = violation.get('suggestion', '')
    code_snippet = violation.get('code_snippet', '')
    confidence = violation.get('confidence', 0)
    
    # Format location
    if line_end and line_end != line:
        location = f"`{file_path}` (lines {line}-{line_end})"
    else:
        location = f"`{file_path}:{line}`"
    
    md = f"""
#### {emoji} [{rule_id}] {rule_name}

**Location:** {location}

{explanation}
"""
    
    if code_snippet:
        md += f"""
<details>
<summary>Code</summary>

```
{code_snippet}
```
</details>
"""
    
    if suggestion:
        md += f"""
**💡 Suggestion:** {suggestion}
"""
    
    if confidence and confidence < 0.8:
        md += f"\n_Confidence: {confidence:.0%}_"
    
    return md


def format_summary_table(violations: list[dict]) -> str:
    """Create a summary table of violations by severity."""
    counts = {}
    for v in violations:
        sev = v.get('severity', 'medium').lower()
        counts[sev] = counts.get(sev, 0) + 1
    
    if not counts:
        return "✅ **No violations found!**"
    
    rows = []
    for sev in SEVERITY_ORDER:
        if sev in counts:
            emoji = SEVERITY_EMOJI.get(sev, '❓')
            rows.append(f"| {emoji} {sev.title()} | {counts[sev]} |")
    
    table = """| Severity | Count |
|----------|-------|
""" + "\n".join(rows)
    
    return table


def format_full_review(
    results: list[dict],
    violations: list[dict],
    max_violations_shown: int = 15
) -> str:
    """Format the complete PR review comment."""
    
    total_violations = len(violations)
    max_severity = get_max_severity(violations)
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    
    # Header based on results
    if total_violations == 0:
        header = "## ✅ Code Review Passed"
        status_text = "No rule violations detected in this PR."
    elif max_severity == 'critical':
        header = "## 🚨 Code Review: Critical Issues Found"
        status_text = f"Found **{total_violations}** violation(s) including critical issues that must be addressed."
    elif max_severity == 'high':
        header = "## ❌ Code Review: Issues Found"
        status_text = f"Found **{total_violations}** violation(s) that should be addressed before merge."
    else:
        header = "## ⚠️ Code Review: Suggestions"
        status_text = f"Found **{total_violations}** item(s) to review."
    
    # Build review
    review = f"""{header}

{status_text}

### Summary

{format_summary_table(violations)}

"""
    
    # Add violations
    if violations:
        review += "### Violations\n"
        
        shown = violations[:max_violations_shown]
        for v in shown:
            review += format_violation_markdown(v)
        
        if len(violations) > max_violations_shown:
            remaining = len(violations) - max_violations_shown
            review += f"\n\n_... and {remaining} more violations not shown._\n"
    
    # Add recommendations
    all_recommendations = []
    for result in results:
        all_recommendations.extend(result.get('recommendations', []))
    
    unique_recommendations = list(set(all_recommendations))
    if unique_recommendations:
        review += "\n### General Recommendations\n\n"
        for rec in unique_recommendations[:5]:
            review += f"- {rec}\n"
    
    # Footer
    review += f"""
---
<sub>Generated by PR Validation Agent • {timestamp}</sub>
"""
    
    return review


def extract_inline_comments(violations: list[dict]) -> list[dict]:
    """
    Extract violations suitable for inline PR comments.
    Only includes violations with specific file/line locations.
    """
    inline = []
    
    for v in violations:
        file_path = v.get('file')
        line = v.get('line')
        
        if not file_path or not line or line == '?':
            continue
        
        severity = v.get('severity', 'medium').lower()
        emoji = SEVERITY_EMOJI.get(severity, '⚠️')
        rule_id = v.get('rule_id', '')
        explanation = v.get('explanation', 'Issue detected')
        suggestion = v.get('suggestion', '')
        
        body = f"{emoji} **{rule_id}**: {explanation}"
        if suggestion:
            body += f"\n\n💡 {suggestion}"
        
        inline.append({
            'path': file_path,
            'line': int(line) if isinstance(line, (int, str)) and str(line).isdigit() else None,
            'body': body,
            'severity': severity
        })
    
    # Filter out any with invalid line numbers
    return [c for c in inline if c['line'] is not None]


def main():
    parser = argparse.ArgumentParser(description='Format analysis results as PR review')
    parser.add_argument('--results-dir', required=True, help='Directory containing result JSON files')
    parser.add_argument('--output', required=True, help='Output markdown file')
    parser.add_argument('--summary', required=True, help='Output summary JSON file')
    parser.add_argument('--max-shown', type=int, default=15, help='Max violations to show in detail')
    
    args = parser.parse_args()
    
    # Load all results
    results = load_all_results(args.results_dir)
    
    if not results:
        print("No results found to process")
        # Create empty outputs
        with open(args.output, 'w') as f:
            f.write("## ✅ Code Review Passed\n\nNo analysis results available.")
        with open(args.summary, 'w') as f:
            json.dump({
                'has_violations': False,
                'total_violations': 0,
                'max_severity': 'none',
                'inline_comments': []
            }, f)
        return
    
    # Aggregate violations
    violations = aggregate_violations(results)
    
    print(f"Loaded {len(results)} result file(s) with {len(violations)} total violation(s)")
    
    # Format review
    review_md = format_full_review(
        results=results,
        violations=violations,
        max_violations_shown=args.max_shown
    )
    
    # Extract inline comments
    inline_comments = extract_inline_comments(violations)
    
    # Write outputs
    with open(args.output, 'w') as f:
        f.write(review_md)
    
    summary = {
        'has_violations': len(violations) > 0,
        'total_violations': len(violations),
        'max_severity': get_max_severity(violations),
        'by_severity': {},
        'by_language': {},
        'inline_comments': inline_comments[:20]  # Limit inline comments
    }
    
    # Count by severity
    for v in violations:
        sev = v.get('severity', 'medium')
        summary['by_severity'][sev] = summary['by_severity'].get(sev, 0) + 1
    
    # Count by language
    for v in violations:
        lang = v.get('_language', 'common')
        summary['by_language'][lang] = summary['by_language'].get(lang, 0) + 1
    
    with open(args.summary, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Review written to {args.output}")
    print(f"Summary written to {args.summary}")
    
    # Print summary for logs
    if violations:
        print(f"\nViolation Summary:")
        for sev in SEVERITY_ORDER:
            count = summary['by_severity'].get(sev, 0)
            if count:
                print(f"  {SEVERITY_EMOJI.get(sev, '?')} {sev.title()}: {count}")


if __name__ == '__main__':
    main()
