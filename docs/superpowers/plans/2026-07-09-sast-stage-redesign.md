# SAST / Security Stage Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn every security-scanning job in `.gitlab-ci.yml` into a visibility-first, non-blocking stage with rich terminal output, while generalizing branch coverage so future `Phase_N` branches need zero yml edits.

**Architecture:** Two new shared Python reporting scripts (`monitoring/scripts/security_report.py` for JSON-based scanners, `monitoring/scripts/sonar_report.py` for SonarQube's Web API) get called from every scanning job's `script:` block after the scan runs. Every scanning job becomes `allow_failure: true` (except `build-images`, which stays hard-blocking — a broken build is not a "finding"). A YAML anchor replaces the repeated hardcoded branch-name regex.

**Tech Stack:** GitLab CI YAML, Python 3.11 (stdlib only — `json`, `urllib`, no new pip dependencies for the reporting scripts themselves), pytest (existing project convention: `tests/**/*.test.py`, `testpaths = tests`), PyYAML for config tests.

## Global Constraints

- Design source of truth: `docs/superpowers/specs/2026-07-09-sast-stage-redesign-design.md` — every decision below traces back to a `D1`–`D4` entry there.
- Test file naming: `<name>.test.py` under `tests/` (matches `pytest.ini`: `python_files = *.test.py`, `testpaths = tests`) — NOT the default `test_*.py` convention.
- No new pip/npm dependencies added to the app itself — reporting scripts use stdlib only, runnable with plain `python3`.
- `build-images` stays `allow_failure: false` — the one job in this plan that keeps hard-blocking.
- Every other scanning job (`scan-secrets`, `audit-backend`, `audit-frontend`, `license-scan-backend`, `license-scan-frontend`, `sonarqube-scan`, `iac-scan`, `image-scan`) becomes `allow_failure: true`.
- Branch rules: replace every hardcoded `$CI_COMMIT_BRANCH =~ /^(Phase_1|clean_Phase_1|main|Phase_2)$/` with the shared anchor `*branch-rules` matching `/^(main|clean_Phase_\d+|Phase_\d+)$/`.
- Reporting scripts always exit 0 — they are display-only, never a pipeline gate.

---

### Task 1: Branch rule YAML anchor

**Files:**
- Modify: `.gitlab-ci.yml:11-21` (insert anchor after `variables:` block)
- Test: `tests/cicd/branch_rules.test.py` (new)
- Test: `tests/cicd/conftest.py` (new)

**Interfaces:**
- Produces: YAML anchor `&branch-rules` referenced as `rules: *branch-rules` by every job in later tasks.

- [ ] **Step 1: Write the failing test**

Create `tests/cicd/conftest.py`:

```python
"""CI config test conftest — adds monitoring/scripts to sys.path so the
reporting scripts are importable, and exposes the repo root path."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_PATH = REPO_ROOT / "monitoring" / "scripts"
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))
```

Create `tests/cicd/branch_rules.test.py`:

```python
"""Verifies the .gitlab-ci.yml branch-rules anchor matches the intended
branch naming convention (main, clean_Phase_N, Phase_N) and rejects
anything else."""
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent.parent
CI_FILE = REPO_ROOT / ".gitlab-ci.yml"

# The exact regex the anchor must use — kept here as the single source of
# truth for what "should match" means, independent of the yml file's
# current content.
EXPECTED_PATTERN = r"^(main|clean_Phase_\d+|Phase_\d+)$"


def test_ci_file_parses_as_valid_yaml():
    with open(CI_FILE) as fh:
        data = yaml.safe_load(fh)
    assert "stages" in data


def test_branch_rules_anchor_exists_in_raw_yaml():
    raw = CI_FILE.read_text()
    assert "&branch-rules" in raw, "branch-rules anchor not found in .gitlab-ci.yml"
    assert "*branch-rules" in raw, "branch-rules anchor is never referenced"


def test_branch_regex_matches_current_and_future_phase_branches():
    pattern = re.compile(EXPECTED_PATTERN)
    for branch in ["main", "clean_Phase_1", "Phase_1", "Phase_2", "Phase_3", "Phase_47", "clean_Phase_99"]:
        assert pattern.match(branch), f"expected {branch!r} to match"


def test_branch_regex_rejects_unrelated_branches():
    pattern = re.compile(EXPECTED_PATTERN)
    for branch in ["feature/foo", "bugfix-123", "Phase_", "Phase_a", "random"]:
        assert not pattern.match(branch), f"expected {branch!r} to NOT match"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/cicd/branch_rules.test.py -v`
Expected: FAIL on `test_branch_rules_anchor_exists_in_raw_yaml` (anchor doesn't exist yet — the other two regex tests will PASS since they only test the `EXPECTED_PATTERN` constant, not the file).

- [ ] **Step 3: Add the anchor to `.gitlab-ci.yml`**

Insert immediately after the `variables:` block (after line 21, before `default:`):

```yaml
variables:
  GIT_LFS_SKIP_SMUDGE: "1"

# Shared branch/MR trigger condition. Matches "main", any "clean_Phase_N",
# and any "Phase_N" branch — so Phase_3, Phase_4, etc. get full pipeline
# coverage automatically, with zero edits to this file.
.branch-rules: &branch-rules
  - if: $CI_COMMIT_BRANCH =~ /^(main|clean_Phase_\d+|Phase_\d+)$/
  - if: $CI_PIPELINE_SOURCE == "merge_request_event"

default:
  interruptible: true
  retry:
    max: 1
    when:
      - runner_system_failure
```

Then replace **every** occurrence of the 2-line pattern:

```yaml
  rules:
    - if: $CI_COMMIT_BRANCH =~ /^(Phase_1|clean_Phase_1|main|Phase_2)$/
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

with the single line:

```yaml
  rules: *branch-rules
```

This occurs in every job: `scan-secrets`, `audit-backend`, `audit-frontend`, `sonarqube-scan`, `build-images`, `iac-scan`, `image-scan`, `push-vuln-metrics`, `lint-backend`, `lint-frontend`, `quality-gate` (11 occurrences).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/cicd/branch_rules.test.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add .gitlab-ci.yml tests/cicd/conftest.py tests/cicd/branch_rules.test.py
git commit -m "ci: generalize branch rules to Phase_N pattern via shared anchor"
```

---

### Task 2: `security_report.py` — universal terminal reporter

**Files:**
- Create: `monitoring/scripts/security_report.py`
- Test: `tests/cicd/security_report.test.py`
- Test fixtures: `tests/cicd/fixtures/gitleaks_sample.json`, `tests/cicd/fixtures/pip_audit_sample.json`, `tests/cicd/fixtures/pnpm_audit_sample.json`, `tests/cicd/fixtures/trivy_sample.json`

**Interfaces:**
- Produces: `parse_gitleaks(data) -> list[Finding]`, `parse_pip_audit(data) -> list[Finding]`, `parse_pnpm_audit(data) -> list[Finding]`, `parse_trivy(data) -> list[Finding]`, `print_report(tool: str, findings: list[Finding], label: str) -> None`, `Finding` NamedTuple with fields `(id, name, installed, fixed, severity, location)`. CLI: `python3 security_report.py <tool> <json_file> [label]`, always exits 0.

- [ ] **Step 1: Write the failing tests and fixtures**

Create `tests/cicd/fixtures/gitleaks_sample.json`:

```json
[
  {
    "RuleID": "generic-api-key",
    "File": "app/backend/core/config.py",
    "StartLine": 42,
    "EndLine": 42,
    "Match": "REDACTED",
    "Secret": "REDACTED",
    "Author": "dev",
    "Email": "dev@example.com",
    "Date": "2026-01-01T00:00:00Z",
    "Commit": "abc123",
    "Message": "wip",
    "Fingerprint": "abc123:app/backend/core/config.py:generic-api-key:42"
  }
]
```

Create `tests/cicd/fixtures/pip_audit_sample.json`:

```json
{
  "dependencies": [
    {
      "name": "requests",
      "version": "2.25.0",
      "vulns": [
        {
          "id": "PYSEC-2023-74",
          "fix_versions": ["2.31.0"],
          "description": "example vuln"
        }
      ]
    },
    {
      "name": "flask",
      "version": "2.0.0",
      "vulns": []
    }
  ]
}
```

Create `tests/cicd/fixtures/pnpm_audit_sample.json`:

```json
{
  "vulnerabilities": {
    "lodash": {
      "severity": "high",
      "range": "<4.17.21",
      "fixAvailable": { "name": "lodash", "version": "4.17.21" },
      "via": [{ "source": 1065, "title": "Prototype Pollution" }]
    },
    "minimist": {
      "severity": "critical",
      "range": "<1.2.6",
      "fixAvailable": true,
      "via": [{ "source": 1179, "title": "Prototype Pollution" }]
    }
  }
}
```

Create `tests/cicd/fixtures/trivy_sample.json`:

```json
{
  "Results": [
    {
      "Target": "eam-backend:ci (debian 13.4)",
      "Vulnerabilities": [
        {
          "VulnerabilityID": "CVE-2024-1234",
          "PkgName": "openssl",
          "InstalledVersion": "3.0.0",
          "FixedVersion": "3.0.5",
          "Severity": "CRITICAL"
        },
        {
          "VulnerabilityID": "CVE-2024-5678",
          "PkgName": "libc6",
          "InstalledVersion": "2.36",
          "FixedVersion": "",
          "Severity": "MEDIUM"
        }
      ]
    }
  ]
}
```

Create `tests/cicd/security_report.test.py`:

```python
"""Tests for monitoring/scripts/security_report.py's parsers and terminal
report formatting. conftest.py adds monitoring/scripts to sys.path."""
import json
from pathlib import Path

import pytest

import security_report as sr

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name):
    with open(FIXTURES / name) as fh:
        return json.load(fh)


def test_parse_gitleaks_marks_all_findings_critical():
    findings = sr.parse_gitleaks(_load("gitleaks_sample.json"))
    assert len(findings) == 1
    assert findings[0].severity == "CRITICAL"
    assert findings[0].id == "generic-api-key"
    assert "config.py:42" in findings[0].location


def test_parse_gitleaks_handles_empty_list():
    assert sr.parse_gitleaks([]) == []
    assert sr.parse_gitleaks(None) == []


def test_parse_pip_audit_extracts_cve_and_fix_version():
    findings = sr.parse_pip_audit(_load("pip_audit_sample.json"))
    assert len(findings) == 1
    f = findings[0]
    assert f.id == "PYSEC-2023-74"
    assert f.name == "requests"
    assert f.installed == "2.25.0"
    assert f.fixed == "2.31.0"


def test_parse_pip_audit_skips_deps_with_no_vulns():
    findings = sr.parse_pip_audit(_load("pip_audit_sample.json"))
    names = [f.name for f in findings]
    assert "flask" not in names


def test_parse_pnpm_audit_maps_severity_and_extracts_fix():
    findings = sr.parse_pnpm_audit(_load("pnpm_audit_sample.json"))
    by_name = {f.name: f for f in findings}
    assert by_name["lodash"].severity == "HIGH"
    assert by_name["lodash"].fixed == "4.17.21"
    assert by_name["minimist"].severity == "CRITICAL"
    assert by_name["minimist"].fixed == "yes (see advisory)"


def test_parse_pnpm_audit_legacy_advisories_format():
    legacy = {
        "advisories": {
            "1065": {
                "module_name": "lodash",
                "severity": "moderate",
                "vulnerable_versions": "<4.17.21",
                "patched_versions": ">=4.17.21",
            }
        }
    }
    findings = sr.parse_pnpm_audit(legacy)
    assert len(findings) == 1
    assert findings[0].name == "lodash"
    assert findings[0].severity == "MEDIUM"


def test_parse_trivy_extracts_all_fields():
    findings = sr.parse_trivy(_load("trivy_sample.json"))
    assert len(findings) == 2
    critical = [f for f in findings if f.severity == "CRITICAL"][0]
    assert critical.id == "CVE-2024-1234"
    assert critical.name == "openssl"
    assert critical.fixed == "3.0.5"
    medium = [f for f in findings if f.severity == "MEDIUM"][0]
    assert medium.fixed == "none"  # empty FixedVersion normalized to "none"


def test_print_report_shows_severity_breakdown(capsys):
    findings = sr.parse_trivy(_load("trivy_sample.json"))
    sr.print_report("trivy", findings, "eam-backend:ci")
    out = capsys.readouterr().out
    assert "eam-backend:ci" in out
    assert "CRITICAL: 1" in out
    assert "MEDIUM: 1" in out
    assert "CVE-2024-1234" in out
    assert "TOTAL: 2" in out


def test_print_report_handles_zero_findings(capsys):
    sr.print_report("trivy", [], "clean-image")
    out = capsys.readouterr().out
    assert "No findings." in out
    assert "TOTAL: 0" in out


def test_main_exits_zero_on_missing_file(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["security_report.py", "trivy", "/nonexistent/file.json"])
    with pytest.raises(SystemExit) as exc_info:
        sr.main()
    assert exc_info.value.code == 0


def test_main_exits_zero_on_unknown_tool(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["security_report.py", "unknown-tool", "x.json"])
    with pytest.raises(SystemExit) as exc_info:
        sr.main()
    assert exc_info.value.code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/cicd/security_report.test.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'security_report'`

- [ ] **Step 3: Write `monitoring/scripts/security_report.py`**

```python
#!/usr/bin/env python3
"""
security_report.py — universal terminal formatter for security scan JSON output.

Never fails: always exits 0. This script is display-only; pipeline gating
(or lack thereof) is controlled entirely by allow_failure: true on the
GitLab CI job, not by this script's exit code.

Usage:
  python3 security_report.py <tool> <json_file> [label]

  tool  : gitleaks | pip-audit | pnpm-audit | trivy
  label : optional string shown in the report header (e.g. image name)
"""

import json
import sys
from typing import NamedTuple

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]

COLOR = {
    "CRITICAL": "\033[1;31m",
    "HIGH": "\033[0;31m",
    "MEDIUM": "\033[0;33m",
    "LOW": "\033[0;34m",
    "UNKNOWN": "\033[0;37m",
}
RESET = "\033[0m"
BOLD = "\033[1m"


class Finding(NamedTuple):
    id: str
    name: str
    installed: str
    fixed: str
    severity: str
    location: str


def parse_gitleaks(data) -> list:
    findings = []
    for leak in data or []:
        findings.append(Finding(
            id=leak.get("RuleID", "unknown-rule"),
            name=leak.get("File", "unknown-file"),
            installed="-",
            fixed="-",
            severity="CRITICAL",
            location=f'{leak.get("File", "?")}:{leak.get("StartLine", "?")}',
        ))
    return findings


def parse_pip_audit(data) -> list:
    findings = []
    deps = data.get("dependencies", []) if isinstance(data, dict) else (data or [])
    for dep in deps:
        pkg = dep.get("name", "unknown")
        version = dep.get("version", "?")
        for vuln in dep.get("vulns", []) or []:
            fix_versions = vuln.get("fix_versions") or []
            findings.append(Finding(
                id=vuln.get("id", "unknown-cve"),
                name=pkg,
                installed=version,
                fixed=", ".join(fix_versions) if fix_versions else "none",
                severity="UNKNOWN",
                location="app/backend/requirements.txt",
            ))
    return findings


def _map_npm_severity(sev: str) -> str:
    return {
        "critical": "CRITICAL",
        "high": "HIGH",
        "moderate": "MEDIUM",
        "low": "LOW",
        "info": "LOW",
    }.get((sev or "").lower(), "UNKNOWN")


def parse_pnpm_audit(data: dict) -> list:
    findings = []

    vulns = data.get("vulnerabilities")
    if isinstance(vulns, dict):
        for pkg, info in vulns.items():
            fix = info.get("fixAvailable")
            if isinstance(fix, dict):
                fixed = fix.get("version", "unknown")
            elif fix is True:
                fixed = "yes (see advisory)"
            else:
                fixed = "none"
            via = info.get("via") or []
            adv_id = "advisory"
            if via and isinstance(via[0], dict):
                adv_id = str(via[0].get("source", "advisory"))
            findings.append(Finding(
                id=adv_id,
                name=pkg,
                installed=info.get("range", "?"),
                fixed=fixed,
                severity=_map_npm_severity(info.get("severity", "")),
                location="app/frontend/package.json",
            ))
        return findings

    advisories = data.get("advisories")
    if isinstance(advisories, dict):
        for adv_id, info in advisories.items():
            findings.append(Finding(
                id=str(adv_id),
                name=info.get("module_name", "unknown"),
                installed=info.get("vulnerable_versions", "?"),
                fixed=info.get("patched_versions", "none"),
                severity=_map_npm_severity(info.get("severity", "")),
                location="app/frontend/package.json",
            ))
    return findings


def parse_trivy(data: dict) -> list:
    findings = []
    for result in data.get("Results", []) or []:
        for vuln in result.get("Vulnerabilities") or []:
            findings.append(Finding(
                id=vuln.get("VulnerabilityID", "unknown-cve"),
                name=vuln.get("PkgName", "unknown"),
                installed=vuln.get("InstalledVersion", "?"),
                fixed=vuln.get("FixedVersion") or "none",
                severity=vuln.get("Severity", "UNKNOWN"),
                location=result.get("Target", "?"),
            ))
    return findings


PARSERS = {
    "gitleaks": parse_gitleaks,
    "pip-audit": parse_pip_audit,
    "pnpm-audit": parse_pnpm_audit,
    "trivy": parse_trivy,
}


def print_report(tool: str, findings: list, label: str) -> None:
    header = f"{tool.upper()} — {label}" if label else tool.upper()
    width = max(64, len(header) + 4)

    print("=" * width)
    print(f"  {header}")
    print("=" * width)

    counts = {sev: 0 for sev in SEVERITY_ORDER}
    for f in findings:
        counts[f.severity if f.severity in counts else "UNKNOWN"] += 1
    total = sum(counts.values())

    print(f"{BOLD}Severity Breakdown:{RESET}")
    parts = []
    for sev in SEVERITY_ORDER:
        c = counts[sev]
        if c:
            parts.append(f"{COLOR[sev]}{sev}: {c}{RESET}")
        else:
            parts.append(f"{sev}: {c}")
    print("  " + "   ".join(parts))
    print(f"  {BOLD}TOTAL: {total}{RESET}")
    print()

    if total == 0:
        print("No findings.")
    else:
        print(f"{BOLD}Findings:{RESET}")
        for sev in SEVERITY_ORDER:
            for f in [x for x in findings if x.severity == sev]:
                color = COLOR[f.severity]
                print(
                    f"  {color}{f.severity:<8}{RESET} "
                    f"{f.id:<20} {f.name:<25} "
                    f"{f.installed} -> {f.fixed}   [{f.location}]"
                )
    print("=" * width)
    print()


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: security_report.py <tool> <json_file> [label]", file=sys.stderr)
        sys.exit(0)

    tool = sys.argv[1]
    json_file = sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else ""

    parser = PARSERS.get(tool)
    if parser is None:
        print(f"[security_report] Unknown tool '{tool}', skipping report.", file=sys.stderr)
        sys.exit(0)

    try:
        with open(json_file) as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[security_report] Could not read {json_file}: {exc}", file=sys.stderr)
        sys.exit(0)

    findings = parser(data)
    print_report(tool, findings, label)
    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/cicd/security_report.test.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add monitoring/scripts/security_report.py tests/cicd/security_report.test.py tests/cicd/fixtures/
git commit -m "feat: add universal terminal security report formatter"
```

---

### Task 3: `sonar_report.py` — SonarQube Web API terminal reporter

**Files:**
- Create: `monitoring/scripts/sonar_report.py`
- Test: `tests/cicd/sonar_report.test.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (independent script).
- Produces: `fetch_issues(host, project_key, token) -> list[dict]`, `fetch_hotspots(host, project_key, token) -> list[dict]`, `print_report(project_key, issues, hotspots) -> None`. CLI: `python3 sonar_report.py <host_url> <project_key> <token> [output_json]`, always exits 0.

- [ ] **Step 1: Write the failing tests**

Create `tests/cicd/sonar_report.test.py`:

```python
"""Tests for monitoring/scripts/sonar_report.py. conftest.py adds
monitoring/scripts to sys.path."""
import json
import urllib.error

import pytest

import sonar_report as sonar


ISSUES_RESPONSE = {
    "total": 2,
    "issues": [
        {
            "key": "issue1",
            "rule": "python:S105",
            "severity": "CRITICAL",
            "component": "eamsagemcom-phase_2:app/backend/core/config.py",
            "line": 10,
            "message": "Hardcoded credential",
            "type": "VULNERABILITY",
        },
        {
            "key": "issue2",
            "rule": "typescript:S1481",
            "severity": "MINOR",
            "component": "eamsagemcom-phase_2:app/frontend/src/App.tsx",
            "line": 5,
            "message": "Unused variable",
            "type": "CODE_SMELL",
        },
    ],
}

HOTSPOTS_RESPONSE = {
    "paging": {"total": 1},
    "hotspots": [
        {
            "key": "hotspot1",
            "component": "eamsagemcom-phase_2:app/backend/core/security.py",
            "line": 20,
            "message": "Make sure this weak hash algorithm is not used",
            "vulnerabilityProbability": "HIGH",
        }
    ],
}


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_fetch_issues_parses_response(monkeypatch):
    monkeypatch.setattr(
        sonar.urllib.request, "urlopen",
        lambda req, timeout=30: FakeResponse(ISSUES_RESPONSE)
    )
    issues = sonar.fetch_issues("http://sonar.local", "eamsagemcom-phase_2", "faketoken")
    assert len(issues) == 2
    assert issues[0]["severity"] == "CRITICAL"


def test_fetch_hotspots_parses_response(monkeypatch):
    monkeypatch.setattr(
        sonar.urllib.request, "urlopen",
        lambda req, timeout=30: FakeResponse(HOTSPOTS_RESPONSE)
    )
    hotspots = sonar.fetch_hotspots("http://sonar.local", "eamsagemcom-phase_2", "faketoken")
    assert len(hotspots) == 1
    assert hotspots[0]["vulnerabilityProbability"] == "HIGH"


def test_print_report_shows_severity_breakdown_and_hotspots(capsys):
    sonar.print_report(
        "eamsagemcom-phase_2",
        ISSUES_RESPONSE["issues"],
        HOTSPOTS_RESPONSE["hotspots"],
    )
    out = capsys.readouterr().out
    assert "eamsagemcom-phase_2" in out
    assert "CRITICAL: 1" in out
    assert "MINOR: 1" in out
    assert "TOTAL ISSUES: 2" in out
    assert "SECURITY HOTSPOTS: 1" in out
    assert "python:S105" in out
    assert "config.py:10" in out
    assert "security.py:20" in out


def test_print_report_handles_zero_issues(capsys):
    sonar.print_report("empty-project", [], [])
    out = capsys.readouterr().out
    assert "TOTAL ISSUES: 0" in out
    assert "SECURITY HOTSPOTS: 0" in out


def test_main_exits_zero_when_api_unreachable(monkeypatch, capsys):
    def raise_url_error(req, timeout=30):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(sonar.urllib.request, "urlopen", raise_url_error)
    monkeypatch.setattr(
        "sys.argv",
        ["sonar_report.py", "http://sonar.local", "eamsagemcom-phase_2", "faketoken"],
    )
    with pytest.raises(SystemExit) as exc_info:
        sonar.main()
    assert exc_info.value.code == 0


def test_main_writes_output_json_when_given(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sonar.urllib.request, "urlopen",
        lambda req, timeout=30: FakeResponse(ISSUES_RESPONSE)
        if "issues" in req.full_url else FakeResponse(HOTSPOTS_RESPONSE)
    )
    out_file = tmp_path / "sonar-issues.json"
    monkeypatch.setattr(
        "sys.argv",
        ["sonar_report.py", "http://sonar.local", "eamsagemcom-phase_2", "faketoken", str(out_file)],
    )
    sonar.main()
    assert out_file.exists()
    saved = json.loads(out_file.read_text())
    assert len(saved["issues"]) == 2
    assert len(saved["hotspots"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/cicd/sonar_report.test.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sonar_report'`

- [ ] **Step 3: Write `monitoring/scripts/sonar_report.py`**

```python
#!/usr/bin/env python3
"""
sonar_report.py — fetches SonarQube issues + security hotspots via the Web
API and prints a formatted terminal report.

Never fails: always exits 0. Display-only, same contract as
security_report.py — pipeline gating comes from allow_failure: true on the
GitLab CI job, not from this script.

Usage:
  python3 sonar_report.py <sonar_host_url> <project_key> <token> [output_json]
"""

import base64
import json
import sys
import urllib.error
import urllib.request

SEVERITY_ORDER = ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"]
COLOR = {
    "BLOCKER": "\033[1;31m",
    "CRITICAL": "\033[0;31m",
    "MAJOR": "\033[0;33m",
    "MINOR": "\033[0;34m",
    "INFO": "\033[0;37m",
}
RESET = "\033[0m"
BOLD = "\033[1m"


def _get(url: str, token: str) -> dict:
    auth = base64.b64encode(f"{token}:".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_issues(host: str, project_key: str, token: str) -> list:
    url = f"{host.rstrip('/')}/api/issues/search?componentKeys={project_key}&resolved=false&ps=100"
    data = _get(url, token)
    return data.get("issues", [])


def fetch_hotspots(host: str, project_key: str, token: str) -> list:
    url = f"{host.rstrip('/')}/api/hotspots/search?projectKey={project_key}&ps=100"
    data = _get(url, token)
    return data.get("hotspots", [])


def print_report(project_key: str, issues: list, hotspots: list) -> None:
    header = f"SONARQUBE — {project_key}"
    width = max(64, len(header) + 4)

    print("=" * width)
    print(f"  {header}")
    print("=" * width)

    counts = {sev: 0 for sev in SEVERITY_ORDER}
    for issue in issues:
        sev = issue.get("severity", "INFO")
        counts[sev if sev in counts else "INFO"] += 1
    total = len(issues)

    print(f"{BOLD}Issue Severity Breakdown:{RESET}")
    parts = []
    for sev in SEVERITY_ORDER:
        c = counts[sev]
        if c:
            parts.append(f"{COLOR[sev]}{sev}: {c}{RESET}")
        else:
            parts.append(f"{sev}: {c}")
    print("  " + "   ".join(parts))
    print(f"  {BOLD}TOTAL ISSUES: {total}{RESET}")
    print(f"  {BOLD}SECURITY HOTSPOTS: {len(hotspots)}{RESET}")
    print()

    if issues:
        print(f"{BOLD}Issues:{RESET}")
        for sev in SEVERITY_ORDER:
            for issue in [i for i in issues if i.get("severity", "INFO") == sev]:
                color = COLOR[sev]
                rule = issue.get("rule", "unknown-rule")
                component = issue.get("component", "?").split(":")[-1]
                line = issue.get("line", "-")
                itype = issue.get("type", "?")
                message = issue.get("message", "")
                print(f"  {color}{sev:<9}{RESET} [{itype}] {rule}")
                print(f"           {component}:{line} — {message}")

    if hotspots:
        print()
        print(f"{BOLD}Security Hotspots:{RESET}")
        for h in hotspots:
            component = h.get("component", "?").split(":")[-1]
            line = h.get("line", "-")
            prob = h.get("vulnerabilityProbability", "?")
            message = h.get("message", "")
            print(f"  [{prob}] {component}:{line} — {message}")

    print("=" * width)
    print()


def main() -> None:
    if len(sys.argv) < 4:
        print("Usage: sonar_report.py <host_url> <project_key> <token> [output_json]", file=sys.stderr)
        sys.exit(0)

    host = sys.argv[1]
    project_key = sys.argv[2]
    token = sys.argv[3]
    output_json = sys.argv[4] if len(sys.argv) > 4 else None

    try:
        issues = fetch_issues(host, project_key, token)
        hotspots = fetch_hotspots(host, project_key, token)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"[sonar_report] Could not reach SonarQube API: {exc}", file=sys.stderr)
        print("[sonar_report] Skipping detailed report — check quality gate status above.", file=sys.stderr)
        sys.exit(0)

    print_report(project_key, issues, hotspots)

    if output_json:
        with open(output_json, "w") as fh:
            json.dump({"issues": issues, "hotspots": hotspots}, fh, indent=2)
        print(f"[sonar_report] Raw data saved to {output_json}")

    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/cicd/sonar_report.test.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add monitoring/scripts/sonar_report.py tests/cicd/sonar_report.test.py
git commit -m "feat: add SonarQube Web API terminal report formatter"
```

---

### Task 4: Wire `scan-secrets` (gitleaks) — JSON report, non-blocking, terminal output

**Files:**
- Modify: `.gitlab-ci.yml:32-53` (the `scan-secrets` job, after Task 1's anchor rewrite)

**Interfaces:**
- Consumes: `security_report.py` CLI (`python3 security_report.py gitleaks <json> <label>`) from Task 2.

- [ ] **Step 1: Replace the `scan-secrets` job**

gitleaks' Docker image (`zricethezav/gitleaks`) is Alpine-based — `apk` installs `python3` fast. No SARIF output for this tool (gitleaks has no JSON→SARIF convert utility, and re-running the scan a second time just to get a second format would violate "avoid duplicate scans" — JSON + terminal fully cover the requirement here).

```yaml
scan-secrets:
  stage: secret-scan
  image:
    name: zricethezav/gitleaks:v8.18.4
    entrypoint: [""]
  variables:
    GIT_DEPTH: "0"
  before_script:
    - apk add --no-cache python3 2>/dev/null || echo "WARN: could not install python3, terminal report will be skipped"
  script:
    - |
      if [ -n "$CI_MERGE_REQUEST_DIFF_BASE_SHA" ]; then
        RANGE="$CI_MERGE_REQUEST_DIFF_BASE_SHA..$CI_COMMIT_SHA"
      elif [ -n "$CI_COMMIT_BEFORE_SHA" ] && [ "$CI_COMMIT_BEFORE_SHA" != "0000000000000000000000000000000000000000" ]; then
        RANGE="$CI_COMMIT_BEFORE_SHA..$CI_COMMIT_SHA"
      else
        RANGE="$CI_COMMIT_SHA"
      fi
      gitleaks detect \
        --source . \
        --config .gitleaks.toml \
        --verbose \
        --redact \
        --log-opts="$RANGE" \
        --report-format json \
        --report-path gitleaks-report.json \
        --exit-code 0
      python3 monitoring/scripts/security_report.py gitleaks gitleaks-report.json "$CI_COMMIT_REF_NAME" || true
  artifacts:
    paths:
      - gitleaks-report.json
    expire_in: 1 week
    when: always
  rules: *branch-rules
  timeout: 10 minutes
  allow_failure: true
```

- [ ] **Step 2: Verify the yml still parses**

Run: `python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "ci: make secret scan non-blocking with terminal + JSON report"
```

---

### Task 5: Wire `audit-backend` (pip-audit) — JSON report, non-blocking, terminal output

**Files:**
- Modify: `.gitlab-ci.yml` (the `audit-backend` job)

**Interfaces:**
- Consumes: `security_report.py` CLI (`python3 security_report.py pip-audit <json> <label>`) from Task 2. Image is `python:3.11-slim` — python already present, no install step needed.

No SARIF for this job, same reasoning as Task 4's gitleaks note: `pip-audit` has no
built-in SARIF exporter, and there's no `trivy convert`-style tool to derive SARIF
from its JSON without re-running the audit — a second network round-trip that would
violate the "avoid duplicate scans" goal for a format GitLab's own security dashboard
doesn't require here. JSON + terminal output covers the "no download needed"
requirement in full.

- [ ] **Step 1: Replace the `audit-backend` job**

```yaml
audit-backend:
  stage: sca-deps
  needs: [scan-secrets]
  image: python:3.11-slim
  before_script:
    - pip install pip-audit --quiet
  script:
    - |
      pip-audit -r app/backend/requirements.txt -f json -o pip-audit-report.json || true
      python3 monitoring/scripts/security_report.py pip-audit pip-audit-report.json "app/backend/requirements.txt"
  artifacts:
    paths:
      - pip-audit-report.json
    expire_in: 1 week
    when: always
  rules: *branch-rules
  timeout: 10 minutes
  allow_failure: true
```

- [ ] **Step 2: Verify the yml still parses**

Run: `python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "ci: make backend SCA non-blocking with terminal + JSON report"
```

---

### Task 6: Wire `audit-frontend` (pnpm audit) — dedupe double-scan, non-blocking, terminal output

**Files:**
- Modify: `.gitlab-ci.yml` (the `audit-frontend` job)

**Interfaces:**
- Consumes: `security_report.py` CLI (`python3 security_report.py pnpm-audit <json> <label>`) from Task 2. Image is `node:18-alpine` — Alpine-based, `apk` for python3.

Same SARIF trade-off as Task 5: `pnpm audit` has no SARIF exporter and no
convert-from-JSON tool, so this job stays JSON + terminal only — consistent with the
"avoid duplicate scans" goal over blanket format completeness.

- [ ] **Step 1: Replace the `audit-frontend` job**

The old job ran `pnpm audit` twice (once piped to JSON with `|| true`, once with `--audit-level=high` purely to get a blocking exit code). Now that nothing needs a blocking exit code, that's one call, one JSON file, one report.

```yaml
audit-frontend:
  stage: sca-deps
  needs: [scan-secrets]
  image: node:18-alpine
  before_script:
    - apk add --no-cache python3 2>/dev/null || echo "WARN: could not install python3, terminal report will be skipped"
    - npm install -g pnpm --quiet
    - cd app/frontend && pnpm install --frozen-lockfile
  script:
    - |
      cd app/frontend
      pnpm audit --json > pnpm-audit.json || true
      python3 ../../monitoring/scripts/security_report.py pnpm-audit pnpm-audit.json "app/frontend/package.json"
  artifacts:
    paths:
      - app/frontend/pnpm-audit.json
    expire_in: 1 week
    when: always
  rules: *branch-rules
  timeout: 10 minutes
  allow_failure: true
```

- [ ] **Step 2: Verify the yml still parses**

Run: `python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "ci: dedupe pnpm audit double-scan, make non-blocking with terminal report"
```

---

### Task 7: Add `license-scan-backend` + `license-scan-frontend` jobs (new)

**Files:**
- Modify: `.gitlab-ci.yml` (insert two new jobs in the `sca-deps` stage, after `audit-frontend`)

**Interfaces:**
- Produces: `licenses-backend.json`, `licenses-frontend.json` artifacts.

Split into two jobs (backend/frontend) rather than one combined job — matches the existing `audit-backend`/`audit-frontend` split exactly, and avoids installing Node inside a Python image (or vice versa), which would slow the job down for no benefit.

- [ ] **Step 1: Add the two jobs**

Insert after the `audit-frontend` job block, before the `# ─── Stage 3: SonarQube ...` comment:

```yaml
license-scan-backend:
  stage: sca-deps
  needs: [scan-secrets]
  image: python:3.11-slim
  before_script:
    - pip install --quiet pip-licenses
    - pip install --quiet -r app/backend/requirements.txt
  script:
    - |
      echo "================================================================"
      echo "  LICENSE COMPLIANCE — Backend (Python)"
      echo "================================================================"
      pip-licenses --format=json --with-urls --output-file=licenses-backend.json
      pip-licenses --format=plain-vertical --with-urls
      echo "================================================================"
  artifacts:
    paths:
      - licenses-backend.json
    expire_in: 1 week
    when: always
  rules: *branch-rules
  timeout: 10 minutes
  allow_failure: true

license-scan-frontend:
  stage: sca-deps
  needs: [scan-secrets]
  image: node:18-alpine
  before_script:
    - npm install -g pnpm license-checker --quiet
    - cd app/frontend && pnpm install --frozen-lockfile
  script:
    - |
      cd app/frontend
      echo "================================================================"
      echo "  LICENSE COMPLIANCE — Frontend (npm)"
      echo "================================================================"
      license-checker --json --out ../../licenses-frontend.json
      license-checker --summary
      echo "================================================================"
  artifacts:
    paths:
      - licenses-frontend.json
    expire_in: 1 week
    when: always
  rules: *branch-rules
  timeout: 10 minutes
  allow_failure: true
```

- [ ] **Step 2: Verify the yml still parses**

Run: `python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "ci: add license compliance scanning (backend + frontend)"
```

---

### Task 8: Wire `sonarqube-scan` — non-blocking, issue-detail terminal output

**Files:**
- Modify: `.gitlab-ci.yml` (the `sonarqube-scan` job, and stage name `sonarqube` → `sast`)

**Interfaces:**
- Consumes: `sonar_report.py` CLI (`python3 sonar_report.py <host> <project_key> <token> [output_json]`) from Task 3. Image `sonarsource/sonar-scanner-cli` — base uncertain (JRE-based), use dual apt/apk fallback attempt.

- [ ] **Step 1: Rename the stage in the `stages:` list**

Change:
```yaml
stages:
  - secret-scan
  - sca-deps
  - sonarqube
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
  - lint
  - gate
```

- [ ] **Step 2: Replace the `sonarqube-scan` job**

```yaml
sonarqube-scan:
  stage: sast
  needs: [audit-backend, audit-frontend]
  tags: [local]
  image: sonarsource/sonar-scanner-cli:latest
  variables:
    SONAR_HOST_URL: "http://host.docker.internal:9090"
    SONAR_PROJECT_KEY: "eamsagemcom-$CI_COMMIT_REF_SLUG"
    GIT_DEPTH: "0"
  before_script:
    - (apt-get update -qq && apt-get install -y -qq python3 2>/dev/null) || (apk add --no-cache python3 2>/dev/null) || echo "WARN: could not install python3, issue-detail report will be skipped"
  script:
    - |
      sonar-scanner \
        -Dsonar.projectKey=$SONAR_PROJECT_KEY \
        -Dsonar.projectName="EAMSagemCom ($CI_COMMIT_REF_SLUG)" \
        -Dsonar.sources=app/backend,app/frontend,app/ml-microservice,app/rag-service \
        -Dsonar.exclusions=app/frontend/seo-scripts/**,**/node_modules/**,**/dist/**,**/__pycache__/**,**/.venv/**,**/*.egg-info/**,**/.ipynb_checkpoints/** \
        -Dsonar.issue.ignore.multicriteria=r3f \
        -Dsonar.issue.ignore.multicriteria.r3f.ruleKey=typescript:S6747 \
        -Dsonar.issue.ignore.multicriteria.r3f.resourceKey=app/frontend/src/modules/shared/machines/components/3d/**/*.tsx \
        -Dsonar.host.url=$SONAR_HOST_URL \
        -Dsonar.token=$sonar \
        -Dsonar.qualitygate.wait=true \
        -Dsonar.qualitygate.timeout=300 || true
      python3 monitoring/scripts/sonar_report.py "$SONAR_HOST_URL" "$SONAR_PROJECT_KEY" "$sonar" sonar-issues.json || true
  artifacts:
    paths:
      - sonar-issues.json
    expire_in: 1 week
    when: always
  rules: *branch-rules
  timeout: 15 minutes
  allow_failure: true
```

Also update the stage comment block above it:
```yaml
# ─── Stage 3: SonarQube (self-hosted, local runner only) — sole SAST tool ───
# Community Edition has no branch analysis: each branch gets its own SonarQube
# project (projectKey suffixed with $CI_COMMIT_REF_SLUG) so results don't get
# overwritten cross-branch. Dashboards live at
# http://host.docker.internal:9090/dashboard?id=eamsagemcom-<branch-slug>
# allow_failure: true — quality gate failures are surfaced via sonar_report.py's
# terminal output and the job's warning icon, not a pipeline block.
```

- [ ] **Step 3: Verify the yml still parses**

Run: `python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))" && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "ci: rename sonarqube stage to sast, make non-blocking with issue-detail terminal report"
```

---

### Task 9: Wire `iac-scan` — remove blocking exit code, add HTML report, terminal output

**Files:**
- Modify: `.gitlab-ci.yml` (the `iac-scan` job)

**Interfaces:**
- Consumes: `security_report.py` CLI (`trivy` mode) from Task 2. Image `aquasec/trivy:latest` — Alpine-based, `apk` for python3.

- [ ] **Step 1: Replace the `iac-scan` job**

```yaml
iac-scan:
  stage: build
  needs: [sonarqube-scan]
  tags: [local]
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  before_script:
    - apk add --no-cache python3 2>/dev/null || echo "WARN: could not install python3, terminal report will be skipped"
  script:
    - |
      for f in docker-compose.yml docker-compose.sonarqube.yml docker-compose.notebooks.yml; do
        BASENAME=$(echo "$f" | sed 's/\.yml$//' | sed 's/[^a-zA-Z0-9_-]/-/g')
        trivy config --severity CRITICAL,HIGH,MEDIUM,LOW --format json --output "trivy-iac-${BASENAME}.json" "$f" || true
        trivy convert --format sarif --output "trivy-iac-${BASENAME}.sarif" "trivy-iac-${BASENAME}.json" || echo "  WARN: sarif conversion failed for $f"
        trivy convert --format template --template "@contrib/html.tpl" --output "trivy-iac-${BASENAME}.html" "trivy-iac-${BASENAME}.json" || echo "  WARN: html conversion failed for $f (template may be unavailable)"
        python3 monitoring/scripts/security_report.py trivy "trivy-iac-${BASENAME}.json" "$f" || true
      done
  artifacts:
    paths:
      - trivy-iac-*.sarif
      - trivy-iac-*.json
      - trivy-iac-*.html
    expire_in: 1 week
    when: always
  rules: *branch-rules
  timeout: 10 minutes
  allow_failure: true
```

- [ ] **Step 2: Verify the yml still parses**

Run: `python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "ci: make IaC scan non-blocking, add HTML report + terminal output"
```

---

### Task 10: Wire `image-scan` — remove blocking exit code, add HTML report, terminal output

**Files:**
- Modify: `.gitlab-ci.yml` (the `image-scan` job)

**Interfaces:**
- Consumes: `security_report.py` CLI (`trivy` mode) from Task 2. Image `aquasec/trivy:latest` — same as Task 9.

- [ ] **Step 1: Replace the `image-scan` job**

```yaml
image-scan:
  stage: image-scan
  needs: [build-images]
  tags: [local]
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  before_script:
    - apk add --no-cache python3 2>/dev/null || echo "WARN: could not install python3, terminal report will be skipped"
  script:
    - |
      for img in eam-backend:ci eam-frontend:ci eam-ml-microservice:ci eam-rag-service:ci eam-ml-research:ci; do
        TAGNAME=$(echo "$img" | cut -d: -f1)
        trivy image \
          --severity CRITICAL,HIGH,MEDIUM,LOW \
          --format json \
          --output "trivy-image-${TAGNAME}.json" \
          "$img" || true
        trivy convert --format sarif --output "trivy-image-${TAGNAME}.sarif" "trivy-image-${TAGNAME}.json" || echo "  WARN: sarif conversion failed for $img"
        trivy convert --format template --template "@contrib/html.tpl" --output "trivy-image-${TAGNAME}.html" "trivy-image-${TAGNAME}.json" || echo "  WARN: html conversion failed for $img (template may be unavailable)"
        python3 monitoring/scripts/security_report.py trivy "trivy-image-${TAGNAME}.json" "$img" || true
      done
  artifacts:
    paths:
      - trivy-image-*.sarif
      - trivy-image-*.json
      - trivy-image-*.html
    expire_in: 1 week
    when: always
  rules: *branch-rules
  timeout: 15 minutes
  allow_failure: true
```

- [ ] **Step 2: Verify the yml still parses**

Run: `python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "ci: make image scan non-blocking, add HTML report + terminal output"
```

---

### Task 11: Update `quality-gate` — needs list + informational wording

**Files:**
- Modify: `.gitlab-ci.yml` (the `quality-gate` job)

**Interfaces:**
- Consumes: job names from Tasks 1-10 (`license-scan-backend`, `license-scan-frontend` added as optional needs).

- [ ] **Step 1: Replace the `quality-gate` job**

```yaml
quality-gate:
  stage: gate
  image: alpine:3.19
  needs:
    - scan-secrets
    - audit-backend
    - audit-frontend
    - sonarqube-scan
    - build-images
    - iac-scan
    - image-scan
    - job: license-scan-backend
      optional: true
    - job: license-scan-frontend
      optional: true
    - job: push-vuln-metrics
      optional: true
    - job: lint-backend
      optional: true
    - job: lint-frontend
      optional: true
  script:
    - |
      echo "All required pipeline stages completed."
      echo "  Secret scan          -- RAN (findings, if any, shown above; non-blocking)"
      echo "  Backend SCA          -- RAN (findings, if any, shown above; non-blocking)"
      echo "  Frontend SCA         -- RAN (findings, if any, shown above; non-blocking)"
      echo "  License compliance   -- RAN (informational)"
      echo "  SonarQube (SAST)     -- RAN (findings, if any, shown above; non-blocking)"
      echo "  Image build          -- PASSED (blocking)"
      echo "  IaC scan (Trivy)     -- RAN (findings, if any, shown above; non-blocking)"
      echo "  Image scan (Trivy)   -- RAN (findings, if any, shown above; non-blocking)"
      echo ""
      echo "Security jobs provide visibility, not gating — review terminal output"
      echo "and job artifacts (SARIF/JSON/HTML) above for full details."
  rules: *branch-rules
  timeout: 2 minutes
  allow_failure: false
```

- [ ] **Step 2: Verify the yml still parses**

Run: `python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "ci: update quality-gate needs + wording for non-blocking security policy"
```

---

### Task 12: Full-pipeline config regression test

**Files:**
- Create: `tests/cicd/gitlab_ci_config.test.py`

**Interfaces:**
- Consumes: the final `.gitlab-ci.yml` produced by Tasks 1-11 (no code interface — this is a config-shape test).

This test is the integration check for the whole plan — it loads the final YAML and asserts the structural properties every earlier task was supposed to produce, catching any wiring mistake made along the way (wrong `allow_failure`, missing `needs`, wrong stage name, etc).

- [ ] **Step 1: Write the test**

Create `tests/cicd/gitlab_ci_config.test.py`:

```python
"""Integration test for the final .gitlab-ci.yml: verifies stage order,
allow_failure policy, and needs graph across every security job produced
by the SAST stage redesign plan."""
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent.parent
CI_FILE = REPO_ROOT / ".gitlab-ci.yml"


def _load_config():
    with open(CI_FILE) as fh:
        return yaml.safe_load(fh)


def test_stage_order():
    config = _load_config()
    assert config["stages"] == [
        "secret-scan",
        "sca-deps",
        "sast",
        "build",
        "image-scan",
        "lint",
        "gate",
    ]


def test_security_jobs_are_non_blocking():
    config = _load_config()
    non_blocking_jobs = [
        "scan-secrets",
        "audit-backend",
        "audit-frontend",
        "license-scan-backend",
        "license-scan-frontend",
        "sonarqube-scan",
        "iac-scan",
        "image-scan",
    ]
    for job in non_blocking_jobs:
        assert job in config, f"expected job {job!r} to exist in .gitlab-ci.yml"
        assert config[job]["allow_failure"] is True, (
            f"expected {job!r} to be allow_failure: true"
        )


def test_build_images_stays_blocking():
    config = _load_config()
    assert config["build-images"]["allow_failure"] is False


def test_quality_gate_stays_blocking():
    config = _load_config()
    assert config["quality-gate"]["allow_failure"] is False


def test_sonarqube_scan_is_in_sast_stage():
    config = _load_config()
    assert config["sonarqube-scan"]["stage"] == "sast"


def test_license_scan_jobs_are_in_sca_deps_stage():
    config = _load_config()
    assert config["license-scan-backend"]["stage"] == "sca-deps"
    assert config["license-scan-frontend"]["stage"] == "sca-deps"


def test_quality_gate_needs_includes_license_scan_optionally():
    config = _load_config()
    needs = config["quality-gate"]["needs"]
    optional_job_names = {
        n["job"] for n in needs if isinstance(n, dict) and n.get("optional")
    }
    assert "license-scan-backend" in optional_job_names
    assert "license-scan-frontend" in optional_job_names


def test_every_job_uses_the_shared_branch_rules_anchor():
    raw = CI_FILE.read_text()
    # Every job's "rules:" line should be the one-line anchor reference,
    # not a re-inlined 2-line if-list (that would defeat the point of
    # the anchor and silently drift out of sync).
    assert "rules:\n    - if: $CI_COMMIT_BRANCH" not in raw, (
        "found an inlined rules block — should reference *branch-rules instead"
    )


def test_all_scan_jobs_reference_security_report_or_sonar_report():
    config = _load_config()
    trivy_and_scan_jobs = ["scan-secrets", "audit-backend", "audit-frontend", "iac-scan", "image-scan"]
    for job in trivy_and_scan_jobs:
        script_text = str(config[job]["script"])
        assert "security_report.py" in script_text, f"{job} should call security_report.py"

    sonar_script = str(config["sonarqube-scan"]["script"])
    assert "sonar_report.py" in sonar_script
```

- [ ] **Step 2: Run the test**

Run: `python -m pytest tests/cicd/gitlab_ci_config.test.py -v`
Expected: PASS (9 tests). If any fail, go back to the relevant task above and fix the yml before proceeding — this test is the final check that all ten prior tasks wired together correctly.

- [ ] **Step 3: Run the full test suite for this plan**

Run: `python -m pytest tests/cicd/ -v`
Expected: PASS (all tests from Tasks 1, 2, 3, and 12 — approximately 29 tests total)

- [ ] **Step 4: Commit**

```bash
git add tests/cicd/gitlab_ci_config.test.py
git commit -m "test: add full-pipeline config regression test for SAST redesign"
```

---

### Task 13: Update project memory

**Files:**
- Modify: `C:\Users\Admin\.claude\projects\C--Users-Admin-Downloads-EAM-EAMSagemCom\memory\devops-phase-status.md`

**Interfaces:** None — documentation/memory hygiene only, no code interface.

This corrects the stale claim in memory ("all severities block, no suppression mechanism... user's deliberate choice") now that the policy has been explicitly reversed, so a future session doesn't act on outdated info.

- [ ] **Step 1: Append a correction section**

Add to the end of `devops-phase-status.md`:

```markdown

**Correction 2026-07-09:** the "all severities block, no suppression" policy from
2026-07-06 was explicitly reversed. Security scanning stage (secret-scan, sca-deps,
sast, iac-scan, image-scan) is now visibility-first: every scanning job is
`allow_failure: true` except `build-images` and `quality-gate`. Reporting happens via
two new shared scripts, `monitoring/scripts/security_report.py` (JSON-based scanners:
gitleaks/pip-audit/pnpm-audit/trivy) and `monitoring/scripts/sonar_report.py`
(SonarQube Web API). Full design: [[sast-stage-redesign]] — see
`docs/superpowers/specs/2026-07-09-sast-stage-redesign-design.md` and
`docs/superpowers/plans/2026-07-09-sast-stage-redesign.md`. Semgrep is fully removed
(`.semgrep/`, `.semgrepignore` deleted) — SonarQube CE is the sole SAST tool, stage
renamed `sonarqube` → `sast`. Branch rules generalized to a `Phase_N` regex pattern
(YAML anchor `&branch-rules`) so future phase branches need no yml edits. License
compliance scanning added (`license-scan-backend`, `license-scan-frontend`,
non-blocking, informational).
```

- [ ] **Step 2: Verify the correction is present**

Run: `grep -q "Correction 2026-07-09" "C:/Users/Admin/.claude/projects/C--Users-Admin-Downloads-EAM-EAMSagemCom/memory/devops-phase-status.md" && echo OK`
Expected: `OK`

- [ ] **Step 3: No commit needed** — memory files live outside the git repo, this step is complete once the file is saved.

---

## Post-Plan Manual Verification (not automated — requires the real GitLab runner)

After all 13 tasks are committed and pushed to `Phase_2`:

1. Confirm every security job shows an orange warning icon (not red X) in the GitLab pipeline view, even when findings exist.
2. Open a job log (e.g. `image-scan`) and confirm the terminal shows severity breakdown + CVE table without needing to download an artifact.
3. Confirm `quality-gate` passes even with CRITICAL findings present upstream.
4. Confirm `license-scan-backend` / `license-scan-frontend` run and print a license table.
5. Rename/create a test branch `Phase_3` (or `clean_Phase_3`), push a trivial commit, and confirm the full pipeline triggers without any `.gitlab-ci.yml` edit.
6. Check the SonarQube dashboard at `http://host.docker.internal:9090/dashboard?id=eamsagemcom-phase_2` — confirm issues/hotspots match what `sonar_report.py` printed in the job log.
