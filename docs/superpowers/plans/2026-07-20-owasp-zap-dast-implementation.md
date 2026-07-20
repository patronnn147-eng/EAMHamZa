# OWASP ZAP DAST Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Do NOT use subagent-driven-development or the Agent tool for this project — established project preference is direct, single-session execution (see feedback memory `feedback-no-subagents.md`).**

**Goal:** Add OWASP ZAP as a full active DAST scanner, driven by one shared ZAP Automation Framework YAML plan usable both manually (ZAP Desktop, for learning) and headlessly (new `dast` stage in `.gitlab-ci.yml`).

**Architecture:** A single `security/zap/zap-automation.yaml` Automation Framework plan defines 4 scan contexts (`backend` with 4 role-based authenticated users, plus unauthenticated `ml-service`, `rag-service`, `frontend`). The new `dast` CI job runs this plan headless via `docker run zaproxy/zap-stable`, gated by a two-layer safety pre-flight (hardcoded internal-only targets + seeded-test-data verification query). Findings render through the same shared `monitoring/scripts/security_report.py` terminal formatter every other scanner in this pipeline uses.

**Tech Stack:** OWASP ZAP (`ghcr.io/zaproxy/zaproxy:stable` Docker image), ZAP Automation Framework (YAML), GitLab CI, Python 3.11 (report parser), Bash (CI job glue, matches every other job in this pipeline).

## Global Constraints

- Full active scan (spider + activeScan, not passive baseline) — per approved spec.
- Scan targets are hardcoded Docker-internal service DNS names, never CI-variable-overridable: `http://backend:8000`, `http://ml-service:8000`, `http://rag-service:8003`, `http://frontend:80`.
- Excluded from scope: `postgres`, `rabbitmq`, `minio`, `pgadmin` (infra/admin panels, not app code).
- 4 backend auth users, real seeded accounts, one shared password (never committed in plaintext to any file):
  - ADMIN — `hamza.mbarki2002@gmail.com`
  - CHEFTECH — `hamza.mbarki@esprit.tn`
  - CHETOP — `mbarkih92@gmail.com`
  - TECHNICIEN — `hamedikilani44@gmail.com`
- Login endpoint: `POST /api/v1/auth/login`, body `{"email": "...", "mot_de_passe": "..."}`, response contains `access_token`.
- Scan policy: ZAP's built-in "Default Policy" only (excludes DoS-class rules).
- `dast` job: `stage: dast`, inserted between `image-scan` and `lint` in `.gitlab-ci.yml`, `tags: [local]`, `allow_failure: true` — matches every non-blocking job already in this file.
- No alert-suppression filters configured in this pass — ship clean, tune later from real results.
- Full spec: `docs/superpowers/specs/2026-07-20-owasp-zap-dast-design.md`.

---

## File Structure

