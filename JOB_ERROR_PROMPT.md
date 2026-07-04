# Job Error Logs & Fix Instructions

## Error Summary
The job failed with exit code 1 from a code formatting check using Black (Python code formatter).

## Job Details
- **Job ID**: 85009594931
- **Run ID**: 28663493396
- **Workflow**: Source Code Security (`.github/workflows/source-security.yml`)
- **Commit**: cbec106d5ab65150753f6de446d341102b1b17b3
- **Timestamp**: 2026-07-03T13:25:59

## Full Job Logs
```
2026-07-03T13:25:59.8521680Z Would reformat: app/backend/main.py
2026-07-03T13:25:59.8522035Z Would reformat: app/backend/modules/chetop/routes/dashboard.py
2026-07-03T13:25:59.8522468Z Would reformat: app/backend/modules/ml/services/quick_action.py
2026-07-03T13:25:59.8522892Z 7 files would be reformatted, 276 files already formatted
2026-07-03T13:25:59.8544588Z ##[error]Process completed with exit code 1.
2026-07-03T13:25:59.8701351Z Node 20 is being deprecated. This workflow is running with Node 24 by default. If you need to temporarily use Node 20, you can set the ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true environment variable. For more information see: https://github.blog/changelog/2025-09-19-de
2026-07-03T13:25:59.8702667Z Post job cleanup.
```

## Problem
Black found that **7 Python files need reformatting**:
- `app/backend/main.py`
- `app/backend/modules/chetop/routes/dashboard.py`
- `app/backend/modules/ml/services/quick_action.py`
- 4 other files

The workflow check failed because the code doesn't match the expected Black formatting standard.

## Solution
Format the Python files using Black:

```bash
black app/backend/main.py app/backend/modules/chetop/routes/dashboard.py app/backend/modules/ml/services/quick_action.py
```

Or format all Python files:

```bash
black .
```

Then commit and push:

```bash
git add .
git commit -m "Format code with black"
git push
```

The workflow should pass on the next run once all files are properly formatted.
