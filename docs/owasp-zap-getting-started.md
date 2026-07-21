# OWASP ZAP — Getting Started (Beginner Guide)

This walks through installing OWASP ZAP, running your first scan by hand, and seeing that it's the exact same scan the CI pipeline runs automatically. No prior ZAP experience assumed.

## 1. Install ZAP Desktop

1. Go to https://www.zaproxy.org/download/ and download the Windows installer.
2. Run the installer, accept defaults.
3. Launch "OWASP ZAP" from the Start menu. First launch asks about persisting sessions — choose "No, I do not want to persist this session" for now (default for ad-hoc runs).

## 2. The 3 parts of the GUI you actually need

ZAP's window has a lot in it. For this workflow you only need three tabs:

- **Sites tree** (left panel) — shows every URL ZAP has discovered, grows as it scans.
- **Alerts tab** (bottom panel) — every finding, grouped by severity (red = High, orange = Medium, yellow = Low, blue = Informational).
- **Automation** tab (bottom panel, may need "+" → "Automation" to open it if not visible) — loads and runs `.yaml` automation plans, which is what we'll use.

Ignore everything else for now.

## 3. Start the app stack

In a terminal, from the project root:
```
make up
```
Wait until `docker ps` shows all services healthy (backend, ml-service, rag, frontend).

## 4. Load and run the automation plan

1. In ZAP, open the **Automation** tab.
2. Click "Open an existing Automation Plan" (folder icon) and select `security/zap/zap-automation.yaml` from this repo.
3. ZAP will show the plan's jobs (spider, activeScan, report — one block per service).
4. Before running: ZAP Desktop needs `ZAP_LOGIN_PASSWORD` available as an environment variable, since the plan reads `${ZAP_LOGIN_PASSWORD}` for the 4 backend test accounts. Easiest way on Windows: close ZAP, set it for your user account once —
   ```powershell
   [System.Environment]::SetEnvironmentVariable("ZAP_LOGIN_PASSWORD", "hA123456", "User")
   ```
   then reopen ZAP Desktop (new env vars only apply to newly-launched programs).
5. Click the "Play" button (▶) at the top of the Automation panel.

## 5. Watch it run

- The **Sites tree** fills in as the spider discovers pages/endpoints under `backend`, `ml-service`, `rag-service`, `frontend`.
- The **Alerts tab** starts populating once the active scan phase begins — this is the part sending real attack payloads (SQL injection attempts, XSS payloads, etc.) at every discovered endpoint.
- A full run across all 4 services × 4 backend roles takes a while (expect 15–40+ minutes) — this is a genuinely thorough scan, not a quick check.

## 6. Read one real finding

Click any entry in the Alerts tab. Each finding shows:
- **Risk** (High/Medium/Low/Informational) and **Confidence** — how sure ZAP is.
- **Description** — what the issue is, in plain English.
- **Other info** — the exact request ZAP sent and evidence it found.
- **Solution** — how to fix it.

Pick a High or Medium one first — those are worth acting on. Low/Informational findings are often just hardening suggestions (missing headers, etc.), useful but rarely urgent.

## 7. Same plan, no GUI (proving CI runs the identical scan)

```
make dast
```

Run from **Git Bash** (the default terminal in this project). The Makefile sets `MSYS_NO_PATHCONV=1` automatically, so you don't need to set anything extra.

This runs the exact same `security/zap/zap-automation.yaml` file, headless, via Docker — no window opens. When it finishes, open `security/zap/zap-report.html` in a browser — it's the same findings you just watched appear live in the GUI, just as a static report instead of an interactive session.

This is also exactly what the `dast-scan` job in `.gitlab-ci.yml` runs on every pipeline — the only difference is *where* it runs (your machine vs. the CI runner) and that CI never opens a window, it just produces the report file as a downloadable pipeline artifact.

> **Windows path note:** If you run Docker commands directly (not via `make dast`) from Git Bash, add `MSYS_NO_PATHCONV=1` before the `docker run` command, or use `//zap/wrk/...` (double leading slash) for the `-autorun` argument. Otherwise Git Bash silently converts `/zap/wrk/...` to a Git installation path and ZAP can't find the plan file.

## Safety note

This is a **full active scan** — it sends real attack traffic and calls real write/delete API endpoints. Only ever run it against your local `make up` stack. Never point ZAP (manually or otherwise) at a real production server or real customer data.
