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
