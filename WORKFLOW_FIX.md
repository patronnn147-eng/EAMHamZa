# GitHub Actions Workflow Fix: Source Code Security

## Failed Job
- **Workflow**: Source Code Security
- **Job**: SAST Auto (Semgrep) 
- **Job ID**: 85009594986
- **Run URL**: https://github.com/patronnn147-eng/EAMHamZa/actions/runs/28663493396/job/85009594986
- **Timestamp**: 2026-07-03T13:26:04 - 2026-07-03T13:27:21

## Error Logs

```
2026-07-03T13:26:51.8343396Z ##[group]Uploading code scanning results
2026-07-03T13:26:51.8809576Z Uploading results
2026-07-03T13:27:06.4610049Z ##[warning]Resource not accessible by integration - https://docs.github.com/rest
2026-07-03T13:27:06.4614646Z ##[error]Resource not accessible by integration - https://docs.github.com/rest
2026-07-03T13:27:21.0220016Z ##[warning]This run of the CodeQL Action does not have permission to access the CodeQL Action API endpoints. This could be because the Action is running on a pull request from a fork. If not, please ensure the workflow has at least the 'security-events: read' permission.
```

## Problem Analysis

The job is failing due to **permission issues when uploading SARIF results to GitHub Code Scanning**. The error messages indicate:

```
##[warning]Resource not accessible by integration - https://docs.github.com/rest
##[error]Resource not accessible by integration - https://docs.github.com/rest
##[warning]This run of the CodeQL Action does not have permission to access the CodeQL Action API endpoints.
```

This typically occurs when:
1. The workflow is running on a pull request from a fork
2. The workflow lacks the required `security-events: write` permission

## Solution

Add the required permissions to your workflow. Update your `.github/workflows/source-security.yml` file to include:

```yaml
name: Source Code Security

on:
  push:
    branches:
      - Phase_1
      - clean_Phase_1
      - main
  pull_request:
    branches:
      - Phase_1
      - clean_Phase_1
      - main
  workflow_dispatch:

permissions:
  security-events: write  # Add this line
  contents: read          # Add this line (good practice)

jobs:
  # ... rest of your jobs ...
```

The `security-events: write` permission is required for the `github/codeql-action/upload-sarif` action to successfully upload security scan results to GitHub Code Scanning.

### Alternative: Handle Fork Pull Requests

If this workflow is running on pull requests from forks, GitHub has security restrictions that prevent forked PRs from writing to the Code Scanning API. In that case, you may need to use a conditional check in each SARIF upload step:

```yaml
- name: Upload SARIF
  if: always() && github.event_name != 'pull_request'
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: sast-auto.sarif
    category: sast-auto
```

Apply this conditional to all three SARIF upload steps:
- `sast-auto` job (line 85-90)
- `sast-explicit` job (line 107-112)
- `sast-custom` job (line 129-134)

This prevents the upload from failing on forked PRs while still allowing uploads on pushes to your main branches.

## Implementation Steps

1. Open `.github/workflows/source-security.yml`
2. Add the `permissions` block after the `on:` section (before `jobs:`)
3. For fork PR handling, update the `if:` condition in all three SARIF upload steps
4. Commit and push the changes
5. Re-run the workflow to verify the fix
