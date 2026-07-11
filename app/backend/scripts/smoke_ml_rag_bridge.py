"""
Smoke test: ML <-> RAG chat bridge.

Spec: docs/superpowers/specs/2026-06-12-ml-rag-bridge-verification-design.md

Verifies on the LIVE stack that machine-scoped chat injects real ML
predictions into the LLM prompt (proven via ChatResponse.ml_context_used),
with separate BRIDGE and LLM verdicts so a Groq outage never reports the
bridge as broken.

Usage:
    python smoke_ml_rag_bridge.py [--machine-id N] [--allow-destructive]
                                  [--base-url http://localhost:8000]
Env:
    SMOKE_USER / SMOKE_PASS  — login credentials (required)

Exit codes: 0 = PASS, 1 = FAIL, 2 = MANUAL_REVIEW (human must read the answer)
"""

import argparse
import os
import re
import subprocess
import sys
import time

import httpx

# Windows consoles default to cp1252 — make unicode in LLM answers printable.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAG_HEALTH_URL = "http://localhost:8003/health"
ML_CONTAINER = "asset_management_ml_service"
QUESTION_FR = (
    "Quel est l'état actuel de cette machine ? "
    "Donne les valeurs des capteurs et le score de santé."
)
CHAT_TIMEOUT = 120.0  # Groq + tools can be slow

# Result severity: PASS < SKIP < MANUAL_REVIEW < FAIL
PASS, SKIP, MANUAL_REVIEW, FAIL = "PASS", "SKIP", "MANUAL_REVIEW", "FAIL"
_SEVERITY = {PASS: 0, SKIP: 0, MANUAL_REVIEW: 2, FAIL: 1}

# Check names reused across multiple record() calls (SonarQube S1192).
CHECK_RAG_MANUAL_CORPUS = "RAG manual corpus (soft)"
CHECK_NO_MACHINE_CHAT_ISOLATED = "no-machine chat isolated"

results: dict = {}  # name -> (status, detail)


def record(name: str, status: str, detail: str = ""):
    results[name] = (status, detail)
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")


def login(client: httpx.Client, base: str) -> str:
    user = os.getenv("SMOKE_USER")
    pwd = os.getenv("SMOKE_PASS")
    if not user or not pwd:
        print("FATAL: SMOKE_USER / SMOKE_PASS env vars required.")
        sys.exit(1)
    r = client.post(
        f"{base}/api/v1/auth/login", json={"email": user, "mot_de_passe": pwd}
    )
    if r.status_code != 200:
        print(f"FATAL: login failed ({r.status_code}): {r.text[:300]}")
        sys.exit(1)
    return r.json()["access_token"]


def layer1_stack_health(client: httpx.Client, base: str, headers: dict):
    print("\n== Layer 1: stack health ==")
    try:
        r = client.get(f"{base}/docs")
        record(
            "backend /docs",
            PASS if r.status_code == 200 else FAIL,
            f"HTTP {r.status_code}",
        )
    except Exception as e:
        record("backend /docs", FAIL, str(e))

    try:
        r = client.get(RAG_HEALTH_URL)
        ok = r.status_code == 200 and r.json().get("status") == "ok"
        record("rag-service /health", PASS if ok else FAIL, r.text[:100])
    except Exception as e:
        record("rag-service /health", FAIL, str(e))

    # Soft corpus check — at least one manual-type document. Never exact counts.
    try:
        r = client.get(f"{base}/api/v1/rag/documents", headers=headers)
        if r.status_code == 200:
            docs = r.json()
            manuals = [d for d in docs if d.get("doc_type") == "manual"]
            record(
                CHECK_RAG_MANUAL_CORPUS,
                PASS if manuals else FAIL,
                f"{len(manuals)} manual docs / {len(docs)} total",
            )
        else:
            record(CHECK_RAG_MANUAL_CORPUS, FAIL, f"HTTP {r.status_code}")
    except Exception as e:
        record(CHECK_RAG_MANUAL_CORPUS, FAIL, str(e))


