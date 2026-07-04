import os

from sqlalchemy import create_engine, text
import pandas as pd

# Ad-hoc analysis script (not part of the app, not run in CI).
# Read the DB connection string from the environment instead of hardcoding
# credentials in source; falls back to the local dev default for convenience.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/asset_management"
)
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # 1. Get all unique sub-zones to identify the CMS lines
    result = conn.execute(text("SELECT DISTINCT sous_zone FROM machines"))
    zones = [r[0] for r in result.fetchall()]
    print("--- ALL SUB-ZONES ---")
    for z in sorted(zones):
        print(z)

    # 2. Count current totals
    m_total = conn.execute(text("SELECT count(*) FROM machines")).scalar()
    i_total = conn.execute(text("SELECT count(*) FROM ordres_travail")).scalar()
    print(f"\n--- CURRENT TOTALS ---")
    print(f"Total Machines: {m_total}")
    print(f"Total Interventions: {i_total}")

    # 3. Simulate focus on LINE 1 and 2
    # Search for variations of "LINE 1" and "LINE 2"
    target_lines = [z for z in zones if "LINE 1" in z or "LINE 2" in z]
    print(f"\n--- DETECTED TARGET LINES ---")
    for line in target_lines:
        print(line)

    if target_lines:
        kept_m = conn.execute(text("SELECT count(*) FROM machines WHERE sous_zone IN :lines"), {"lines": tuple(target_lines)}).scalar()
        print(f"\nMachines to KEEP: {kept_m}")
        print(f"Machines to DELETE: {m_total - kept_m}")
