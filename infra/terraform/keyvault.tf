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

  rbac_authorization_enabled = true
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
