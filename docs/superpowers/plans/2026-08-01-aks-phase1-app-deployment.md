# AKS Phase 1 — Application Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy all 8 EAM app pieces onto the Phase 0 AKS cluster, in a new `eam-staging` namespace, reachable over real HTTPS at a free Azure hostname, with all secrets sourced from Key Vault (never hand-copied).

**Architecture:** Terraform grants the cluster the two new Azure permissions it needs (ACR pull, Key Vault read via the AKS-managed Secrets Store CSI Driver addon) and provisions the app's Postgres database + three missing app secrets. `ingress-nginx` + `cert-manager` go in via Helm CLI as cluster-wide add-ons. The app itself is one Helm chart (`infra/helm/eam/`) with a generic "workload" template (range-based) covering the 6 pieces that share a Deployment+Service shape (backend, celery_worker, celery_beat, ml-service, rag-service, frontend), plus dedicated templates for RabbitMQ and MinIO. Kubernetes Service names exactly match the hostnames already hardcoded in the app (`backend`, `ml-service`, `rag-service`, `minio`, `rabbitmq`) so zero application code changes are needed.

**Tech Stack:** Terraform (azurerm provider, already in use), Helm 3, kubectl, ingress-nginx, cert-manager, GitLab CI (docker buildx).

## Global Constraints

