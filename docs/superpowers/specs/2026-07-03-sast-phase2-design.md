# Phase 2a: SAST (Semgrep) — Design Spec

**Date:** 2026-07-03
**Status:** Approved
**Branch:** clean_Phase_1
**Depends on:** Phase 1 — `docs/superpowers/specs/2026-06-20-source-code-security-design.md`

---

## Problem

Phase 1 covers secrets (gitleaks) and third-party dependency CVEs (pip-audit, pnpm audit). Neither checks code written in-house for security bugs (SQL injection, XSS, command injection, insecure config). Additionally, Phase 1's lint/audit jobs only cover `app/backend` and `app/frontend` — `app/ml-microservice` and `app/rag-service` have zero automated checks of any kind.

## Goal

Add SAST (Static Application Security Testing) via Semgrep as a new blocking CI stage, covering all 4 services, closing both gaps.

---

## Pipeline Placement

New stage inserted into both `.gitlab-ci.yml` and `.github/workflows/source-security.yml`:

```
secret-scan → sca-deps → sast → lint → gate
```

`quality-gate` adds `sast-auto`, `sast-explicit`, `sast-custom` as blocking `needs`.

Branch rules identical to existing jobs: `clean_Phase_1`, `Phase_1`, `main`, plus MR/PR events.

## Jobs

Three separate jobs, each scanning all 4 service directories (`app/backend`, `app/frontend`, `app/ml-microservice`, `app/rag-service`):

| Job | Command | Config source |
|---|---|---|
| `sast-auto` | `semgrep scan --config auto app/backend app/frontend app/ml-microservice app/rag-service` | Semgrep registry, auto-resolved (calls semgrep.dev to pick rulesets) |
| `sast-explicit` | `semgrep scan --config p/owasp-top-ten --config p/python --config p/typescript app/backend app/frontend app/ml-microservice app/rag-service` | Pinned Semgrep Registry rulesets, no external resolution |
| `sast-custom` | `semgrep scan --config .semgrep/custom.yml app/backend app/frontend app/ml-microservice app/rag-service` | Project-owned rule file, committed to repo |

Each job:
- `--severity WARNING --severity ERROR` findings → exit code 1 (blocks). `INFO` findings do not block.
- `--sarif -o <job>.sarif` output as CI artifact (all 3 pipelines/platforms).
- GitHub Actions additionally runs `github/codeql-action/upload-sarif@v3` per job, uploading to the repo's Security → Code scanning tab, so findings persist across runs instead of living only in job logs.
- Timeout: 10 minutes (matches sca-deps jobs).
- `allow_failure: false` (GitLab) / no `continue-on-error` (GitHub) — blocking, same tier as secret-scan/sca-deps.

## Custom Ruleset — `.semgrep/custom.yml`

Starter rules (v1, expected to grow):

1. `sqlalchemy-raw-sql-interpolation` — flags `text()` calls built with f-strings, `.format()`, or `%` interpolation instead of bound parameters.
2. `fastapi-cors-wildcard-with-credentials` — flags `CORSMiddleware(allow_origins=["*"], allow_credentials=True)`.
3. `hardcoded-secret-default` — flags `os.getenv("SECRET_KEY"|"JWT_SECRET", <string literal>)` (non-empty fallback default in source).
4. `react-dangerous-html-unsanitized` — flags `dangerouslySetInnerHTML` where the value isn't passed through a known sanitizer call (e.g. `DOMPurify.sanitize`) in the same expression.
5. `subprocess-dynamic-input` — flags `subprocess.*`/`os.system` calls where the command argument is not a fixed string literal.

Each rule: `severity: WARNING`, includes a `message` explaining the risk and the fix, in Semgrep YAML rule format.

## Suppression

- **Inline:** `# nosemgrep: <rule-id>` (Python) / `// nosemgrep: <rule-id>` (TS/JS), with a trailing comment explaining why. Reviewed like any other code change — visible in diffs.
- **Path-level:** `.semgrepignore` at repo root, pre-seeded with:
  ```
  **/__pycache__/
  **/node_modules/
  **/*.min.js
  **/migrations/
  **/.next/
  ```

## Error Handling

| Failure | Behavior |
|---|---|
| WARNING/ERROR finding, any of the 3 jobs | Job fails, gate blocks merge, SARIF shows exact file:line + rule + message |
| INFO finding | Logged in job output, does not fail |
| Semgrep registry unreachable (`sast-auto` only) | Job fails (network dependency is accepted for this job only — `sast-explicit`/`sast-custom` have no such dependency) |
| First run against existing (unaudited) code | Expected to surface real findings — one-time triage pass required (fix or suppress with reason) before pipeline goes green |

## Out of Scope (this spec)

- Docker image scanning (Trivy/Grype) — next track, separate spec.
- DAST, IaC scanning of docker-compose.yml — later phases per Phase 1 spec's roadmap.
- Auto-remediation / PR auto-fix suggestions.

## Success Criteria

- [ ] `.semgrep/custom.yml` created with the 5 starter rules, validated via `semgrep --validate`
- [ ] `.semgrepignore` created with starter exclusions
- [ ] `sast-auto`, `sast-explicit`, `sast-custom` jobs added to `.gitlab-ci.yml`
- [ ] Same 3 jobs added to `.github/workflows/source-security.yml`, with SARIF upload to GitHub code scanning
- [ ] `quality-gate` in both pipelines updated to depend on all 3 new jobs
- [ ] First run triaged: every WARNING/ERROR finding either fixed or suppressed with a documented reason
- [ ] Pipeline green on `clean_Phase_1` after triage

---

*Spec written: 2026-07-03 | Approved: user | Companion doc: `docs/sast-phase2-plain-english.md` (non-technical audience)*

---

## Addendum: Semgrep AppSec Platform reporting (added 2026-07-03, post-approval)

User requested a 4th SAST job, `sast-appsec-platform`, using `semgrep ci` to report findings to the Semgrep AppSec Platform dashboard. This is a deliberate exception to this spec's original "no Semgrep account/API token" constraint — the user was asked and confirmed they want this despite requiring a `SEMGREP_APP_TOKEN` secret (GitHub Actions secret + GitLab CI/CD variable), which they do not have set up yet.

Decisions:
- **Blocking, same tier as `sast-auto`/`sast-explicit`/`sast-custom`** (not report-only) — user's explicit choice.
- Sequenced as Task 10, after Task 9's push/triage of the original 3-job scope, not parallel with Tasks 7-8 (same CI files, would conflict) and not blocking the original spec's success criteria (Task 9 closes those independently).
- Account/token creation is a manual user step (`docs/superpowers/plans/2026-07-03-sast-phase2.md`, Task 10, Step 1) — no tool available can create a Semgrep account or generate the token.

Full implementation details: `docs/superpowers/plans/2026-07-03-sast-phase2.md`, Task 10.
