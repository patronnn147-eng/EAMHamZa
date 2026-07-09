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
