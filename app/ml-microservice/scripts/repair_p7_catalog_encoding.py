"""Repair mojibake in the P7 parts vocabulary baked into ml_model_p7_parts_demand.pkl.

Root cause: app/ml-microservice/ml_research/p7_parts_demand.ipynb read
db_ml_training/*.csv with encoding='latin-1' even though those files are UTF-8,
then lowercased the resulting strings. So a byte pair like C3 AA ("ê") became
U+00C3 U+00AA ("Ã" + "ª") and the lowercase pass turned the lead byte into
U+00E3 ("ã") — which is why a plain .encode('latin-1').decode('utf-8') repair
fails on the stored strings.

This script inverts that transformation in place. It only rewrites text labels;
no numeric model parameter is touched, so P7 does not need retraining. The
notebook's read encoding is fixed separately so future retrains stay clean.

Usage:
    python repair_p7_catalog_encoding.py --check      # report only, write nothing
    python repair_p7_catalog_encoding.py --apply      # rewrite the pkl(s)
"""

import argparse
import pickle
import shutil
from pathlib import Path

# Both copies must stay in sync (see CLAUDE.md "Model pkl Rules").
PKL_PATHS = [
    Path(__file__).resolve().parents[1] / "models" / "ml_model_p7_parts_demand.pkl",
    Path(__file__).resolve().parents[3]
    / "app" / "backend" / "modules" / "ml" / "models" / "ml_model_p7_parts_demand.pkl",
]

CONTINUATION = range(0x80, 0xC0)


def repair_text(s: str) -> str:
    """Undo (utf-8 bytes -> latin-1 decode -> lower) for one string.

    Walks the string looking for a lead byte followed by UTF-8 continuation
    bytes. A lead byte may have been lowercased (0xC0-0xDE -> 0xE0-0xFE), so
    both the literal value and value-0x20 are candidates. The first candidate
    that yields a valid UTF-8 decode wins; anything else is passed through
    untouched, which makes the function safe to run on already-clean text.
    """
    if not isinstance(s, str) or all(ord(c) < 0x80 for c in s):
        return s

    out = []
    i = 0
    n = len(s)
    while i < n:
        code = ord(s[i])
        if code < 0x80 or code > 0xFF:
            out.append(s[i])
            i += 1
            continue

        # Collect the following continuation bytes.
        j = i + 1
        cont = []
        while j < n and 0x80 <= ord(s[j]) <= 0xBF and len(cont) < 3:
            cont.append(ord(s[j]))
            j += 1

        if not cont:
            out.append(s[i])
            i += 1
            continue

        decoded = None
        # Try the byte as-is first, then as a lowercased lead byte.
        for lead in (code, code - 0x20):
            if lead < 0xC0 or lead > 0xF4:
                continue
            # A 2-byte lead takes 1 continuation, 3-byte takes 2, 4-byte takes 3.
            width = 1 if lead < 0xE0 else (2 if lead < 0xF0 else 3)
            if len(cont) < width:
                continue
            try:
                decoded = bytes([lead] + cont[:width]).decode("utf-8")
                i = i + 1 + width
                break
            except UnicodeDecodeError:
                continue

        if decoded is None:
            out.append(s[i])
            i += 1
        else:
            out.append(decoded)

    return "".join(out)


def repair_obj(obj):
    """Recursively repair every string inside dicts/lists/tuples."""
    if isinstance(obj, str):
        return repair_text(obj)
    if isinstance(obj, dict):
        return {repair_obj(k): repair_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [repair_obj(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(repair_obj(v) for v in obj)
    return obj


def _collect_names(data) -> list:
    names = []
    for entry in (data.get("parts_catalog") or {}).values():
        if isinstance(entry, dict) and entry.get("name"):
            names.append(entry["name"])
    return names


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write the repaired pkl(s)")
    parser.add_argument("--check", action="store_true", help="report only (default)")
    args = parser.parse_args()

    for pkl_path in PKL_PATHS:
        if not pkl_path.exists():
            print(f"SKIP (missing): {pkl_path}")
            continue

        with open(pkl_path, "rb") as fh:
            data = pickle.load(fh)

        before = _collect_names(data)
        repaired = repair_obj(data)
        after = _collect_names(repaired)

        changed = [(b, a) for b, a in zip(before, after) if b != a]
        print(f"\n{pkl_path}")
        print(f"  parts: {len(before)} | repaired: {len(changed)}")
        for b, a in changed[:8]:
            print(f"    {b!r}\n      -> {a!r}")
        if len(changed) > 8:
            print(f"    ... and {len(changed) - 8} more")

        # Nothing should still carry a mojibake lead byte after repair.
        residue = [a for a in after if any(0xC0 <= ord(c) <= 0xFF for c in a)
                   and any(0x80 <= ord(c) <= 0xBF for c in a)]
        if residue:
            print(f"  WARNING: {len(residue)} name(s) still look corrupted: {residue[:3]}")

        if args.apply and changed:
            backup = pkl_path.with_suffix(".pkl.bak")
            if not backup.exists():
                shutil.copy2(pkl_path, backup)
                print(f"  backup -> {backup.name}")
            with open(pkl_path, "wb") as fh:
                pickle.dump(repaired, fh)
            print("  WROTE repaired pkl")
        elif not args.apply:
            print("  (check only — pass --apply to write)")


if __name__ == "__main__":
    main()
