#!/usr/bin/env python3
"""
zap_push_metrics.py
Parses OWASP ZAP JSON report → Prometheus text format → Pushgateway

Usage:
  python3 zap_push_metrics.py <zap_report_json> <pushgateway_url>

Example:
  python3 zap_push_metrics.py security/zap/zap-report.json http://localhost:9091

Metrics exposed:
  zap_site_alerts{site, severity}          — count of alerts per severity per site
  zap_site_alerts_total{site}               — total alert count per site
  zap_scan_timestamp_seconds{site}          — Unix timestamp of scan
  zap_alert_info{site, plugin_id, alert_name, severity, cwe_id} — 1 per
      HIGH/MEDIUM/LOW alert (informational excluded, avoids cardinality
      explosion — same convention as trivy_push_metrics.py's CRITICAL/HIGH-only
      detail metric)
"""

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict


def _label(value: str) -> str:
    """Sanitize a string to be safe inside Prometheus label values."""
    return re.sub(r'[\\"\n\r]', '_', str(value))


def _map_severity(riskdesc: str) -> str:
    # riskdesc looks like "High (Medium)" — risk level, then confidence in parens.
    level = (riskdesc or "").split(" ")[0].strip().lower()
    return {
        "high": "HIGH",
        "medium": "MEDIUM",
        "low": "LOW",
        "informational": "UNKNOWN",
    }.get(level, "UNKNOWN")


def build_metrics(data: dict) -> str:
    """Convert ZAP JSON report → Prometheus text format."""
    lines: list[str] = []
    now = int(time.time())

    sites = data.get("site", []) or []

    site_severity_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    alert_details: list[dict] = []

    for site in sites:
        site_name = _label(site.get("@name", "unknown-site"))
        for alert in site.get("alerts", []) or []:
            sev = _map_severity(alert.get("riskdesc", ""))
            site_severity_counts[site_name][sev] += 1
            if sev in ("HIGH", "MEDIUM", "LOW"):
                alert_details.append({
                    "site": site_name,
                    "plugin_id": alert.get("pluginid", "unknown-plugin"),
                    "alert_name": alert.get("alert", alert.get("name", "unknown-alert")),
                    "severity": sev,
                    "cwe_id": alert.get("cweid", "-1"),
                })

    # ── Severity counts per site ────────────────────────────────────────────
    lines += [
        "# HELP zap_site_alerts Number of ZAP alerts by severity per site",
        "# TYPE zap_site_alerts gauge",
    ]
    for site_name, counts in site_severity_counts.items():
        for sev in ("HIGH", "MEDIUM", "LOW", "UNKNOWN"):
            count = counts.get(sev, 0)
            lines.append(f'zap_site_alerts{{site="{site_name}",severity="{sev}"}} {count}')

    # ── Total per site ───────────────────────────────────────────────────────
    lines += [
        "# HELP zap_site_alerts_total Total ZAP alerts across all severities per site",
        "# TYPE zap_site_alerts_total gauge",
    ]
    for site_name, counts in site_severity_counts.items():
        total = sum(counts.values())
        lines.append(f'zap_site_alerts_total{{site="{site_name}"}} {total}')

    # ── Scan timestamp ──────────────────────────────────────────────────────
    lines += [
        "# HELP zap_scan_timestamp_seconds Unix timestamp of last ZAP scan",
        "# TYPE zap_scan_timestamp_seconds gauge",
    ]
    for site_name in site_severity_counts:
        lines.append(f'zap_scan_timestamp_seconds{{site="{site_name}"}} {now}')

    # ── Individual alert info (HIGH/MEDIUM/LOW only) ────────────────────────
    lines += [
        "# HELP zap_alert_info Individual ZAP alert details (value=1 means present)",
        "# TYPE zap_alert_info gauge",
    ]
    seen: set[tuple] = set()
    for a in alert_details:
        key = (a["site"], a["plugin_id"])
        if key in seen:
            continue
        seen.add(key)
        plugin_id  = _label(a["plugin_id"])
        alert_name = _label(a["alert_name"])
        cwe_id     = _label(a["cwe_id"])
        lines.append(
            f'zap_alert_info{{'
            f'site="{a["site"]}",plugin_id="{plugin_id}",alert_name="{alert_name}",'
            f'severity="{a["severity"]}",cwe_id="{cwe_id}"'
            f'}} 1'
        )

    return "\n".join(lines) + "\n"


def push(metrics_text: str, job: str, pushgateway_url: str, instance: str) -> None:
    """HTTP POST metrics to Prometheus Pushgateway."""
    encoded_instance = urllib.parse.quote(instance, safe="")
    url = f"{pushgateway_url.rstrip('/')}/metrics/job/{job}/instance/{encoded_instance}"
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
    if len(sys.argv) < 3:
        print("Usage: zap_push_metrics.py <zap_report_json> <pushgateway_url>")
        sys.exit(1)

    json_file       = sys.argv[1]
    pushgateway_url = sys.argv[2]

    with open(json_file) as fh:
        data = json.load(fh)

    metrics = build_metrics(data)

    for line in metrics.splitlines():
        if line.startswith("zap_site_alerts{") or line.startswith("zap_site_alerts_total"):
            print(f"  {line}")

    push(metrics, "zap_dast_scan", pushgateway_url, "zap")
    print("[DONE] ZAP DAST metrics pushed.")


if __name__ == "__main__":
    main()