def discover_machine(client: httpx.Client, base: str, headers: dict, override):
    """Dynamic discovery — first machine whose unified-health returns telemetry."""
    print("\n== Machine discovery ==")
    candidates = []
    if override is not None:
        candidates = [override]
    else:
        r = client.get(
            f"{base}/api/v1/entities/machines", headers=headers, params={"limit": 100}
        )
        if r.status_code != 200:
            record("machine list", FAIL, f"HTTP {r.status_code}")
            return None, None
        payload = r.json()
        items = payload.get("items", payload) if isinstance(payload, dict) else payload
        candidates = [m["id"] for m in items if isinstance(m, dict) and "id" in m]

    for mid in candidates:
        try:
            r = client.get(
                f"{base}/api/v1/ml/machines/{mid}/unified-health", headers=headers
            )
            if r.status_code != 200:
                continue
            h = r.json()
            if (
                h.get("unified_health_score") is not None
                and h.get("air_temperature") is not None
            ):
                record(
                    "machine discovery",
                    PASS,
                    f"machine_id={mid} ({h.get('machine_name', '?')})",
                )
                return mid, h
        except Exception:
            continue

    record("machine discovery", FAIL, "no machine has telemetry — seed telemetry first")
    return None, None


def _grounding_hits(answer: str, health: dict) -> list:
    """Fuzzy evidence that the answer references live ML state."""
    hits = []
    low = answer.lower()

    score = health.get("unified_health_score")
    if score is not None and re.search(rf"\b{round(score)}\b", answer):
        hits.append(f"health_score≈{round(score)}")

    risk = (health.get("risk_level") or "").lower()
    risk_words = {
        "critical": ["critique", "critical"],
        "high": ["élevé", "eleve", "high", "haut"],
        "medium": ["modéré", "modere", "moyen", "medium"],
        "low": ["faible", "low", "bas"],
    }
    if risk and any(w in low for w in risk_words.get(risk, [risk])):
        hits.append(f"risk={risk}")

    rpm = health.get("rotational_speed")
    if rpm is not None and str(int(rpm)) in answer:
        hits.append(f"rpm={int(rpm)}")

    rul = health.get("rul_days")
    if rul is not None and re.search(rf"\b{round(rul)}\b", answer):
        hits.append(f"rul≈{round(rul)}")

    if "anomal" in low:
        hits.append("anomaly-mentioned")

    proc = health.get("process_temperature")
    if proc is not None:
        celsius = round(proc - 273.15)
        if re.search(rf"\b{round(proc)}\b", answer) or re.search(
            rf"\b{celsius}\b", answer
        ):
            hits.append(f"process_temp≈{round(proc)}K/{celsius}C")

    return hits


def layer2_bridge(
    client: httpx.Client, base: str, headers: dict, mid: int, health: dict
):
    print("\n== Layer 2: bridge + LLM ==")

    # --- machine-scoped chat ---
    try:
        r = client.post(
            f"{base}/api/v1/chat/ai/chat",
            headers=headers,
            json={"message": QUESTION_FR, "machine_id": mid},
            timeout=CHAT_TIMEOUT,
        )
    except Exception as e:
        record("BRIDGE", FAIL, f"chat request error: {e}")
        record("LLM", FAIL, "unreachable")
        return

    if r.status_code == 503:
        # Groq down — bridge still assessable from unified-health + backend log.
        record("LLM", FAIL, f"Groq unavailable: {r.text[:200]}")
        record(
            "BRIDGE",
            MANUAL_REVIEW,
            "unified-health OK; confirm backend log line "
            "[ml_bridge] ml_context_used=True (docker logs asset_management_backend)",
        )
        return

    if r.status_code != 200:
        record("BRIDGE", FAIL, f"HTTP {r.status_code}: {r.text[:200]}")
        record("LLM", FAIL, f"HTTP {r.status_code}")
        return

    data = r.json()
    answer = data.get("message", "")

    # Decisive bridge check — injection proven, not inferred.
    if data.get("ml_context_used") is True:
        record("BRIDGE", PASS, "ml_context_used=true on machine-scoped chat")
    else:
        record(
            "BRIDGE",
            FAIL,
            f"ml_context_used={data.get('ml_context_used')!r} — ML block NOT injected",
        )

    # LLM grounding — fuzzy, non-deterministic answers tolerated.
    hits = _grounding_hits(answer, health)
    if len(hits) >= 2:
        record("LLM", PASS, f"grounded ({', '.join(hits)})")
    elif answer.strip():
        record("LLM", MANUAL_REVIEW, f"only {len(hits)} grounding hit(s): {hits}")
        print("\n--- FULL ANSWER (human: does it use the live ML numbers?) ---")
        print(answer)
        print("--- END ANSWER ---")
    else:
        record("LLM", FAIL, "empty answer")

    # --- no-machine chat: ML state must NOT leak ---
    try:
        r2 = client.post(
            f"{base}/api/v1/chat/ai/chat",
            headers=headers,
            json={"message": QUESTION_FR},
            timeout=CHAT_TIMEOUT,
        )
        if r2.status_code == 200:
            d2 = r2.json()
            no_leak = d2.get("ml_context_used") is False and bool(
                d2.get("message", "").strip()
            )
            record(
                CHECK_NO_MACHINE_CHAT_ISOLATED,
                PASS if no_leak else FAIL,
                f"ml_context_used={d2.get('ml_context_used')!r}",
            )
        else:
            record(CHECK_NO_MACHINE_CHAT_ISOLATED, FAIL, f"HTTP {r2.status_code}")
    except Exception as e:
        record(CHECK_NO_MACHINE_CHAT_ISOLATED, FAIL, str(e))


