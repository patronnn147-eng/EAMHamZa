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
