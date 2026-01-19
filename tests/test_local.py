#!/usr/bin/env python3
"""
Local development test runner for PR validation agents.
Allows testing the analysis without GitHub Actions.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def check_environment():
    """Check required environment variables."""
    required = ['DATABRICKS_HOST', 'DATABRICKS_TOKEN']
    missing = [var for var in required if not os.environ.get(var)]
    
    if missing:
        print("Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nSet them with:")
        print("  export DATABRICKS_HOST='https://your-workspace.cloud.databricks.com'")
        print("  export DATABRICKS_TOKEN='your-token'")
        print("\nOr use --mock to test without real API calls")
        return False
    return True


def run_analysis(diff_file: str, language: str = None, mock: bool = False, strictness: str = "normal"):
    """Run analysis on a diff file."""
    
    project_root = Path(__file__).parent.parent
    scripts_dir = project_root / 'scripts'
    rules_dir = project_root / 'rules'
    prompts_dir = project_root / 'prompts'
    
    # Determine which rules to use
    if language:
        rules_file = rules_dir / f'{language}.yaml'
        if not rules_file.exists():
            print(f"No language-specific rules for {language}, using common rules only")
            rules_file = rules_dir / 'common.yaml'
    else:
        rules_file = rules_dir / 'common.yaml'
    
    print(f"📋 Using rules: {rules_file}")
    print(f"📄 Analyzing: {diff_file}")
    print(f"⚡ Strictness: {strictness}")
    print()
    
    # Build command
    cmd = [
        sys.executable,
        str(scripts_dir / 'analyze_code.py'),
        '--diff', diff_file,
        '--rules', str(rules_file),
        '--prompt', str(prompts_dir / 'system_base.md'),
        '--output', 'analysis_results.json',
        '--strictness', strictness
    ]
    
    if language:
        language_prompt = prompts_dir / 'language_specific' / f'{language}.md'
        if language_prompt.exists():
            cmd.extend(['--base-prompt', str(prompts_dir / 'system_base.md')])
            cmd[cmd.index('--prompt') + 1] = str(language_prompt)
            cmd.extend(['--language', language])
    
    if mock:
        print("🎭 Running in mock mode (no API calls)")
        # Set mock environment
        os.environ['DATABRICKS_ENDPOINT'] = 'mock'
    
    # Run analysis
    print("🔍 Running analysis...")
    print(f"   Command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    if result.returncode != 0:
        print(f"❌ Analysis failed with exit code {result.returncode}")
        return False
    
    # Display results
    if Path('analysis_results.json').exists():
        with open('analysis_results.json', 'r') as f:
            results = json.load(f)
        
        print("\n" + "="*60)
        print("📊 ANALYSIS RESULTS")
        print("="*60)
        
        print(f"\n📝 Summary: {results.get('summary', 'N/A')}")
        
        violations = results.get('violations', [])
        print(f"\n🚨 Violations Found: {len(violations)}")
        
        if violations:
            for i, v in enumerate(violations, 1):
                severity = v.get('severity', 'unknown').upper()
                rule_id = v.get('rule_id', 'UNKNOWN')
                file_path = v.get('file', 'unknown')
                line = v.get('line', '?')
                explanation = v.get('explanation', 'No explanation')
                
                severity_emoji = {
                    'CRITICAL': '🚨',
                    'HIGH': '❌',
                    'MEDIUM': '⚠️',
                    'LOW': '💡',
                    'INFO': 'ℹ️'
                }.get(severity, '❓')
                
                print(f"\n{i}. {severity_emoji} [{severity}] {rule_id}")
                print(f"   📍 {file_path}:{line}")
                print(f"   📄 {explanation[:100]}...")
                
                if v.get('suggestion'):
                    print(f"   💡 {v['suggestion'][:100]}...")
        
        passed = results.get('passed_checks', [])
        if passed:
            print(f"\n✅ Passed Checks: {len(passed)}")
            for check in passed[:5]:
                print(f"   - {check}")
            if len(passed) > 5:
                print(f"   ... and {len(passed) - 5} more")
        
        print("\n" + "="*60)
        print("Full results saved to: analysis_results.json")
        
    return True


def generate_diff_from_git(base_branch: str = "main") -> str:
    """Generate a diff from current git changes."""
    output_file = "current_changes.diff"
    
    # Check if we're in a git repo
    result = subprocess.run(['git', 'status'], capture_output=True, text=True)
    if result.returncode != 0:
        print("Not in a git repository")
        return None
    
    # Generate diff
    result = subprocess.run(
        ['git', 'diff', base_branch, '--', '.'],
        capture_output=True,
        text=True
    )
    
    if not result.stdout.strip():
        print(f"No changes compared to {base_branch}")
        return None
    
    with open(output_file, 'w') as f:
        f.write(result.stdout)
    
    print(f"Generated diff from {base_branch}: {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description='Local test runner for PR validation agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a diff file
  python test_local.py --diff my_changes.diff
  
  # Analyze with Python-specific rules
  python test_local.py --diff changes.diff --language python
  
  # Analyze current git changes
  python test_local.py --git-diff --base-branch develop
  
  # Test without API (mock mode)
  python test_local.py --diff sample.diff --mock
  
  # Strict mode (as if from contractor)
  python test_local.py --diff changes.diff --strictness high
        """
    )
    
    parser.add_argument('--diff', help='Path to diff file to analyze')
    parser.add_argument('--git-diff', action='store_true', 
                       help='Generate diff from current git changes')
    parser.add_argument('--base-branch', default='main',
                       help='Base branch for git diff (default: main)')
    parser.add_argument('--language', choices=['python', 'java', 'javascript', 'go', 'terraform'],
                       help='Programming language for specialized rules')
    parser.add_argument('--mock', action='store_true',
                       help='Run without real API calls (mock mode)')
    parser.add_argument('--strictness', choices=['low', 'normal', 'high'],
                       default='normal', help='Analysis strictness level')
    parser.add_argument('--sample', action='store_true',
                       help='Run against sample bad code for testing')
    
    args = parser.parse_args()
    
    # Determine diff file
    if args.sample:
        diff_file = str(Path(__file__).parent / 'sample_violations' / 'bad_code.diff')
        print("🧪 Running against sample bad code...")
    elif args.git_diff:
        diff_file = generate_diff_from_git(args.base_branch)
        if not diff_file:
            return
    elif args.diff:
        diff_file = args.diff
    else:
        parser.print_help()
        print("\n❌ Please provide a diff file or use --git-diff")
        return
    
    # Check environment (unless mock mode)
    if not args.mock and not check_environment():
        print("\n💡 Tip: Use --mock to test without API credentials")
        return
    
    # Run analysis
    success = run_analysis(
        diff_file=diff_file,
        language=args.language,
        mock=args.mock,
        strictness=args.strictness
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
