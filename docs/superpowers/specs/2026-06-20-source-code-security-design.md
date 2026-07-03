# Phase 1: Source Code Security — Design Spec

**Date:** 2026-06-20
**Status:** Approved
**Branch:** clean_Phase_1
**Stack:** Next.js 18 (pnpm) + FastAPI (Python 3.11) + Docker + PostgreSQL + MinIO

---

## Problem

EAMSagemCom has zero source-level security controls:
- No secret scanning (`.env` with real credentials lives in repo)
- No CODEOWNERS (any contributor can merge anything)
- No dependency vulnerability checks (requirements.txt + package.json unaudited)
- No CI pipeline of any kind
- No pre-commit hooks

## Goal

Implement Phase 1 of the DevSecOps pipeline: Source Code Security. Every commit and PR must pass secret scanning, dependency CVE checks, and lint gates before merge is permitted.

---

## Deliverables (6 files, 1 atomic commit)

```
EAMSagemCom/
├── CODEOWNERS
├── .gitleaks.toml
├── .pre-commit-config.yaml
├── renovate.json
├── .gitlab-ci.yml
└── .github/workflows/source-security.yml
```

---

## Architecture

### CODEOWNERS
Maps repository paths to `@hamzAmbarki2` (sole owner for now). Ensures all PRs to `app/backend/`, `app/frontend/`, `app/ml-microservice/`, `app/rag-service/` require owner approval. `CODEOWNERS` itself is self-protecting (any change requires owner sign-off).

### .gitleaks.toml
Custom rules layered on top of gitleaks default ruleset. Project-specific patterns:
- MinIO access/secret key patterns (`MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`)
- FastAPI JWT secret (`SECRET_KEY`, `JWT_SECRET`)
- PostgreSQL DSN (`postgresql://`)
- OpenAI / HuggingFace tokens (used by RAG service)
- `.env` file commit prevention (allowlist `.env.example`)

### .pre-commit-config.yaml
Local dev hooks, run on every `git commit`:
1. `gitleaks` — secret scan staged files
2. `eslint` — frontend TypeScript lint (existing config)
3. `ruff` — Python backend lint + format check
4. `check-yaml` / `end-of-file-fixer` — standard pre-commit hygiene

### renovate.json
Weekly auto-PR schedule for:
- `app/frontend/package.json` (pnpm ecosystem)
- `app/backend/requirements.txt` (pip ecosystem)
- Docker base images in `app/backend/Dockerfile`, `app/frontend/Dockerfile`
- Groups minor/patch bumps into single PR, separates major bumps

### .gitlab-ci.yml (GitLab CI)
4-stage pipeline, triggers on push + MR to `Phase_1` / `clean_Phase_1`:

```
secret-scan → sca-deps → lint → gate
```

| Stage | Job | Tool | Blocks merge? |
|-------|-----|------|--------------|
| secret-scan | scan-secrets | gitleaks 8.x | YES — any secret = fail |
| sca-deps | audit-backend | pip-audit | YES — CRITICAL/HIGH CVE |
| sca-deps | audit-frontend | pnpm audit | YES — CRITICAL/HIGH CVE |
| lint | lint-backend | ruff | NO — allow_failure: true |
| lint | lint-frontend | eslint | NO — allow_failure: true |
| gate | quality-gate | bash script | YES — fails if upstream critical jobs failed |

### .github/workflows/source-security.yml (GitHub Actions)
Exact same 4 stages via GitHub Actions syntax. Triggers on:
- `push` to `Phase_1`, `clean_Phase_1`, `main`
- `pull_request` targeting those branches

---

## Pipeline Flow

```
PR opened / push
     │
     ├─► secret-scan     (gitleaks — FAIL on ANY credential found)
     │        │ pass
     ├─► sca-deps        (pip-audit + pnpm audit — FAIL on CRITICAL/HIGH CVE)
     │        │ pass
     ├─► lint            (ruff + eslint — warn only, NON-BLOCKING)
     │        │ always
     └─► gate            (merge blocked if secret-scan or sca-deps failed)
```

---

## Security Controls Mapping

| Control | Mechanism | Implementation |
|---------|-----------|---------------|
| Branch protection | GitHub/GitLab repo settings | Documented in this spec — manual step |
| Commit signing | GPG | Setup guide below |
| Code owners | CODEOWNERS file | Delivered as file |
| Secret detection | gitleaks (pre-commit + CI) | .gitleaks.toml + CI job |
| Dependency CVE | pip-audit + pnpm audit | CI job (sca-deps stage) |
| Auto dep updates | Renovate bot | renovate.json |
| Code quality gate | ruff + ESLint | CI job (lint stage, non-blocking) |

---

## Branch Protection Settings (Manual — Apply After CI is Live)

**GitHub Settings → Branches → Add rule → `Phase_1` / `main`:**
- [x] Require a pull request before merging
- [x] Require status checks to pass before merging
  - Required: `secret-scan / scan-secrets`
  - Required: `sca-deps / audit-backend`
  - Required: `sca-deps / audit-frontend`
  - Required: `gate / quality-gate`
- [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings

**GitLab Settings → Repository → Protected branches → `Phase_1`:**
- Allowed to merge: Maintainers
- Allowed to push: No one (force MR flow)
- Required approvals: 1

---

## Commit Signing Setup (Developer Reference)

```bash
# Generate GPG key (if not existing)
gpg --full-generate-key  # RSA 4096, no expiry

# Get key ID
gpg --list-secret-keys --keyid-format=long

# Configure git to sign
git config --global user.signingkey <KEY_ID>
git config --global commit.gpgsign true
git config --global gpg.program gpg

# Add public key to GitHub: Settings → SSH and GPG keys → New GPG key
gpg --armor --export <KEY_ID>
```

---

## Error Handling

| Failure | Behavior |
|---------|----------|
| Secret found by gitleaks | Pipeline fails, PR blocked, error shows file:line |
| CRITICAL/HIGH CVE found | Pipeline fails, PR blocked, CVE ID + fix version shown |
| Lint warning | Pipeline continues, warning shown in job output |
| Renovate PR opened | Auto-assigns to owner, CI runs on the dep-update PR |

---

## What's Out of Scope (Phase 2+)

- SAST (static analysis beyond lint) → Phase 3
- Docker image scanning → Phase 4
- IaC scanning of docker-compose.yml → Phase 3
- DAST → Phase 6
- Deployment pipelines → Phase 5

---

## Success Criteria

- [x] `CODEOWNERS` created and validated by GitHub/GitLab
- [x] `.gitleaks.toml` scans clean on current codebase (no false positives from `.env.example`)
- [x] `.pre-commit-config.yaml` installs and runs locally with `pre-commit install`
- [x] `renovate.json` validated by Renovate config validator
- [x] `.gitlab-ci.yml` passes `devops-skills:gitlab-ci-validator` with zero Critical/High issues
- [x] `.github/workflows/source-security.yml` passes GitHub Actions schema validation
- [x] All 6 files committed in one atomic commit on `clean_Phase_1`

**Verified 2026-07-03:** pushed 25 commits to `origin/clean_Phase_1`, all CI jobs (secret-scan, sca-deps backend/frontend, lint, gate) passing on GitHub Actions.

---

*Spec written: 2026-06-20 | Approved: user | Skills used: brainstorming, gsd:plan-phase, engineering-advanced-skills, gitlab-ci-generator, gitlab-ci-validator, gsd:debug*
