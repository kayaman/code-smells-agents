# PR Validation Agents - PoC

A GitHub Actions-based system for validating pull requests against company coding standards using LLM agents powered by Databricks Model Serving.

## 🎯 Purpose

Catch company rule violations in code delivered by third-party contractors before merge, using specialized AI agents that understand both industry best practices and your specific company rules.

## 🏗️ Architecture

```
PR Event → Language Detection → Rule Loading → LLM Analysis → PR Review Comment
                                    ↓
                          ┌─────────────────┐
                          │  Rules Repo     │
                          │  - Common       │
                          │  - Python       │
                          │  - Java         │
                          │  - JavaScript   │
                          │  - Infrastructure│
                          └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

1. **Databricks Model Serving Endpoint** configured
2. **GitHub Actions** enabled on your repository
3. **Minimal permissions**: `pull-requests: write`, `contents: read`

### Setup

1. **Copy workflow files** to your repository:
   ```bash
   cp -r .github/workflows/ YOUR_REPO/.github/workflows/
   ```

2. **Copy rules directory**:
   ```bash
   cp -r rules/ YOUR_REPO/rules/
   ```

3. **Set repository secrets**:
   - `DATABRICKS_HOST`: Your Databricks workspace URL
   - `DATABRICKS_TOKEN`: Service principal or PAT token
   - `DATABRICKS_ENDPOINT`: Model serving endpoint name

4. **Customize rules** in `rules/` directory for your company

### Testing Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run against a local diff
python scripts/analyze_code.py --diff sample.diff --rules rules/
```

## 📁 Structure

```
├── .github/
│   └── workflows/
│       └── pr-validation.yml      # Main workflow
├── rules/
│   ├── common.yaml                # Universal rules
│   ├── python.yaml                # Python-specific
│   ├── java.yaml                  # Java-specific
│   ├── javascript.yaml            # JS/TS-specific
│   └── infrastructure.yaml        # IaC rules
├── scripts/
│   ├── analyze_code.py            # Main analysis script
│   ├── detect_language.py         # Language detection
│   ├── databricks_client.py       # Databricks API client
│   └── format_review.py           # Output formatting
├── prompts/
│   ├── system_base.md             # Base system prompt
│   └── language_specific/
│       ├── python.md
│       ├── java.md
│       └── javascript.md
└── tests/
    └── sample_violations/         # Test cases
```

## 🔧 Configuration

See `rules/README.md` for detailed rule configuration.

## 📊 Supported Languages

- Python
- Java
- JavaScript/TypeScript
- Go
- Terraform/HCL
- Kubernetes YAML
- Shell scripts

## 🔐 Security

- No code is stored or logged
- Only diffs are sent to the model
- Secrets managed via GitHub encrypted secrets
- Model endpoint secured via Databricks access controls
