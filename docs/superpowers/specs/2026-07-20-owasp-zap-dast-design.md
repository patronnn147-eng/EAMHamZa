# OWASP ZAP — Dynamic Application Security Testing (DAST) — Design Spec

**Date:** 2026-07-20
**Status:** Approved
**Branch:** Phase_2
**Depends on:** Phase 1 — `docs/superpowers/specs/2026-06-20-source-code-security-design.md`, Phase 2b — `docs/superpowers/specs/2026-07-06-trivy-image-iac-scan-design.md`, `2026-07-09-sast-stage-redesign-design.md`

---

## Problem

Every scanner in the current pipeline (secret-scan, SCA, SAST/SonarQube, Trivy image/IaC) inspects source code, dependency manifests, or built image layers — all *static* analysis. None of them exercise the running application. Runtime-only issues — broken access control between roles, injection points only reachable through live request/response flow, missing security headers, session handling bugs — are invisible to every tool currently in the pipeline.

OWASP ZAP fills that gap: a dynamic scanner that runs actual attack traffic against the live stack.

The user is a first-time ZAP user. This spec covers both the automated CI integration and a manual learning path, using the same underlying config so neither path is throwaway work.

## Goal

Add OWASP ZAP as a new automated scanner, run two ways from one shared config:

1. **Manual (ZAP Desktop, GUI)** — installed locally, used to learn the tool and watch a scan execute live against the already-running `make up` stack.
2. **CI (headless, Docker)** — new `dast` stage in `.gitlab-ci.yml`, same automation plan, no GUI, results as pipeline artifacts.

Single source of truth: a ZAP **Automation Framework** YAML plan (`security/zap/zap-automation.yaml`), not the legacy `zap-baseline.py`/`zap-full-scan.py` scripts — both GUI and headless runners can execute the same plan file, so there's no drift between what the user learns by hand and what CI runs.

## Scope

**Scan depth:** Full active scan (spider + active attack, not passive-only baseline) — explicit user choice, understanding this sends real attack payloads (SQLi/XSS attempts, and it will call write/delete endpoints for real).

**Targets scanned (4, all resolved via Docker Compose network `asset_management_network`, hardcoded — not parameterized by any CI variable):**

| Service | Internal URL | Auth |
|---|---|---|
| `backend` | `http://backend:8000` | JWT bearer, multi-role (see below) |
| `ml-service` | `http://ml-service:8000` | none (no auth in code — internal-only service) |
| `rag-service` | `http://rag-service:8003` | none (same — internal-only service) |
| `frontend` | `http://frontend:80` | none (public UI, spidered anonymously) |

**Explicitly excluded:** `postgres`, `rabbitmq`, `minio`, `pgadmin`. These are third-party infra/admin panels, not application code this team wrote — out of scope for an app-focused DAST pass. (Revisit later if desired; not in this pass.)

**Multi-role authentication (backend only):**

ZAP Automation Framework context defines 4 users, all against the real seeded dev DB (confirmed via direct query, not assumed):

| Role | Email |
|---|---|
| ADMIN | `hamza.mbarki2002@gmail.com` |
| CHEFTECH | `hamza.mbarki@esprit.tn` |
| CHETOP | `mbarkih92@gmail.com` |
| TECHNICIEN | `hamedikilani44@gmail.com` |

All 4 share one password. ZAP logs in as each via `POST /login` (`{email, mot_de_passe}` → `access_token`), then runs the full active scan once per user — an `Authorization: Bearer <token>` HTTP Sender script attaches the right token per scan pass.

This buys broken-access-control detection for free: if a TECHNICIEN session can reach an ADMIN-only route (procurement draft approval, RAG doc delete) that should 403 and doesn't, the per-role scan surfaces it as a real finding — not just injection-class bugs.

**Credential handling:** the shared password is never written into any committed file (not the YAML, not this spec). It's injected at runtime:
- Manual runs: local `.env` (already gitignored)
- CI runs: GitLab CI/CD masked variable `ZAP_LOGIN_PASSWORD`

The YAML references `${ZAP_LOGIN_PASSWORD}` only.

**Scan policy:** ZAP's built-in **Default Policy** — not the aggressive "Attack" policy. Default Policy already excludes the disruptive DoS-class rule set, which matters for a scan that's going to run repeatedly in CI against a shared dev stack.

## Safety Guard

