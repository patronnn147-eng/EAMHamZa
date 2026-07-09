"""CI config test conftest — adds monitoring/scripts to sys.path so the
reporting scripts are importable, and exposes the repo root path."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_PATH = REPO_ROOT / "monitoring" / "scripts"
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))
