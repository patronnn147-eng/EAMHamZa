# x86 (Standard_B2s_v2), not ARM64, despite the design spec's ARM64-only
# assumption. That assumption held for the single germanywestcentral demo
# VM, but AKS Phase 0 execution discovered this subscription's ARM64
# quota/SKU availability genuinely does not exist outside germanywestcentral
# — none of the other 4 Azure-Policy-allowed regions
# (switzerlandnorth/spaincentral/norwayeast/polandcentral) offer any ARM64
# VM SKU at all, confirmed via `az vm list-skus`. germanywestcentral itself
# is stuck at a regional vCPU quota of 4/6 used (by the demo VM) that did
# not free up even after deallocating it. Revisit ARM64 if germanywestcentral
# quota is ever freed (see the demo VM deletion option in
# docs/superpowers/plans/2026-07-30-aks-phase0-foundations.md's execution
# history) or if Azure approves additional regions/quota for this subscription.
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
    vm_size        = "Standard_B2s_v2" # x86 — see note below
    vnet_subnet_id = azurerm_subnet.aks.id
    zones          = ["1", "2", "3"]

    only_critical_addons_enabled = true # keeps app workloads off this pool

    # Declared explicitly to match AKS's own applied defaults — otherwise
    # Terraform sees this block as absent from config and tries to null
    # these out on every plan, a permanent (harmless but noisy) drift.
    upgrade_settings {
      max_surge = "10%"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }

  # Required by azurerm provider v5. This plan uses explicit, manually
  # defined node pools (system + user below) rather than AKS's Node Auto
  # Provisioning (Karpenter-based) feature, so mode = "Manual" (the
  # provider's own default) is what we want here.
  node_provisioning_profile {
    mode = "Manual"
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
  vm_size               = "Standard_B2s_v2" # x86 — see note below
  vnet_subnet_id        = azurerm_subnet.aks.id
  zones                 = ["1", "2", "3"]

  auto_scaling_enabled = true
  min_count             = var.user_node_min_count
  max_count             = var.user_node_max_count
  node_count             = var.user_node_min_count

  mode = "User"

  upgrade_settings {
    max_surge = "10%"
  }

  tags = {
    environment = var.environment
    managed_by  = "terraform"
  }
}
