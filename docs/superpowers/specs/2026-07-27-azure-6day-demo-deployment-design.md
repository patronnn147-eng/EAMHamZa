# Azure 6-Day Demo Deployment — Design

> **Correction discovered during execution (2026-07-28):** this ESPRIT-tenant
> Azure for Students subscription is restricted by an "Allowed resource
> deployment regions" policy to exactly 5 regions (`switzerlandnorth`,
> `spaincentral`, `germanywestcentral`, `norwayeast`, `polandcentral`) — not
> `westeurope` as originally planned. It further restricts the B-series VM
> family to ARM64 ("p"-suffix) sizes only; the planned `Standard_B4ms` (x86)
> is `NotAvailableForSubscription`. Actual deployment uses **region
> `germanywestcentral`, VM size `Standard_D4as_v7`** (x86_64 AMD, 4vCPU/16GB
> — same specs, different family, keeps parity with the amd64 CI images).
> `scripts/azure-provision-vm.sh` reflects this; the plan doc's embedded
> code blocks below still show the original values as a historical record.

## Purpose

Get the EAM app reachable at a public URL on Azure, driven by an automated GitLab CI deploy stage, for a short (~6 day) window. Produce screenshots (live app, Azure portal, GitLab CI pipeline runs) for the PFE report and for the CV. Not a long-term production system — everything gets torn down after the window closes.

## Constraints

- First-ever deployment for the developer — no prior hands-on deployment experience.
- ~6 days total, including learning time.
- Budget: Azure for Students credit, $100.
- Existing GitLab CI pipeline (8 stages: secret-scan, sca-deps, test, sast, build, image-scan, dast, lint, gate) must stay intact — extend it, don't replace it.
- Existing `docker-compose.yml` stack is the baseline: backend (FastAPI), frontend (Next.js), ml-microservice, rag-service, Postgres, MinIO, plus a separate monitoring stack (Prometheus, Grafana, Pushgateway) and a separate SonarQube stack.
- "Development deployment" already exists and needs no new work: local `docker-compose.yml` + `make up` on the developer's own machine.

## Out of scope

