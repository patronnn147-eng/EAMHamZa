#!/usr/bin/env bash
# One-time Azure resource setup for the 6-day EAM demo deployment.
# Run manually: `az login` first, then `bash scripts/azure-provision-vm.sh`.
# Prints the values to register as GitLab CI/CD variables at the end.
set -euo pipefail

RESOURCE_GROUP="eam-demo-rg"
LOCATION="germanywestcentral"
VM_NAME="eam-demo-vm"
DNS_LABEL="eam-demo"
ACR_NAME="eamdemoacr$(date +%s | tail -c 6)"   # ACR names: globally unique, alnum only
SSH_KEY_PATH="$HOME/.ssh/eam_demo_deploy"

echo "== Resource group =="
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output table

echo "== SSH key pair (for GitLab CI -> VM deploy access) =="
if [ ! -f "$SSH_KEY_PATH" ]; then
  ssh-keygen -t ed25519 -f "$SSH_KEY_PATH" -N "" -C "eam-demo-deploy"
else
  echo "Reusing existing key at $SSH_KEY_PATH"
fi

echo "== VM (Standard_D4as_v7, Ubuntu 22.04) =="
# Standard_B4ms is blocked on this Azure-for-Students subscription
# (NotAvailableForSubscription capacity restriction — the subscription's
# B-series access is limited to ARM64 "p" variants only). Standard_D4as_v7
# is x86_64 (AMD), 4vCPU/16GB, and available on this subscription — keeps
# parity with the amd64 images the CI pipeline builds.
az vm create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$VM_NAME" \
  --image Ubuntu2204 \
  --size Standard_D4as_v7 \
  --admin-username azureuser \
  --ssh-key-values "${SSH_KEY_PATH}.pub" \
  --public-ip-sku Standard \
  --public-ip-address-dns-name "$DNS_LABEL" \
  --output table

echo "== Network security group: open 80/443 (22 is open by default via az vm create) =="
NSG_NAME=$(az network nsg list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)
az network nsg rule create \
  --resource-group "$RESOURCE_GROUP" --nsg-name "$NSG_NAME" \
  --name allow-http --priority 200 --access Allow --protocol Tcp --destination-port-ranges 80 \
  --output none
az network nsg rule create \
  --resource-group "$RESOURCE_GROUP" --nsg-name "$NSG_NAME" \
  --name allow-https --priority 210 --access Allow --protocol Tcp --destination-port-ranges 443 \
  --output none

echo "== Azure Container Registry (Basic tier, admin auth enabled) =="
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true \
  --output table

echo ""
echo "=========================================================="
echo "Provisioning complete. Register these as GitLab CI/CD"
echo "variables (Project -> Settings -> CI/CD -> Variables),"
echo "all Protected, secrets Masked:"
echo "=========================================================="
echo "AZURE_VM_HOST      = ${DNS_LABEL}.${LOCATION}.cloudapp.azure.com   (plain)"
echo "ACR_LOGIN_SERVER   = $(az acr show -n "$ACR_NAME" --query loginServer -o tsv)   (plain)"
az acr credential show -n "$ACR_NAME" -o table
echo "  -> ACR_USERNAME (masked) = the 'Username' above"
echo "  -> ACR_PASSWORD (masked) = 'password' value above"
echo ""
echo "SSH_PRIVATE_KEY (masked, multi-line — paste the full block including BEGIN/END lines):"
cat "$SSH_KEY_PATH"
