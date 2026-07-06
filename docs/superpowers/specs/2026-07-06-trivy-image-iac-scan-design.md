# Phase 2b (Track 1): Container Image + IaC Scanning (Trivy) — Design Spec

**Date:** 2026-07-06
**Status:** Approved
**Branch:** clean_Phase_1
**Depends on:** Phase 1 — `docs/superpowers/specs/2026-06-20-source-code-security-design.md`, Phase 2a — `docs/superpowers/specs/2026-07-03-sast-phase2-design.md`

---

## Problem

Phase 1 (gitleaks, pip-audit/pnpm audit) and Phase 2a (semgrep, SonarQube) cover secrets, declared source dependencies, and code written in-house. None of them look inside the actual built Docker images: the base OS layer (e.g. `python:3.11-slim`) and anything installed via shell commands in a Dockerfile are invisible to source-only and dependency-manifest scanning. Phase 2a's first-run triage already surfaced one symptom of this gap manually (both Dockerfiles running as root) — this spec adds automated, ongoing coverage instead of relying on manual discovery.

Separately, none of the 3 `docker-compose*.yml` files have ever been checked for misconfiguration (missing resource limits, unsafe defaults, etc.).

## Goal

Add Trivy as a new tool covering two independent checks:
1. **Image vulnerability scanning** — known CVEs in the built container images (OS packages + baked-in dependencies).
2. **IaC misconfiguration scanning** — the 3 docker-compose files.

Both blocking, all severities (CRITICAL/HIGH/MEDIUM/LOW), no suppression mechanism — user's explicit choice after being flagged that this will likely surface unfixable base-image findings on first run (see Risks).

## Scope

**Images scanned (5, all Dockerfiles in the repo):**
- `app/backend/Dockerfile`
- `app/frontend/Dockerfile`
- `app/ml-microservice/Dockerfile`
- `app/rag-service/Dockerfile`
- `app/ml_research/Dockerfile` (dev-only Jupyter notebooks, scanned anyway for completeness)

`app/frontend/Dockerfile.dev` excluded — dev-only, never used in any built/shipped artifact path this pipeline cares about.

**IaC files scanned (3, all compose files in the repo):**
- `docker-compose.yml`
- `docker-compose.sonarqube.yml`
- `docker-compose.notebooks.yml`

## Pipeline Placement

Current pipeline (`.gitlab-ci.yml`): `secret-scan → sca-deps → sast → sonarqube → lint → gate`

**Key constraint:** this CI has no `build` stage today — no job builds a Docker image anywhere. Trivy's image mode needs a built image to scan, so a build step is new infrastructure, not just a new scan.

New pipeline:

```
secret-scan → sca-deps → sast → sonarqube → build + iac-scan (parallel) → image-scan → lint → gate
```

- `iac-scan` has no dependency on `build` (it reads static YAML files) — runs in parallel with `build`.
- `image-scan` depends on `build` completing (needs the 5 images to exist locally).
- Both new stages run on the self-hosted `tags: [local]` runner (same one `sonarqube-scan` already uses) — that runner already has Docker installed since it's the machine running the actual docker-compose stack. This avoids setting up Docker-in-Docker on shared runners, which would need privileged-mode containers — an added attack surface not worth taking on for a scan-only, no-registry-push use case.
- Images are built and scanned for CI purposes only. **No registry push** — none exists in this project. Images are discarded after the job (ephemeral runner workspace).

## Jobs

| Job | Stage | Command (shape) |
|---|---|---|
| `build-images` | `build` | `docker build` each of the 5 Dockerfiles, tagged locally (e.g. `eam-backend:ci`, `eam-frontend:ci`, etc.) |
| `image-scan` | `image-scan` | `trivy image --severity CRITICAL,HIGH,MEDIUM,LOW --exit-code 1` against each of the 5 tagged images |
| `iac-scan` | `iac-scan` | `trivy config --severity CRITICAL,HIGH,MEDIUM,LOW --exit-code 1` against the 3 compose files |

Both scan jobs:
- `--format sarif -o <job>.sarif` artifact, matching the SARIF convention from Phase 2a's semgrep jobs (kept for consistency even though there's no GitHub code-scanning upload target on this GitLab-only pipeline — the artifact is still useful for local/manual review).
- `allow_failure: false` — blocking, same tier as every other stage.
- Runs on `tags: [local]`.
- Rules: same branch/MR conditions as existing jobs (`clean_Phase_1`, `Phase_1`, `main`, plus `merge_request_event`).

`quality-gate` updated to add `build-images`, `image-scan`, `iac-scan` as blocking `needs`.

## Error Handling

| Failure | Behavior |
|---|---|
| Any CVE at CRITICAL/HIGH/MEDIUM/LOW in any of the 5 images | Job fails, gate blocks merge |
| Any misconfig at CRITICAL/HIGH/MEDIUM/LOW in any of the 3 compose files | Job fails, gate blocks merge |
| `build-images` fails (bad Dockerfile syntax, etc.) | `image-scan` never runs (hard `needs` dependency), gate blocks |
| First run against existing images/compose files | Expected to surface real findings, likely including base-image CVEs with no available fix — **no suppression mechanism exists to unblock these**, user's explicit choice |

## Risks (flagged, accepted by user)

- **No escape valve.** Every other stage in this pipeline (gitleaks, semgrep, SonarQube) has a suppression mechanism for reviewed-and-accepted findings. This one doesn't. If Trivy finds a CVE in a base OS package with no patch available yet, the pipeline stays red until Trivy's database changes, the base image is upgraded, or this policy is revisited — there is no way to merge in the meantime.
- **First run will very likely fail immediately** — this is normal for image scanning in general (near-universal in real-world first runs), not a sign of something wrong with the setup.
- If this proves unworkable in practice, the fix is revisiting severity threshold or adding `.trivyignore` later — not something to pre-build now per user's explicit "no exceptions" choice.

## Out of Scope (this spec)

- IaC scanning of Kubernetes manifests, Terraform, CloudFormation — not applicable, project has none of these.
- Branch protection enforcement (Phase 2b, next track).
- DAST (Phase 2b, final track).
- Grype — not adopted; Trivy covers both image CVE and IaC scanning in one tool, per tool-selection discussion.
- Trivy Kubernetes-cluster mode (`trivy k8s` / Trivy Operator) — no cluster exists yet.

## Success Criteria

- [ ] `build-images` job added to `.gitlab-ci.yml`, builds all 5 images successfully
- [ ] `image-scan` job added, scans all 5 images, SARIF artifact produced
- [ ] `iac-scan` job added, scans all 3 compose files, SARIF artifact produced
- [ ] `quality-gate` updated to depend on all 3 new jobs
- [ ] First run triaged: every finding at any severity either fixed or the underlying image/compose file changed to resolve it (no suppression path exists)
- [ ] Pipeline green on `clean_Phase_1` after triage

---

*Spec written: 2026-07-06 | Approved: user*
