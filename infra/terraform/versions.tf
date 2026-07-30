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
    resource_group_name  = "eam-tfstate-rg"
    storage_account_name = "eamtfstate7b8a6c"
    container_name        = "tfstate"
    key                   = "phase0.tfstate"
  }
}
