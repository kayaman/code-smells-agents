# 🚀 Quick Start Guide - PR Validation Agents PoC

This guide gets you from zero to working PoC in 15 minutes.

## Prerequisites

- Python 3.10+
- Databricks workspace with Model Serving
- A GitHub repository with Actions enabled

## Step 1: Databricks Setup (5 min)

### Option A: Use Existing Model Endpoint
If you already have a model serving endpoint (e.g., DBRX, Llama, or a fine-tuned model):

```bash
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="your-token-here"
export DATABRICKS_ENDPOINT="your-endpoint-name"
```

### Option B: Create a New Endpoint
```python
# In Databricks notebook or using the SDK
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Create a model serving endpoint using Foundation Model APIs
# (adjust based on your available models)
endpoint = w.serving_endpoints.create(
    name="code-review-v1",
    config={
        "served_models": [{
            "model_name": "databricks-dbrx-instruct",  # or your model
            "model_version": "1",
            "workload_size": "Small",
            "scale_to_zero_enabled": True
        }]
    }
)
```

## Step 2: Local Testing (5 min)

```bash
# Clone/copy this project
cd pr-validation-agents

# Install dependencies
pip install -r scripts/requirements.txt

# Test with sample bad code
python tests/test_local.py --sample --mock

# Test with real API (requires env vars set)
python tests/test_local.py --sample
```

### Expected output:
```
📋 Using rules: rules/common.yaml
📄 Analyzing: tests/sample_violations/bad_code.diff
⚡ Strictness: normal

🔍 Running analysis...
Analysis complete. Found 8 violation(s)

============================================================
📊 ANALYSIS RESULTS
============================================================

🚨 Violations Found: 8

1. 🚨 [CRITICAL] SEC-001
   📍 services/user_service.py:6
   📄 Hardcoded API key detected...

2. 🚨 [CRITICAL] SEC-002
   📍 services/user_service.py:13
   📄 SQL injection vulnerability via f-string...
...
```

## Step 3: GitHub Actions Setup (5 min)

### 1. Add Secrets to Repository

Go to: `Settings > Secrets and variables > Actions`

Add:
- `DATABRICKS_HOST` - Your workspace URL
- `DATABRICKS_TOKEN` - Your access token

Add Variables:
- `DATABRICKS_ENDPOINT` - Your model endpoint name

### 2. Copy Workflow Files

```bash
# From the project root
cp -r .github/workflows/* YOUR_REPO/.github/workflows/
cp -r rules/ YOUR_REPO/rules/
cp -r scripts/ YOUR_REPO/scripts/
cp -r prompts/ YOUR_REPO/prompts/
```

### 3. Commit and Push

```bash
cd YOUR_REPO
git add .
git commit -m "Add PR validation agents"
git push
```

### 4. Test with a PR

Create a branch with some code changes and open a PR. The workflow will:
1. Detect changed files
2. Identify programming languages
3. Run analysis with appropriate rules
4. Post a review comment

## Step 4: Customize Rules (Optional)

Edit the YAML files in `rules/` to match your company standards:

```yaml
# rules/common.yaml
rules:
  company_policy:
    - id: CORP-NEW-001
      name: "Your Custom Rule"
      severity: high
      description: |
        Description of what this rule checks for
      bad_example: "what not to do"
      good_example: "what to do instead"
```

## Minimal Permissions Required

For GitHub Enterprise environments with restricted permissions:

| Permission | Scope | Required For |
|------------|-------|--------------|
| `contents: read` | Repository | Read PR diff |
| `pull-requests: write` | Repository | Post comments |

These are minimal permissions that should be easy to approve.

## Troubleshooting

### "Failed to connect to Databricks"
- Verify `DATABRICKS_HOST` includes `https://`
- Check token has `Can Manage` or `Can Use` permission on endpoint
- Ensure endpoint is running (not scaled to zero)

### "No analysis results"
- Check if files match supported extensions
- Verify diff is not empty
- Check workflow logs for errors

### "Workflow not triggering"
- Ensure workflow file is in `.github/workflows/`
- Check PR is targeting correct branch
- Verify Actions are enabled in repository settings

## Next Steps

1. **Add more language rules**: Copy `rules/python.yaml` as a template
2. **Customize prompts**: Edit `prompts/system_base.md` for your style
3. **Add contractor detection**: Modify the `is_contractor` logic in workflow
4. **Enable strict mode**: Add team members to contractor patterns for testing

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Enterprise                        │
│  ┌───────────┐     ┌────────────┐     ┌────────────────┐    │
│  │ PR Event  │────▶│  Actions   │────▶│ Review Comment │    │
│  └───────────┘     └─────┬──────┘     └────────────────┘    │
│                          │                                  │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Analysis   │
                    │   Script    │
                    └─────┬───────┘
                          │
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
      ┌─────────┐   ┌─────────┐   ┌─────────┐
      │ Common  │   │ Python  │   │   JS    │
      │  Rules  │   │  Rules  │   │  Rules  │
      └─────────┘   └─────────┘   └─────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │   Databricks    │
                 │ Model Serving   │
                 └─────────────────┘
```

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review workflow logs in GitHub Actions
3. Test locally with `--mock` flag to isolate issues