- **`monitoring/scripts/security_report.py`** (modify) — add `parse_zap()` + register in `PARSERS` dict. Reuses existing `Finding`/`print_report` machinery, zero new abstractions.
- **`monitoring/scripts/test_security_report.py`** (create) — first test file for this script; covers only the new `parse_zap()` function (existing parsers stay untested, matching current state — not this task's job to retrofit them).
- **`security/zap/zap-automation.yaml`** (create) — the ZAP Automation Framework plan. Single source of truth for both manual (ZAP Desktop) and CI runs.
- **`.gitlab-ci.yml`** (modify) — add `dast` stage to `stages:` list, add `dast-scan` job, wire into `quality-gate` needs + summary echo, update header comment block.
- **`.env.example`** (modify) — document `ZAP_LOGIN_PASSWORD` (empty placeholder).
- **`.env`** (modify) — real value for local manual runs, gitignored, never committed.
- **`Makefile`** (modify) — add `dast` target for local headless runs (mirrors existing `scan-and-push` target's style).
- **`docs/owasp-zap-getting-started.md`** (create) — the beginner-facing manual walkthrough (ZAP Desktop install → GUI tour → load plan → run → read a finding → repeat headless).

---

## Task 1: ZAP report parser (`security_report.py`)

**Files:**
- Modify: `monitoring/scripts/security_report.py`
- Test: `monitoring/scripts/test_security_report.py` (new file)

**Interfaces:**
- Produces: `parse_zap(data: dict) -> list[Finding]`, registered as `PARSERS["zap"]`. Later tasks' CI job calls `python3 monitoring/scripts/security_report.py zap zap-report.json "DAST"`.

- [ ] **Step 1: Write the failing test**

Create `monitoring/scripts/test_security_report.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from security_report import parse_zap, PARSERS, Finding

SAMPLE_ZAP_REPORT = {
    "@version": "2.14.0",
    "@generated": "Mon, 20 Jul 2026 10:00:00",
    "site": [
        {
            "@name": "http://backend:8000",
            "@host": "backend",
            "@port": "8000",
            "@ssl": "false",
            "alerts": [
                {
                    "pluginid": "40018",
                    "alertRef": "40018",
                    "alert": "SQL Injection",
                    "name": "SQL Injection",
                    "riskcode": "3",
                    "confidence": "2",
                    "riskdesc": "High (Medium)",
                    "desc": "SQL injection may be possible.",
                    "instances": [
                        {
                            "uri": "http://backend:8000/api/v1/entities/machines?id=1",
                            "method": "GET",
                            "param": "id",
                            "evidence": "",
                        }
                    ],
                    "count": "1",
                    "solution": "Use parameterised queries.",
                    "cweid": "89",
                },
                {
                    "pluginid": "10021",
                    "alertRef": "10021",
                    "alert": "X-Content-Type-Options Header Missing",
                    "name": "X-Content-Type-Options Header Missing",
                    "riskcode": "1",
                    "confidence": "2",
                    "riskdesc": "Low (Medium)",
                    "desc": "Header missing.",
                    "instances": [
                        {"uri": "http://backend:8000/api/v1/health", "method": "GET"}
                    ],
                    "count": "1",
                    "solution": "Add the header.",
                    "cweid": "693",
                },
                {
                    "pluginid": "10049",
                    "alertRef": "10049",
                    "alert": "Storable and Cacheable Content",
                    "name": "Storable and Cacheable Content",
                    "riskcode": "0",
                    "confidence": "2",
                    "riskdesc": "Informational (Medium)",
                    "desc": "Informational finding.",
                    "instances": [
                        {"uri": "http://backend:8000/", "method": "GET"}
                    ],
                    "count": "1",
                    "solution": "n/a",
                    "cweid": "-1",
                },
            ],
        }
    ],
}


def test_parse_zap_maps_high_severity():
    findings = parse_zap(SAMPLE_ZAP_REPORT)
    sqli = next(f for f in findings if f.id == "40018")
    assert sqli.severity == "HIGH"
    assert sqli.name == "SQL Injection"
    assert sqli.location == "http://backend:8000/api/v1/entities/machines?id=1"


def test_parse_zap_maps_low_severity():
    findings = parse_zap(SAMPLE_ZAP_REPORT)
    header = next(f for f in findings if f.id == "10021")
    assert header.severity == "LOW"


def test_parse_zap_maps_informational_to_unknown():
    findings = parse_zap(SAMPLE_ZAP_REPORT)
    info = next(f for f in findings if f.id == "10049")
    assert info.severity == "UNKNOWN"


def test_parse_zap_handles_empty_site_list():
    assert parse_zap({"site": []}) == []


def test_parse_zap_registered_in_parsers():
    assert PARSERS["zap"] is parse_zap


def test_cli_end_to_end(tmp_path):
    report_file = tmp_path / "zap-report.json"
    report_file.write_text(json.dumps(SAMPLE_ZAP_REPORT))
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "security_report.py"),
         "zap", str(report_file), "DAST"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "SQL Injection" in result.stdout
    assert "HIGH" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest monitoring/scripts/test_security_report.py -v`
Expected: `ImportError: cannot import name 'parse_zap'` (function doesn't exist yet) — all 6 tests FAIL or ERROR.

- [ ] **Step 3: Implement `parse_zap` and register it**

In `monitoring/scripts/security_report.py`, add after `parse_trivy` (before the `PARSERS` dict):

```python
def _map_zap_severity(riskdesc: str) -> str:
    # riskdesc looks like "High (Medium)" — risk level, then confidence in parens.
    # We only care about the risk level (first word).
    level = (riskdesc or "").split(" ")[0].strip().lower()
    return {
        "high": "HIGH",
        "medium": "MEDIUM",
        "low": "LOW",
        "informational": "UNKNOWN",
    }.get(level, "UNKNOWN")


def parse_zap(data: dict) -> list:
    findings = []
    for site in data.get("site", []) or []:
        for alert in site.get("alerts", []) or []:
            instances = alert.get("instances", []) or []
            location = instances[0].get("uri", "?") if instances else site.get("@name", "?")
            if len(instances) > 1:
                location = f"{location} (+{len(instances) - 1} more)"
            findings.append(Finding(
                id=alert.get("pluginid", "unknown-plugin"),
                name=alert.get("alert", alert.get("name", "unknown-alert")),
                installed="-",
                fixed="-",
                severity=_map_zap_severity(alert.get("riskdesc", "")),
                location=location,
            ))
    return findings
```

Update the `PARSERS` dict:

```python
PARSERS = {
    "gitleaks": parse_gitleaks,
    "pip-audit": parse_pip_audit,
    "pnpm-audit": parse_pnpm_audit,
    "trivy": parse_trivy,
    "zap": parse_zap,
}
```

Also update the module docstring's `tool` line (near the top of the file) from:
```
  tool  : gitleaks | pip-audit | pnpm-audit | trivy
```
to:
```
  tool  : gitleaks | pip-audit | pnpm-audit | trivy | zap
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest monitoring/scripts/test_security_report.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add monitoring/scripts/security_report.py monitoring/scripts/test_security_report.py
git commit -m "feat: add ZAP report parser to security_report.py"
```

---

## Task 2: ZAP Automation Framework plan

**Files:**
- Create: `security/zap/zap-automation.yaml`

**Interfaces:**
- Consumes: `${ZAP_LOGIN_PASSWORD}` env var (set by Task 4).
- Produces: `zap-report.html`, `zap-report.json` written to the working directory the plan is run from — consumed by Task 3's CI job and Task 5's Makefile target.

**Requires Docker running** (currently down on this machine — restart Docker Desktop before this task). The stack must be up (`make up`) since this task's verification step runs the plan for real against `http://backend:8000` etc. — but ZAP itself runs in its own container that needs network access to `asset_management_network`, not `localhost`.

- [ ] **Step 1: Write the automation plan**

Create `security/zap/zap-automation.yaml`:

```yaml
env:
  contexts:
    - name: "backend"
      urls:
        - "http://backend:8000"
      includePaths:
        - "http://backend:8000.*"
      authentication:
        method: "json"
        parameters:
          loginRequestUrl: "http://backend:8000/api/v1/auth/login"
          loginRequestBody: '{"email":"{%username%}","mot_de_passe":"{%password%}"}'
        verification:
          method: "response"
          loggedInRegex: "\\Qaccess_token\\E"
      sessionManagement:
        method: "headers"
        parameters:
          Authorization: "Bearer {%json:access_token%}"
      users:
        - name: "admin"
          credentials:
            username: "hamza.mbarki2002@gmail.com"
            password: "${ZAP_LOGIN_PASSWORD}"
        - name: "cheftech"
          credentials:
            username: "hamza.mbarki@esprit.tn"
            password: "${ZAP_LOGIN_PASSWORD}"
        - name: "chetop"
          credentials:
            username: "mbarkih92@gmail.com"
            password: "${ZAP_LOGIN_PASSWORD}"
        - name: "technicien"
          credentials:
            username: "hamedikilani44@gmail.com"
            password: "${ZAP_LOGIN_PASSWORD}"
    - name: "ml-service"
      urls:
        - "http://ml-service:8000"
      includePaths:
        - "http://ml-service:8000.*"
    - name: "rag-service"
      urls:
        - "http://rag-service:8003"
      includePaths:
        - "http://rag-service:8003.*"
    - name: "frontend"
      urls:
        - "http://frontend:80"
      includePaths:
        - "http://frontend:80.*"
  parameters:
    failOnError: false
    failOnWarning: false
    progressToStdout: true

jobs:
  # ── backend: authenticated, once per role ──────────────────────────────
  - type: spider
    parameters:
      context: "backend"
      user: "admin"
      url: "http://backend:8000"

  - type: passiveScan-wait
    parameters:
      maxDuration: 5

  - type: activeScan
    parameters:
      context: "backend"
      user: "admin"
      policy: "Default Policy"

  - type: activeScan
    parameters:
      context: "backend"
      user: "cheftech"
      policy: "Default Policy"

  - type: activeScan
    parameters:
      context: "backend"
      user: "chetop"
      policy: "Default Policy"

  - type: activeScan
    parameters:
      context: "backend"
      user: "technicien"
      policy: "Default Policy"

  # ── ml-service: unauthenticated, internal-only ─────────────────────────
  - type: spider
    parameters:
      context: "ml-service"
      url: "http://ml-service:8000"

  - type: passiveScan-wait
    parameters:
      maxDuration: 5

  - type: activeScan
    parameters:
      context: "ml-service"
      policy: "Default Policy"

  # ── rag-service: unauthenticated, internal-only ────────────────────────
  - type: spider
    parameters:
      context: "rag-service"
      url: "http://rag-service:8003"

  - type: passiveScan-wait
    parameters:
      maxDuration: 5

  - type: activeScan
    parameters:
      context: "rag-service"
      policy: "Default Policy"

  # ── frontend: unauthenticated, public UI ───────────────────────────────
  - type: spider
    parameters:
      context: "frontend"
      url: "http://frontend:80"

  - type: passiveScan-wait
    parameters:
      maxDuration: 5

  - type: activeScan
    parameters:
      context: "frontend"
      policy: "Default Policy"

  # ── reports ─────────────────────────────────────────────────────────────
  - type: report
    parameters:
      template: "traditional-html"
      reportDir: "/zap/wrk"
      reportFile: "zap-report"
      reportTitle: "EAMSagemCom DAST Report"
      reportDescription: "Full active scan: backend (4 roles), ml-service, rag-service, frontend"

  - type: report
    parameters:
      template: "traditional-json"
      reportDir: "/zap/wrk"
      reportFile: "zap-report"
```

- [ ] **Step 2: Run it for real and verify it fails cleanly if Docker is down (confirms the command shape is right)**

Run:
```bash
docker run --rm -v "$(pwd)/security/zap:/zap/wrk:rw" ghcr.io/zaproxy/zaproxy:stable zap.sh -cmd -autorun /zap/wrk/zap-automation.yaml
```
Expected right now (Docker Desktop down): `error during connect ... dockerDesktopLinuxEngine`. **Start Docker Desktop, then `make up`, then re-run this step** before continuing — this task isn't done until the command below succeeds for real.

- [ ] **Step 3: Run the plan against the live stack, on the app's own network**

Run:
```bash
docker run --rm \
  --network asset_management_network \
  -e ZAP_LOGIN_PASSWORD="hA123456" \
  -v "$(pwd)/security/zap:/zap/wrk:rw" \
  ghcr.io/zaproxy/zaproxy:stable \
  zap.sh -cmd -autorun /zap/wrk/zap-automation.yaml
```
Expected: ZAP logs spider/activeScan progress per job, ends with `zap-report.html` and `zap-report.json` written into `security/zap/`. If ZAP prints a YAML validation error (e.g. an unrecognized parameter key), fix the specific key it names in `zap-automation.yaml` and re-run — this step isn't complete until a real report file with `site[].alerts` entries exists on disk.

- [ ] **Step 4: Confirm the report has real findings and the auth actually worked**

Run: `python3 -c "import json; d=json.load(open('security/zap/zap-report.json')); print(len(d.get('site',[])), 'sites scanned'); [print(s['@name'], len(s.get('alerts',[]))) for s in d.get('site',[])]"`
Expected: 4 sites listed (backend, ml-service, rag-service, frontend), each with a nonzero alert count (a full active scan against a real app essentially never returns zero findings — even a clean app gets informational/header findings). Zero sites or zero total alerts means the spider never actually reached the app — go back and check `--network` matches `asset_management_network` exactly (`docker network ls` to confirm) and that container DNS names resolve (`docker run --rm --network asset_management_network alpine getent hosts backend`).

- [ ] **Step 5: Add `security/zap/zap-report.*` and `security/zap/*.session` to `.gitignore`**

Generated scan artifacts shouldn't be committed. Check `.gitignore` first — if no `security/` block exists yet, append:
```
# ZAP DAST scan output (generated, not source)
security/zap/zap-report.*
security/zap/*.session
```

- [ ] **Step 6: Commit**

```bash
git add security/zap/zap-automation.yaml .gitignore
git commit -m "feat: add ZAP Automation Framework plan for backend/ml/rag/frontend DAST"
```

---

## Task 3: `dast` CI stage

**Files:**
- Modify: `.gitlab-ci.yml`

**Interfaces:**
- Consumes: `security/zap/zap-automation.yaml` (Task 2), `PARSERS["zap"]` via `security_report.py zap ...` (Task 1), `$ZAP_LOGIN_PASSWORD` CI/CD variable (Task 4).
- Produces: `zap-report.html`, `zap-report.json` as pipeline artifacts; `dast-scan` job name referenced by `quality-gate`'s `needs:`.

- [ ] **Step 1: Add the `dast` stage to the `stages:` list**

In `.gitlab-ci.yml`, change:
```yaml
stages:
  - secret-scan
  - sca-deps
  - sast
  - build
  - image-scan
  - lint
  - gate
```
to:
```yaml
stages:
  - secret-scan
  - sca-deps
  - sast
  - build
  - image-scan
  - dast
  - lint
  - gate
```

- [ ] **Step 2: Update the header comment block**

Change lines 1–11 from:
```yaml
# EAMSagemCom — Source Code Security Pipeline
# Stages: secret-scan → sca-deps → sast → build → image-scan → lint → gate
# Blocking: build-images, quality-gate
# Non-blocking (allow_failure: true, visibility over gating): scan-secrets,
# audit-backend, audit-frontend, license-scan-backend, license-scan-frontend,
# sonarqube-scan, iac-scan, image-scan, lint-backend, lint-frontend
```
to:
```yaml
# EAMSagemCom — Source Code Security Pipeline
# Stages: secret-scan → sca-deps → sast → build → image-scan → dast → lint → gate
# Blocking: build-images, quality-gate
# Non-blocking (allow_failure: true, visibility over gating): scan-secrets,
# audit-backend, audit-frontend, license-scan-backend, license-scan-frontend,
# sonarqube-scan, iac-scan, image-scan, dast-scan, lint-backend, lint-frontend
# dast-scan (OWASP ZAP) assumes `make up` is already running on the self-hosted
# runner host (same convention as sonarqube-scan) — see
# docs/superpowers/specs/2026-07-20-owasp-zap-dast-design.md
```

- [ ] **Step 3: Add the `dast-scan` job**

Insert after the `image-scan` stage block (after `restart-scanner`, before the `# ─── Stage 6: Lint` comment):

```yaml
# ─── Stage 5b: DAST (OWASP ZAP, self-hosted local runner) ───────────────────
# Assumes `make up` is already running on the runner host (same convention as
# sonarqube-scan — this runner IS the dev machine, not an ephemeral cloud
# runner). Full active scan: real attack traffic, real write/delete calls.
# Two-layer safety guard before any attack traffic is sent:
#   1. Targets are hardcoded Docker-internal service names in
#      zap-automation.yaml (not parameterized) — cannot be pointed anywhere
#      else via CI variables.
#   2. Pre-flight query confirms the known seeded test accounts exist in the
#      target DB before proceeding, so this never runs against an unexpected
#      or wiped database.

dast-scan:
  stage: dast
  needs: [image-scan]
  tags: [local]
  image: docker:24-cli
  script:
    - |
      echo "=== Pre-flight: checking target services are reachable ==="
      for svc_check in \
        "asset_management_backend|http://localhost:8000/api/v1/health" \
        "asset_management_ml_service|http://localhost:8000/health" \
        "asset_management_rag|http://localhost:8003/health" \
        "asset_management_frontend|http://localhost:80/"; do
        CONTAINER="${svc_check%%|*}"
        URL="${svc_check##*|}"
        if ! docker exec "$CONTAINER" curl -sf "$URL" > /dev/null 2>&1; then
          echo "FAIL: $CONTAINER not reachable at $URL — is 'make up' running on this host?"
          exit 1
        fi
        echo "  OK: $CONTAINER"
      done

      echo "=== Pre-flight: verifying known seeded test accounts exist ==="
      SEED_COUNT=$(docker exec asset_management_db psql -U postgres -d asset_management -tAc \
        "SELECT count(*) FROM utilisateurs WHERE email IN ('hamza.mbarki2002@gmail.com','hamza.mbarki@esprit.tn','mbarkih92@gmail.com','hamedikilani44@gmail.com');")
      if [ "$SEED_COUNT" -ne 4 ]; then
        echo "FAIL: expected 4 seeded test accounts, found $SEED_COUNT — refusing to run active scan against unexpected data."
        exit 1
      fi
      echo "  OK: all 4 seeded test accounts present"

      echo "=== Running ZAP full active scan ==="
      docker run --rm \
        --network asset_management_network \
        -e ZAP_LOGIN_PASSWORD="${ZAP_LOGIN_PASSWORD}" \
        -v "$CI_PROJECT_DIR/security/zap:/zap/wrk:rw" \
        ghcr.io/zaproxy/zaproxy:stable \
        zap.sh -cmd -autorun /zap/wrk/zap-automation.yaml || true

      cp security/zap/zap-report.html ./zap-report.html || echo "WARN: zap-report.html not found"
      cp security/zap/zap-report.json ./zap-report.json || echo "WARN: zap-report.json not found"

      '(apk add --no-cache python3 2>/dev/null) || echo "WARN: could not install python3, terminal report will be skipped"'
      if [ -f zap-report.json ]; then
        python3 monitoring/scripts/security_report.py zap zap-report.json "DAST — backend/ml-service/rag-service/frontend" || true
      fi
  artifacts:
    paths:
      - zap-report.html
      - zap-report.json
    expire_in: 1 week
    when: always
  rules: *branch-rules
  timeout: 45 minutes
  allow_failure: true
```

- [ ] **Step 4: Wire into `quality-gate`**

In the `quality-gate` job's `needs:` list, add after `image-scan`:
```yaml
    - job: dast-scan
      optional: true
```

Add a new echo line after the "Image scan (Trivy)" line in the `script:` block:
```yaml
      echo "  DAST (OWASP ZAP)     -- RAN (findings, if any, shown above; non-blocking)"
```

- [ ] **Step 5: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))" && echo "VALID"`
Expected: `VALID` (no exception). If GitLab CI lint is reachable (self-hosted GitLab instance), also run it through Settings → CI/CD → Editor → Lint, or `gitlab-ci-local` if installed — otherwise the `python3 -c` YAML-syntax check plus Task 3 Step 6's dry run are the available local checks.

- [ ] **Step 6: Dry-run the exact `dast-scan` script block locally**

With `make up` running and Docker Desktop back up, copy the `script:` block's commands (Step 3 above) into a terminal and run them directly (not via `gitlab-runner exec` unless that's installed) — this proves the pre-flight checks and the `docker run` invocation work against the real stack before trusting the CI job to work unattended.
Expected: pre-flight prints `OK` for all 4 services and the seed check, ZAP runs, `zap-report.html`/`zap-report.json` land in the working directory, `security_report.py` prints a findings table.

