# Rules Configuration Guide

This guide explains how to configure and customize the validation rules for your organization.

## Rules Structure

Rules are stored in YAML files in the `rules/` directory:

```
rules/
├── common.yaml          # Universal rules (all languages)
├── python.yaml          # Python-specific rules
├── javascript.yaml      # JS/TS-specific rules
├── java.yaml           # Java-specific rules
└── infrastructure.yaml  # Terraform/K8s rules
```

## Rule Format

Each rule follows this structure:

```yaml
rules:
  category_name:
    - id: "UNIQUE-ID"           # Required: Unique identifier
      name: "Rule Name"          # Required: Human-readable name
      severity: "critical"       # Required: critical|high|medium|low|info
      description: |             # Required: What this rule checks
        Detailed explanation of the rule,
        why it matters, and what it prevents.
      
      # Optional fields:
      patterns:                  # Regex patterns to detect violations
        - "pattern1"
        - "pattern2"
      
      bad_example: |             # Example of violation
        code that breaks the rule
      
      good_example: |            # Example of compliance
        code that follows the rule
      
      indicators:                # Heuristics for detection
        - "Large class (>500 lines)"
        - "Multiple responsibilities"
```

## Severity Levels

| Level | When to Use | PR Impact |
|-------|-------------|-----------|
| `critical` | Security vulnerabilities, will break production | Blocks merge |
| `high` | Significant issues, architectural problems | Should block |
| `medium` | Standard violations, coding standards | Review required |
| `low` | Style issues, minor improvements | Advisory |
| `info` | Suggestions, observations | Informational |

## Adding Company-Specific Rules

### Step 1: Identify Your Rules

Common sources for company rules:
- IT Security policies
- Architecture decision records (ADRs)
- Coding standards documentation
- Post-mortem action items
- Compliance requirements (SOC2, HIPAA, etc.)

### Step 2: Create or Update Rules

Example of adding a company-specific rule:

```yaml
# rules/common.yaml
rules:
  company_policy:
    # Existing rules...
    
    - id: CORP-SEC-001
      name: "PII Logging Prohibited"
      severity: critical
      description: |
        Personally Identifiable Information (PII) must never be logged.
        This includes: email addresses, phone numbers, SSNs, credit cards,
        and any data that can identify a specific individual.
        
        This rule is required for GDPR and CCPA compliance.
      patterns:
        - "log.*email"
        - "log.*phone"
        - "log.*ssn"
        - "logger\\..*\\(.*user\\.email"
      bad_example: |
        logger.info(f"User {user.email} logged in")
      good_example: |
        logger.info("User logged in", extra={"user_id": user.id})
```

### Step 3: Add Good/Bad Examples

Examples are crucial for LLM accuracy. Include:
- 2-3 bad examples showing common violation patterns
- 2-3 good examples showing correct approaches
- Edge cases if relevant

### Step 4: Test Your Rules

```bash
# Create a test diff with violations
cat > test_violation.diff << 'EOF'
diff --git a/test.py b/test.py
--- /dev/null
+++ b/test.py
@@ -0,0 +1,5 @@
+def login(user):
+    logger.info(f"User {user.email} logged in from {user.ip}")
+    return True
EOF

# Run analysis
python scripts/analyze_code.py \
    --diff test_violation.diff \
    --rules rules/common.yaml \
    --prompt prompts/system_base.md \
    --output test_results.json

# Check results
cat test_results.json | jq '.violations'
```

## Rule Categories

Organize rules into logical categories:

### Security (`security:`)
- Authentication/authorization
- Input validation
- Secrets management
- Injection vulnerabilities

### Quality (`quality:`)
- Code complexity
- Documentation
- Naming conventions
- Test coverage

### Architecture (`architecture:`)
- SOLID principles
- Layer boundaries
- Dependency management
- Design patterns

### Company Policy (`company_policy:`)
- Approved libraries
- Logging standards
- Error handling
- API design

## Language-Specific Rules

For language-specific rules, create a separate file:

```yaml
# rules/python.yaml
version: "1.0"

metadata:
  name: "Python Standards"
  applies_to: ["py"]

rules:
  type_safety:
    - id: PY-TYPE-001
      name: "Type Hints Required"
      severity: medium
      description: |
        All function parameters and return types must have type hints.
```

## Advanced Configuration

### Exceptions

You can configure exceptions for specific paths:

```yaml
# rules/common.yaml
exceptions:
  # Allow TODOs in test files
  allowed_todos_in:
    - "tests/"
    - "scripts/dev/"
  
  # Allow print statements in CLI tools
  allowed_print_in:
    - "cli/"
    - "scripts/"
  
  # Skip analysis for generated files
  skip_files:
    - "*_generated.py"
    - "*.pb.go"
```

### Strictness Levels

Rules can behave differently based on strictness:

```yaml
- id: DOC-001
  name: "Function Documentation"
  severity: medium
  strictness_behavior:
    low: skip          # Don't check
    normal: warn       # Report as low severity
    high: enforce      # Report as medium severity
```

### Rule Dependencies

Some rules may depend on others:

```yaml
- id: ARCH-005
  name: "Use Repository Pattern"
  depends_on:
    - ARCH-001  # Single Responsibility
    - ARCH-002  # Dependency Injection
```

## Migrating from Existing Standards

### From ESLint Rules

```yaml
# Convert ESLint's no-unused-vars
- id: JS-CLEAN-001
  name: "No Unused Variables"
  severity: low
  description: "Variables that are declared but never used should be removed."
  eslint_equivalent: "no-unused-vars"
```

### From SonarQube

```yaml
# Convert SonarQube's S1135 (Track TODOs)
- id: QUAL-001
  name: "No TODO Comments"
  severity: medium
  description: "TODO comments indicate incomplete work."
  sonar_equivalent: "S1135"
```

## Best Practices for Rule Writing

1. **Be Specific**: Vague rules lead to false positives
2. **Include Examples**: LLMs learn from examples
3. **Explain Why**: Help reviewers understand the importance
4. **Test Thoroughly**: Validate against real code
5. **Iterate**: Refine based on false positive/negative feedback
6. **Document Exceptions**: When rules don't apply

## Syncing with External Documentation

If your rules are documented elsewhere (Confluence, Notion, etc.), consider:

1. **Single Source of Truth**: Keep rules in code, reference docs for details
2. **Links**: Include links to detailed documentation
3. **Automated Sync**: Build a script to export rules to docs
4. **Version Control**: Track rule changes with git history

```yaml
- id: SEC-001
  name: "Secrets Management"
  documentation_url: "https://confluence.company.com/security/secrets"
```