Full active scan sends real write/delete traffic. Two structural safeguards, both fail-closed:

1. **Non-parameterized, internal-only targets.** The automation YAML hardcodes Docker-internal service DNS names (`backend`, `ml-service`, `rag-service`, `frontend`). No CI variable can redirect the scan to an external or production URL — there's no target variable to override in the first place.
2. **Pre-flight seed check.** Before the ZAP container starts, a query confirms the 4 known seeded test emails above exist in the target DB. Missing any of them aborts the job before any attack traffic is sent. This is a positive check ("this is the known dev/test dataset") rather than trying to infer "not production" from a flag the codebase doesn't have (there is currently no environment/staging/prod distinction anywhere in `settings.py` — this project has one deployment target: local Docker dev).

Both checks are pre-flight steps in the `dast` job, ahead of the ZAP container invocation.

## Pipeline Placement

Current pipeline: `secret-scan → sca-deps → sast → build → image-scan → lint → gate`

New pipeline:

```
secret-scan → sca-deps → sast → build → image-scan → dast → lint → gate
```

`dast` runs last among the scanner stages, consistent with DAST needing a fully running stack (only possible after `build`), and matching the user's framing of it as "the last automated scanner."

**Execution model** — follows the existing `sonarqube-scan` convention rather than introducing a new one: that job already assumes a pre-existing local service (`host.docker.internal:9090`) instead of spinning one up fresh in CI, because the runner is self-hosted and doubles as the dev machine. `dast` does the same:

- Assumes `make up` is already running on the runner host.
- Health-checks all 4 targets with a short retry loop; on failure, fails with a clear "run `make up` first" message.
- Runs the pre-flight seed check (above).
- Runs `zaproxy/zap-stable` via `docker run` on `asset_management_network`, pointed at the mounted automation YAML.
- `allow_failure: true` — same as every scanner except `build-images`/`quality-gate`. Visibility, not gating.

Rejected alternative: job spins up its own disposable `docker compose up` stack. More self-contained in theory, but this project's ML/RAG containers are heavy (TensorFlow model loading) — meaningfully slower per pipeline run for no benefit when a live stack already exists on the same host, and it breaks from the `sonarqube-scan` convention already established in this pipeline.

## Reports & Gate Integration

- HTML + JSON reports via ZAP's built-in `report` job type in the automation plan, saved as GitLab CI artifacts (same pattern as `image-scan`'s SARIF/JSON output).
- No alert-suppression/false-positive filtering configured upfront — start clean, tune based on real first-run output. Matches the project's established pattern (`sonar_report.py`'s custom parsing was written after seeing real SonarQube output, not speculatively).
- `quality-gate` job: `dast` added to its `needs:` list as `optional: true` (same as `lint-backend`/`lint-frontend`), plus one new summary line: `DAST (OWASP ZAP) -- RAN (findings, if any, shown above; non-blocking)`. Purely additive — doesn't change gate pass/fail logic.

## Manual Learning Walkthrough (scope for implementation)

Delivered as a step-by-step guide once implementation starts:

1. Install ZAP Desktop on Windows (official installer).
2. Minimal GUI tour — Sites tree, Alerts tab, Automation tab only; skip the rest of ZAP's surface area.
3. Load `zap-automation.yaml` into ZAP Desktop, run it against the already-running `make up` stack.
4. Watch live: spider crawl, alerts populating, active attack progress per role.
5. Walk through one real finding together so "vulnerability report" isn't abstract.
6. Repeat the same plan headless via `docker run` locally, to see the manual and CI paths are literally the same config, different runner.

## Risks

- **First run will likely be noisy.** Full active scan across 4 services × 4 roles will surface a mix of real findings and false positives (e.g. informational disclosures on non-sensitive endpoints). No suppression is pre-configured (see Reports section) — expected, triaged after first real run, not designed away in advance.
- **Scan duration.** Multi-role full active scan against 4 services is meaningfully slower than a passive baseline scan (likely 15–40+ minutes depending on endpoint count). Acceptable per explicit user choice; revisit if pipeline time becomes a problem.
- **Shared dev DB mutation.** Write/delete payloads will alter data in the shared local dev database (new fake work orders, possibly deleted RAG docs, etc.) every run. This is accepted as a consequence of testing against real seeded accounts rather than provisioning an isolated ephemeral scan-only dataset — cheaper to build now, revisit if it causes friction with other dev work sharing the same DB.