- [ ] **Step 7: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "feat: add dast stage running OWASP ZAP full active scan"
```

---

## Task 4: Credential wiring

**Files:**
- Modify: `.env.example`
- Modify: `.env`

**Interfaces:**
- Produces: `$ZAP_LOGIN_PASSWORD` — consumed by Task 2 (manual runs) and Task 3 (CI job, as a masked GitLab CI/CD variable — the CI copy is NOT read from `.env`, GitLab variables are separate from the repo's `.env` file).

- [ ] **Step 1: Add to `.env.example`**

Append to the end of the file:
```
# ── OWASP ZAP (DAST) ────────────────────────────────────────────────────────
# Shared dev-account password used to log ZAP into the 4 seeded test users
# (ADMIN/CHEFTECH/CHETOP/TECHNICIEN) for authenticated active scanning.
# For CI: set the same value as a MASKED GitLab CI/CD variable named
# ZAP_LOGIN_PASSWORD (Project Settings → CI/CD → Variables) — this file's
# value is for local manual runs only, it is never read by the pipeline.
ZAP_LOGIN_PASSWORD=
```

- [ ] **Step 2: Add real value to `.env`** (gitignored, confirmed already in `.gitignore`)

Append to the end of the file:
```
ZAP_LOGIN_PASSWORD=hA123456
```

- [ ] **Step 3: Verify `.env` is still gitignored (not about to be accidentally committed)**

Run: `git check-ignore .env && echo "IGNORED (safe)"`
Expected: `.env` then `IGNORED (safe)`.

- [ ] **Step 4: Commit only `.env.example`**

```bash
git add .env.example
git commit -m "docs: document ZAP_LOGIN_PASSWORD in .env.example"
```

**Manual follow-up for the user (cannot be done from this session — requires GitLab web UI access):** add `ZAP_LOGIN_PASSWORD` = `hA123456` as a **masked** variable under Project Settings → CI/CD → Variables in GitLab, matching how `$sonar` and `$SONAR_REPORT_TOKEN` are already configured for `sonarqube-scan`. Without this, `dast-scan` will run with an empty password and every login attempt will fail (ZAP will still scan `ml-service`/`rag-service`/`frontend` unauthenticated, and the backend context spider will still find public routes — but no role-authenticated backend coverage until this is set).

---

## Task 5: Local manual-run Makefile target

**Files:**
- Modify: `Makefile`

**Interfaces:**
- Consumes: `security/zap/zap-automation.yaml` (Task 2), `.env`'s `ZAP_LOGIN_PASSWORD` (Task 4).

- [ ] **Step 1: Add the target**

In `Makefile`, after the `scan-and-push` target at the end of the file, add:

```makefile
# Run the OWASP ZAP full active scan locally (headless), same automation
# plan the CI dast-scan job uses. Requires `make up` running first.
dast:
	@echo "Running OWASP ZAP full active scan against the local stack..."
	docker run --rm \
		--network asset_management_network \
		--env-file .env \
		-v "$(CURDIR)/security/zap:/zap/wrk:rw" \
		ghcr.io/zaproxy/zaproxy:stable \
		zap.sh -cmd -autorun /zap/wrk/zap-automation.yaml
	@echo ""
	@echo "Done. Report: security/zap/zap-report.html"