def layer3_degradation(
    client: httpx.Client, base: str, headers: dict, mid: int, allow: bool
):
    print("\n== Layer 3: degradation (ML service down) ==")
    if not allow:
        record("degradation", SKIP, "--allow-destructive not set (local-only test)")
        return

    try:
        subprocess.run(  # NOSONAR -- list-form invocation, no shell expansion, controlled args
            ["docker", "stop", ML_CONTAINER], check=True, capture_output=True
        )
        print(f"  stopped {ML_CONTAINER}")
        try:
            r = client.post(
                f"{base}/api/v1/chat/ai/chat",
                headers=headers,
                json={"message": QUESTION_FR, "machine_id": mid},
                timeout=CHAT_TIMEOUT,
            )
            if r.status_code == 200:
                d = r.json()
                # Safety property: chat answers without error when ML container is
                # down. ml_context_used may legitimately remain True — the backend
                # falls back to rule-based scoring (RULCalculator, score_source=
                # fallback_additive) and still injects a valid context block.
                ok = bool(d.get("message", "").strip())
                record(
                    "degradation",
                    PASS if ok else FAIL,
                    f"HTTP 200, answer present, ml_context_used={d.get('ml_context_used')!r} "
                    "(rule-based fallback keeps context alive — by design)",
                )
            else:
                record(
                    "degradation",
                    FAIL,
                    f"HTTP {r.status_code} — chat broke when ML down",
                )
        except Exception as e:
            record("degradation", FAIL, f"chat error with ML down: {e}")
    finally:
        subprocess.run(  # NOSONAR -- list-form invocation, no shell expansion, controlled args
            ["docker", "start", ML_CONTAINER], check=False, capture_output=True
        )
        print(f"  restarted {ML_CONTAINER}, waiting for health…")
        deadline = time.time() + 120
        while time.time() < deadline:
            try:
                r = client.get(
                    f"{base}/api/v1/ml/machines/{mid}/unified-health", headers=headers
                )
                if r.status_code == 200:
                    print("  ml-service healthy again")
                    break
            except Exception:
                pass
            time.sleep(5)
        else:
            print(
                "  WARNING: ml-service not confirmed healthy after restart — check manually"
            )


def main():
    ap = argparse.ArgumentParser(description="ML<->RAG bridge smoke test")
    ap.add_argument(
        "--machine-id", type=int, default=None, help="override machine discovery"
    )
    ap.add_argument(
        "--allow-destructive",
        action="store_true",
        help="enable Layer 3 (docker stop ml-service) — LOCAL ENVIRONMENTS ONLY",
    )
    ap.add_argument("--base-url", default="http://localhost:8000")
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    with httpx.Client(timeout=30.0) as client:
        token = login(client, base)
        headers = {"Authorization": f"Bearer {token}"}

        layer1_stack_health(client, base, headers)
        if any(s == FAIL for s, _ in results.values()):
            print(
                "\nLayer 1 failed — aborting (no point testing the bridge on a broken stack)."
            )
            _verdict()
            sys.exit(1)

        mid, health = discover_machine(client, base, headers, args.machine_id)
        if mid is None:
            _verdict()
            sys.exit(1)

        layer2_bridge(client, base, headers, mid, health)
        layer3_degradation(client, base, headers, mid, args.allow_destructive)

    sys.exit(_verdict())


def _verdict() -> int:
    print("\n==== VERDICT ====")
    worst = 0
    for name, (status, detail) in results.items():
        print(f"  {name:30s} {status}" + (f"  ({detail})" if detail else ""))
        worst = max(worst, _SEVERITY[status])
    label = {0: "PASS", 1: "FAIL", 2: "MANUAL_REVIEW"}[worst]
    print(f"\nOverall: {label} (exit {worst})")
    return worst


if __name__ == "__main__":
    main()
