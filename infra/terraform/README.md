# Terraform state backend — bootstrap (one-time, already done)

This directory's Terraform state lives in Azure Blob Storage, in a resource
group (`eam-tfstate-rg`) that is intentionally **not** managed by this same
Terraform config — you can't have Terraform manage the backend it's storing
its own state in without a chicken-and-egg problem.

Storage account name: `eamtfstate<suffix>` — see `versions.tf` for the exact
name in use. Container: `tfstate`. State file key: `phase0.tfstate`.

**Do not run `terraform destroy` against `eam-tfstate-rg` unless you are
intentionally tearing down every environment this backend serves.**

If you ever need to recreate the backend from scratch, rerun the `az group
create` / `az storage account create` / `az storage container create`
commands in Task 1 of `docs/superpowers/plans/2026-07-30-aks-phase0-foundations.md`
with a new random suffix, then update the `backend "azurerm"` block in
`versions.tf` to match.
