# AKS Phase 0 — Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provision the AKS cluster, Azure Database for PostgreSQL (with pgvector), and Key Vault via Terraform — infrastructure only, no application deployed, no traffic served. This is Phase 0 of `docs/superpowers/specs/2026-07-30-aks-production-migration-design.md`.

**Architecture:** Terraform (`azurerm` provider) manages all Phase 0 resources except the Terraform remote-state backend itself, which is bootstrapped once via plain `az` CLI (standard chicken-and-egg pattern — you can't point Terraform's backend config at a storage account Terraform itself hasn't created yet). All resource names that must be globally unique (Postgres server, Key Vault, state storage account) get a short random suffix generated once and reused on every apply.

**Tech Stack:** Terraform >= 1.7, `azurerm` provider `~> 5.0`, `random` provider `~> 3.6`, Azure CLI (`az`) for auth and the one-time bootstrap step, `kubectl` for cluster verification.

**IMPORTANT — who runs these commands:** This environment has no Azure CLI session authenticated against your subscription. Every `az`/`terraform`/`kubectl` command in this plan must be run by you, in your own terminal, exactly as shown — the same pattern as the VM work earlier this session. Code/HCL files get written to the repo; commands that touch real Azure resources do not get run automatically.

## Global Constraints

(Copied from the approved design spec — every task below implicitly follows these.)

- Single region: `germanywestcentral`.
- ARM64 (Ampere Altra) AKS node pools throughout — subscription only has ARM64 VM quota approved.
- System pool: 2 nodes. User pool: 2-4 nodes, autoscaling.
- Azure Database for PostgreSQL Flexible Server, Small/burstable tier, `pgvector` extension enabled, **no zone-redundant HA at launch** (cost control — explicit open risk in the spec).
- Key Vault for secrets (the Secrets Store CSI Driver wiring itself is Phase 1 — this plan only provisions the vault).
- **Do not provision Azure Container Registry.** Keep using the existing GitLab Container Registry (`registry.gitlab.com/sagemcom-group4/eamhamza/*`) — it already works, provisioning ACR would be pure scope creep for Phase 0.
- AKS API server public but IP-restricted to admin IPs + the GitLab runner's egress IP.
- Phase 0 produces infrastructure only — verified via direct `az`/`kubectl`/`psql` checks, not application health checks (no app is deployed yet).

## File Structure

```
infra/terraform/
├── README.md              # one-time bootstrap instructions (state backend)
├── versions.tf            # required_providers + backend "azurerm" block
├── providers.tf           # provider "azurerm" {} configuration
├── variables.tf           # all input variables
├── terraform.tfvars.example  # example values (real tfvars is gitignored)
├── network.tf             # resource group, VNet, subnet
├── aks.tf                 # AKS cluster + node pools
├── keyvault.tf             # Key Vault
├── postgres.tf            # Azure Database for PostgreSQL Flexible Server
├── outputs.tf              # cluster name, kube config command, postgres FQDN, vault URI
└── .gitignore              # *.tfstate*, .terraform/, terraform.tfvars
```

**Interfaces produced by this plan (Phase 1 will consume these):**
- `outputs.tf` exposes: `aks_cluster_name` (string), `aks_resource_group` (string), `postgres_fqdn` (string), `postgres_admin_login` (string, sensitive), `key_vault_name` (string), `key_vault_uri` (string).
- AKS cluster is reachable via `az aks get-credentials --resource-group <aks_resource_group> --name <aks_cluster_name>`.

---

### Task 1: Bootstrap Terraform remote state backend

**Files:**
- Create: `infra/terraform/README.md`
- Create: `infra/terraform/.gitignore`

**Interfaces:**
- Produces: an Azure Storage Account + blob container that every later `terraform init` in this directory points at. Name of the storage account is generated in this task and must be written into `versions.tf` in Task 2.

- [ ] **Step 1: Run the one-time bootstrap commands yourself**

```bash
az login
az account show --query "{subscriptionId:id, name:name}" -o table
```

Confirm this prints the correct subscription before continuing.

```bash
RANDOM_SUFFIX=$(openssl rand -hex 3)
echo "Save this suffix, you need it in Task 2: $RANDOM_SUFFIX"

az group create \
  --name eam-tfstate-rg \
  --location germanywestcentral

az storage account create \
  --name "eamtfstate${RANDOM_SUFFIX}" \
  --resource-group eam-tfstate-rg \
  --location germanywestcentral \
  --sku Standard_LRS \
  --encryption-services blob \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false

az storage container create \
  --name tfstate \
  --account-name "eamtfstate${RANDOM_SUFFIX}" \
  --auth-mode login
```

Expected: each command prints a JSON object with `"provisioningState": "Succeeded"` (storage account) or the container create prints `"created": true`.

- [ ] **Step 2: Write the bootstrap README**

```markdown
# Terraform state backend — bootstrap (one-time, already done)

This directory's Terraform state lives in Azure Blob Storage, in a resource
group (`eam-tfstate-rg`) that is intentionally **not** managed by this same
Terraform config — you can't have Terraform manage the backend it's storing
its own state in without a chicken-and-egg problem.

Storage account name: `eamtfstate<suffix>` — see `versions.tf` for the exact
name in use. Container: `tfstate`. State file key: `phase0.tfstate`.

**Do not run `terraform destroy` against `eam-tfstate-rg` unless you are
intentionally tearing down every environment this backend serves.**

If you ever need to recreate the backend from scratch, rerun the `az group
create` / `az storage account create` / `az storage container create`
commands in Task 1 of `docs/superpowers/plans/2026-07-30-aks-phase0-foundations.md`
with a new random suffix, then update the `backend "azurerm"` block in
`versions.tf` to match.
```

- [ ] **Step 3: Write the gitignore**

```
*.tfstate
*.tfstate.*
.terraform/
.terraform.lock.hcl
terraform.tfvars
```

`.terraform.lock.hcl` is excluded here deliberately for a solo-operator setup with infrequent applies — re-resolve providers fresh each time rather than risk a stale lockfile blocking a legitimate provider upgrade. Revisit (stop ignoring it) once more than one person runs `terraform apply` against this config.

- [ ] **Step 4: Commit**

```bash
git add infra/terraform/README.md infra/terraform/.gitignore
git commit -m "docs: add Terraform state backend bootstrap notes for AKS Phase 0"
```

---

### Task 2: Terraform project skeleton — providers, backend, variables

**Files:**
- Create: `infra/terraform/versions.tf`
- Create: `infra/terraform/providers.tf`
- Create: `infra/terraform/variables.tf`
- Create: `infra/terraform/terraform.tfvars.example`

**Interfaces:**
- Consumes: `eamtfstate<suffix>` storage account name from Task 1, Step 1.
- Produces: `var.project_name`, `var.location`, `var.environment`, `var.admin_ip_ranges` (list(string)), `var.postgres_admin_login`, `var.postgres_admin_password` (sensitive) — every later task's `.tf` file references these variables by name.

- [ ] **Step 1: Write `versions.tf`**

Replace `<suffix>` with the actual value from Task 1, Step 1.

```hcl
terraform {
  required_version = ">= 1.7.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "azurerm" {
    resource_group_name = "eam-tfstate-rg"
    storage_account_name = "eamtfstate<suffix>"
    container_name       = "tfstate"
    key                   = "phase0.tfstate"
  }
}
```

- [ ] **Step 2: Write `providers.tf`**

```hcl
provider "azurerm" {
  features {}

  # First-time subscription setup — registers every resource provider this
  # config needs (Microsoft.ContainerService, Microsoft.DBforPostgreSQL,
  # Microsoft.KeyVault, Microsoft.Network, Microsoft.Storage) instead of
  # relying on the provider's default "core" subset, which can miss one of
  # these and fail the first apply with a cryptic "provider not registered"
  # error. Safe to narrow later once the subscription is fully set up.
  resource_provider_registrations = "all"
}

provider "random" {}
```

- [ ] **Step 3: Write `variables.tf`**

```hcl
variable "project_name" {
  description = "Short name prefixed onto every resource name."
  type        = string
  default     = "eam-prod"
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "germanywestcentral"
}

variable "environment" {
  description = "Environment tag applied to every resource."
  type        = string
  default     = "production"
}

variable "admin_ip_ranges" {
  description = <<-EOT
    CIDR ranges allowed to reach the AKS API server (your admin IP(s) and
    the GitLab runner's egress IP, each as e.g. "203.0.113.5/32").
  EOT
  type = list(string)
}

variable "system_node_count" {
  description = "Fixed node count for the system node pool."
  type        = number
  default     = 2
}

variable "user_node_min_count" {
  description = "Minimum node count for the autoscaling user node pool."
  type        = number
  default     = 2
}

variable "user_node_max_count" {
  description = "Maximum node count for the autoscaling user node pool."
  type        = number
  default     = 4
}

variable "postgres_admin_login" {
  description = "Admin username for the Postgres Flexible Server."
  type        = string
  default     = "eamadmin"
}

variable "postgres_admin_password" {
  description = "Admin password for the Postgres Flexible Server. Set via TF_VAR_postgres_admin_password env var, never commit it."
  type        = string
  sensitive   = true
}
```

- [ ] **Step 4: Write `terraform.tfvars.example`**

```hcl
# Copy to terraform.tfvars (gitignored) and fill in real values.
# postgres_admin_password is intentionally NOT here — export it as
# TF_VAR_postgres_admin_password in your shell instead, so it never touches
# a file on disk.

admin_ip_ranges = [
  "203.0.113.5/32",  # replace with your actual admin IP
]
```

- [ ] **Step 5: Verify `terraform init` succeeds**

```bash
cd infra/terraform
terraform init
```

Expected: ends with `Terraform has been successfully initialized!`. If it fails with a backend/storage error, confirm the storage account name in `versions.tf` exactly matches what Task 1 created (`az storage account list --resource-group eam-tfstate-rg -o table`).

- [ ] **Step 6: Commit**

```bash
git add infra/terraform/versions.tf infra/terraform/providers.tf infra/terraform/variables.tf infra/terraform/terraform.tfvars.example
git commit -m "feat: add Terraform provider/backend/variables skeleton for AKS Phase 0"
```

---

### Task 3: Resource group and networking

**Files:**
- Create: `infra/terraform/network.tf`

**Interfaces:**
- Consumes: `var.project_name`, `var.location`, `var.environment` from Task 2.
- Produces: `azurerm_resource_group.main` (referenced by every later resource's `resource_group_name`), `azurerm_subnet.aks.id` (consumed by Task 4's AKS cluster).

- [ ] **Step 1: Write `network.tf`**

```hcl
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-rg"
  location = var.location

  tags = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "azurerm_virtual_network" "main" {
  name                = "${var.project_name}-vnet"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  address_space       = ["10.10.0.0/16"]

  tags = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "azurerm_subnet" "aks" {
  name                 = "${var.project_name}-aks-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.10.1.0/24"]
}
```

`/24` gives 251 usable IPs for pods+nodes under Azure CNI — comfortably above the 4-6 node ceiling this plan's node pools ever reach, with headroom for Phase 1's pod count.

- [ ] **Step 2: Verify the plan**

```bash
terraform plan
```

Expected: `Plan: 3 to add, 0 to change, 0 to destroy.` (resource group, vnet, subnet). No errors.

- [ ] **Step 3: Apply**

```bash
terraform apply
```

Type `yes` when prompted. Expected: `Apply complete! Resources: 3 added, 0 changed, 0 destroyed.`

- [ ] **Step 4: Verify in Azure**

```bash
az group show --name eam-prod-rg -o table
az network vnet show --resource-group eam-prod-rg --name eam-prod-vnet -o table
```

Expected: both print the resources with `ProvisioningState: Succeeded`.

- [ ] **Step 5: Commit**

```bash
git add infra/terraform/network.tf
git commit -m "feat: add resource group and VNet/subnet for AKS Phase 0"
```

---

### Task 4: AKS cluster with ARM64 system and user node pools

**Files:**
- Create: `infra/terraform/aks.tf`

**Interfaces:**
- Consumes: `azurerm_resource_group.main`, `azurerm_subnet.aks.id` (Task 3); `var.system_node_count`, `var.user_node_min_count`, `var.user_node_max_count`, `var.admin_ip_ranges` (Task 2).
- Produces: `azurerm_kubernetes_cluster.main` — `.name`, `.id`, and `.kube_config_raw` (sensitive), all consumed by Task 5 (Key Vault access policy for the cluster's managed identity) and by `outputs.tf` (Task 7).

- [ ] **Step 1: Write `aks.tf`**

```hcl
resource "azurerm_kubernetes_cluster" "main" {
  name                = "${var.project_name}-aks"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  dns_prefix          = "${var.project_name}-aks"

  # Left unset deliberately — tracks AKS's current default supported
  # version instead of a version pinned at write time, which would go
  # stale and eventually fail to apply once Azure deprecates it. Pin
  # explicitly (e.g. kubernetes_version = "1.31") once the cluster is
  # stable and you want deterministic, manually-triggered upgrades.

  default_node_pool {
    name           = "system"
    node_count     = var.system_node_count
    vm_size        = "Standard_D2ps_v5" # ARM64 (Ampere Altra)
    vnet_subnet_id = azurerm_subnet.aks.id
    zones          = ["1", "2", "3"]

    only_critical_addons_enabled = true # keeps app workloads off this pool
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "azure"
    network_policy = "azure"
    service_cidr   = "10.20.0.0/24"
    dns_service_ip = "10.20.0.10"
  }

  api_server_access_profile {
    authorized_ip_ranges = var.admin_ip_ranges
  }

  tags = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "user" {
  name                  = "user"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = "Standard_D2ps_v5" # ARM64 (Ampere Altra)
  vnet_subnet_id        = azurerm_subnet.aks.id
  zones                 = ["1", "2", "3"]

  auto_scaling_enabled = true
  min_count             = var.user_node_min_count
  max_count             = var.user_node_max_count
  node_count             = var.user_node_min_count

  mode = "User"

  tags = {
    environment = var.environment
    managed_by  = "terraform"
  }
}
```

`service_cidr`/`dns_service_ip` are the cluster's internal Kubernetes Service network — must not overlap the VNet's `10.10.0.0/16` from Task 3, hence `10.20.0.0/24`.

- [ ] **Step 2: Verify the plan**

```bash
terraform plan
```

Expected: `Plan: 2 to add, 0 to change, 0 to destroy.` (cluster + user node pool).

- [ ] **Step 3: Apply**

```bash
terraform apply
```

Type `yes`. This step takes 5-10 minutes — AKS cluster creation is not instant. Expected: `Apply complete! Resources: 2 added, 0 changed, 0 destroyed.`

- [ ] **Step 4: Verify cluster access and node architecture**

```bash
az aks get-credentials --resource-group eam-prod-rg --name eam-prod-aks --overwrite-existing
kubectl get nodes -o wide
```

Expected: 4 nodes total (2 system + 2 user), all `STATUS: Ready`. Check the `ARCH` column (or run `kubectl get nodes -o jsonpath='{.items[*].status.nodeInfo.architecture}'`) — every node must report `arm64`. If any node shows `amd64`, the `vm_size` in this task is wrong for an ARM64 SKU and must be fixed before continuing.

- [ ] **Step 5: Commit**

```bash
git add infra/terraform/aks.tf
git commit -m "feat: add AKS cluster with ARM64 system and user node pools"
```

---

### Task 5: Key Vault

**Files:**
- Create: `infra/terraform/keyvault.tf`

**Interfaces:**
- Consumes: `azurerm_resource_group.main` (Task 3), `azurerm_kubernetes_cluster.main.identity[0].principal_id` (Task 4).
- Produces: `azurerm_key_vault.main.name` and `.vault_uri`, consumed by `outputs.tf` (Task 7) and by Phase 1's Secrets Store CSI Driver setup.

- [ ] **Step 1: Write `keyvault.tf`**

```hcl
data "azurerm_client_config" "current" {}

resource "random_string" "kv_suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_key_vault" "main" {
  name                = "${var.project_name}-kv-${random_string.kv_suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  enable_rbac_authorization = true
  purge_protection_enabled  = true

  tags = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

# Lets the AKS cluster's own managed identity read secrets — the exact
# permission the Secrets Store CSI Driver needs in Phase 1. Granted now so
# Phase 1 doesn't need a second Terraform apply just for this.
resource "azurerm_role_assignment" "aks_kv_reader" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id          = azurerm_kubernetes_cluster.main.identity[0].principal_id
}

# Lets whoever is running Terraform (you) manage secrets in the vault —
# without this, Terraform's own identity can create the vault but can't
# write anything into it.
resource "azurerm_role_assignment" "operator_kv_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id          = data.azurerm_client_config.current.object_id
}
```

`purge_protection_enabled = true` means a deleted vault can't be permanently purged for 90 days — deliberate for production (protects against an accidental `terraform destroy` of this one resource being unrecoverable), but means if you truly need to reuse this exact vault name later, you can't for up to 90 days after deletion. Acceptable trade-off for a resource meant to be long-lived.

- [ ] **Step 2: Verify the plan**

```bash
terraform plan
```

Expected: `Plan: 3 to add, 0 to change, 0 to destroy.` (random suffix, key vault, 2 role assignments count as 2 — so actually 4 to add; if your plan shows 4, that's correct, adjust expectation to `Plan: 4 to add`).

- [ ] **Step 3: Apply**

```bash
terraform apply
```

Type `yes`. Expected: `Apply complete!` with 4 resources added.

- [ ] **Step 4: Verify**

```bash
terraform output key_vault_name
az keyvault show --name "$(terraform output -raw key_vault_name)" -o table
```

(This step depends on `outputs.tf` from Task 7 — if running Task 5 before Task 7 exists yet, substitute the vault name directly from `terraform state show azurerm_key_vault.main | grep '^  name'` instead.)

Expected: `ProvisioningState: Succeeded`.

- [ ] **Step 5: Commit**

```bash
git add infra/terraform/keyvault.tf
git commit -m "feat: add Key Vault with AKS managed identity access"
```

---

### Task 6: Azure Database for PostgreSQL Flexible Server with pgvector

**Files:**
- Create: `infra/terraform/postgres.tf`

**Interfaces:**
- Consumes: `azurerm_resource_group.main` (Task 3), `var.postgres_admin_login`, `var.postgres_admin_password` (Task 2).
- Produces: `azurerm_postgresql_flexible_server.main.fqdn`, consumed by `outputs.tf` (Task 7) and by Phase 2's data migration.

- [ ] **Step 1: Write `postgres.tf`**

```hcl
resource "random_string" "psql_suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                = "${var.project_name}-psql-${random_string.psql_suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  version                      = "15" # matches the current pgvector/pgvector:pg15 container
  administrator_login          = var.postgres_admin_login
  administrator_password       = var.postgres_admin_password

  storage_mb = 32768 # 32 GB — Small tier starting point, can grow online later
  sku_name   = "B_Standard_B2s" # burstable, Small/no-HA per spec's cost decision

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  # Explicit per the spec's Phase 0 cost decision: no zone-redundant HA at
  # launch. This is a documented open risk in the design spec, not an
  # oversight — revisit before Medium-scale traffic.
  high_availability {
    mode = "Disabled"
  }

  tags = {
    environment = var.environment
    managed_by  = "terraform"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_postgresql_flexible_server_configuration" "pgvector" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "VECTOR"
}

# Allows the AKS subnet's outbound traffic to reach Postgres. Azure Flexible
# Server firewall rules work on IP ranges, not VNet peering by default at
# this tier — this rule is intentionally broad (the VNet's whole address
# space) since Phase 1 hasn't assigned static egress IPs to individual pods
# yet. Tighten to specific IPs once Phase 1's networking is finalized.
resource "azurerm_postgresql_flexible_server_firewall_rule" "aks_subnet" {
  name             = "allow-aks-vnet"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "10.10.1.0"
  end_ip_address   = "10.10.1.255"
}
```

`prevent_destroy = true` is deliberate — this holds real production data from Phase 2 onward. Running `terraform destroy` on this resource requires manually removing the lifecycle block first, a speed bump that's meant to make destroying the production database a conscious, hard-to-do-by-accident action.

- [ ] **Step 2: Set the admin password**

```bash
export TF_VAR_postgres_admin_password="$(openssl rand -base64 24)"
echo "Save this password somewhere safe RIGHT NOW (e.g. paste it directly into the Key Vault in Task 8) — it will not be printed again by this plan:"
echo "$TF_VAR_postgres_admin_password"
```

- [ ] **Step 3: Verify the plan**

```bash
terraform plan
```

Expected: `Plan: 4 to add, 0 to change, 0 to destroy.` (random suffix, server, extension config, firewall rule).

- [ ] **Step 4: Apply**

```bash
terraform apply
```

Type `yes`. This step takes 5-10 minutes. Expected: `Apply complete!` with 4 resources added.

- [ ] **Step 5: Verify connectivity and pgvector**

```bash
PSQL_FQDN=$(terraform state show azurerm_postgresql_flexible_server.main | grep '^    fqdn' | awk '{print $3}' | tr -d '"')
psql "host=$PSQL_FQDN port=5432 dbname=postgres user=$(terraform output -raw postgres_admin_login 2>/dev/null || echo eamadmin) sslmode=require" -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

You'll be prompted for the password set in Step 2. Expected: a row showing `vector` with a version number — confirms the extension is both allow-listed (via the `azure.extensions` config) and successfully created.

If this fails with "extension vector is not allow-listed", the `azurerm_postgresql_flexible_server_configuration.pgvector` resource didn't apply correctly — check `terraform state list` includes it and re-run `terraform apply`.

- [ ] **Step 6: Commit**

```bash
git add infra/terraform/postgres.tf
git commit -m "feat: add Azure Database for PostgreSQL Flexible Server with pgvector"
```

---

### Task 7: Outputs

**Files:**
- Create: `infra/terraform/outputs.tf`

**Interfaces:**
- Consumes: every resource from Tasks 3-6.
- Produces: the six named outputs listed in the File Structure section above — this is the complete interface Phase 1's plan will read from.

- [ ] **Step 1: Write `outputs.tf`**

```hcl
output "aks_cluster_name" {
  description = "AKS cluster name — used with 'az aks get-credentials'."
  value       = azurerm_kubernetes_cluster.main.name
}

output "aks_resource_group" {
  description = "Resource group containing all Phase 0 resources."
  value       = azurerm_resource_group.main.name
}

output "postgres_fqdn" {
  description = "Fully qualified domain name of the Postgres Flexible Server."
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "postgres_admin_login" {
  description = "Admin username for the Postgres Flexible Server."
  value       = var.postgres_admin_login
  sensitive   = true
}

output "key_vault_name" {
  description = "Key Vault name."
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "Key Vault URI — used by the Secrets Store CSI Driver in Phase 1."
  value       = azurerm_key_vault.main.vault_uri
}
```

- [ ] **Step 2: Verify**

```bash
terraform apply
```

Expected: `Apply complete! Resources: 0 added, 0 changed, 0 destroyed.` (outputs alone don't create resources — this just confirms the config is valid and prints the output values).

```bash
terraform output
```

Expected: all six outputs listed, with `postgres_admin_login` shown as `<sensitive>` (use `terraform output -raw postgres_admin_login` to see the actual value when needed).

- [ ] **Step 3: Commit**

```bash
git add infra/terraform/outputs.tf
git commit -m "feat: add Terraform outputs for AKS Phase 0"
```

---

### Task 8: Store the Postgres admin password in Key Vault

**Files:** none (Azure CLI only — this is data, not infrastructure-as-code, and the password must never be written to a file in this repo).

**Interfaces:**
- Consumes: `key_vault_name` output (Task 7), the password generated in Task 6 Step 2.
- Produces: a Key Vault secret named `postgres-admin-password`, which Phase 1's Secrets Store CSI Driver setup will reference by this exact name.

- [ ] **Step 1: Store the secret**

```bash
az keyvault secret set \
  --vault-name "$(cd infra/terraform && terraform output -raw key_vault_name)" \
  --name postgres-admin-password \
  --value "$TF_VAR_postgres_admin_password"
```

Expected: prints the secret metadata (not the value) with `"enabled": true`.

- [ ] **Step 2: Verify without printing the value**

```bash
az keyvault secret show \
  --vault-name "$(cd infra/terraform && terraform output -raw key_vault_name)" \
  --name postgres-admin-password \
  --query "{name:name, enabled:attributes.enabled}" -o table
```

Expected: `Name: postgres-admin-password`, `Enabled: True`.

- [ ] **Step 3: Clear the password from your shell session**

```bash
unset TF_VAR_postgres_admin_password
```

No git commit for this task — nothing here touches a tracked file.

---

## Definition of done for Phase 0

- [ ] `terraform apply` runs clean with zero pending changes (`terraform plan` shows `No changes.`).
- [ ] `kubectl get nodes -o wide` shows 4 Ready nodes, all `arm64`.
- [ ] `psql` can connect to the Postgres Flexible Server and `CREATE EXTENSION vector` succeeds.
- [ ] Key Vault contains the `postgres-admin-password` secret.
- [ ] No application code has been deployed and no traffic has been routed anywhere — Phase 0 is infrastructure only, confirmed by `kubectl get pods -A` showing only AKS system pods (`kube-system` namespace), nothing in an `eam-*` namespace yet.
- [ ] All `infra/terraform/*.tf` files are committed to git (`terraform.tfvars`, `.terraform/`, and `*.tfstate*` remain gitignored, per Task 1's `.gitignore`).

Once this is all true, Phase 1 (Helm charts, staging namespace deployment) gets its own plan, written after this one is real and validated on the ground — per the spec's phased approach.
