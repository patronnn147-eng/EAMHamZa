# Phase 2b (Track 1): Trivy Image + IaC Scanning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Trivy-based container image CVE scanning (5 images) and IaC misconfiguration scanning (3 docker-compose files) as new blocking CI stages, closing the gap where nothing inspects what's actually inside built Docker images or the compose configs themselves.

**Architecture:** Two new stages, `build` and `image-scan`, inserted between `sonarqube` and `lint` in `.gitlab-ci.yml`. The `build` stage runs two independent jobs in parallel: `build-images` (builds all 5 Dockerfiles locally) and `iac-scan` (Trivy config-mode scan of the 3 compose files — no dependency on the build). The `image-scan` stage runs one job, `image-scan`, which needs `build-images` to have produced the 5 tagged images first. All new jobs run on the self-hosted `tags: [local]` runner (same one `sonarqube-scan` already uses) via a Docker-socket bind mount, avoiding Docker-in-Docker on shared runners.

**Tech Stack:** Trivy CLI (`aquasec/trivy` image), `docker:24-cli` image for builds, GitLab CI, self-hosted `local` runner with Docker socket access.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-06-trivy-image-iac-scan-design.md`
- Pipeline stage order: `secret-scan → sca-deps → sast → sonarqube → build → image-scan → lint → gate` (exact — do not reorder)
- Job names, exact: `build-images`, `iac-scan` (both `stage: build`), `image-scan` (`stage: image-scan`)
- Blocking rule: ALL severities (CRITICAL, HIGH, MEDIUM, LOW) fail the job — no severity floor, per user's explicit choice
- **No suppression mechanism** — do not add a `.trivyignore` file or any ignore-list; this is a deliberate constraint from the spec, not an oversight
- Images scanned, exact 5: `app/backend/Dockerfile`, `app/frontend/Dockerfile`, `app/ml-microservice/Dockerfile`, `app/rag-service/Dockerfile`, `app/ml-microservice/ml_research/Dockerfile`
- Build contexts, exact (copied from existing `docker-compose.yml`/`docker-compose.notebooks.yml` `build:` blocks — do not invent different contexts):
  | Image tag | Context | Dockerfile |
  |---|---|---|
  | `eam-backend:ci` | `./app/backend` | `Dockerfile` |
  | `eam-frontend:ci` | `./app/frontend` | `Dockerfile` (build arg `VITE_API_BASE_URL=http://localhost:8000`) |
  | `eam-ml-microservice:ci` | `./app/ml-microservice` | `Dockerfile` |
  | `eam-rag-service:ci` | `./app/rag-service` | `Dockerfile` |
  | `eam-ml-research:ci` | `.` (repo root) | `app/ml-microservice/ml_research/Dockerfile` |
- IaC files scanned, exact 3: `docker-compose.yml`, `docker-compose.sonarqube.yml`, `docker-compose.notebooks.yml`
- All new jobs: `tags: [local]`, `allow_failure: false`, same branch `rules:` as every existing job (`clean_Phase_1`, `Phase_1`, `main`, plus `merge_request_event`)
- No registry push anywhere — images exist only for the duration of the CI job on the local runner's Docker daemon

---

## File Structure

```
.gitlab-ci.yml                          # modified: +build stage, +image-scan stage, +3 jobs, gate needs updated
docs/superpowers/specs/2026-07-06-trivy-image-iac-scan-design.md  # modified: success criteria checked off (Task 5)
```

No new source files — this is CI configuration only. Trivy and Docker CLI come from their respective official images (`docker:24-cli`, `aquasec/trivy`), no repo-local install scripts needed.

---

### Task 1: Local runner prerequisite — Docker socket access (manual, one-time)

**Files:** none in this repo — this is GitLab Runner host configuration, which lives outside the repository (typically `/etc/gitlab-runner/config.toml` on the runner host).

