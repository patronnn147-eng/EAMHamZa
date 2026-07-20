"""
Phase 4.2 prototype: Cox PH / Weibull AFT for P3 RUL, explicitly modeling
right-censoring, vs. a naive regression baseline that treats every duration
as fully observed (today's actual production approach).

Not wired into the retrain pipeline or served by ml-microservice — this is
the "prototype ... compare C-index vs baseline" step from the P1-P7 roadmap
doc (Phase 4.2), a standalone research script (lifelines isn't a backend
dependency; adding it there is a separate decision once/if this prototype
earns its keep).

Reuses the exact machine/cycle/RUL construction from p3_lstm_hybrid_rul.ipynb
(100 synthetic machines x 100 cycles off ai4i2020.csv, train<70, test>=80)
so the C-index numbers here are directly comparable to that notebook's
recorded XGBoost-baseline C-index, not a new incomparable benchmark.

Key difference from the existing RUL target: every row here also gets an
explicit `event` flag (1 = machine actually failed at that duration, 0 =
still running at window end / right-censored). The naive baseline ignores
this distinction (treats censored durations as if they were the true time-
to-failure); Cox/Weibull are built to use it.

Run: python p3_cox_weibull_prototype.py   (from this directory)
"""
import os
import sys

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter, WeibullAFTFitter
from lifelines.utils import concordance_index
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ml_problems.shared.feature_engineering import SENSOR_COLS  # noqa: E402

CSV_PATH = os.path.join(ROOT, "ai4i2020.csv")
N_MACHINES = 100
TRAIN_MACHINES = 70          # machine_id < 70  -> train (matches LSTM notebook)
TEST_MACHINES_START = 80     # machine_id >= 80 -> test  (matches LSTM notebook)


def build_dataset() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    cycles_per_machine = len(df) // N_MACHINES
    df["machine_id"] = np.arange(len(df)) // cycles_per_machine
    df["cycle"] = np.arange(len(df)) % cycles_per_machine

    durations, events = [], []
    for mid in df["machine_id"].unique():
        mask = (df["machine_id"] == mid).values
        sub = df.loc[mask]
        fail_cycles = sub["cycle"][sub["Machine failure"] == 1].tolist()
        for cyc in sub["cycle"]:
            future_fail = [f for f in fail_cycles if f >= cyc]
            if future_fail:
                durations.append(future_fail[0] - cyc)
                events.append(1)
            else:
                durations.append(cycles_per_machine - 1 - cyc)
                events.append(0)  # right-censored: still running at window end
    df["duration"] = durations
    df["event"] = events
    df["duration"] = df["duration"].clip(lower=1)  # lifelines requires duration > 0
    return df


def main():
    df = build_dataset()
    train = df[df["machine_id"] < TRAIN_MACHINES]
    test = df[df["machine_id"] >= TEST_MACHINES_START]

    n_censored_train = int((train["event"] == 0).sum())
    print(f"Train rows: {len(train)} ({n_censored_train} censored, "
          f"{n_censored_train / len(train):.1%})")
    print(f"Test rows:  {len(test)}")

    cols = SENSOR_COLS + ["duration", "event"]
    # XGBoost rejects '[', ']', '<' in feature names (same fix as
    # ml_retraining.py's xgb_features derivation) — lifelines doesn't care,
    # so only the XGBoost baseline needs the safe-name columns.
    safe_cols = [c.replace("[", "").replace("]", "").replace("<", "").strip() for c in SENSOR_COLS]
    train_xgb = train[SENSOR_COLS].copy()
    train_xgb.columns = safe_cols
    test_xgb = test[SENSOR_COLS].copy()
    test_xgb.columns = safe_cols

    # ── Baseline: naive regression, censoring ignored (today's actual
    # production approach — a censored "still running" row is fed to the
    # regressor as if `duration` were its true, fully-observed RUL). ──
    xgb = XGBRegressor(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42)
    xgb.fit(train_xgb, train["duration"])
    xgb_pred = xgb.predict(test_xgb)
    baseline_mae = mean_absolute_error(test["duration"], xgb_pred)
    baseline_r2 = r2_score(test["duration"], xgb_pred)
    baseline_cidx = concordance_index(test["duration"], xgb_pred, test["event"])

    # ── Cox PH: explicit hazard model, uses `event` to distinguish observed
    # failures from censored survivors instead of averaging them together. ──
    cph = CoxPHFitter()
    cph.fit(train[cols], duration_col="duration", event_col="event")
    cox_cidx = cph.score(test[cols], scoring_method="concordance_index")

    # ── Weibull AFT: parametric alternative, same censoring-aware fit. ──
    aft = WeibullAFTFitter()
    aft.fit(train[cols], duration_col="duration", event_col="event")
    aft_cidx = aft.score(test[cols], scoring_method="concordance_index")

    print("\n" + "=" * 60)
    print("P3 RUL - censoring-aware vs. naive baseline (test = machines 80-99)")
    print("=" * 60)
    print(f"{'Model':<28}{'C-index':>10}{'MAE (naive-target)':>22}")
    print(f"{'XGBoost (naive, censoring-blind)':<28}{baseline_cidx:>10.4f}{baseline_mae:>22.2f}")
    print(f"{'Cox PH (censoring-aware)':<28}{cox_cidx:>10.4f}{'n/a':>22}")
    print(f"{'Weibull AFT (censoring-aware)':<28}{aft_cidx:>10.4f}{'n/a':>22}")
    print(f"\nBaseline R2 (naive target, for reference): {baseline_r2:.4f}")

    best_censoring_aware = max(cox_cidx, aft_cidx)
    verdict = "beats" if best_censoring_aware > baseline_cidx else "does not beat"
    print(f"\nVerdict: best censoring-aware model {verdict} the naive baseline "
          f"({best_censoring_aware:.4f} vs {baseline_cidx:.4f}).")


if __name__ == "__main__":
    main()
