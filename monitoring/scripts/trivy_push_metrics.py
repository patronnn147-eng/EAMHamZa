#!/usr/bin/env python3
"""
trivy_push_metrics.py
Parses Trivy JSON scan output → Prometheus text format → Pushgateway

Usage:
  python3 trivy_push_metrics.py <trivy_json_file> <image_name> <pushgateway_url>

Example:
  python3 trivy_push_metrics.py trivy-eam-backend.json eam-backend:ci http://localhost:9091

Metrics exposed:
  trivy_image_vulnerabilities{image, severity}     — count per severity
  trivy_image_vulnerabilities_total{image}          — total count
  trivy_scan_timestamp_seconds{image}               — Unix timestamp of scan
  trivy_vulnerability_info{image, cve_id, package,  — 1 per CRITICAL/HIGH CVE
                           severity, installed_version, fixed_version}
"""

import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict


def _label(value: str) -> str:
    """Sanitize a string to be safe inside Prometheus label values."""
    # Keep alphanumeric, dot, dash, underscore, colon, slash (for image tags like img:ci)
    return re.sub(r'[\\"\n\r]', '_', str(value))


def build_metrics(scan_data: dict, image_name: str) -> str:
    """Convert Trivy JSON → Prometheus text format."""
    img = _label(image_name)
    severity_counts: dict[str, int] = defaultdict(int)
    cve_details: list[dict] = []

    for result in scan_data.get("Results", []):
        for vuln in result.get("Vulnerabilities") or []:
            sev = vuln.get("Severity", "UNKNOWN")
            severity_counts[sev] += 1
            if sev in ("CRITICAL", "HIGH"):
                cve_details.append({
                    "cve_id":            vuln.get("VulnerabilityID", ""),
                    "package":           vuln.get("PkgName", ""),
                    "installed_version": vuln.get("InstalledVersion", ""),
                    "fixed_version":     vuln.get("FixedVersion", "") or "none",
                    "severity":          sev,
                })

    lines: list[str] = []
    now = int(time.time())

    # ── Severity counts ──────────────────────────────────────────────────────
    lines += [
        "# HELP trivy_image_vulnerabilities Number of vulnerabilities by severity",
        "# TYPE trivy_image_vulnerabilities gauge",
    ]
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"):
        count = severity_counts.get(sev, 0)
        lines.append(f'trivy_image_vulnerabilities{{image="{img}",severity="{sev}"}} {count}')

    # ── Total count ──────────────────────────────────────────────────────────
    lines += [
        "# HELP trivy_image_vulnerabilities_total Total vulnerabilities across all severities",
        "# TYPE trivy_image_vulnerabilities_total gauge",
    ]
    total = sum(severity_counts.values())
    lines.append(f'trivy_image_vulnerabilities_total{{image="{img}"}} {total}')

    # ── Scan timestamp ────────────────────────────────────────────────────────
    lines += [
        "# HELP trivy_scan_timestamp_seconds Unix timestamp of last Trivy scan",
        "# TYPE trivy_scan_timestamp_seconds gauge",
    ]
    lines.append(f'trivy_scan_timestamp_seconds{{image="{img}"}} {now}')

    # ── Individual CVE info (CRITICAL/HIGH only — avoids label cardinality explosion) ──
    lines += [
        "# HELP trivy_vulnerability_info Individual CVE details (value=1 means present)",
        "# TYPE trivy_vulnerability_info gauge",
    ]
    seen: set[tuple] = set()
    for v in cve_details:
        key = (v["cve_id"], v["package"], img, v["severity"])
        if key in seen:
            continue
        seen.add(key)
        cve     = _label(v["cve_id"])
        pkg     = _label(v["package"])
        inst    = _label(v["installed_version"])
        fixed   = _label(v["fixed_version"])
        sev     = v["severity"]
        lines.append(
            f'trivy_vulnerability_info{{'
            f'image="{img}",cve_id="{cve}",package="{pkg}",'
            f'severity="{sev}",installed_version="{inst}",fixed_version="{fixed}"'
            f'}} 1'
        )

    return "\n".join(lines) + "\n"


def push(metrics_text: str, job: str, pushgateway_url: str) -> None:
    """HTTP POST metrics to Prometheus Pushgateway."""
    url = f"{pushgateway_url.rstrip('/')}/metrics/job/{job}"
    data = metrics_text.encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "text/plain; version=0.0.4; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[OK] Pushed to Pushgateway ({url}) — HTTP {resp.status}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"[ERROR] HTTP {exc.code} from Pushgateway: {body}", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        print(
            f"[WARN] Could not reach Pushgateway at {url}: {exc}\n"
            f"       Monitoring stack may not be running — skipping metric push.",
            file=sys.stderr,
        )
        # Exit 0: monitoring unavailability must NOT block the CI pipeline
        sys.exit(0)


def main() -> None:
    if len(sys.argv) < 4:
        print("Usage: trivy_push_metrics.py <json_file> <image_name> <pushgateway_url>")
        sys.exit(1)

    json_file        = sys.argv[1]
    image_name       = sys.argv[2]
    pushgateway_url  = sys.argv[3]

    with open(json_file) as fh:
        scan_data = json.load(fh)

    metrics = build_metrics(scan_data, image_name)

    # Print summary to CI log
    for line in metrics.splitlines():
        if line.startswith("trivy_image_vulnerabilities{") or \
           line.startswith("trivy_image_vulnerabilities_total"):
            print(f"  {line}")

    push(metrics, "trivy_image_scan", pushgateway_url)
    print(f"[DONE] {image_name} metrics pushed.")


if __name__ == "__main__":
    main()
