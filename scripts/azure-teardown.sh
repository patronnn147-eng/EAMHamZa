#!/usr/bin/env bash
# Deletes every Azure resource created for the 6-day EAM demo.
# Run manually once screenshots are captured and the demo window is over.
set -euo pipefail

RESOURCE_GROUP="eam-demo-rg"

echo "Deleting resource group '$RESOURCE_GROUP' and everything in it (VM, ACR, NSG, public IP, disk)..."
az group delete --name "$RESOURCE_GROUP" --yes --no-wait

echo "Deletion started (--no-wait). Confirm with:"
echo "  az group show --name $RESOURCE_GROUP"
echo "(should eventually error 'ResourceGroupNotFound' once fully deleted)"
