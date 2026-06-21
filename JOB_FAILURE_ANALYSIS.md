# Job Failure Analysis: audit-frontend

**Workflow:** Source Code Security  
**Job ID:** 82564095361  
**Status:** ❌ Failed  
**Date:** 2026-06-21T10:56:43Z  
**Workflow File:** `.github/workflows/source-security.yml`

---

## Root Cause

The **audit-frontend** job failed because `pnpm audit` detected **60 vulnerabilities** in the frontend dependencies:
- **2 low** severity
- **29 moderate** severity
- **29 high** severity

The workflow is configured to fail when vulnerabilities at or above the "high" level are detected (line 66 in `source-security.yml`).

---

## Job Output

```
2026-06-21T10:56:37.0657426Z + react 19.2.3
2026-06-21T10:56:37.0657818Z + react-day-picker 9.13.0
2026-06-21T10:56:37.0658234Z + react-dom 19.2.3
2026-06-21T10:56:37.0658621Z + react-dropzone 14.3.8
2026-06-21T10:56:37.0659065Z + react-error-boundary 4.1.2
2026-06-21T10:56:37.0659515Z + react-hook-form 7.70.0
2026-06-21T10:56:37.0660003Z + react-resizable-panels 2.1.9

--- ERROR ---
2026-06-21T10:56:43.2809537Z │ More info           │ https://github.com/advisories/GHSA-fx2h-pf6j-xcff      │
2026-06-21T10:56:43.2810154Z └─────────────────────┴────────────────────────────────────────────────────────┘
2026-06-21T10:56:43.2810510Z 60 vulnerabilities found
2026-06-21T10:56:43.2810818Z Severity: 2 low | 29 moderate | 29 high
2026-06-21T10:56:43.2822721Z ##[error]Process completed with exit code 1.
```

---

## Workflow Configuration (Relevant Section)

```yaml
audit-frontend:
  name: SCA Frontend (pnpm audit)
  runs-on: ubuntu-latest
  needs: scan-secrets
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: "22"
    - uses: pnpm/action-setup@v4
      with:
        version: latest
    - name: Install dependencies
      working-directory: app/frontend
      run: pnpm install --frozen-lockfile
    - name: Audit frontend dependencies
      working-directory: app/frontend
      run: pnpm audit --audit-level=high  # ← Fails on HIGH severity vulnerabilities
```

---

## Recommended Solutions

### Option 1: Update Dependencies (Recommended) ✅

The best approach is to update your frontend dependencies to patch the vulnerabilities:

```bash
cd app/frontend
pnpm update
pnpm audit
```

Then commit and push the updated `pnpm-lock.yaml` file to trigger the workflow again.

---

### Option 2: Lower Audit Threshold (Temporary)

If you need a quick fix while addressing vulnerabilities, modify `.github/workflows/source-security.yml` (line 66):

```yaml
- name: Audit frontend dependencies
  working-directory: app/frontend
  run: pnpm audit --audit-level=moderate
```

⚠️ **Note:** This is a temporary workaround and not recommended for production environments.

---

### Option 3: Allow Specific Vulnerabilities

Create a `.pnpmfile.cjs` in `app/frontend` to allow specific CVEs, but this should only be a temporary measure while you work on updates.

---

## Additional Issues

### Git Submodule Warning

There's a cleanup warning related to a missing git submodule:

```
fatal: No url found for submodule path 'claude-code' in .gitmodules
##[warning]The process '/usr/bin/git' failed with exit code 128
```

This doesn't cause the job failure but indicates that the `claude-code` submodule in `.gitmodules` is either:
- No longer available
- Has an invalid URL
- Is no longer needed

**Action:** Review `.gitmodules` and either update/remove the `claude-code` entry.

---

## Next Steps

1. Run `pnpm update` locally in the `app/frontend` directory
2. Review the changes to `pnpm-lock.yaml`
3. Commit and push the changes
4. The workflow should pass on the next run
5. (Optional) Remove or fix the `claude-code` submodule reference

---

**Workflow URL:** https://github.com/hamzAmbarki2/EAMSagemCom/actions/runs/27902089373/job/82564095361