- Reuse the existing ACR `eamdemoacr24102` (resource group `eam-demo-rg`, login server `eamdemoacr24102.azurecr.io`) — do not create a new registry.
- Do not modify or remove any existing `:demo` CI jobs (ARM64, for `eam-demo-vm`) — they must keep working unchanged.
- AKS cluster: `eam-prod-aks` in resource group `eam-prod-rg`, region `polandcentral`. Key Vault: `eam-prod-kv-h597b3` (tenant `604f1a96-cbe8-43f8-abbf-f8eaf5d85730`). Postgres: `eam-prod-psql-1a6mi7.postgres.database.azure.com`.
- All Terraform and kubectl/helm commands run from this session (Claude's own shell) — matches the Phase 0 workaround for the unresolved local Windows `az`-subprocess bug (see memory `aks-phase0-build.md`). The user verifies via Azure Portal / `kubectl` output shown to them, not by running Terraform themselves.
- No secret value is ever written into a Helm values file, Kubernetes manifest, or committed to git in plaintext. Secrets flow: Key Vault → Secrets Store CSI Driver → synced Kubernetes Secret → pod env var.
- Namespace for this plan: `eam-staging` only. `eam-prod` is a later, separate promotion step — out of scope here.
- **Before running Task 3**, the user must have their Groq API key ready (same value as their local `.env`'s `GROQ_API_KEY` — the RAG chat feature needs it). SMTP password is optional for this phase (email sending simply won't work in staging if omitted; nothing else breaks).

---

### Task 1: Install Helm CLI

**Files:**
- Create: `C:\Users\Admin\AppData\Local\helm\helm.exe` (binary, not tracked in git)

**Interfaces:**
- Produces: a `helm` executable at a known path, used by every later task in this plan.

- [ ] **Step 1: Download and extract the Windows amd64 Helm binary**

```bash
mkdir -p "/c/Users/Admin/AppData/Local/helm" && \
curl -sSL -o /tmp/helm.zip https://get.helm.sh/helm-v3.16.4-windows-amd64.zip && \
unzip -o /tmp/helm.zip -d /tmp/helm-extract && \
cp /tmp/helm-extract/windows-amd64/helm.exe "/c/Users/Admin/AppData/Local/helm/helm.exe" && \
rm -rf /tmp/helm.zip /tmp/helm-extract
```

- [ ] **Step 2: Verify it runs**

Run: `/c/Users/Admin/AppData/Local/helm/helm.exe version --short`
Expected: output starting with `v3.16.4`

- [ ] **Step 3: Confirm kubectl already points at the right cluster**

Run: `kubectl config current-context`
Expected: `eam-prod-aks`

No commit for this task — it only installs a local tool, nothing in the repo changes.

---

### Task 2: Terraform — ACR pull permission for AKS

**Files:**
- Create: `infra/terraform/acr.tf`
- Modify: `infra/terraform/variables.tf`

**Interfaces:**
- Produces: the AKS cluster's kubelet identity can now `docker pull` from `eamdemoacr24102.azurecr.io` without embedded credentials — every later Helm-deployed pod referencing that registry relies on this.

- [ ] **Step 1: Add ACR variables**

Append to `infra/terraform/variables.tf`:

```hcl
variable "acr_name" {
  description = "Existing Azure Container Registry to grant AKS pull access to (not managed by this Terraform config — created manually for the demo VM pipeline)."
  type        = string
  default     = "eamdemoacr24102"
}

variable "acr_resource_group_name" {
  description = "Resource group containing the existing ACR."
  type        = string
  default     = "eam-demo-rg"
}
```

- [ ] **Step 2: Create the ACR data source and role assignment**

Create `infra/terraform/acr.tf`:

```hcl
# The ACR already exists (created manually for the ARM64 demo-VM pipeline,
# resource group eam-demo-rg) — not provisioned here, only referenced.
data "azurerm_container_registry" "existing" {
  name                = var.acr_name
  resource_group_name = var.acr_resource_group_name
}

# Lets AKS nodes pull images from that ACR via their kubelet identity —
# no docker-login credentials embedded in any pod spec.
resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                = data.azurerm_container_registry.existing.id
  role_definition_name = "AcrPull"
  principal_id          = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
}
```

- [ ] **Step 3: Plan and verify**

Run: `cd "C:/Users/Admin/Downloads/EAM/EAMSagemCom/infra/terraform" && /c/Users/Admin/AppData/Local/terraform/terraform.exe plan -out=tfplan-task2`
Expected: `Plan: 1 to add, 0 to change, 0 to destroy.` (the new `azurerm_role_assignment.aks_acr_pull`; the data source doesn't count as a plan change)

- [ ] **Step 4: Apply**

Run: `/c/Users/Admin/AppData/Local/terraform/terraform.exe apply tfplan-task2`
Expected: `Apply complete! Resources: 1 added, 0 changed, 0 destroyed.`

- [ ] **Step 5: Verify the role assignment exists in Azure**

Run: `az role assignment list --assignee 47feff28-a2e6-4d76-a357-f635588517e8 --query "[?roleDefinitionName=='AcrPull'].{scope:scope}" -o table`
Expected: one row, scope ending in `.../registries/eamdemoacr24102`

- [ ] **Step 6: Commit**

```bash
git add infra/terraform/acr.tf infra/terraform/variables.tf
git commit -m "feat(terraform): grant AKS kubelet identity AcrPull on existing ACR"
```

---

### Task 3: Terraform — Key Vault Secrets Provider addon, app secrets, Postgres database

**Files:**
- Modify: `infra/terraform/aks.tf`
- Modify: `infra/terraform/keyvault.tf`
- Modify: `infra/terraform/postgres.tf`
- Modify: `infra/terraform/variables.tf`
- Modify: `infra/terraform/outputs.tf`

**Interfaces:**
- Produces: `azurerm_kubernetes_cluster.main.key_vault_secrets_provider[0].secret_identity[0]` (`.client_id`, `.object_id`) — Task 7's `SecretProviderClass` references `.client_id` by its Terraform output value. Also produces Key Vault secrets named `jwt-secret-key`, `groq-api-key`, `smtp-password` (alongside the existing `postgres-admin-password`), and a Postgres database named `asset_management`.

- [ ] **Step 1: Enable the Key Vault Secrets Provider addon on the AKS cluster**

In `infra/terraform/aks.tf`, add this block inside `resource "azurerm_kubernetes_cluster" "main" { ... }`, alongside the existing `identity`, `network_profile`, etc. blocks:

```hcl
  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }
```

- [ ] **Step 2: Add new variables for the two secrets Terraform can't generate itself**

Append to `infra/terraform/variables.tf`:

```hcl
variable "groq_api_key" {
  description = "Groq LLM API key for the RAG chat feature. Set via TF_VAR_groq_api_key, never commit it."
  type        = string
  sensitive   = true
}

variable "smtp_password" {
  description = "SMTP password for outbound email. Optional for the AKS staging POC — leave unset and email sending simply won't work; nothing else breaks. Set via TF_VAR_smtp_password."
  type        = string
  sensitive   = true
  default     = ""
}
```

- [ ] **Step 3: Grant the addon's identity read access, generate/store the three new secrets**

Append to `infra/terraform/keyvault.tf`:

```hcl
# The Secrets Store CSI Driver addon gets its own dedicated managed identity
# (distinct from both the cluster's control-plane identity and the kubelet
# identity) the moment key_vault_secrets_provider is enabled on the cluster.
# This is the identity SecretProviderClass resources authenticate as.
resource "azurerm_role_assignment" "secrets_provider_kv_reader" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id          = azurerm_kubernetes_cluster.main.key_vault_secrets_provider[0].secret_identity[0].object_id
}

# JWT signing secret — generated fresh for this environment rather than
# reusing the local-dev value, since every deployment should have its own.
resource "random_password" "jwt_secret_key" {
  length  = 64
  special = false
}

resource "azurerm_key_vault_secret" "jwt_secret_key" {
  name         = "jwt-secret-key"
  value        = random_password.jwt_secret_key.result
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.operator_kv_admin]
}

resource "azurerm_key_vault_secret" "groq_api_key" {
  name         = "groq-api-key"
  value        = var.groq_api_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.operator_kv_admin]
}

resource "azurerm_key_vault_secret" "smtp_password" {
  name         = "smtp-password"
  value        = var.smtp_password
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.operator_kv_admin]
}
```

- [ ] **Step 4: Create the app's Postgres database**

Append to `infra/terraform/postgres.tf`:

```hcl
# Matches the local docker-compose DB name exactly — the app's DATABASE_URL
# in every environment points at a database literally named "asset_management".
resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = "asset_management"
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "utf8"
}
```

- [ ] **Step 5: Output the addon identity's client ID**

Append to `infra/terraform/outputs.tf`:

```hcl
output "key_vault_secrets_provider_client_id" {
  description = "Client ID of the Secrets Store CSI Driver addon's identity — used in Helm's SecretProviderClass."
  value       = azurerm_kubernetes_cluster.main.key_vault_secrets_provider[0].secret_identity[0].client_id
}
```

- [ ] **Step 6: Plan (with the Groq key supplied)**

Run: `cd "C:/Users/Admin/Downloads/EAM/EAMSagemCom/infra/terraform" && TF_VAR_groq_api_key="<the real key>" /c/Users/Admin/AppData/Local/terraform/terraform.exe plan -out=tfplan-task3`
Expected: `Plan: 6 to add, 1 to change, 0 to destroy.` (5 new resources: role assignment, random_password, 3 key vault secrets, 1 database; 1 change: the AKS cluster gaining the addon block)

- [ ] **Step 7: Apply**

Run: `TF_VAR_groq_api_key="<the real key>" /c/Users/Admin/AppData/Local/terraform/terraform.exe apply tfplan-task3`
Expected: `Apply complete! Resources: 6 added, 1 changed, 0 destroyed.`

- [ ] **Step 8: Capture the addon client ID for later tasks**

Run: `/c/Users/Admin/AppData/Local/terraform/terraform.exe output -raw key_vault_secrets_provider_client_id`
Expected: a GUID printed to stdout — write it down, Task 7 needs it verbatim.

- [ ] **Step 9: Verify all 4 secrets are in the vault**

Run: `az keyvault secret list --vault-name eam-prod-kv-h597b3 --query "[].name" -o tsv`
Expected: `postgres-admin-password`, `jwt-secret-key`, `groq-api-key`, `smtp-password` (4 lines)

- [ ] **Step 10: Commit**

```bash
git add infra/terraform/aks.tf infra/terraform/keyvault.tf infra/terraform/postgres.tf infra/terraform/variables.tf infra/terraform/outputs.tf
git commit -m "feat(terraform): enable Key Vault Secrets Provider addon, add app secrets and Postgres database"
```

---

### Task 4: Cluster add-ons — ingress-nginx + cert-manager

**Files:**
- Create: `infra/helm/cluster-addons/cluster-issuer-staging.yaml`
- Create: `infra/helm/cluster-addons/cluster-issuer-prod.yaml`

**Interfaces:**
- Produces: a public LoadBalancer IP with Azure DNS label `eam-staging` (hostname `eam-staging.polandcentral.cloudapp.azure.com`), and two `ClusterIssuer` resources (`letsencrypt-staging`, `letsencrypt-prod`) that Task 9's Ingress references by name.

- [ ] **Step 1: Add the ingress-nginx and jetstack Helm repos**

```bash
HELM="/c/Users/Admin/AppData/Local/helm/helm.exe"
$HELM repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
$HELM repo add jetstack https://charts.jetstack.io
$HELM repo update
```

- [ ] **Step 2: Install ingress-nginx with the Azure DNS label annotation**

```bash
$HELM install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=eam-staging \
  --set controller.replicaCount=1
```

- [ ] **Step 3: Wait for the public IP and confirm the hostname resolves**

Run: `kubectl get svc -n ingress-nginx ingress-nginx-controller -w`
Expected: `EXTERNAL-IP` column fills in with a real IP within a few minutes (Ctrl+C once it does)

Run: `nslookup eam-staging.polandcentral.cloudapp.azure.com`
Expected: resolves to the same IP shown above (DNS propagation may take a couple minutes — retry if it fails immediately)

- [ ] **Step 4: Install cert-manager**

```bash
$HELM install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set crds.enabled=true
```

Run: `kubectl get pods -n cert-manager`
Expected: 3 pods (`cert-manager`, `cert-manager-cainjector`, `cert-manager-webhook`), all `Running`

- [ ] **Step 5: Create the staging Let's Encrypt ClusterIssuer (used first, to avoid burning the real rate limit while debugging)**

Create `infra/helm/cluster-addons/cluster-issuer-staging.yaml`:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: hamza.mbarki2002@gmail.com
    privateKeySecretRef:
      name: letsencrypt-staging-key
    solvers:
      - http01:
          ingress:
            ingressClassName: nginx
```

- [ ] **Step 6: Create the production Let's Encrypt ClusterIssuer (switch to this once staging cert issuance is confirmed working)**

Create `infra/helm/cluster-addons/cluster-issuer-prod.yaml`:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: hamza.mbarki2002@gmail.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            ingressClassName: nginx
```

- [ ] **Step 7: Apply both and verify they're Ready**

```bash
kubectl apply -f infra/helm/cluster-addons/cluster-issuer-staging.yaml
kubectl apply -f infra/helm/cluster-addons/cluster-issuer-prod.yaml
kubectl get clusterissuer
```

Expected: both `letsencrypt-staging` and `letsencrypt-prod` show `READY: True` (may take ~30s)

- [ ] **Step 8: Commit**

```bash
git add infra/helm/cluster-addons/cluster-issuer-staging.yaml infra/helm/cluster-addons/cluster-issuer-prod.yaml
git commit -m "feat(k8s): install ingress-nginx + cert-manager, add Let's Encrypt ClusterIssuers"
```

---

### Task 5: New CI job — build and push x86 images

**Files:**
- Modify: `.gitlab-ci.yml`

**Interfaces:**
- Produces: 4 images in ACR tagged `:aks-staging` (`backend`, `frontend`, `ml-service`, `rag-service`), `linux/amd64`. `celery-worker`/`celery-beat` reuse the `backend` image (different `command:`, set in Helm values, not a separate build).

- [ ] **Step 1: Add the new jobs after the existing `registry-push-frontend` job**

In `.gitlab-ci.yml`, insert immediately after the `registry-push-frontend` job (currently ending at line 610):

```yaml
# ─── AKS x86 image builds (new cluster target, existing :demo ARM64 jobs above are untouched) ──

.registry_push_aks_base: &registry_push_aks_base
  stage: registry-push
  needs: [quality-gate]
  tags: [local]
  image: docker:24-cli
  rules: *branch-rules
  timeout: 2 hours
  allow_failure: false
  when: manual

registry-push-backend-aks:
  <<: *registry_push_aks_base
  script:
    - docker buildx create --name eamaksbuilder --use 2>/dev/null || docker buildx use eamaksbuilder
    - echo "$ACR_PASSWORD" | docker login $ACR_LOGIN_SERVER -u $ACR_USERNAME --password-stdin
    - docker buildx build --platform linux/amd64 -t "$ACR_LOGIN_SERVER/backend:aks-staging" --push ./app/backend

registry-push-ml-service-aks:
  <<: *registry_push_aks_base
  script:
    - docker buildx create --name eamaksbuilder --use 2>/dev/null || docker buildx use eamaksbuilder
    - echo "$ACR_PASSWORD" | docker login $ACR_LOGIN_SERVER -u $ACR_USERNAME --password-stdin
    - docker buildx build --platform linux/amd64 -t "$ACR_LOGIN_SERVER/ml-service:aks-staging" --push ./app/ml-microservice

registry-push-rag-service-aks:
  <<: *registry_push_aks_base
  script:
    - docker buildx create --name eamaksbuilder --use 2>/dev/null || docker buildx use eamaksbuilder
    - echo "$ACR_PASSWORD" | docker login $ACR_LOGIN_SERVER -u $ACR_USERNAME --password-stdin
    - docker buildx build --platform linux/amd64 -t "$ACR_LOGIN_SERVER/rag-service:aks-staging" --push ./app/rag-service

registry-push-frontend-aks:
  <<: *registry_push_aks_base
  script:
    - docker buildx create --name eamaksbuilder --use 2>/dev/null || docker buildx use eamaksbuilder
    - echo "$ACR_PASSWORD" | docker login $ACR_LOGIN_SERVER -u $ACR_USERNAME --password-stdin
    # Empty VITE_API_BASE_URL -> frontend calls relative /api/* paths, proxied
    # same-origin by its own nginx.conf. Works unchanged for staging AND prod,
    # no rebuild needed when promoting.
    - docker buildx build --platform linux/amd64 --build-arg VITE_API_BASE_URL= -t "$ACR_LOGIN_SERVER/frontend:aks-staging" --push ./app/frontend
```

`when: manual` — these are new and unproven, so they don't fire automatically on every push like the `:demo` jobs do; trigger them by hand from the GitLab pipeline UI when you're ready to build.

- [ ] **Step 2: Trigger the 4 jobs manually from GitLab's pipeline UI, wait for them to go green**

No local command — this runs on the GitLab runner. Confirm in the GitLab UI that all 4 `*-aks` jobs succeed.

- [ ] **Step 3: Verify the images landed in ACR**

Run: `az acr repository show-tags -n eamdemoacr24102 --repository backend --query "[?contains(@, 'aks-staging')]" -o tsv`
Expected: `aks-staging`
(repeat with `--repository frontend`, `--repository ml-service`, `--repository rag-service`)

- [ ] **Step 4: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "feat(ci): add manual x86/amd64 image build jobs for AKS, tagged :aks-staging"
```

---

### Task 6: Helm chart scaffold

**Files:**
- Create: `infra/helm/eam/Chart.yaml`
- Create: `infra/helm/eam/values.yaml`
- Create: `infra/helm/eam/templates/_helpers.tpl`

**Interfaces:**
- Produces: the chart skeleton every later task's templates render against — `.Values.image.registry`, `.Values.image.tag`, `.Values.workloads.<name>` (map), `.Values.postgres`, `.Values.keyVault`, `.Values.ingress`.

- [ ] **Step 1: Chart.yaml**

Create `infra/helm/eam/Chart.yaml`:

```yaml
apiVersion: v2
name: eam
description: EAM SagemCom application — all pieces (backend, frontend, ml-service, rag-service, celery, rabbitmq, minio)
type: application
version: 0.1.0
appVersion: "1.0.0"
```

- [ ] **Step 2: Base values.yaml (environment-agnostic defaults)**

Create `infra/helm/eam/values.yaml`:

```yaml
image:
  registry: eamdemoacr24102.azurecr.io
  tag: aks-staging
  pullPolicy: IfNotPresent

postgres:
  fqdn: eam-prod-psql-1a6mi7.postgres.database.azure.com
  db: asset_management
  user: eamadmin

keyVault:
  name: eam-prod-kv-h597b3
  tenantId: "604f1a96-cbe8-43f8-abbf-f8eaf5d85730"
  clientId: ""  # set in values-staging.yaml from `terraform output key_vault_secrets_provider_client_id`

ingress:
  hostname: eam-staging.polandcentral.cloudapp.azure.com
  clusterIssuer: letsencrypt-staging

workloads:
  backend:
    image: backend
    port: 8000
    replicas: 1
    command: []
    healthPath: /api/v1/health
    env:
      HOST: "0.0.0.0"
      PORT: "8000"
      ENVIRONMENT: "production"
      PYTHONUNBUFFERED: "1"
      CELERY_BROKER_URL: "amqp://guest:guest@rabbitmq:5672//"
      OSS_SERVICE_URL: "http://minio:9000/"
      OSS_API_KEY: "minioadmin"
      OSS_SECRET_KEY: "minioadmin"
      OSS_PUBLIC_URL: "http://minio:9000/"
      ML_SERVICE_URL: "http://ml-service:8000"
      RAG_SERVICE_URL: "http://rag-service:8003"
      ML_ALLOW_SYNTHETIC_TELEMETRY: "false"
      JWT_ALGORITHM: "HS256"
      JWT_EXPIRE_MINUTES: "1440"
  celery-worker:
    image: backend
    port: 0
    replicas: 1
    command: ["celery", "-A", "core.celery_app", "worker", "-l", "info"]
    healthPath: ""
    env:
      ENVIRONMENT: "production"
      PYTHONUNBUFFERED: "1"
      CELERY_BROKER_URL: "amqp://guest:guest@rabbitmq:5672//"
      OSS_SERVICE_URL: "http://minio:9000/"
      OSS_API_KEY: "minioadmin"
      OSS_SECRET_KEY: "minioadmin"
      OSS_PUBLIC_URL: "http://minio:9000/"
  celery-beat:
    image: backend
    port: 0
    replicas: 1
    command: ["celery", "-A", "core.celery_app", "beat", "-l", "info"]
    healthPath: ""
    env:
      ENVIRONMENT: "production"
      PYTHONUNBUFFERED: "1"
      CELERY_BROKER_URL: "amqp://guest:guest@rabbitmq:5672//"
      OSS_SERVICE_URL: "http://minio:9000/"
      OSS_API_KEY: "minioadmin"
      OSS_SECRET_KEY: "minioadmin"
  ml-service:
    image: ml-service
    port: 8000
    replicas: 1
    command: []
    healthPath: /health
    env:
      PYTHONUNBUFFERED: "1"
      PYTHONPATH: "/app"
  rag-service:
    image: rag-service
    port: 8003
    replicas: 1
    command: []
    healthPath: /health
    env:
      PYTHONUNBUFFERED: "1"
      RERANK_ENABLED: "true"
      HYBRID_ENABLED: "true"
  frontend:
    image: frontend
    port: 80
    replicas: 1
    command: []
    healthPath: /health
    env: {}
```

- [ ] **Step 3: Shared naming helper**

Create `infra/helm/eam/templates/_helpers.tpl`:

```
{{- define "eam.fullname" -}}
{{ .name }}
{{- end -}}
```

(Kept minimal — Service names must exactly match the map keys in `.Values.workloads`, e.g. `backend`, `ml-service`, since those are the hostnames already hardcoded in `nginx.conf` and the backend's own env defaults.)

- [ ] **Step 4: Lint the chart (will show "no objects" warnings until Task 7-9 add templates — that's expected here)**

Run: `/c/Users/Admin/AppData/Local/helm/helm.exe lint infra/helm/eam`
Expected: `1 chart(s) linted, 0 chart(s) failed`

- [ ] **Step 5: Commit**

```bash
git add infra/helm/eam/Chart.yaml infra/helm/eam/values.yaml infra/helm/eam/templates/_helpers.tpl
git commit -m "feat(helm): scaffold eam chart with shared values for all 8 workloads"
```

---

### Task 7: Helm templates — SecretProviderClass + generic workload (Deployment + Service)

**Files:**
- Create: `infra/helm/eam/templates/secretproviderclass.yaml`
- Create: `infra/helm/eam/templates/workload.yaml`

**Interfaces:**
- Consumes: `.Values.keyVault.{name,tenantId,clientId}`, `.Values.workloads` (map), `.Values.postgres.{fqdn,db,user}`, `.Values.image.{registry,tag,pullPolicy}`
- Produces: a `Secret` named `eam-secrets` (synced from Key Vault, keys `postgres-password`/`jwt-secret-key`/`groq-api-key`/`smtp-password`) that `workload.yaml`'s Deployments reference; one `Deployment` + one `Service` per entry in `.Values.workloads` (Service only created when `port` is nonzero — celery-worker/celery-beat have no port).

- [ ] **Step 1: SecretProviderClass — mounts Key Vault secrets and syncs them into a native K8s Secret**

Create `infra/helm/eam/templates/secretproviderclass.yaml`:

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: eam-secrets-provider
spec:
  provider: azure
  secretObjects:
    - secretName: eam-secrets
      type: Opaque
      data:
        - objectName: postgres-admin-password
          key: postgres-password
        - objectName: jwt-secret-key
          key: jwt-secret-key
        - objectName: groq-api-key
          key: groq-api-key
        - objectName: smtp-password
          key: smtp-password
  parameters:
    usePodIdentity: "false"
    useVMManagedIdentity: "false"
    clientID: {{ .Values.keyVault.clientId | quote }}
    keyvaultName: {{ .Values.keyVault.name | quote }}
    tenantId: {{ .Values.keyVault.tenantId | quote }}
    objects: |
      array:
        - |
          objectName: postgres-admin-password
          objectType: secret
        - |
          objectName: jwt-secret-key
          objectType: secret
        - |
          objectName: groq-api-key
          objectType: secret
        - |
          objectName: smtp-password
          objectType: secret
```

- [ ] **Step 2: Generic workload template — Deployment + optional Service, looping over `.Values.workloads`**

Create `infra/helm/eam/templates/workload.yaml`:

```yaml
{{- range $name, $cfg := .Values.workloads }}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ $name }}
spec:
  replicas: {{ $cfg.replicas }}
  selector:
    matchLabels:
      app: {{ $name }}
  template:
    metadata:
      labels:
        app: {{ $name }}
    spec:
      # Every pod needs the CSI volume mounted so eam-secrets gets synced,
      # even workloads (frontend) that don't consume secrets directly —
      # cheap and keeps this template uniform.
      volumes:
        - name: secrets-store
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: eam-secrets-provider
      containers:
        - name: {{ $name }}
          image: "{{ $.Values.image.registry }}/{{ $cfg.image }}:{{ $.Values.image.tag }}"
          imagePullPolicy: {{ $.Values.image.pullPolicy }}
          {{- if $cfg.command }}
          command: {{ toYaml $cfg.command | nindent 12 }}
          {{- end }}
          {{- if gt ($cfg.port | int) 0 }}
          ports:
            - containerPort: {{ $cfg.port }}
          {{- end }}
          volumeMounts:
            - name: secrets-store
              mountPath: "/mnt/secrets-store"
              readOnly: true
          env:
            {{- range $k, $v := $cfg.env }}
            - name: {{ $k }}
              value: {{ $v | quote }}
            {{- end }}
            {{- if or (eq $name "backend") (eq $name "celery-worker") (eq $name "celery-beat") }}
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: eam-secrets
                  key: postgres-password
            - name: DATABASE_URL
              value: "postgresql+asyncpg://{{ $.Values.postgres.user }}:$(POSTGRES_PASSWORD)@{{ $.Values.postgres.fqdn }}:5432/{{ $.Values.postgres.db }}?ssl=require"
            - name: JWT_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: eam-secrets
                  key: jwt-secret-key
            - name: GROQ_API_KEY
              valueFrom:
                secretKeyRef:
                  name: eam-secrets
                  key: groq-api-key
            - name: SMTP_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: eam-secrets
                  key: smtp-password
            - name: FRONTEND_URL
              value: "https://{{ $.Values.ingress.hostname }}"
            {{- end }}
          {{- if $cfg.healthPath }}
          readinessProbe:
            httpGet:
              path: {{ $cfg.healthPath }}
              port: {{ $cfg.port }}
            initialDelaySeconds: 20
            periodSeconds: 10
          {{- end }}
---
{{- if gt ($cfg.port | int) 0 }}
apiVersion: v1
kind: Service
metadata:
  name: {{ $name }}
spec:
  selector:
    app: {{ $name }}
  ports:
    - port: {{ $cfg.port }}
      targetPort: {{ $cfg.port }}
{{- end }}
---
{{- end }}
```

- [ ] **Step 3: Render locally and eyeball the backend Deployment's env block**

Run: `/c/Users/Admin/AppData/Local/helm/helm.exe template eam infra/helm/eam --set keyVault.clientId=00000000-0000-0000-0000-000000000000 | grep -A 30 "name: backend$"`
Expected: shows `DATABASE_URL` built from `$(POSTGRES_PASSWORD)`, `JWT_SECRET_KEY`/`GROQ_API_KEY`/`SMTP_PASSWORD` as `secretKeyRef`s, and a `readinessProbe` on `/api/v1/health`

- [ ] **Step 4: Commit**

```bash
git add infra/helm/eam/templates/secretproviderclass.yaml infra/helm/eam/templates/workload.yaml
git commit -m "feat(helm): add SecretProviderClass and generic workload template for 6 shared-shape services"
```

---

### Task 8: Helm templates — RabbitMQ + MinIO

**Files:**
- Create: `infra/helm/eam/templates/rabbitmq.yaml`
- Create: `infra/helm/eam/templates/minio.yaml`
- Create: `infra/helm/eam/templates/minio-init-job.yaml`

**Interfaces:**
- Produces: `Service`s named `rabbitmq` and `minio` (matching the hostnames the app already expects), and a post-install Helm hook Job that creates the `attachments`/`rag-docs` buckets — mirrors docker-compose's `minio_init` service exactly.

- [ ] **Step 1: RabbitMQ — official image, ephemeral storage (acceptable for a staging POC; queue contents aren't data worth persisting)**

Create `infra/helm/eam/templates/rabbitmq.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rabbitmq
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rabbitmq
  template:
    metadata:
      labels:
        app: rabbitmq
    spec:
      containers:
        - name: rabbitmq
          image: rabbitmq:3-management-alpine
          ports:
            - containerPort: 5672
            - containerPort: 15672
---
apiVersion: v1
kind: Service
metadata:
  name: rabbitmq
spec:
  selector:
    app: rabbitmq
  ports:
    - name: amqp
      port: 5672
      targetPort: 5672
    - name: management
      port: 15672
      targetPort: 15672
```

- [ ] **Step 2: MinIO — official image, persistent volume (holds real uploaded documents)**

Create `infra/helm/eam/templates/minio.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: minio-data
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 5Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
spec:
  replicas: 1
  strategy:
    type: Recreate  # ReadWriteOnce volume — avoid two pods mounting it at once during rollout
  selector:
    matchLabels:
      app: minio
  template:
    metadata:
      labels:
        app: minio
    spec:
      containers:
        - name: minio
          image: minio/minio:latest
          args: ["server", "/data", "--console-address", ":9001"]
          env:
            - name: MINIO_ROOT_USER
              value: "minioadmin"
            - name: MINIO_ROOT_PASSWORD
              value: "minioadmin"
          ports:
            - containerPort: 9000
            - containerPort: 9001
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: minio-data
---
apiVersion: v1
kind: Service
metadata:
  name: minio
spec:
  selector:
    app: minio
  ports:
    - name: api
      port: 9000
      targetPort: 9000
    - name: console
      port: 9001
      targetPort: 9001
```

- [ ] **Step 3: MinIO bucket init — Helm post-install hook Job, same commands as docker-compose's `minio_init`**

Create `infra/helm/eam/templates/minio-init-job.yaml`:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: minio-init
  annotations:
    "helm.sh/hook": post-install,post-upgrade
    "helm.sh/hook-weight": "1"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  backoffLimit: 3
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: minio-init
          image: minio/mc:latest
          command: ["/bin/sh", "-c"]
          args:
            - |
              until mc alias set local http://minio:9000 minioadmin minioadmin; do echo "waiting for minio..."; sleep 3; done
              mc mb -p local/attachments || true
              mc anonymous set download local/attachments || true
              mc mb -p local/rag-docs || true
              mc anonymous set download local/rag-docs || true
```

- [ ] **Step 4: Render and check both objects appear**

Run: `/c/Users/Admin/AppData/Local/helm/helm.exe template eam infra/helm/eam --set keyVault.clientId=00000000-0000-0000-0000-000000000000 | grep "^kind:"`
Expected: includes `kind: Deployment` (x8), `kind: Service` (x7 — 6 workload Services + rabbitmq + minio is actually 8; frontend/backend/ml-service/rag-service/rabbitmq/minio = 6 real Services, celery-worker/celery-beat have none), `kind: PersistentVolumeClaim` (x1), `kind: Job` (x1), `kind: SecretProviderClass` (x1)

- [ ] **Step 5: Commit**

```bash
git add infra/helm/eam/templates/rabbitmq.yaml infra/helm/eam/templates/minio.yaml infra/helm/eam/templates/minio-init-job.yaml
git commit -m "feat(helm): add RabbitMQ and MinIO (with bucket-init hook Job) templates"
```

---

### Task 9: Helm templates — Ingress + staging values

**Files:**
- Create: `infra/helm/eam/templates/ingress.yaml`
- Create: `infra/helm/eam/values-staging.yaml`

**Interfaces:**
- Consumes: `.Values.ingress.{hostname,clusterIssuer}`
- Produces: an `Ingress` routing all traffic for `eam-staging.polandcentral.cloudapp.azure.com` to the `frontend` Service on port 80, TLS terminated by cert-manager. Frontend's own `nginx.conf` (unchanged) then internally proxies `/api/*` to the `backend` Service — no path-splitting needed at the ingress level.

- [ ] **Step 1: Ingress — single rule, everything to frontend**

Create `infra/helm/eam/templates/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: eam-ingress
  annotations:
    cert-manager.io/cluster-issuer: {{ .Values.ingress.clusterIssuer }}
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - {{ .Values.ingress.hostname }}
      secretName: eam-tls
  rules:
    - host: {{ .Values.ingress.hostname }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
```

- [ ] **Step 2: Staging values — fills in the addon client ID from Task 3's Terraform output**

Create `infra/helm/eam/values-staging.yaml` (replace `<PASTE_CLIENT_ID_FROM_TASK_3_STEP_8>` with the real GUID captured earlier):

```yaml
keyVault:
  clientId: "<PASTE_CLIENT_ID_FROM_TASK_3_STEP_8>"

ingress:
  hostname: eam-staging.polandcentral.cloudapp.azure.com
  clusterIssuer: letsencrypt-staging
```

- [ ] **Step 3: Final full-chart lint**

Run: `/c/Users/Admin/AppData/Local/helm/helm.exe lint infra/helm/eam -f infra/helm/eam/values-staging.yaml`
Expected: `1 chart(s) linted, 0 chart(s) failed`

- [ ] **Step 4: Commit**

```bash
git add infra/helm/eam/templates/ingress.yaml infra/helm/eam/values-staging.yaml
git commit -m "feat(helm): add Ingress and eam-staging values file"
```

---

### Task 10: Deploy to eam-staging and verify end-to-end

**Files:**
- None (deployment step — nothing new to create; this task exercises everything built in Tasks 1-9)

**Interfaces:**
- Consumes: the full `infra/helm/eam` chart from Tasks 6-9, the CSI driver addon and secrets from Task 3, the images from Task 5, ingress-nginx/cert-manager from Task 4.

- [ ] **Step 1: Create the namespace**

Run: `kubectl create namespace eam-staging`
Expected: `namespace/eam-staging created`

- [ ] **Step 2: Install the chart**

```bash
HELM="/c/Users/Admin/AppData/Local/helm/helm.exe"
$HELM install eam infra/helm/eam -n eam-staging -f infra/helm/eam/values-staging.yaml
```

Expected: `STATUS: deployed`

- [ ] **Step 3: Watch pods come up**

Run: `kubectl get pods -n eam-staging -w`
Expected: all pods eventually `Running` (backend/celery may restart once or twice while waiting on the DB — that's the `start.sh` retry loop, not a failure; give it ~2 minutes). Ctrl+C once stable.

If any pod is stuck `CrashLoopBackOff`: `kubectl logs -n eam-staging <pod-name>` and diagnose before continuing — do not skip ahead with broken pods.

If a pod is stuck `Pending`: `kubectl describe pod -n eam-staging <pod-name>` and check the Events section for `Insufficient memory`/`Insufficient cpu` — this is the resource-sizing risk flagged in the design spec (ml-service's TensorFlow footprint on small `B2s_v2` nodes). If you see it, scale the user node pool rather than trimming the image: `az aks nodepool scale -g eam-prod-rg --cluster-name eam-prod-aks -n user --node-count 3`.

- [ ] **Step 4: Confirm the secret synced correctly**

Run: `kubectl get secret eam-secrets -n eam-staging -o jsonpath='{.data.postgres-password}' | base64 -d | wc -c`
Expected: a nonzero character count (proves the CSI driver actually pulled and synced the real Key Vault value, not an empty placeholder)

- [ ] **Step 5: Confirm the HTTPS cert issued**

Run: `kubectl get certificate -n eam-staging`
Expected: `eam-tls` shows `READY: True` (may take 1-2 minutes for the HTTP-01 challenge to complete)

- [ ] **Step 6: Hit the live URL**

Run: `curl -sf https://eam-staging.polandcentral.cloudapp.azure.com/health`
Expected: `healthy` (served by frontend's nginx, confirms ingress + TLS + frontend pod all working)

Run: `curl -sf https://eam-staging.polandcentral.cloudapp.azure.com/api/v1/health`
Expected: HTTP 200 (confirms frontend's internal `/api/` proxy → backend Service → backend pod → Postgres connection all working)

- [ ] **Step 7: Manual browser check — login and RAG upload**

Open `https://eam-staging.polandcentral.cloudapp.azure.com` in a browser, log in with the same dev credentials used locally (see memory `dev-login-creds.md`), upload one document through the RAG UI to confirm MinIO wiring, then send one message in the chat assistant to confirm the full path (frontend → backend → Postgres → ml-service/rag-service, per the design spec's testing plan). Report back what you see — this step needs your eyes, not a command.

- [ ] **Step 8: Update memory with the live staging state**

No code changes — after Step 7 confirms working, this plan's implementation is complete. Record the outcome in memory `aks-phase0-build.md` (staging live, URL, what was verified) so future sessions don't re-discover this from scratch.
