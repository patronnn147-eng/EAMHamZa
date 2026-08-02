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

# The raw Postgres admin password contains a "/" — a reserved URL delimiter.
# Embedding it unencoded in DATABASE_URL breaks connection-string parsing
# (discovered live during Phase 1 Task 10: asyncpg misparsed the URL and
# tried to int()-parse a password fragment as a port number). Storing a
# separately URL-encoded copy rather than changing the actual DB password,
# which would be a real operational change.
resource "azurerm_key_vault_secret" "postgres_admin_password_urlencoded" {
  name         = "postgres-admin-password-urlencoded"
  value        = urlencode(var.postgres_admin_password)
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.operator_kv_admin]
}
