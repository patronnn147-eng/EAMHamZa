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
    with pytest.raises(SystemExit) as exc_info:
        sonar.main()
    assert exc_info.value.code == 0
    assert out_file.exists()
    saved = json.loads(out_file.read_text())
    assert len(saved["issues"]) == 2
    assert len(saved["hotspots"]) == 1


def test_main_exits_zero_on_malformed_json_response(monkeypatch, capsys):
    class BadJSONResponse:
        def read(self):
            return b"not valid json{{{"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        sonar.urllib.request, "urlopen",
        lambda req, timeout=30: BadJSONResponse()
    )
    monkeypatch.setattr(
        "sys.argv",
        ["sonar_report.py", "http://sonar.local", "eamsagemcom-phase_2", "faketoken"],
    )
    with pytest.raises(SystemExit) as exc_info:
        sonar.main()
    assert exc_info.value.code == 0


def test_print_report_does_not_drop_issues_with_unrecognized_severity(capsys):
    weird_issue = {
        "key": "issue3",
        "rule": "custom:R1",
        "severity": "UNKNOWN_SEV",
        "component": "eamsagemcom-phase_2:app/backend/weird.py",
        "line": 1,
        "message": "Unrecognized severity from a future SonarQube version",
        "type": "BUG",
    }
    sonar.print_report("eamsagemcom-phase_2", [weird_issue], [])
    out = capsys.readouterr().out
    assert "custom:R1" in out, "finding with unrecognized severity must still appear in the Findings list"