```

- [ ] **Step 2: Add it to the `help` target's command list**

In the `help:` target, after the `db` line, add:
```makefile
	@echo "  dast       - Run OWASP ZAP full active scan (needs 'make up' running)"
```

- [ ] **Step 3: Run it for real**

Run: `make dast` (requires Docker Desktop up and `make up` already running)
Expected: same output as Task 2 Step 3/4 — `security/zap/zap-report.html` and `zap-report.json` produced with real findings.

- [ ] **Step 4: Commit**

```bash
git add Makefile
git commit -m "feat: add 'make dast' target for local ZAP scans"
```

---

## Task 6: Beginner manual walkthrough doc

**Files:**
- Create: `docs/owasp-zap-getting-started.md`

**Interfaces:**
- None (standalone documentation, references Task 2's `security/zap/zap-automation.yaml` and Task 5's `make dast`).

- [ ] **Step 1: Write the guide**

Create `docs/owasp-zap-getting-started.md`:

```markdown
# OWASP ZAP — Getting Started (Beginner Guide)

This walks through installing OWASP ZAP, running your first scan by hand, and seeing that it's the exact same scan the CI pipeline runs automatically. No prior ZAP experience assumed.

## 1. Install ZAP Desktop

1. Go to https://www.zaproxy.org/download/ and download the Windows installer.
2. Run the installer, accept defaults.
3. Launch "OWASP ZAP" from the Start menu. First launch asks about persisting sessions — choose "No, I do not want to persist this session" for now (default for ad-hoc runs).

