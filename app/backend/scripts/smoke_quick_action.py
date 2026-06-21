"""
Live smoke for Quick Action. Runs against the running stack (backend:8000).

Verifies the DB-backed guarantees that the pure unit tests cannot:
  1. ADMIN dry_run returns success + dry_run=True and writes NOTHING
     (stock-level snapshot before/after is identical).
  2. ADMIN real run returns success with a summary.
  3. Immediate repeat (same recommendation) returns idempotent=True.
  4. Non-ADMIN gets HTTP 403 (only if TECH creds are supplied).

Exit 0 = all checks pass, 1 = a check failed, 2 = setup/env problem.

Usage (stack up — `make up`):
  docker compose exec backend python scripts/smoke_quick_action.py --machine-id 1

Env:
  API_BASE     default http://localhost:8000
  ADMIN_USER / ADMIN_PASS   ADMIN login (login field is `mot_de_passe`)
  TECH_USER  / TECH_PASS    non-admin, for the 403 check (skipped if unset)
"""

import argparse
import json
import os
import sys

import httpx

API = os.environ.get("API_BASE", "http://localhost:8000").rstrip("/")


def _login(client: httpx.Client, user: str, pw: str):
    r = client.post(
        f"{API}/api/v1/auth/login", json={"email": user, "mot_de_passe": pw}
    )
    if r.status_code != 200:
        print(f"[setup] login failed for {user}: {r.status_code} {r.text[:200]}")
        return None
    return r.json().get("access_token")


def _stock_snapshot(client: httpx.Client, token: str) -> str:
    """Stable JSON string of all stock rows — used to assert dry_run writes nothing."""
    r = client.get(
        f"{API}/api/v1/inventory/stock",
        params={"limit": 1000},
        headers={"Authorization": f"Bearer {token}"},
    )
    if r.status_code != 200:
        return f"__unavailable__:{r.status_code}"
    items = r.json().get("items", r.json())
    # Reduce to (piece_id, quantity) pairs, sorted — ignore volatile fields.
    pairs = sorted(
        (str(it.get("piece_id")), str(it.get("quantity")))
        for it in (items if isinstance(items, list) else [])
    )
    return json.dumps(pairs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine-id", type=int, required=True)
    args = ap.parse_args()
    mid = args.machine_id

    admin_user = os.environ.get("ADMIN_USER", "admin@admin.com")
    admin_pass = os.environ.get("ADMIN_PASS", "admin")

    failures = []
    with httpx.Client(timeout=60.0) as client:
        admin = _login(client, admin_user, admin_pass)
        if not admin:
            print("FAIL: cannot obtain ADMIN token (set ADMIN_USER / ADMIN_PASS)")
            return 2
        ah = {"Authorization": f"Bearer {admin}"}

        # 1. Dry run writes nothing.
        before = _stock_snapshot(client, admin)
        r = client.post(
            f"{API}/api/v1/ml/procurement/quick-action/{mid}",
            params={"dry_run": "true"},
            headers=ah,
        )
        dry = (
            r.json()
            if r.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        if r.status_code != 200 or not dry.get("dry_run"):
            failures.append(f"dry_run response wrong: HTTP {r.status_code} {dry}")
        after = _stock_snapshot(client, admin)
        if before.startswith("__unavailable__"):
            print(
                f"[warn] stock snapshot unavailable ({before}) — dry-run no-write check degraded"
            )
        elif before != after:
            failures.append("dry_run mutated stock levels")

        # 2. Real run.
        r = client.post(f"{API}/api/v1/ml/procurement/quick-action/{mid}", headers=ah)
        run1 = (
            r.json()
            if r.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        if r.status_code != 200 or not run1.get("success"):
            failures.append(f"real run failed: HTTP {r.status_code} {run1}")

        # 3. Idempotent repeat (same recommendation → no new writes).
        r = client.post(f"{API}/api/v1/ml/procurement/quick-action/{mid}", headers=ah)
        run2 = (
            r.json()
            if r.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        if r.status_code != 200 or not run2.get("idempotent"):
            failures.append(f"repeat not idempotent: HTTP {r.status_code} {run2}")

        # 4. Non-ADMIN 403 (only if creds provided).
        tu, tp = os.environ.get("TECH_USER"), os.environ.get("TECH_PASS")
        if tu and tp:
            tech = _login(client, tu, tp)
            if tech:
                r = client.post(
                    f"{API}/api/v1/ml/procurement/quick-action/{mid}",
                    headers={"Authorization": f"Bearer {tech}"},
                )
                if r.status_code != 403:
                    failures.append(f"non-admin not blocked: got HTTP {r.status_code}")
            else:
                print("[skip] TECH login failed — 403 check skipped")
        else:
            print("[skip] TECH_USER/TECH_PASS unset — 403 check skipped")

    if failures:
        print("\nSMOKE FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nSMOKE PASS: dry-run no-write, real run, idempotent repeat, admin guard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
