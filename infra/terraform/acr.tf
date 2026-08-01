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
