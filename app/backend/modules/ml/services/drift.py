"""Drift detection over logged predictions — PSI + mean shift. Pure, stdlib only."""

import math

SENSORS = (
    "air_temperature",
    "process_temperature",
    "rotational_speed",
    "torque",
    "tool_wear",
)
_ORDER = {"stable": 0, "watch": 1, "drifting": 2}


def population_stability_index(baseline, recent, bins: int = 10) -> float:
    if not baseline or not recent:
        return 0.0
    lo, hi = min(baseline), max(baseline)
    if hi == lo:
        return 0.0
    width = (hi - lo) / bins

    def dist(xs):
        counts = [0] * bins
        for x in xs:
            idx = int((x - lo) / width)
            idx = 0 if idx < 0 else bins - 1 if idx >= bins else idx
            counts[idx] += 1
        n = len(xs)
        return [(c / n) or 1e-6 for c in counts]

    b, r = dist(baseline), dist(recent)
    return sum((r[i] - b[i]) * math.log(r[i] / b[i]) for i in range(bins))


def compute_drift(baseline_rows, recent_rows, sensors=SENSORS) -> dict:
    if len(baseline_rows) < 5 or len(recent_rows) < 5:
        return {"verdict": "insufficient_data", "sensors": {}}
    out, worst = {}, "stable"
    for s in sensors:
        b = [r[s] for r in baseline_rows if r.get(s) is not None]
        rc = [r[s] for r in recent_rows if r.get(s) is not None]
        if len(b) < 5 or len(rc) < 5:
            continue
        psi = population_stability_index(b, rc)
        bmean = sum(b) / len(b)
        rmean = sum(rc) / len(rc)
        shift = 0.0 if bmean == 0 else (rmean - bmean) / abs(bmean) * 100
        status = "drifting" if psi >= 0.25 else "watch" if psi >= 0.1 else "stable"
        out[s] = {
            "psi": round(psi, 3),
            "mean_shift_pct": round(shift, 1),
            "status": status,
        }
        if _ORDER[status] > _ORDER[worst]:
            worst = status
    if not out:
        return {"verdict": "insufficient_data", "sensors": {}}
    return {"verdict": worst, "sensors": out}
