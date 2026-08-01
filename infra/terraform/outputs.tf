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

output "key_vault_secrets_provider_client_id" {
  description = "Client ID of the Secrets Store CSI Driver addon's identity — used in Helm's SecretProviderClass."
  value       = azurerm_kubernetes_cluster.main.key_vault_secrets_provider[0].secret_identity[0].client_id
}
