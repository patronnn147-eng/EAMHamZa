"""Backend test conftest — adds app/backend to sys.path so models/services are importable."""
import sys
from pathlib import Path

BACKEND_PATH = Path(__file__).parent.parent.parent / "app" / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
