# The Key Vault Secrets Provider addon auto-creates its own managed identity
# in the AKS node resource group (not exposed as a manageable Terraform
# resource in this config) — referenced here only to attach a federated
# credential to it.
data "azurerm_user_assigned_identity" "kv_secrets_provider" {
  name                = "azurekeyvaultsecretsprovider-${azurerm_kubernetes_cluster.main.name}"
  resource_group_name = azurerm_kubernetes_cluster.main.node_resource_group
}

# Lets the addon's identity be assumed by pods running under the
# eam-secrets-sa ServiceAccount in eam-staging, via OIDC federation —
# this is the missing piece that made SecretProviderClass mounts fail.
resource "azurerm_federated_identity_credential" "kv_secrets_provider_staging" {
  name                       = "eam-staging-secrets-sa"
  user_assigned_identity_id = data.azurerm_user_assigned_identity.kv_secrets_provider.id
  audience                   = ["api://AzureADTokenExchange"]
  issuer                      = azurerm_kubernetes_cluster.main.oidc_issuer_url
  subject                     = "system:serviceaccount:eam-staging:eam-secrets-sa"
}

# Same addon identity, federated for the eam-prod namespace's copy of the
# ServiceAccount too — each namespace needs its own subject entry.
resource "azurerm_federated_identity_credential" "kv_secrets_provider_prod" {
  name                       = "eam-prod-secrets-sa"
  user_assigned_identity_id = data.azurerm_user_assigned_identity.kv_secrets_provider.id
  audience                   = ["api://AzureADTokenExchange"]
  issuer                      = azurerm_kubernetes_cluster.main.oidc_issuer_url
  subject                     = "system:serviceaccount:eam-prod:eam-secrets-sa"
}
