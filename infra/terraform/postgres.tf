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

  # No high_availability block at all = HA disabled (provider v5: there is
  # no "Disabled" mode value: to disable HA you omit the block). Explicit
  # per the spec's Phase 0 cost decision: no zone-redundant HA at launch.
  # This is a documented open risk in the design spec, not an oversight —
  # revisit before Medium-scale traffic.

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
