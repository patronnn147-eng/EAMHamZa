"""
Root conftest.py — makes `app.ml_microservice` importable.

The directory on disk is `app/ml-microservice/` (hyphen), which Python
cannot import directly. This conftest registers a module alias so that
`import app.ml_microservice` resolves to the hyphenated directory.
"""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).parent
ML_MICROSERVICE_PATH = ROOT / "app" / "ml-microservice"


def _register_ml_microservice_alias():
    """Register app.ml_microservice as an alias for app/ml-microservice."""
    # Ensure 'app' package is importable (it has an __init__.py already)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    # Create a virtual package 'app.ml_microservice' pointing at the real directory
    if "app.ml_microservice" not in sys.modules:
        pkg = types.ModuleType("app.ml_microservice")
        pkg.__path__ = [str(ML_MICROSERVICE_PATH)]
        pkg.__package__ = "app.ml_microservice"
        pkg.__spec__ = None
        sys.modules["app.ml_microservice"] = pkg

    # Register subpackages that tests need
    for subpkg in ("src", "src.core"):
        full_name = f"app.ml_microservice.{subpkg}"
        if full_name not in sys.modules:
            parts = subpkg.split(".")
            dir_path = ML_MICROSERVICE_PATH.joinpath(*parts)
            mod = types.ModuleType(full_name)
            mod.__path__ = [str(dir_path)]
            mod.__package__ = full_name
            mod.__spec__ = None
            sys.modules[full_name] = mod


_register_ml_microservice_alias()
