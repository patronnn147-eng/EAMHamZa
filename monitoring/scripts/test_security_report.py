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
