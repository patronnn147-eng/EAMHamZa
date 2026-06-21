"""CI gate: fail if the two model dirs diverge. Exit 1 on divergence, else 0."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # app/backend
from modules.ml.services.model_registry import check_sync

BACKEND = Path(__file__).resolve().parents[1] / "modules" / "ml" / "models"
MICRO = Path(__file__).resolve().parents[2] / "ml-microservice" / "models"

div = check_sync(str(BACKEND), str(MICRO))
if div:
    print("Model sync divergences:")
    for d in div:
        print(f"  {d['filename']}: {d['reason']}")
    sys.exit(1)
print("Models in sync.")
sys.exit(0)
