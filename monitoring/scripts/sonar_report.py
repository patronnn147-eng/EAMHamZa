#!/usr/bin/env python3
"""
sonar_report.py — fetches SonarQube issues + security hotspots via the Web
API and prints a formatted terminal report.

Never fails: always exits 0. Display-only, same contract as
security_report.py — pipeline gating comes from allow_failure: true on the
GitLab CI job, not from this script.

IMPORTANT — token type:
  The scanner token ($sonar / SONAR_TOKEN) is a Project Analysis Token.
  That token can ONLY push analysis results; it returns HTTP 403 on browse
  endpoints (/api/issues/search, /api/hotspots/search).
  To enable the terminal report, create a *User Token* in SonarQube
  (My Account → Security → Generate Tokens → type: User Token) and add it
  to GitLab CI/CD variables as SONAR_REPORT_TOKEN.
  The CI passes it as the <token> arg; if absent the script falls back to
  $sonar which will 403, but the dashboard URL is still printed.

Usage:
  python3 sonar_report.py <sonar_host_url> <project_key> <token> [output_json]
"""

import json
import os
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
YELLOW = "\033[0;33m"


def _read_report_task() -> dict:
    """Read .scannerwork/report-task.txt produced by sonar-scanner."""
    path = os.path.join(".scannerwork", "report-task.txt")
    result = {}
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if "=" in line:
                    k, _, v = line.partition("=")
                    result[k.strip()] = v.strip()
    except OSError:
        pass
    return result


def _get(url: str, token: str) -> dict:
    # SonarQube 10.x+ uses Bearer token auth.
    # Note: Project Analysis Tokens return 403 on browse APIs — use a User Token.
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_issues(host: str, project_key: str, token: str) -> list:
    url = (
        f"{host.rstrip('/')}/api/issues/search"
        f"?componentKeys={project_key}&resolved=false&ps=500"
    )
    data = _get(url, token)
    return data.get("issues", [])


def fetch_hotspots(host: str, project_key: str, token: str) -> list:
    url = (
        f"{host.rstrip('/')}/api/hotspots/search"
        f"?projectKey={project_key}&ps=100"
    )
    data = _get(url, token)
    return data.get("hotspots", [])


def print_report(project_key: str, issues: list, hotspots: list) -> None:
    header = f"SONARQUBE — {project_key}"
    width = max(64, len(header) + 4)

    print("=" * width)
    print(f"  {header}")
    print("=" * width)

    # Normalize severity once — single source of truth for counting and display.
    normalized = [
        (
            issue,
            issue.get("severity", "INFO")
            if issue.get("severity", "INFO") in SEVERITY_ORDER
            else "INFO",
        )
        for issue in issues
    ]

    counts = {sev: 0 for sev in SEVERITY_ORDER}
    for _issue, nsev in normalized:
        counts[nsev] += 1
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
            for issue, nsev in normalized:
                if nsev != sev:
                    continue
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


def _print_dashboard_fallback(host: str, project_key: str, exc: Exception) -> None:
    """Print dashboard URL when the API call fails (e.g. wrong token type)."""
    task_info = _read_report_task()
    dashboard_url = task_info.get(
        "dashboardUrl",
        f"{host.rstrip('/')}/dashboard?id={project_key}",
    )
    width = 72
    print("=" * width, file=sys.stderr)
    print(f"  {YELLOW}SONARQUBE REPORT — API unavailable{RESET}", file=sys.stderr)
    print("=" * width, file=sys.stderr)
    print(f"  Error  : {exc}", file=sys.stderr)
    print(file=sys.stderr)
    if "403" in str(exc):
        print(
            f"  {YELLOW}Token type mismatch:{RESET} the scanner token ($sonar) is a\n"
            "  Project Analysis Token — it cannot call browse APIs.\n"
            "  To fix: create a User Token in SonarQube → My Account → Security\n"
            "  → Generate Tokens (type: User Token) and add it to GitLab CI/CD\n"
            "  variables as  SONAR_REPORT_TOKEN  (protected, masked).",
            file=sys.stderr,
        )
        print(file=sys.stderr)
    print(f"  {BOLD}View results in the dashboard:{RESET}", file=sys.stderr)
    print(f"  {dashboard_url}", file=sys.stderr)
    print("=" * width, file=sys.stderr)
    print(file=sys.stderr)


def main() -> None:
    if len(sys.argv) < 4:
        print(
            "Usage: sonar_report.py <host_url> <project_key> <token> [output_json]",
            file=sys.stderr,
        )
        sys.exit(0)

    host = sys.argv[1]
    project_key = sys.argv[2]
    token = sys.argv[3]
    output_json = sys.argv[4] if len(sys.argv) > 4 else None

    # Broad except is deliberate: this script's entire contract is "never
    # fail the pipeline" (see module docstring).
    try:
        issues = fetch_issues(host, project_key, token)
        hotspots = fetch_hotspots(host, project_key, token)
        print_report(project_key, issues, hotspots)

        if output_json:
            with open(output_json, "w") as fh:
                json.dump({"issues": issues, "hotspots": hotspots}, fh, indent=2)
            print(f"[sonar_report] Raw data saved to {output_json}")
    except Exception as exc:  # noqa: BLE001 — intentional, see module docstring
        _print_dashboard_fallback(host, project_key, exc)
        if output_json:
            try:
                with open(output_json, "w") as fh:
                    json.dump(
                        {"issues": [], "hotspots": [], "error": str(exc)}, fh, indent=2
                    )
            except Exception:
                pass

    sys.exit(0)


if __name__ == "__main__":
    main()
