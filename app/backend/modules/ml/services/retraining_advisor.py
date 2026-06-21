"""Deterministic guarded-retraining recommendation."""


def recommend_retraining(
    new_data_points: int, drift_verdict: str, min_points: int = 50
) -> dict:
    reasons = []
    if new_data_points >= min_points:
        reasons.append(f"{new_data_points} nouvelles données disponibles")
    if drift_verdict == "drifting":
        reasons.append("dérive détectée dans les capteurs")
    return {"recommended": bool(reasons), "reasons": reasons}
