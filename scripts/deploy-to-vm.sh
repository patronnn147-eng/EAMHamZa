#!/usr/bin/env bash
# Deploys the current registry-pushed :demo images to the Azure demo VM.
# Run by the GitLab CI `deploy` job. Expects these env vars to already be
# set (GitLab CI/CD variables): AZURE_VM_HOST, SSH_PRIVATE_KEY, CI_REGISTRY,
# CI_REGISTRY_IMAGE, DEPLOY_TOKEN_USER, DEPLOY_TOKEN_PASSWORD, plus every
# EAM_* app secret (see docs/azure-demo-ci-variables.md).
set -euo pipefail

VM_USER="azureuser"
REMOTE_DIR="EAMSagemCom"

mkdir -p ~/.ssh
echo "$SSH_PRIVATE_KEY" > ~/.ssh/eam_demo_deploy
chmod 600 ~/.ssh/eam_demo_deploy
ssh-keyscan -H "$AZURE_VM_HOST" >> ~/.ssh/known_hosts 2>/dev/null

SSH_CMD=(ssh -i ~/.ssh/eam_demo_deploy -o StrictHostKeyChecking=accept-new "${VM_USER}@${AZURE_VM_HOST}")
SCP_CMD=(scp -i ~/.ssh/eam_demo_deploy)

# Build the .env the VM's compose stack will read: every EAM_* CI variable,
# stripped of its prefix, plus the three vars docker-compose.prod.yml needs.
env | grep '^EAM_' | sed 's/^EAM_//' > .env.demo
{
  echo "IMAGE_TAG=demo"
  echo "CI_REGISTRY_IMAGE=${CI_REGISTRY_IMAGE}"
  echo "AZURE_VM_HOST=${AZURE_VM_HOST}"
} >> .env.demo

"${SCP_CMD[@]}" .env.demo "${VM_USER}@${AZURE_VM_HOST}:${REMOTE_DIR}/.env"
"${SCP_CMD[@]}" docker-compose.prod.yml Caddyfile "${VM_USER}@${AZURE_VM_HOST}:${REMOTE_DIR}/"

"${SSH_CMD[@]}" "cd ${REMOTE_DIR} && git pull --quiet"
"${SSH_CMD[@]}" "echo '${DEPLOY_TOKEN_PASSWORD}' | docker login ${CI_REGISTRY} -u '${DEPLOY_TOKEN_USER}' --password-stdin"
"${SSH_CMD[@]}" "cd ${REMOTE_DIR} && docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.monitoring.yml pull"
"${SSH_CMD[@]}" "cd ${REMOTE_DIR} && docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.monitoring.yml up -d --remove-orphans"

rm -f .env.demo ~/.ssh/eam_demo_deploy