- Long-term/ongoing production hosting (this is a throwaway demo window).
- Staging/prod branch-promotion flow (single branch, `Phase_2`, drives everything — it's the only branch currently in good shape).
- Deploying SonarQube to the cloud (stays local/CI-only).
- Cost-optimized scale-to-zero architecture (Azure Container Apps was evaluated and rejected — see Alternatives Considered).
- Automated rollback (acceptable to redeploy manually if a deploy fails, given the short/low-stakes window).
- Autoscaling, high availability, multi-node/multi-replica resilience — single-node/single-VM by design, for demo purposes only.

## Two-phase plan

Two phases run in sequence, both within the 6-day window, both landing in the same GitLab CI pipeline:

### Phase 1 — Plain VM (safety net, do this first)

Goal: guarantee *something* is live and screenshottable early, before attempting the harder AKS path.

**One-time manual setup (not automated in CI):**
- One Azure VM, Ubuntu, Standard_B4ms (4 vCPU / 16GB RAM) — sized with headroom above the minimum so the torch/transformers-heavy ml-microservice and rag-service don't risk OOM crashes alongside Postgres/MinIO/Prometheus/Grafana/Pushgateway on the same box. ~$24 for 6 days.
- Free Azure DNS label enabled (e.g. `eam-demo.<region>.cloudapp.azure.com`) instead of a raw IP, for cleaner screenshots.
- SSH key pair generated once; public key installed on the VM; private key stored as a masked/protected GitLab CI variable.
- One Azure Container Registry (ACR) resource created — used for an extra "Azure resource" screenshot in phase 1, and becomes functionally load-bearing in phase 2 (AKS pulls from it directly).
- **Caddy** added as a reverse proxy in front of the frontend/backend, config'd with the DNS label as its site address — Caddy issues and renews a Let's Encrypt HTTPS cert automatically with no manual certificate handling. Without this, the browser shows "Not Secure" on every screenshot, which is an avoidable, noticeable flaw for a jury demo.

**CI pipeline additions (after the existing `gate` stage):**
- `registry-push`: tag the already-built, already-scanned images; push to GitLab Container Registry (primary — zero new auth needed, already available via `CI_JOB_TOKEN`) and to ACR (bonus screenshot, becomes load-bearing in phase 2).
- `deploy`: SSH into the VM using the stored key; write a `.env` file from masked GitLab CI variables (DB password, MinIO keys, JWT secret, etc.) — all such variables follow an `EAM_*` naming prefix in GitLab's CI/CD variable settings, so the deploy script can enumerate and write them without a hand-maintained list; run `docker compose pull && docker compose up -d`. This requires a deploy-specific compose file (e.g. `docker-compose.prod.yml`, kept in the repo) referencing the pushed registry image tags instead of the local `build:` directives that `docker-compose.yml` uses — the VM pulls pre-built, already-scanned images rather than rebuilding them. The VM holds a one-time `git clone` of the repo (for this compose file and any static config); `deploy` does a `git pull` before `compose pull`/`up -d` to pick up compose-file changes. `docker-compose.prod.yml` sets `restart: always` on every service and a basic `healthcheck:` (HTTP endpoint for backend/frontend, `pg_isready` for Postgres, etc.) — on a single VM with no redundancy, a crashed container should come back on its own rather than silently killing the demo.
- `verify`: `curl` the public URL's health endpoint from CI; fail the pipeline if it doesn't respond. Gives an automated "deployment verified" pipeline screenshot, not just manual eyeballing.

**Scope running on the VM:** core app (backend, frontend, ml-microservice, rag-service, Postgres, MinIO) + monitoring (Prometheus, Grafana, Pushgateway). SonarQube stays off the VM. Monitoring is included primarily for demonstration value (a Grafana dashboard is a strong CV/report artifact), not because a 6-day demo has real operational monitoring needs.

**Routing:** Caddy is the only public entry point (ports 80/443) and reverse-proxies to the frontend; the frontend calls the backend over the VM's internal Docker network (not separately exposed publicly); ml-microservice and rag-service are internal-only, reachable solely from the backend over the same Docker network; Postgres and MinIO are internal-only; Grafana is reverse-proxied through Caddy on a subpath (or separate DNS label) for screenshotting, Prometheus/Pushgateway stay internal.

**Data flow:** `git push to Phase_2` → existing security/test/build/scan stages (unchanged) → `registry-push` → `deploy` (SSH + compose) → `verify` (curl) → developer browses the URL and takes screenshots (live app, Azure portal VM view, GitLab CI green pipeline).

**Error handling:** minimal by design. If `deploy` fails, the pipeline goes red (clear signal); previously-running containers keep serving until fixed and re-pushed. No automated rollback for a 6-day demo.

### Phase 2 — AKS (optional stretch goal, attempted after phase 1 is confirmed working)

**Phase 2 is explicitly optional. Phase 1 alone fully satisfies the Success Criteria below.** AKS is real-world known to be non-trivial for a first-timer — ingress/networking setup commonly costs a full day or two on its own, and PVC/storage issues are a common second time-sink. If phase 2 runs out of time or gets stuck, stop and ship phase 1 only: a clean VM + CI/CD pipeline + screenshots is a solid deliverable on its own and is strictly better than a broken or half-finished Kubernetes demo. Do not sacrifice phase 1 polish or time to chase phase 2.

Goal (if attempted): a more impressive, Kubernetes-based deployment for the report/CV, attempted with the remaining days once phase 1 has already produced guaranteed screenshots.

**One-time manual setup:**
- One AKS cluster, single node pool, one node, Standard_D4s_v5 (4 vCPU / 16GB) — comparable sizing to the phase 1 VM. AKS control plane is free; only the node costs.
- ACR from phase 1 attached to AKS (`az aks update --attach-acr`) — AKS can then pull images with no manual `imagePullSecret` configuration.
- NGINX ingress controller installed once via Helm, giving a public URL/IP for the app.
- Kubeconfig fetched once (`az aks get-credentials`), base64-encoded, stored as a masked GitLab CI variable. This avoids running Azure CLI or handling a service principal inside CI — the deploy stage just uses `kubectl` directly against the stored config.

**Kubernetes manifests** (new `k8s/` directory):
- Deployments + Services: backend, frontend, ml-microservice, rag-service, Prometheus, Grafana, Pushgateway.
- Postgres and MinIO, each backed by an Azure Disk-backed PersistentVolumeClaim.
- A Secret (DB password, MinIO keys, JWT secret, etc.) and ConfigMap for non-secret env vars, applied from the same masked GitLab CI variables used in phase 1.
- An Ingress routing the public hostname to the frontend/backend.

**CI pipeline additions (alongside, not replacing, phase 1's stages):**
- `deploy-aks`: `kubectl --kubeconfig=$KUBE_CONFIG apply -f k8s/`.
- `verify-aks`: curl the ingress's public URL; fail the pipeline if it doesn't respond.

**Data flow:** same `registry-push` stage from phase 1 feeds both targets — GitLab Registry is used for the VM; images are additionally available in ACR, which AKS pulls from directly. `deploy-aks` applies the manifests; `verify-aks` confirms the app responds; developer browses the ingress URL and screenshots the AKS workloads view, the live app, and the green pipeline.

**Teardown:** around day 6 (or once screenshots are captured), `az aks delete` for the cluster and stop/delete the phase 1 VM — both are manual one-line actions, not automated, to avoid accidentally deleting things mid-use.

## Risks and mitigations

- **First-time deployer + AKS complexity** → mitigated by doing phase 1 first: guarantees usable screenshots exist even if AKS setup runs into trouble (ingress/networking are the classic first-timer trap).
- **Azure Container Apps was considered and rejected**: 24/7 consumption pricing for this stack (torch + transformers services running continuously) was estimated at ~$235–465/month depending on scope — the $100 credit would be exhausted in under two weeks even at minimum scope. Not viable for an always-reachable demo. A flat-rate VM/AKS node is far cheaper for a steady-state heavy workload; Container Apps' scale-to-zero benefit only pays off for spiky/idle-heavy traffic, which doesn't match "reachable for screenshots over several days."
- **CI credentials for two deploy targets (SSH key + kubeconfig)** → both stored as masked/protected GitLab CI variables, scoped to the `Phase_2` branch's pipeline only.

## Success criteria

**Required (phase 1 alone must deliver this):**
- GitLab CI pipeline runs green end-to-end on a push to `Phase_2`, including the new `registry-push`/`deploy`/`verify` stages.
- Live app reachable over HTTPS and screenshotted from the VM's public DNS label.
- Azure portal screenshots showing the VM and the ACR.
- All Azure resources deleted after the window closes, confirmed via the portal (no ongoing billing).

**Bonus (only if phase 2 succeeds):**
- Live app additionally reachable and screenshotted via the AKS ingress URL.
- Azure portal screenshot showing the AKS cluster with running workloads.
- `deploy-aks`/`verify-aks` stages also green in the pipeline.

## Limitations

Documented explicitly here (and worth stating plainly in the PFE report — it reads as engineering maturity, not a gap):

- No autoscaling — fixed single VM / single AKS node.
- No high availability — one instance of every service; a node failure takes the whole demo down.
- No automated rollback — a bad deploy is fixed by pushing a corrected commit, not reverted automatically.
- Single-node/single-VM deployment throughout — this is a demo/portfolio artifact, not a production architecture.
- Designed for a ~6-day window only; not intended to run indefinitely.

## Alternatives considered

- **Azure Container Apps** (managed, serverless containers): rejected on cost grounds for 24/7 operation (see Risks). Also awkward for stateful services (Postgres/MinIO would need conversion to managed Azure equivalents), adding rework for a throwaway demo.
- **Azure DevOps** (as a CI/CD replacement for GitLab CI): rejected — the existing GitLab CI pipeline is a substantial, working, already-tested asset (SAST/DAST/SonarQube gate); rebuilding it in a different tool for a 6-day demo would be pure waste.
- **Manual-only deploy (no CI automation)**: rejected per explicit choice — the CV/report value of "an automated pipeline deploys this" was judged worth the extra setup time over a first-time deployer just SSHing in by hand.
