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
