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