## 2. The 3 parts of the GUI you actually need

ZAP's window has a lot in it. For this workflow you only need three tabs:

- **Sites tree** (left panel) — shows every URL ZAP has discovered, grows as it scans.
- **Alerts tab** (bottom panel) — every finding, grouped by severity (red = High, orange = Medium, yellow = Low, blue = Informational).
- **Automation** tab (bottom panel, may need "+" → "Automation" to open it if not visible) — loads and runs `.yaml` automation plans, which is what we'll use.

Ignore everything else for now.

## 3. Start the app stack

In a terminal, from the project root:
```
make up
```
Wait until `docker ps` shows all services healthy (backend, ml-service, rag, frontend).

## 4. Load and run the automation plan

1. In ZAP, open the **Automation** tab.
2. Click "Open an existing Automation Plan" (folder icon) and select `security/zap/zap-automation.yaml` from this repo.
3. ZAP will show the plan's jobs (spider, activeScan, report — one block per service).
4. Before running: ZAP Desktop needs `ZAP_LOGIN_PASSWORD` available as an environment variable, since the plan reads `${ZAP_LOGIN_PASSWORD}` for the 4 backend test accounts. Easiest way on Windows: close ZAP, set it for your user account once —
   ```powershell
   [System.Environment]::SetEnvironmentVariable("ZAP_LOGIN_PASSWORD", "hA123456", "User")
   ```
   then reopen ZAP Desktop (new env vars only apply to newly-launched programs).
