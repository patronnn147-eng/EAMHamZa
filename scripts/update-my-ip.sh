#!/usr/bin/env bash
# Update the AKS API server's authorized_ip_ranges to your current public IP
# and apply. Run this whenever kubectl/deploy-aks.sh fails with a "connectex"
# / "dial tcp ...:443" error against the AKS API server — that means your
# ISP rotated your IP and the firewall no longer recognizes you.
#
#   ./scripts/update-my-ip.sh
#
# Pulls postgres_admin_password / groq_api_key from Key Vault (never printed,
# never written to disk) so it doesn't depend on your shell already having
# them exported. Scopes the apply to just the AKS resource (-target) so it
# never touches unrelated drift elsewhere in the plan.
set -euo pipefail

TF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../infra/terraform" && pwd)"
TFVARS="$TF_DIR/terraform.tfvars"
KEY_VAULT="eam-prod-kv-h597b3"

echo ">> checking current public IP"
CURRENT_IP="$(curl -s https://api.ipify.org)"
if [[ ! "$CURRENT_IP" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
  echo "!! could not determine public IP (got: '$CURRENT_IP')" >&2
  exit 1
fi
echo "   current IP: $CURRENT_IP"

STORED_IP="$(grep -oE '[0-9]{1,3}(\.[0-9]{1,3}){3}/32' "$TFVARS" | head -1 | sed 's#/32##')"
echo "   tfvars has: ${STORED_IP:-<none>}"

if [ "$CURRENT_IP" = "$STORED_IP" ]; then
  echo ">> already up to date, nothing to do"
  exit 0
fi

echo ">> updating terraform.tfvars ($STORED_IP -> $CURRENT_IP)"
PYTHON_BIN="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "!! no python3/python found on PATH" >&2
  exit 1
fi
"$PYTHON_BIN" - "$TFVARS" "$STORED_IP" "$CURRENT_IP" <<'PYEOF'
import sys
path, old_ip, new_ip = sys.argv[1:4]
with open(path, encoding='utf-8') as f:
    content = f.read()
if old_ip:
    content = content.replace(f'"{old_ip}/32"', f'"{new_ip}/32"')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
PYEOF

echo ">> fetching secrets from Key Vault"
export TF_VAR_postgres_admin_password
export TF_VAR_groq_api_key
TF_VAR_postgres_admin_password="$(az keyvault secret show --vault-name "$KEY_VAULT" --name postgres-admin-password --query value -o tsv)"
TF_VAR_groq_api_key="$(az keyvault secret show --vault-name "$KEY_VAULT" --name groq-api-key --query value -o tsv)"

echo ">> applying (scoped to the AKS cluster resource only)"
cd "$TF_DIR"
terraform apply -target=azurerm_kubernetes_cluster.main -auto-approve

echo ">> verifying cluster access"
kubectl get nodes --request-timeout=15s
echo ">> done — kubectl and deploy-aks.sh should work now"
