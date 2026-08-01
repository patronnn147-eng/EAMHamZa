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

  # Migrated from the azurerm blob backend to HCP Terraform (app.terraform.io)
  # so state has a live web dashboard to view/screenshot. The Azure Blob
  # backend (eam-tfstate-rg / eamtfstate7b8a6c) still holds the pre-migration
  # state file as a historical artifact but is no longer read/written by
  # this config. No Azure resources were touched by this migration — it
  # only changes where the state *bookkeeping* lives, not what it tracks.
  cloud {
    organization = "eam-sagemcom"

    workspaces {
      name = "aks-phase0"
    }
  }
}
