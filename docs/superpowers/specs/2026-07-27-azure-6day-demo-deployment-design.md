# Azure 6-Day Demo Deployment — Design

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

## Two-phase plan

Two phases run in sequence, both within the 6-day window, both landing in the same GitLab CI pipeline:

### Phase 1 — Plain VM (safety net, do this first)

Goal: guarantee *something* is live and screenshottable early, before attempting the harder AKS path.

**One-time manual setup (not automated in CI):**
- One Azure VM, Ubuntu, Standard_B4ms (4 vCPU / 16GB RAM) — sized with headroom above the minimum so the torch/transformers-heavy ml-microservice and rag-service don't risk OOM crashes alongside Postgres/MinIO/Prometheus/Grafana/Pushgateway on the same box. ~$24 for 6 days.
- Free Azure DNS label enabled (e.g. `eam-demo.<region>.cloudapp.azure.com`) instead of a raw IP, for cleaner screenshots.
- SSH key pair generated once; public key installed on the VM; private key stored as a masked/protected GitLab CI variable.
- One Azure Container Registry (ACR) resource created — used for an extra "Azure resource" screenshot in phase 1, and becomes functionally load-bearing in phase 2 (AKS pulls from it directly).

**CI pipeline additions (after the existing `gate` stage):**
- `registry-push`: tag the already-built, already-scanned images; push to GitLab Container Registry (primary — zero new auth needed, already available via `CI_JOB_TOKEN`) and to ACR (bonus screenshot, becomes load-bearing in phase 2).
- `deploy`: SSH into the VM using the stored key; write a `.env` file from masked GitLab CI variables (DB password, MinIO keys, JWT secret, etc.); run `docker compose pull && docker compose up -d`. This requires a deploy-specific compose file (e.g. `docker-compose.prod.yml`, kept in the repo) referencing the pushed registry image tags instead of the local `build:` directives that `docker-compose.yml` uses — the VM pulls pre-built, already-scanned images rather than rebuilding them. The VM holds a one-time `git clone` of the repo (for this compose file and any static config); `deploy` does a `git pull` before `compose pull`/`up -d` to pick up compose-file changes.
- `verify`: `curl` the public URL's health endpoint from CI; fail the pipeline if it doesn't respond. Gives an automated "deployment verified" pipeline screenshot, not just manual eyeballing.

**Scope running on the VM:** core app (backend, frontend, ml-microservice, rag-service, Postgres, MinIO) + monitoring (Prometheus, Grafana, Pushgateway). SonarQube stays off the VM.

**Data flow:** `git push to Phase_2` → existing security/test/build/scan stages (unchanged) → `registry-push` → `deploy` (SSH + compose) → `verify` (curl) → developer browses the URL and takes screenshots (live app, Azure portal VM view, GitLab CI green pipeline).

**Error handling:** minimal by design. If `deploy` fails, the pipeline goes red (clear signal); previously-running containers keep serving until fixed and re-pushed. No automated rollback for a 6-day demo.

### Phase 2 — AKS (stretch goal, attempted after phase 1 is confirmed working)

Goal: a more impressive, Kubernetes-based deployment for the report/CV, attempted with the remaining days once phase 1 has already produced guaranteed screenshots.

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

- GitLab CI pipeline runs green end-to-end on a push to `Phase_2`, including the new `registry-push`/`deploy`/`verify` (phase 1) and `deploy-aks`/`verify-aks` (phase 2) stages.
- Live app reachable and screenshotted from both the VM's public DNS label and the AKS ingress URL.
- Azure portal screenshots showing the VM, the ACR, and the AKS cluster with running workloads.
- All Azure resources deleted after the window closes, confirmed via the portal (no ongoing billing).

## Alternatives considered

- **Azure Container Apps** (managed, serverless containers): rejected on cost grounds for 24/7 operation (see Risks). Also awkward for stateful services (Postgres/MinIO would need conversion to managed Azure equivalents), adding rework for a throwaway demo.
- **Azure DevOps** (as a CI/CD replacement for GitLab CI): rejected — the existing GitLab CI pipeline is a substantial, working, already-tested asset (SAST/DAST/SonarQube gate); rebuilding it in a different tool for a 6-day demo would be pure waste.
- **Manual-only deploy (no CI automation)**: rejected per explicit choice — the CV/report value of "an automated pipeline deploys this" was judged worth the extra setup time over a first-time deployer just SSHing in by hand.