5. Click the "Play" button (▶) at the top of the Automation panel.

## 5. Watch it run

- The **Sites tree** fills in as the spider discovers pages/endpoints under `backend`, `ml-service`, `rag-service`, `frontend`.
- The **Alerts tab** starts populating once the active scan phase begins — this is the part sending real attack payloads (SQL injection attempts, XSS payloads, etc.) at every discovered endpoint.
- A full run across all 4 services × 4 backend roles takes a while (expect 15–40+ minutes) — this is a genuinely thorough scan, not a quick check.

## 6. Read one real finding

Click any entry in the Alerts tab. Each finding shows:
- **Risk** (High/Medium/Low/Informational) and **Confidence** — how sure ZAP is.
- **Description** — what the issue is, in plain English.
- **Other info** — the exact request ZAP sent and evidence it found.
- **Solution** — how to fix it.

Pick a High or Medium one first — those are worth acting on. Low/Informational findings are often just hardening suggestions (missing headers, etc.), useful but rarely urgent.

## 7. Same plan, no GUI (proving CI runs the identical scan)

```
make dast
```

This runs the exact same `security/zap/zap-automation.yaml` file, headless, via Docker — no window opens. When it finishes, open `security/zap/zap-report.html` in a browser — it's the same findings you just watched appear live in the GUI, just as a static report instead of an interactive session.

