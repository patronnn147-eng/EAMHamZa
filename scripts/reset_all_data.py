#!/usr/bin/env python3
"""
NUCLEAR RESET — deletes ALL data from PostgreSQL and MinIO.
Reads connection info from .env in project root.

Usage:
    python scripts/reset_all_data.py            # dry-run (shows what would be deleted)
    python scripts/reset_all_data.py --confirm  # actually deletes everything
"""

import argparse
import os
import sys
from pathlib import Path

# ── Load .env ─────────────────────────────────────────────────────────────────

def load_env(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env

ROOT = Path(__file__).resolve().parent.parent
env_vars = load_env(ROOT / ".env")

# Override with real env if set
def cfg(key: str, default: str = "") -> str:
    return os.environ.get(key) or env_vars.get(key) or default

# ── Config ────────────────────────────────────────────────────────────────────

PG_HOST     = cfg("POSTGRES_HOST", "localhost")
PG_PORT     = int(cfg("POSTGRES_PORT", "5432"))
PG_USER     = cfg("POSTGRES_USER", "postgres")
PG_PASSWORD = cfg("POSTGRES_PASSWORD", "postgres")
PG_DB       = cfg("POSTGRES_DB", "asset_management")

MINIO_ENDPOINT = cfg("OSS_SERVICE_URL", "localhost:9000")
MINIO_USER     = cfg("MINIO_ROOT_USER", "minioadmin")
MINIO_PASSWORD = cfg("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKETS  = ["attachments", "rag-docs"]

# Strip http/https prefix from endpoint if present
for prefix in ("http://", "https://"):
    if MINIO_ENDPOINT.startswith(prefix):
        MINIO_ENDPOINT = MINIO_ENDPOINT[len(prefix):]
        break

MINIO_SECURE = False  # local MinIO — no TLS

# ── Helpers ───────────────────────────────────────────────────────────────────

def banner(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")

def info(msg: str):  print(f"  [INFO]  {msg}")
def ok(msg: str):    print(f"  [OK]    {msg}")
def warn(msg: str):  print(f"  [WARN]  {msg}")
def err(msg: str):   print(f"  [ERROR] {msg}", file=sys.stderr)

# ── PostgreSQL reset ──────────────────────────────────────────────────────────

def reset_postgres(dry_run: bool):
    banner("PostgreSQL — truncate all tables")
    try:
        import psycopg2
    except ImportError:
        err("psycopg2 not installed. Run: pip install psycopg2-binary")
        sys.exit(1)

    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        user=PG_USER, password=PG_PASSWORD,
        dbname=PG_DB
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Fetch all user tables in public schema (excludes alembic_version)
    cur.execute("""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename != 'alembic_version'
        ORDER BY tablename;
    """)
    tables = [row[0] for row in cur.fetchall()]

    if not tables:
        warn("No tables found — database might already be empty.")
        conn.close()
        return

    info(f"Tables found: {len(tables)}")
    for t in tables:
        info(f"  - {t}")

    if dry_run:
        warn("DRY-RUN: no changes made. Pass --confirm to delete.")
        conn.close()
        return

    # TRUNCATE all tables in one shot with CASCADE to handle FK constraints
    table_list = ", ".join(f'"{t}"' for t in tables)
    cur.execute(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE;")
    ok(f"Truncated {len(tables)} tables (RESTART IDENTITY CASCADE).")

    cur.close()
    conn.close()

# ── MinIO reset ───────────────────────────────────────────────────────────────

def reset_minio(dry_run: bool):
    banner("MinIO — delete all objects in all buckets")
    try:
        from minio import Minio
        from minio.error import S3Error
    except ImportError:
        err("minio not installed. Run: pip install minio")
        sys.exit(1)

    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_USER,
        secret_key=MINIO_PASSWORD,
        secure=MINIO_SECURE,
    )

    for bucket in MINIO_BUCKETS:
        info(f"Bucket: {bucket}")
        try:
            exists = client.bucket_exists(bucket)
        except Exception as e:
            warn(f"  Cannot reach bucket '{bucket}': {e}")
            continue

        if not exists:
            warn(f"  Bucket '{bucket}' does not exist — skipping.")
            continue

        # List all objects including versions
        objects = list(client.list_objects(bucket, recursive=True))
        info(f"  Objects: {len(objects)}")

        if not objects:
            ok(f"  Bucket '{bucket}' already empty.")
            continue

        for obj in objects:
            info(f"    {obj.object_name}")

        if dry_run:
            warn(f"  DRY-RUN: would delete {len(objects)} objects.")
            continue

        # Delete all objects
        from minio.deleteobjects import DeleteObject
        delete_list = [DeleteObject(obj.object_name) for obj in objects]
        errors = list(client.remove_objects(bucket, delete_list))
        if errors:
            for e in errors:
                err(f"  Delete error: {e}")
        else:
            ok(f"  Deleted {len(delete_list)} objects from '{bucket}'.")

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Nuclear reset — wipes DB and S3 buckets.")
    parser.add_argument("--confirm", action="store_true",
                        help="Actually delete. Without this flag, runs as dry-run.")
    args = parser.parse_args()

    dry_run = not args.confirm

    print()
    if dry_run:
        print("  *** DRY-RUN MODE — no data will be deleted ***")
        print("  *** Pass --confirm to actually delete everything ***")
    else:
        print("  *** WARNING: THIS WILL PERMANENTLY DELETE ALL DATA ***")
        answer = input("  Type YES to continue: ").strip()
        if answer != "YES":
            print("  Aborted.")
            sys.exit(0)

    reset_postgres(dry_run)
    reset_minio(dry_run)

    banner("Done")
    if dry_run:
        print("  Re-run with --confirm to execute.")
    else:
        print("  All data deleted. Run 'make up' to start fresh.")
        print("  Alembic schema is preserved — migrations won't re-run.")
        print("  To also reset schema: docker compose down -v && make up")

if __name__ == "__main__":
    main()
