"""
P3 "practice test" on NASA CMAPSS (FD001) — NOT Sagemcom data, NOT production.

Why this exists: P3's real fix needs more Sagemcom machines run to real
failure, which is calendar-gated (months). CMAPSS is a different equipment
domain (turbofan jet engines, not Sagemcom's machines) but has the one thing
our own data structurally lacks — many machines (100), each tracked
cycle-by-cycle from healthy to failure. That's exactly what's needed to
prove group-holdout + Cox/Weibull-style censoring-aware modeling generalize
before betting months of real Sagemcom data collection on the approach.
Numbers here do NOT transfer to Sagemcom's real machines — different
sensors, different physics, different failure modes. This validates the
METHOD, not a deployable number.

Uses CMAPSS's own official train/test split (not a custom one): train on
all 100 engines' full run-to-failure trajectories, score against the
official held-out test set (test_FD001.txt, each of 100 engines cut off at
a random cycle before failure) using the official ground truth
(RUL_FD001.txt) — this is the dataset's own designed benchmark task, not a
split invented for this comparison.

Run: python p3_practice_test_cmapss.py   (from this directory; expects
train_FD001.txt / test_FD001.txt / RUL_FD001.txt at the repo root)
"""
import os

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter, WeibullAFTFitter
from lifelines.utils import concordance_index
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TRAIN_PATH = os.path.join(ROOT, "train_FD001.txt")
TEST_PATH = os.path.join(ROOT, "test_FD001.txt")
RUL_PATH = os.path.join(ROOT, "RUL_FD001.txt")

COLS = (
    ["unit", "cycle", "setting1", "setting2", "setting3"]
    + [f"sensor{i}" for i in range(1, 22)]
)
RUL_CAP = 125  # standard CMAPSS convention: early-life degradation isn't
               # meaningfully predictable, capping avoids rewarding a model
               # for guessing a huge number on a barely-worn engine.


def load_raw(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=r"\s+", header=None, names=COLS)
    return df


def add_rul(train: pd.DataFrame) -> pd.DataFrame:
    max_cycle = train.groupby("unit")["cycle"].transform("max")
    train = train.copy()
    train["duration"] = (max_cycle - train["cycle"]).clip(lower=1, upper=RUL_CAP)
    train["rul_capped"] = train["duration"]
    train["event"] = 1  # every training unit runs to actual failure in FD001
    return train


def drop_constant_sensors(train: pd.DataFrame, test: pd.DataFrame, feature_cols: list) -> list:
    std = train[feature_cols].std()
    keep = [c for c in feature_cols if std[c] > 1e-6]
    dropped = [c for c in feature_cols if c not in keep]
    print(f"Dropping {len(dropped)} constant/near-constant sensors: {dropped}")
    return keep


def main():
    train = load_raw(TRAIN_PATH)
    test = load_raw(TEST_PATH)
    true_rul = pd.read_csv(RUL_PATH, sep=r"\s+", header=None, names=["RUL"])
    print(f"Train: {train['unit'].nunique()} engines, {len(train)} rows")
    print(f"Test:  {test['unit'].nunique()} engines, {len(test)} rows "
          f"(cut off before failure, official ground truth in RUL_FD001.txt)")

    train = add_rul(train)
    feature_cols = ["setting1", "setting2", "setting3"] + [f"sensor{i}" for i in range(1, 22)]
    feature_cols = drop_constant_sensors(train, test, feature_cols)

    # Official test task: last row per engine = the observation point;
    # RUL_FD001.txt's i-th value is that engine's true remaining life then.
    test_last = test.sort_values(["unit", "cycle"]).groupby("unit").tail(1).reset_index(drop=True)
    test_last["true_rul"] = true_rul["RUL"].values

    X_train, y_train = train[feature_cols], train["rul_capped"]
    X_test, y_test = test_last[feature_cols], test_last["true_rul"]

    # ── Baseline: naive point regression (same shape as today's production
    # P3 approach — a single point estimate, no censoring awareness). ──
    xgb = XGBRegressor(n_estimators=300, max_depth=5, learning_rate=0.05, random_state=42)
    xgb.fit(X_train, y_train)
    xgb_pred = xgb.predict(X_test)
    xgb_mae = mean_absolute_error(y_test, xgb_pred)
    xgb_rmse = np.sqrt(mean_squared_error(y_test, xgb_pred))
    xgb_cidx = concordance_index(y_test, xgb_pred)

    # ── Cox PH / Weibull AFT: censoring-aware, fit on the full run-to-
    # failure training trajectories (event=1 throughout — FD001 has no
    # censored training units), scored against the official held-out test
    # cutoffs the same way as the baseline. ──
    surv_cols = feature_cols + ["duration", "event"]
    cph = CoxPHFitter(penalizer=0.1)  # small penalty: 21 correlated sensors, avoids convergence issues
    cph.fit(train[surv_cols], duration_col="duration", event_col="event")
    cox_expect = cph.predict_expectation(X_test).clip(lower=0)
    cox_mae = mean_absolute_error(y_test, cox_expect)
    cox_rmse = np.sqrt(mean_squared_error(y_test, cox_expect))
    cox_cidx = concordance_index(y_test, cox_expect)

    aft = WeibullAFTFitter(penalizer=0.1)
    aft.fit(train[surv_cols], duration_col="duration", event_col="event")
    aft_expect = aft.predict_expectation(X_test).clip(lower=0)
    aft_mae = mean_absolute_error(y_test, aft_expect)
    aft_rmse = np.sqrt(mean_squared_error(y_test, aft_expect))
    aft_cidx = concordance_index(y_test, aft_expect)

    print("\n" + "=" * 70)
    print("P3 practice test — NASA CMAPSS FD001 (official train/test split)")
    print("=" * 70)
    print(f"{'Model':<28}{'C-index':>10}{'MAE':>12}{'RMSE':>12}")
    print(f"{'XGBoost (naive point)':<28}{xgb_cidx:>10.4f}{xgb_mae:>12.2f}{xgb_rmse:>12.2f}")
    print(f"{'Cox PH (censoring-aware)':<28}{cox_cidx:>10.4f}{cox_mae:>12.2f}{cox_rmse:>12.2f}")
    print(f"{'Weibull AFT (censoring-aware)':<28}{aft_cidx:>10.4f}{aft_mae:>12.2f}{aft_rmse:>12.2f}")

    best = max(cox_cidx, aft_cidx)
    verdict = "beats" if best > xgb_cidx else "does not beat"
    print(f"\nVerdict: best censoring-aware model {verdict} the naive baseline "
          f"({best:.4f} vs {xgb_cidx:.4f}) on a 100-engine, real-run-to-failure benchmark.")
    print("Reminder: this is a method check on jet-engine data, not a Sagemcom-usable number.")


if __name__ == "__main__":
    main()