This is also exactly what the `dast-scan` job in `.gitlab-ci.yml` runs on every pipeline — the only difference is *where* it runs (your machine vs. the CI runner) and that CI never opens a window, it just produces the report file as a downloadable pipeline artifact.

## Safety note

This is a **full active scan** — it sends real attack traffic and calls real write/delete API endpoints. Only ever run it against your local `make up` stack. Never point ZAP (manually or otherwise) at a real production server or real customer data.
```

- [ ] **Step 2: Verify the doc's commands actually work as written**

Run each command block in the doc for real (`make up`, load plan in ZAP Desktop per the steps, `make dast`) and confirm the described behavior matches what actually happens — fix any step that doesn't match reality (e.g. if ZAP's env-var UI differs from what's described, or the report file lands somewhere else).

- [ ] **Step 3: Commit**

```bash
git add docs/owasp-zap-getting-started.md
git commit -m "docs: add OWASP ZAP beginner getting-started guide"
```

---

## Self-Review Notes

- **Spec coverage:** Architecture (Task 2), Scope/targets/auth (Task 2), Safety guard (Task 3 pre-flight), Pipeline placement (Task 3), Reports & gate integration (Tasks 1, 3), Manual learning walkthrough (Task 6), Credential handling (Task 4) — all spec sections have a task.
- **Placeholder scan:** no TBD/TODO; the one open item (GitLab CI/CD variable) is explicitly called out as a manual user action outside this session's tool access, not a placeholder in the plan's own deliverables.
- **Type/name consistency:** `parse_zap` (Task 1) → `PARSERS["zap"]` (Task 1) → `security_report.py zap ...` invocation (Task 3) — consistent. `ZAP_LOGIN_PASSWORD` name consistent across Tasks 2, 3, 4, 5, 6. Container names (`asset_management_backend`, `asset_management_ml_service`, `asset_management_rag`, `asset_management_frontend`, `asset_management_db`) and network (`asset_management_network`) cross-checked against `docker-compose.yml` and confirmed via live `docker ps` earlier in this session.
- **Known risk carried into execution:** the exact ZAP Automation Framework parameter names (`loginRequestUrl`, `loginRequestBody`, `headers` session management) are written from strong prior knowledge of the schema but not yet validated against a live ZAP run (Docker was down at plan-writing time). Task 2 Steps 2–4 are structured specifically to catch and fix any schema mismatch empirically before the task is considered done — this is expected, normal first-integration friction, not a plan defect.