**Interfaces:**
- Produces: the `local`-tagged runner gains the ability to run `docker build`/Docker API calls against the host's real Docker daemon from inside a job container. Every later task in this plan (`build-images`, `image-scan`) depends on this being done first — without it, those jobs will fail with a "cannot connect to the Docker daemon" error.

**This step cannot be automated from within this repo or this session** — it requires editing the runner host's own config file and restarting the runner service, which is infrastructure outside git's reach (same category as Phase 2a's Task 10, which needed a manually-created Semgrep account).

- [ ] **Step 1: Locate the local runner's `config.toml`**

On the machine running the `local`-tagged GitLab Runner (the same host that already runs `sonarqube-scan` and your docker-compose stack), find its config file — typically:

```bash
find / -name "config.toml" -path "*gitlab-runner*" 2>/dev/null
```

Common default location: `/etc/gitlab-runner/config.toml`.

- [ ] **Step 2: Add the Docker socket volume mount**

Open `config.toml` and find the `[[runners]]` block whose `tags` (or executor config) matches the `local` tag used in `.gitlab-ci.yml`. Under its `[runners.docker]` section, ensure `volumes` includes the Docker socket:

```toml
[[runners]]
  name = "local"
  # ... existing config ...
  [runners.docker]
    # ... existing config ...
    volumes = ["/var/run/docker.sock:/var/run/docker.sock", "/cache"]
```

If `volumes` already exists with other entries (e.g. just `["/cache"]`), add the socket path alongside them rather than replacing the line.

- [ ] **Step 3: Restart the runner**

```bash
sudo gitlab-runner restart
```

(Exact command depends on how the runner was installed — service manager restart if it's running as a system service instead.)

- [ ] **Step 4: Verify socket access with a throwaway job (manual smoke test)**

Temporarily confirm Docker is reachable by running, on the runner host itself (not yet via CI):

```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock docker:24-cli docker ps
```

Expected: prints a table of running containers (including the ones from your docker-compose stack) with no permission/connection errors. If this fails, the socket mount or Docker group permissions on the host need fixing before continuing — do not proceed to Task 2 until this passes.

- [ ] **Step 5: Report completion**

Confirm to the user that this manual step is done before continuing to Task 2 — Tasks 2-4 assume Docker is reachable from `tags: [local]` jobs.

---

### Task 2: GitLab CI — add `build` stage with `build-images` and `iac-scan` jobs

**Files:**
- Modify: `.gitlab-ci.yml`

**Interfaces:**
- Consumes: Docker socket access from Task 1.
- Produces: two new job names in `.gitlab-ci.yml` — `build-images` and `iac-scan` — both in a new `build` stage. `build-images` produces 5 locally-tagged Docker images (`eam-backend:ci`, `eam-frontend:ci`, `eam-ml-microservice:ci`, `eam-rag-service:ci`, `eam-ml-research:ci`) on the local runner's Docker daemon, which Task 3's `image-scan` job depends on existing.

- [ ] **Step 1: Add `build` and `image-scan` to the stages list**

In `.gitlab-ci.yml`, change:

```yaml
stages:
  - secret-scan
  - sca-deps
  - sast
  - sonarqube
  - lint
  - gate
```

to:

```yaml
stages:
  - secret-scan
  - sca-deps
  - sast
  - sonarqube
  - build
  - image-scan
  - lint
  - gate
```

Also update the header comment at the top of the file:

```yaml
# Stages: secret-scan → sca-deps → sast → sonarqube → build → image-scan → lint → gate
# Blocking: secret-scan, sca-deps, sast, sonarqube, build, image-scan, gate
```

- [ ] **Step 2: Insert the `build-images` and `iac-scan` jobs**

Insert this block after the `# ─── Stage 4: SonarQube` section (after `sonarqube-scan`'s closing `allow_failure: false` line) and before the `# ─── Stage 5: Lint` comment:

```yaml
# ─── Stage 5: Build images + IaC scan (parallel, self-hosted local runner) ──

build-images:
  stage: build
  needs: [sonarqube-scan]
  tags: [local]
  image: docker:24-cli
  script:
    - docker build -t eam-backend:ci ./app/backend
    - docker build -t eam-frontend:ci --build-arg VITE_API_BASE_URL=http://localhost:8000 ./app/frontend
    - docker build -t eam-ml-microservice:ci ./app/ml-microservice
    - docker build -t eam-rag-service:ci ./app/rag-service
    - docker build -t eam-ml-research:ci -f app/ml-microservice/ml_research/Dockerfile .
  rules:
    - if: $CI_COMMIT_BRANCH =~ /^(Phase_1|clean_Phase_1|main)$/
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  timeout: 20 minutes
  allow_failure: false

iac-scan:
  stage: build
  needs: [sonarqube-scan]
  tags: [local]
  image: aquasec/trivy:latest
  script:
    - |
      FAILED=0
      for f in docker-compose.yml docker-compose.sonarqube.yml docker-compose.notebooks.yml; do
        BASENAME=$(echo "$f" | sed 's/\.yml$//' | sed 's/[^a-zA-Z0-9_-]/-/g')
        trivy config --severity CRITICAL,HIGH,MEDIUM,LOW --format sarif -o "trivy-iac-${BASENAME}.sarif" --exit-code 1 "$f" || FAILED=1
      done
      exit $FAILED
  artifacts:
    paths:
      - trivy-iac-*.sarif
    expire_in: 1 week
    when: always
  rules:
    - if: $CI_COMMIT_BRANCH =~ /^(Phase_1|clean_Phase_1|main)$/
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  timeout: 10 minutes
  allow_failure: false
```

- [ ] **Step 3: Validate YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml')); print('valid')"`
Expected: `valid` (no exception).

- [ ] **Step 4: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "feat(ci): add build stage with build-images and iac-scan (Trivy) jobs"
```

---

### Task 3: GitLab CI — add `image-scan` stage and job

**Files:**
- Modify: `.gitlab-ci.yml`

**Interfaces:**
- Consumes: the 5 tagged images produced by `build-images` (Task 2) — `eam-backend:ci`, `eam-frontend:ci`, `eam-ml-microservice:ci`, `eam-rag-service:ci`, `eam-ml-research:ci`.
- Produces: `image-scan` job name that Task 4's `quality-gate` update depends on existing.

- [ ] **Step 1: Insert the `image-scan` job**

Insert this block after the `build-images`/`iac-scan` block from Task 2, before the `# ─── Stage 5: Lint` comment (renumber that comment to `# ─── Stage 6: Lint` — see Step 2):

```yaml
# ─── Stage 6: Image Vulnerability Scan (Trivy, self-hosted local runner) ────

image-scan:
  stage: image-scan
  needs: [build-images]
  tags: [local]
  image: aquasec/trivy:latest
  script:
    - |
      FAILED=0
      for img in eam-backend:ci eam-frontend:ci eam-ml-microservice:ci eam-rag-service:ci eam-ml-research:ci; do
        TAGNAME=$(echo "$img" | cut -d: -f1)
        trivy image --severity CRITICAL,HIGH,MEDIUM,LOW --format sarif -o "trivy-image-${TAGNAME}.sarif" --exit-code 1 "$img" || FAILED=1
      done
      exit $FAILED
  artifacts:
    paths:
      - trivy-image-*.sarif
    expire_in: 1 week
    when: always
  rules:
    - if: $CI_COMMIT_BRANCH =~ /^(Phase_1|clean_Phase_1|main)$/
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  timeout: 15 minutes
  allow_failure: false
```

- [ ] **Step 2: Renumber the following stage comments for consistency**

The `# ─── Stage 5: Lint` and `# ─── Stage 6: Quality Gate` comments below are now out of sequence (there are two new stages before them). Update:

```yaml
# ─── Stage 5: Lint (non-blocking) ────────────────────────────────────────────
```
to
```yaml
# ─── Stage 7: Lint (non-blocking) ────────────────────────────────────────────
```

and

```yaml
# ─── Stage 6: Quality Gate ───────────────────────────────────────────────────
```
to
```yaml
# ─── Stage 8: Quality Gate ───────────────────────────────────────────────────
```

This is a comment-only change — no behavioral effect, just keeping the numbering honest for the next person reading the file.

- [ ] **Step 3: Validate YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml')); print('valid')"`
Expected: `valid`.

- [ ] **Step 4: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "feat(ci): add image-scan stage with Trivy CVE scan of 5 built images"
```

---

### Task 4: GitLab CI — update `quality-gate` to depend on the 3 new jobs

**Files:**
- Modify: `.gitlab-ci.yml`

**Interfaces:**
- Consumes: `build-images`, `iac-scan`, `image-scan` job names (Tasks 2-3).
- Produces: updated `quality-gate` job whose `needs:` list Task 5's pipeline run depends on for blocking behavior.

- [ ] **Step 1: Update the `needs:` list**

In the `quality-gate` job, change:

```yaml
  needs:
    - scan-secrets
    - audit-backend
    - audit-frontend
    - sast-auto
    - sast-explicit
    - sast-custom
    - sonarqube-scan
    - job: lint-backend
      optional: true
    - job: lint-frontend
      optional: true
```

to:

```yaml
  needs:
    - scan-secrets
    - audit-backend
    - audit-frontend
    - sast-auto
    - sast-explicit
    - sast-custom
    - sonarqube-scan
    - build-images
    - iac-scan
    - image-scan
    - job: lint-backend
      optional: true
    - job: lint-frontend
      optional: true
```

- [ ] **Step 2: Update the echo block**

Change:

```yaml
  script:
    - |
      echo "All blocking security gates passed."
      echo "  Secret scan   -- PASSED"
      echo "  Backend SCA   -- PASSED"
      echo "  Frontend SCA  -- PASSED"
      echo "  SAST (auto/explicit/custom) -- PASSED"
      echo "  SonarQube     -- PASSED"
      echo "  Lint jobs are non-blocking (warn only)"
```

to:

```yaml
  script:
    - |
      echo "All blocking security gates passed."
      echo "  Secret scan   -- PASSED"
      echo "  Backend SCA   -- PASSED"
      echo "  Frontend SCA  -- PASSED"
      echo "  SAST (auto/explicit/custom) -- PASSED"
      echo "  SonarQube     -- PASSED"
      echo "  Image build   -- PASSED"
      echo "  IaC scan (Trivy)    -- PASSED"
      echo "  Image scan (Trivy)  -- PASSED"
      echo "  Lint jobs are non-blocking (warn only)"
```

- [ ] **Step 3: Validate YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml')); print('valid')"`
Expected: `valid`.

- [ ] **Step 4: Verify job wiring with grep**

Run: `grep -n "build-images\|iac-scan\|image-scan" .gitlab-ci.yml`
Expected: matches in the 3 job definitions themselves (Tasks 2-3), plus 3 mentions in `quality-gate`'s `needs:` list — confirms nothing was missed.

- [ ] **Step 5: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "feat(ci): wire build-images, iac-scan, image-scan into quality-gate"
```

---

### Task 5: Push, verify pipeline, triage first-run findings (no suppression available)

**Files:** none created upfront — this task operates on CI state and, if findings require fixes, on Dockerfiles/compose files/base image choices.

**Interfaces:**
- Consumes: everything from Tasks 1-4 (working Docker socket access, all 3 new jobs wired into the gate).
- Produces: a green pipeline on `clean_Phase_1` with `build-images`, `iac-scan`, and `image-scan` all passing.

- [ ] **Step 1: Push the branch**

```bash
git push origin clean_Phase_1
```

- [ ] **Step 2: Check pipeline status**

Check the GitLab pipeline for `clean_Phase_1` (via GitLab UI — this repo's primary CI is GitLab per `[[devops-phase-status]]`, not GitHub Actions). Note the result of `build-images`, `iac-scan`, and `image-scan`.

Expected on first run: **very likely one or both scan jobs fail** — this is normal for image scanning against real base images (near-universal on a first run) and was flagged as an accepted risk in the spec. If both pass immediately, skip to Step 5.

- [ ] **Step 3: Triage `image-scan` findings, if any**

For each CVE in a failed image's SARIF artifact (download from job artifacts, or read the job log output):

1. Note the image, the affected package, the CVE ID, and severity.
2. Check whether a newer version of that package (or a newer base image tag, e.g. bumping `python:3.11-slim` to a more recent patch release) resolves it: `docker build --no-cache` after bumping the `FROM` line or adding an explicit `apt-get install <package>=<fixed-version>` pin, then re-run `trivy image` locally to confirm the CVE is gone before pushing.
3. **There is no suppression mechanism for this stage** (per spec) — if a CVE genuinely has no available fix yet, the pipeline stays red. Do not add a `.trivyignore` file or any per-CVE ignore flag to work around this; that contradicts the user's explicit "no exceptions" choice from the design phase. Report any such CVE to the user instead of suppressing it.

- [ ] **Step 4: Triage `iac-scan` findings, if any**

For each misconfiguration Trivy reports against a compose file:

1. Read the rule ID and message (e.g. missing resource limits, exposed port ranges, privileged mode).
2. Fix the compose file directly (add the missing config Trivy is asking for).
3. Same no-suppression rule as Step 3 — fix the file, don't ignore the finding.

- [ ] **Step 5: Re-push and re-check until green**

```bash
git add -A
git commit -m "fix(security): remediate Trivy image/IaC findings from first CI run"
git push origin clean_Phase_1
```

Re-check the pipeline. Repeat Steps 3-5 until `build-images`, `iac-scan`, and `image-scan` all pass.

- [ ] **Step 6: Update the spec's success criteria**

In `docs/superpowers/specs/2026-07-06-trivy-image-iac-scan-design.md`, check off all items in `## Success Criteria` and add a `**Verified <date>:**` line noting the pipeline is green and summarizing what first-run triage found, following the same pattern used in the Phase 2a spec.

- [ ] **Step 7: Commit the spec update**

```bash
git add docs/superpowers/specs/2026-07-06-trivy-image-iac-scan-design.md
git commit -m "docs(spec): mark Phase 2b track 1 success criteria complete"
git push origin clean_Phase_1
```

---

## Self-Review Notes

- **Spec coverage:** new `build`/`image-scan` stages (Tasks 2-3), 5-image build matrix with exact contexts (Task 2), 3-file IaC scan (Task 2), all-severities blocking with no suppression (Tasks 2-3, enforced explicitly in Task 5), gate wiring (Task 4), local-runner Docker socket prerequisite (Task 1, flagged as manual/unautomatable same as Phase 2a's Semgrep token step), first-run triage (Task 5) — all covered.
- **Docker socket access is a hard prerequisite** or Tasks 2-3's jobs will fail immediately with a daemon-connection error — Task 1 must be confirmed done by the user before Task 2 begins.
- **Type/name consistency:** job names `build-images`, `iac-scan`, `image-scan` used identically across Tasks 2, 3, 4. Image tags (`eam-backend:ci`, `eam-frontend:ci`, `eam-ml-microservice:ci`, `eam-rag-service:ci`, `eam-ml-research:ci`) match exactly between `build-images`' `docker build -t` commands and `image-scan`'s scan loop.
- **No suppression mechanism is intentional** — Task 5 explicitly calls this out twice to prevent a future implementer from "fixing" a red pipeline by quietly adding an ignore file, which would silently contradict an explicit user decision from the design phase.
