# SAST / Security Stage Redesign — Design

**Date:** 2026-07-09
**Status:** Approved, moving to implementation plan

## Context

Prior phase (`docs/superpowers/specs/2026-07-06-trivy-image-iac-scan-design.md`) made
all security jobs hard-blocking with no suppression. That policy is explicitly reversed
here: security scanning becomes visibility-first, not gate-first. This is a deliberate
user decision, not scope creep — see rationale below.

Also folds in two bugs found this session:
1. `push-vuln-metrics` skipped whenever `image-scan` failed (missing `when: always`) — fixed already.
2. SonarQube CE has no branch analysis — every branch overwrote the same project view.
   Fixed already via `-Dsonar.projectKey=eamsagemcom-$CI_COMMIT_REF_SLUG`.

And a third, found while redesigning: branch `rules:` are hardcoded to an exact list
(`Phase_1|clean_Phase_1|main|Phase_2`), repeated in every job. Any future `Phase_3`,
`Phase_4`, etc. branch gets **zero pipeline coverage** until someone manually edits
this file. Generalizing to a pattern fixes this permanently.

## Goals

1. Rich, human-readable terminal output for every security scanner — CVE IDs, packages,
   installed/fixed versions, file paths, severity breakdown, summary — no artifact
   download required to understand a finding.
2. No security job blocks the pipeline on findings (CRITICAL/HIGH/MEDIUM/LOW). Only
   genuine tool/build failures block.
3. Full report set per scanner: GitLab-consumable SARIF, raw JSON, HTML where practical.
4. Clear separation of security categories: Secret Detection, SCA (dependency scanning),
   SAST, Container Scanning, IaC Scanning, License Compliance.
5. No duplicate scans — generate all report formats from a single scan invocation.
6. Branch coverage that doesn't need manual maintenance for future `Phase_N` branches.

## Non-Goals

- Not restructuring the overall stage graph (secret-scan → sca-deps → sast → build →
  image-scan → lint → gate stays the same shape, one stage renamed).
- Not adding GitLab Ultimate-tier features (native License Compliance / Dependency
  Scanning UI integration) — self-hosted GitLab CE assumed, per [[free-tools-only]].
- Not touching `docker-compose.monitoring.yml` / Prometheus / Grafana stack (separate,
  already built).

## Decisions Made

### D1 — Non-blocking mechanism: `allow_failure: true`

Chosen over forcing every tool to exit 0 internally. Reasoning: tool exit codes stay
truthful (nonzero = found something), so GitLab's job list still shows an orange
warning icon when a scan finds something — a real, at-a-glance signal — while the
pipeline itself never halts. A silently-forced exit 0 everywhere would make a genuine
tool crash (bad auth token, network failure, corrupt scan target) look identical to a
clean scan, which is worse for the "visibility" goal this redesign is chasing.

`needs:`-chained downstream jobs still run automatically when an upstream job is
`allow_failure: true` and fails — no extra `when: always` needed for that reason alone
(kept on `push-vuln-metrics` regardless, since it was already there and is harmless).

**Exception:** `build-images` stays hard-blocking (`allow_failure: false`). A failed
`docker build` is not a "finding" to display — it means the pipeline literally cannot
produce an artifact to scan next. Blocking here is correct.

### D2 — License Compliance: add it

New `license-scan` job in the `sca-deps` stage. `pip-licenses` for backend deps,
`license-checker` (npm) for frontend deps. Non-blocking, informational table in
terminal, JSON artifact. Fills a real gap (nothing currently checks license types).

### D3 — Branch rule generalization

Replace the hardcoded exact-branch-name regex, repeated in every job, with a YAML
anchor matching the naming convention (`main`, `clean_Phase_<n>`, `Phase_<n>`) plus MR
pipelines:

```yaml
.branch-rules: &branch-rules
  - if: $CI_COMMIT_BRANCH =~ /^(main|clean_Phase_\d+|Phase_\d+)$/
  - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

Defined once, referenced everywhere via `rules: *branch-rules`. Any future `Phase_3`,
`Phase_4`... branch is covered automatically — no yml edit needed. If the naming
convention changes later, this is the one place to update.

### D4 — SonarQube stays the sole SAST tool

Confirmed in a prior turn this session (Semgrep removed entirely, `.semgrep/` and
`.semgrepignore` deleted). `sonar.qualitygate.wait=true` stays — it's what produces
the pass/fail line in the terminal for free. Job itself becomes `allow_failure: true`
so a failing quality gate no longer blocks the pipeline, but still shows the warning
icon and prints the gate status.

## Architecture

### Stage/job table (final)

| Stage | Job | Tool | Blocking? | New in this redesign |
|---|---|---|---|---|
| `secret-scan` | `scan-secrets` | gitleaks | `allow_failure: true` | JSON+SARIF reports, terminal summary |
| `sca-deps` | `audit-backend` | pip-audit | `allow_failure: true` | JSON report, terminal summary |
| `sca-deps` | `audit-frontend` | pnpm audit | `allow_failure: true` | dedupe (was scanning twice), terminal summary |
| `sca-deps` | `license-scan` **(new)** | pip-licenses + license-checker | `allow_failure: true` | new job entirely |
| `sast` (renamed from `sonarqube`) | `sonarqube-scan` | SonarQube CE | `allow_failure: true` | issue-detail terminal fetch via Sonar Web API |
| `build` | `build-images` | docker build | **blocking (unchanged)** | — |
| `build` | `iac-scan` | Trivy config | `allow_failure: true` | terminal table + HTML report via `trivy convert` (no re-scan) |
| `image-scan` | `image-scan` | Trivy image | `allow_failure: true` | terminal table + HTML report via `trivy convert` (no re-scan) |
| `image-scan` | `push-vuln-metrics` | custom script | `allow_failure: true` (already was) | unchanged |
| `lint` | `lint-backend`, `lint-frontend` | ruff, eslint | `allow_failure: true` (already was) | unchanged |
| `gate` | `quality-gate` | — | blocking (unchanged) | wording updated: confirms jobs *ran*, not that they were clean |

### Shared reporting scripts (new, `monitoring/scripts/`)

**`security_report.py`** — universal terminal formatter. Dispatches on tool name:
`gitleaks`, `pip-audit`, `pnpm-audit`, `trivy`. Each branch parses that tool's native
JSON schema (no new intermediate format invented) and prints a consistent layout:

```
================================================================
  <TOOL> — <label>
================================================================
Severity Breakdown:
  CRITICAL: N   HIGH: N   MEDIUM: N   LOW: N   UNKNOWN: N
  TOTAL: N

Findings:
  <CVE/rule id>  |  <package/file>  |  <installed> -> <fixed>  |  <severity>
  ...

Reports: <json path> / <sarif path> / <html path>
================================================================
```

ANSI colors (red/orange/yellow/blue) keyed to severity, since GitLab job logs render
ANSI. Always exits 0 — display-only, never a pipeline gate.

**`sonar_report.py`** — separate script (different data source: Sonar Web API, not a
local JSON file). Called after `sonar-scanner` completes; queries
`api/issues/search?componentKeys=<projectKey>` with the CI token, prints rule, severity,
type (BUG/VULNERABILITY/SECURITY_HOTSPOT), file:line, message. Saves raw API response
as `sonar-issues.json` artifact. Always exits 0.

Both scripts live alongside the existing `trivy_push_metrics.py` (same directory,
same reuse-existing-architecture principle — no new top-level `scripts/` location).

### Avoiding duplicate scans

- Trivy: one scan → JSON. `trivy convert` (no re-scan, reads the JSON) produces
  SARIF and HTML from that same JSON. Already the pattern for SARIF; extending it to
  HTML via `trivy convert --format template --template "@contrib/html.tpl"`.
- pnpm audit: currently runs twice (`--json > file || true`, then a second
  `--audit-level=high` call purely to get a blocking exit code). Now that blocking is
  gone, the second call is deleted — one call, one JSON, one terminal summary.
- pip-audit / gitleaks: already single-invocation, just adding `-f json -o <file>` /
  `--report-format json --report-path <file>` flags to capture output instead of
  relying on stdout scraping.

## Testing / Verification

No unit tests apply to CI yml — verification is: push a commit to `Phase_2`, confirm
in the GitLab job log:
1. Every security job shows a warning icon (not red X) even with findings present.
2. Terminal output shows severity breakdown + CVE/rule table for each scanner.
3. Pipeline reaches `quality-gate` and passes even with CRITICAL findings present.
4. `license-scan` job runs and prints a license table.
5. Push to a hypothetical `Phase_3` branch name (or confirm via `rules:` regex test)
   triggers the full pipeline without any yml edit.

## Open Items For Implementation Plan

- Exact CLI flags for `pip-licenses` / `license-checker` output format.
- Confirm `trivy convert --format template --template "@contrib/html.tpl"` works with
  the bundled Trivy image (template file must exist at that path inside
  `aquasec/trivy:latest`) — plan should include a fallback (skip HTML, keep SARIF+JSON)
  if not.
- Confirm gitleaks CLI supports `--report-format json --report-path` alongside the
  existing `--verbose --redact --log-opts` flags without conflict.
