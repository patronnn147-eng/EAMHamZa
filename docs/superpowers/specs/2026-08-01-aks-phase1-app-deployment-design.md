# AKS Phase 1 — Application Deployment Design

**Date:** 2026-08-01
**Status:** Approved, ready for planning
**Parent spec:** [2026-07-30-aks-production-migration-design.md](2026-07-30-aks-production-migration-design.md)
**Prerequisite (complete, verified):** Phase 0 — AKS cluster, Postgres Flexible Server, Key Vault, all live via Terraform in `polandcentral`. See memory `aks-phase0-build.md` for full deviation history (x86 instead of ARM64, polandcentral instead of germanywestcentral, HCP Terraform state backend).

## Goal

Get the full EAM application running on the AKS cluster provisioned in Phase 0, reachable from a browser over real HTTPS, deployed staging-first before any production promotion.

## Scope

All 8 application pieces, deployed together in one pass (not backend-first, not incremental):

1. `backend` (FastAPI)
2. `frontend` (Next.js)
3. `ml-microservice` (Flask + sklearn/XGBoost/TensorFlow)
4. `rag-service`
5. `celery_worker`
6. `celery_beat`
7. `rabbitmq`
8. `minio` — **added to the original 7-piece list during brainstorming**: the backend's RAG document storage (S3-backed, buckets `rag-docs` + `attachments`, migrated 2026-05-30) depends on it. Without MinIO in the cluster, document upload and RAG chat break. Deployed as an in-cluster pod, same role it plays in local `docker-compose.yml` — no backend code changes required.

Azure Database for PostgreSQL Flexible Server (Phase 0) stays external to the cluster; nothing else changes about it.

## Namespace strategy

Staging first: `eam-staging`. Once verified working end-to-end, the same Helm charts get redeployed into `eam-prod` with a different values file — no new charts, no new pipeline, just a second `helm install` with `-f values-prod.yaml`. Prod promotion itself is a later, separate step, not part of this phase's execution.

## Image build & registry

Reuses the **existing ACR** (`$ACR_LOGIN_SERVER`) already used by the `.gitlab-ci.yml` `:demo` pipeline — no new registry provisioned. That pipeline currently builds `linux/arm64` images tagged `:demo` for backend/ml-service/rag-service/frontend, pushed to both GitLab's own registry and ACR.

This phase adds a **new** CI job (does not touch the existing `:demo` jobs, which stay ARM64 for the old `eam-demo-vm`):
- Builds `linux/amd64` images for all 8 pieces (celery_worker/celery_beat likely share the backend image with a different entrypoint/command — confirmed during implementation; rabbitmq and minio use their official upstream images, not custom builds)
- Tags e.g. `:aks-staging`, pushes to the same ACR
- New Terraform resource: `azurerm_role_assignment` granting the AKS cluster's kubelet identity `AcrPull` on the ACR, so the cluster can pull without embedded registry credentials

## Deployment method — Helm

Kubernetes manifests as Helm charts under `infra/helm/`, one chart per app piece (or an umbrella chart with 8 sub-charts — exact structure decided during implementation planning). Environment-specific values (replica count, ingress hostname, resource limits, image tag) live in `values-staging.yaml` / `values-prod.yaml`, not duplicated across raw YAML files.

Chosen over plain YAML (staging/prod would be near-duplicate files that drift apart) and Kustomize (patch-overlay model less intuitive for a first AKS deploy).

## Secrets — Secrets Store CSI Driver

The Postgres admin password (already in Key Vault `eam-prod-kv-h597b3` from Phase 0) is mounted directly into backend/celery pods at pod startup via the Secrets Store CSI Driver AKS add-on, backed by an Azure Managed Identity trusted to read that specific Key Vault. The password is never copied into a Kubernetes Secret — no duplicate copy to go stale if the Key Vault value rotates.

New Terraform work: enable the CSI driver AKS add-on, create the Managed Identity, grant it `get`/`list` on the Key Vault's secrets, and a `SecretProviderClass` resource the backend/celery pods reference.

## Ingress + HTTPS

`ingress-nginx` (routes path-based traffic: `/api/*` → backend, `/` → frontend, other internal services stay ClusterIP-only, not internet-facing) + `cert-manager` (auto-issues and renews free HTTPS certificates via Let's Encrypt's HTTP-01 challenge).

**Hostname:** Azure's free auto-generated DNS label on the ingress controller's public IP (e.g. `eam-app.polandcentral.cloudapp.azure.com`) — no domain purchase required, and it's a real resolvable hostname (not an IP-mapping trick), so Let's Encrypt issues a normal certificate for it.

## Resource sizing

Cluster nodes are small (`Standard_B2s_v2`: 2 vCPU / 4GB RAM), and ml-microservice's production image includes TensorFlow for the P4 autoencoder (Phase 4.3, see project CLAUDE.md changelog) — real memory weight. Decision: ship the same image as local/demo unchanged; if pods fail to schedule or hit OOM, scale the existing user node pool (already configured to autoscale 1-2 nodes) rather than pre-trimming the image. Not pre-optimizing for a POC that may get torn down.

## Data flow (staging)

```
Browser
  → https://eam-app.polandcentral.cloudapp.azure.com
  → ingress-nginx (cert-manager-issued HTTPS)
      → frontend pod (static assets, /)
      → backend pod (/api/*)
          → Azure Postgres Flexible Server (external, Phase 0)
          → in-cluster RabbitMQ (Celery task queue)
          → in-cluster MinIO (RAG document storage)
          → in-cluster ml-service (ClusterIP only)
          → in-cluster rag-service (ClusterIP only)
  celery_worker / celery_beat: consume from RabbitMQ, same backend image, different command
```

## Testing / verification plan

After `helm install` into `eam-staging`:
1. `kubectl get pods -n eam-staging` — all Running, no CrashLoopBackOff
2. `curl https://<hostname>/api/health` from outside the cluster — confirms ingress + cert-manager HTTPS working
3. Frontend loads in a real browser at the hostname
4. Upload one document through the RAG UI — confirms MinIO wiring end-to-end
5. One login + chat round-trip — confirms full path (frontend → backend → Postgres → ml-service/rag-service)

## Out of scope for this phase

- Migrating MinIO to Azure Blob Storage (would require backend S3-client rework — real dev work, not a deploy task)
- Autoscaling/HPA tuning beyond the node pool's existing defaults
- The actual `eam-prod` promotion (separate step once staging is verified)
- Exact CI YAML for the new x86 image job (specified during implementation planning, not design)
- Tearing the cluster down (POC framing from Phase 0 still applies — validate first; teardown timing is the user's call against the finite Azure for Students credit)
