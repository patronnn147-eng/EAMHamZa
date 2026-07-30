# AKS Production Migration — Design

**Date:** 2026-07-30
**Status:** Design only — nothing provisioned yet
**Author context:** Written after a debugging session that took the current single-VM Azure demo deployment (`eam-demo.germanywestcentral.cloudapp.azure.com`, plain Docker Compose) from broken to working. This spec is the roadmap for moving from that demo deployment to a real production deployment on Azure Kubernetes Service (AKS).

## Purpose & scope

The current deployment is a single Azure VM running the full stack via `docker compose up -d` (see `docker-compose.yml` + `.prod.yml` + `.monitoring.yml`), fronted by a self-hosted Caddy container for TLS. It has no orchestration, no horizontal scaling, no managed database, no zero-downtime deploys, and no centralized logging across services. This was explicitly a demo deployment, not production infrastructure.

This spec covers migrating to AKS for a **real production launch**, sized for **Small scale** (tens to low hundreds of concurrent users, a handful of monitored plants/machines), with a documented path to scale up later without a redesign. It does not cover multi-region/DR, which is out of scope until real usage justifies the added cost and complexity.

**Constraint carried over from the current deployment:** the Azure subscription in use only has ARM64 VM quota approved (this is why the current pipeline fights ARM64 wheel/binary availability for `tensorflow-cpu` and Trivy — see this session's fixes to `requirements-tf.txt`, `app/ml-microservice/Dockerfile`, and `monitoring/scanner/Dockerfile`). This design assumes that constraint still holds and targets ARM64 (Ampere Altra) AKS node pools throughout. If amd64 quota becomes available later, the `$TARGETARCH`-based Dockerfile patterns already in place make switching straightforward.

## Cluster architecture

- **AKS**, single cluster, single region (`germanywestcentral`, matching the current VM). One cluster, not separate staging/prod clusters — namespaces provide isolation at this scale.
- **Node pools**:
  - System pool: 2 nodes, ARM64 SKU, hosts only cluster-critical pods (CoreDNS, metrics-server, etc.) — kept separate so app workloads can never starve cluster-critical components.
  - User pool: 2-4 nodes, ARM64 SKU, autoscaling 2→4 on load, hosts all application pods.
- **Namespaces**:
  - `eam-prod` — backend, frontend, ml-service, rag-service, celery_worker, celery_beat
  - `eam-monitoring` — Prometheus, Grafana, Loki, Trivy (as a CI stage, not a namespace resident — see Observability)
  - `eam-ingress` — ingress-nginx, cert-manager
- **Networking**: Azure CNI (pods get real VNet IPs). AKS-managed VNet. API server public but IP-restricted to admin IPs and the GitLab runner's egress IP — no private-cluster/VPN setup at this scale.
- **What replaces the VM**: every service currently defined in `docker-compose.yml` becomes a Kubernetes Deployment + Service, templated as Helm chart(s). Nothing in the app namespace is a StatefulSet once Postgres and object storage move to managed Azure services (see Data & storage) — the one exception is RabbitMQ, which stays self-hosted.

## Data & storage

| Component | Today | Production plan | Why |
|---|---|---|---|
| Postgres | Self-hosted container (`pgvector/pgvector:pg15`) | **Azure Database for PostgreSQL Flexible Server**, Small/burstable tier, `pgvector` extension enabled, no zone-redundant HA at launch | Automated backups and failover are the one thing not worth self-hosting for a real production launch as a solo operator. `pgvector` is supported on Flexible Server, so the RAG tables migrate without schema changes. |
| Object storage (RAG docs) | Self-hosted MinIO container | **Azure Blob Storage** | S3-compatible enough that `app/backend/services/rag_storage.py`'s presigned-URL logic needs minimal changes. Cheap (~$2-5/mo), removes one more self-managed stateful service. |
| Message broker (Celery) | Self-hosted RabbitMQ container | **Stays self-hosted**, in-cluster StatefulSet + PVC, 1 replica at Small scale | Not holding data that can't be regenerated/re-queued on a restart — self-hosting is an acceptable trade-off here, consistent with preferring OSS/self-hosted where the risk is low. |
| pgAdmin | Self-hosted container, always-on exposed UI | **Dropped from production** | It's a dev convenience sitting on an open port. In prod, use Azure Portal's query tool or a bastion-only `kubectl port-forward` when actually needed. |

Persistent Volumes needed in-cluster: only RabbitMQ (Azure Disk-backed, `Standard_LRS`).

## Secrets & configuration

- **Azure Key Vault** holds every runtime secret currently living in the VM's `.env` file (DB password, JWT secret, RabbitMQ credentials, third-party API keys).
- **Secrets Store CSI Driver** (AKS add-on) mounts Key Vault secrets into pods as files/env vars, kept in sync automatically.
- **GitLab CI variables** shrink to build/push/deploy-auth only (`ACR_*` or GitLab registry credentials, an Azure service principal scoped to the cluster and Key Vault). No app secrets live as CI variables anymore — this removes the entire SSH-key-into-a-VM-and-scp-a-`.env` pattern that caused the `SSH_PRIVATE_KEY` masking issue and the accidental key exposure earlier in this project's history.
- **Kubernetes ConfigMaps** hold non-secret configuration (feature flags such as `ML_ALLOW_SYNTHETIC_TELEMETRY`, log levels), versioned in the Helm chart and reviewable in pull requests like code.

## Ingress, TLS, and networking edge

- **ingress-nginx** (self-hosted controller, `eam-ingress` namespace) replaces Caddy as the entry point. One `Ingress` resource per route, mirroring the routing already expressed in the current `Caddyfile`.
- **cert-manager** (self-hosted, OSS) automates Let's Encrypt certificates via a `ClusterIssuer` — same TLS outcome Caddy provides today, K8s-native and auto-renewing.
- **Azure Load Balancer** (Standard SKU) is the public IP in front of ingress-nginx. This is the one unavoidable paid networking component in any cloud Kubernetes setup.

## CI/CD pipeline

- New pipeline stage after the existing `registry-push-*` jobs: `helm upgrade --install eam ./charts/eam -f values-prod.yaml --namespace eam-prod --wait --timeout 5m`, authenticated via `az aks get-credentials` + `kubelogin`, triggered by the same `rules: *branch-rules` pattern already in `.gitlab-ci.yml`.
- `--wait` plus Kubernetes readiness probes replace the current `verify` job's custom curl-retry loop (`scripts/` health-check polling) — Kubernetes blocks the pipeline natively until new pods report healthy.
- Rolling updates are the Kubernetes Deployment default: the old pod stays serving traffic until the new pod passes its readiness probe, giving zero-downtime deploys. The current `docker compose up -d` approach has a real gap where the old container is gone before the new one is confirmed healthy — this is structurally fixed by the migration, not just configured differently.
- Trivy scanning moves from an always-running sidecar container (`monitoring/scanner/`) to a proper CI pipeline stage: scan immediately after build, before push. The `$TARGETARCH` arch-resolution fix already made to `monitoring/scanner/Dockerfile` this session still applies, just invoked differently (as a one-shot CI step, not a long-running container).

## Observability

- **kube-prometheus-stack** (Helm chart, self-hosted, OSS) replaces the standalone Prometheus/Grafana containers in `docker-compose.monitoring.yml`. Same tools, K8s-native service discovery (auto-detects new pods/services instead of manually configured scrape targets).
- **Loki** (self-hosted, OSS) is a genuinely new requirement, not optional polish: with multiple replicas per service, there is no single `docker compose logs backend` to run anymore — centralized log aggregation across pods is required to debug anything. Grafana already speaks Loki natively.
- Existing Grafana dashboards, alert rules, and Trivy-metrics-via-Pushgateway all carry over conceptually, re-pointed at cluster-native data sources.

## Reliability & scaling

- **Replicas**: backend, frontend, rag-service, ml-service run 2 replicas each at Small scale. `celery_worker` runs 1-2. `celery_beat` must run exactly 1 — it's a scheduler, and two replicas would double-fire scheduled tasks.
- **HorizontalPodAutoscaler** on backend and ml-service (scale 2→4 on CPU >70%) — defined at launch even though not load-bearing at Small scale, so it isn't a scramble later.
- **PodDisruptionBudgets** (`minAvailable: 1` per service) so node upgrades or scaling events never take a service to zero replicas.
- **Resource requests/limits** on every container. Nothing on the current VM enforces this — a stuck migration or a memory leak in one container can starve everything else on the box with no isolation. Kubernetes requests/limits make resource contention explicit and contained per pod.
- **Readiness vs. liveness probes**: readiness gates traffic (a bad deploy shows as "pod never ready" in `kubectl get pods`, no traffic sent); liveness restarts a genuinely wedged pod. This distinction would have surfaced this session's `start.sh` migration bug as a clear, visible "pod not ready" state instead of an opaque failing curl loop in CI logs.

## Migration plan (phased)

1. **Phase 0 — Foundations.** Provision AKS cluster, Azure Database for PostgreSQL, Key Vault, container registry. No application traffic yet.
2. **Phase 1 — Containerize for Kubernetes.** Write Helm chart(s) per service, reusing existing Dockerfiles unchanged. Deploy to an `eam-staging` namespace in the same cluster against a copy of production data. Validate the full stack before any real cutover.
3. **Phase 2 — Data migration.** `pg_dump`/`pg_restore` (or Azure Database Migration Service) from the current VM's Postgres into the new managed instance. Sync MinIO objects to Blob Storage.
4. **Phase 3 — Cutover.** Switch DNS from the VM's IP to the new Load Balancer IP. Monitor closely for 24-48 hours. Keep the old VM running (not deleted) as an instant rollback target during this window.
5. **Phase 4 — Decommission.** After a defined burn-in period (recommend 1-2 weeks of stability), tear down the old VM.

## Cost estimate (Small scale, monthly, ballpark)

| Item | Estimated cost |
|---|---|
| AKS control plane | Free |
| Node pools (4-6 ARM64 VMs) | ~$80-150 |
| Azure Database for PostgreSQL (Small, no HA) | ~$50-80 |
| Azure Load Balancer (Standard SKU) | ~$20 |
| Blob Storage | ~$2-5 |
| Key Vault | ~$1-3 |
| **Total** | **~$150-260/mo** |

This is roughly 2-3x the current single-VM cost — the price of real production reliability (backups, zero-downtime deploys, resource isolation, centralized logging) at this scale. Azure bills compute per-second, so short deliberate test windows (provision → validate → tear down) cost proportionally less than a full month.

## Open questions / risks

- **ARM64 quota is assumed to persist.** If it changes, Dockerfiles are already structured (`$TARGETARCH` branching) to make an amd64 switch straightforward, but node pool SKUs and cost estimates above would need revisiting.
- **GitOps (ArgoCD/Flux) is deliberately deferred**, not rejected. CI-driven `helm upgrade` is recommended for launch because it's one fewer new system for a solo operator to run alongside a brand-new cluster. Revisit once the cluster is boring and stable.
- **Zone-redundant HA on Postgres is off at launch** to control cost. This is a single point of failure until turned on — acceptable at Small scale, worth revisiting before Medium-scale traffic.
- **No load testing has been performed** to validate the "Small scale" sizing assumptions (replica counts, node pool sizing, DB tier). Recommend a load test against the Phase 1 staging namespace before Phase 3 cutover.
