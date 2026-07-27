# Azure VM Demo Deployment (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the EAM app reachable over HTTPS at a public Azure URL, deployed automatically by GitLab CI on every push to `Phase_2`, for a ~6-day demo window — producing real screenshots for the PFE report and CV.

**Architecture:** One Azure VM (Ubuntu, Standard_B4ms) runs the existing `docker-compose.yml` stack plus a `docker-compose.prod.yml` override (registry images instead of local builds, no directly-published app ports) plus the existing `docker-compose.monitoring.yml`, fronted by a Caddy reverse proxy that gets a Let's Encrypt HTTPS cert automatically. GitLab CI — unchanged through its existing 9 stages — gains three new stages (`registry-push`, `deploy`, `verify`) that build/push images to GitLab's registry and Azure Container Registry, SSH-deploy to the VM, and curl-verify the result.

**Tech Stack:** Docker Compose, GitLab CI (existing, `tags: [local]` self-hosted runner), Azure CLI (`az`), Caddy 2, Ubuntu 22.04.

## Global Constraints

- Existing GitLab CI pipeline stages (secret-scan, sca-deps, test, sast, build, image-scan, dast, lint, gate) must not be modified — only append new stages after `gate`.
- VM size: Standard_B4ms (4 vCPU / 16GB RAM).
- All app-secret CI/CD variables use an `EAM_*` naming prefix (stripped to the real name when written to the VM's `.env`).
- Everything public must be HTTPS — no plain-HTTP screenshots.
- Only ports 22 (SSH), 80, and 443 are open to the internet on the VM; every other service (backend, ml-service, rag-service, Postgres, MinIO, Prometheus, Pushgateway) is reachable only over the VM's internal Docker network.
- This is a ~6-day throwaway demo: no rollback automation, no HA, no autoscaling (see the spec's Limitations section) — don't add any of that here.
- Reference spec: [`docs/superpowers/specs/2026-07-27-azure-6day-demo-deployment-design.md`](../specs/2026-07-27-azure-6day-demo-deployment-design.md). Phase 2 (AKS) is a separate, optional plan — not covered here.

---

### Task 1: Production compose overlay + HTTPS reverse proxy

**Files:**
- Create: `docker-compose.prod.yml`
- Create: `Caddyfile`
- Modify: `docker-compose.monitoring.yml:83-95` (Grafana sub-path env vars)

**Interfaces:**
- Consumes: existing `docker-compose.yml` service names (`backend`, `celery_worker`, `celery_beat`, `rag-service`, `ml-service`, `frontend`), existing `docker-compose.monitoring.yml` service `grafana`.
- Produces: `docker-compose.prod.yml` referenced by later tasks' deploy script as `-f docker-compose.prod.yml`; `Caddyfile` referenced by the `caddy` service's volume mount; env vars `CI_REGISTRY_IMAGE`, `IMAGE_TAG`, `AZURE_VM_HOST` consumed by `docker-compose.prod.yml`.

- [ ] **Step 1: Write `docker-compose.prod.yml`**

```yaml
# Production overlay for the ~6-day Azure demo deployment.
# Use with: docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.monitoring.yml up -d
# Overrides local `build:` services to pull pre-built, pre-scanned registry
# images instead, and removes host port publishing for every service except
# Caddy — Caddy is the only public entry point (see Caddyfile). Everything
# else is reachable only over the internal Docker network by service name.
# This is defense-in-depth: the Azure NSG (Task 2) already blocks external
# access to all of these ports, but not publishing them at all means a
# misconfigured NSG rule can't accidentally expose Postgres/MinIO/RabbitMQ
# either. pull_policy: always guarantees the `build:` block inherited from
# docker-compose.yml is never used here. restart: always and healthcheck:
# are already set on every service in the base docker-compose.yml — nothing
# to add for that here, this overlay only needs to change image sourcing
# and port exposure.
services:
  postgres:
    ports: []

  rabbitmq:
    ports: []

  minio:
    ports: []

  pgadmin:
    ports: []

  backend:
    image: ${CI_REGISTRY_IMAGE}/backend:${IMAGE_TAG:-demo}
    pull_policy: always
    ports: []

  celery_worker:
    image: ${CI_REGISTRY_IMAGE}/backend:${IMAGE_TAG:-demo}
    pull_policy: always

  celery_beat:
    image: ${CI_REGISTRY_IMAGE}/backend:${IMAGE_TAG:-demo}
    pull_policy: always

  rag-service:
    image: ${CI_REGISTRY_IMAGE}/rag-service:${IMAGE_TAG:-demo}
    pull_policy: always
    ports: []

  ml-service:
    image: ${CI_REGISTRY_IMAGE}/ml-service:${IMAGE_TAG:-demo}
    pull_policy: always
    ports: []

  frontend:
    image: ${CI_REGISTRY_IMAGE}/frontend:${IMAGE_TAG:-demo}
    pull_policy: always
    ports: []

  caddy:
    image: caddy:2.8-alpine
    container_name: eam_caddy
    restart: always
    ports:
      - "80:80"
      - "443:443"
    environment:
      AZURE_VM_HOST: ${AZURE_VM_HOST}
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - frontend
      - backend
    networks:
      - asset_management_network

volumes:
  caddy_data:
    driver: local
  caddy_config:
    driver: local
```

- [ ] **Step 2: Write `Caddyfile`**

The app is a browser-side SPA (Vite): the *browser*, not the frontend container, calls the backend API directly, so the backend must be reachable through Caddy too (path-routed, not directly published — see Task 1 Step 1's `ports: []`). Backend routes already live under `/api/v1/...` (confirmed via the existing healthcheck `http://localhost:8000/api/v1/health` in `docker-compose.yml:160`), so no path-stripping is needed for `/api`.

```
{$AZURE_VM_HOST} {
	handle /grafana/* {
		uri strip_prefix /grafana
		reverse_proxy grafana:3000
	}

	handle /api/* {
		reverse_proxy backend:8000
	}

	handle {
		reverse_proxy frontend:80
	}
}
```

- [ ] **Step 3: Add Grafana sub-path env vars to `docker-compose.monitoring.yml`**

Grafana needs to know it's served from `/grafana/` behind the proxy, or its internal links break. Edit the `grafana` service's `environment:` block (currently at `docker-compose.monitoring.yml:83-95`):

```yaml
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_UNIFIED_ALERTING_ENABLED: "true"
      GF_ALERTING_ENABLED: "false"
      GF_SERVER_ROOT_URL: "${GF_SERVER_ROOT_URL:-%(protocol)s://%(domain)s:%(http_port)s/}"
      GF_SERVER_SERVE_FROM_SUB_PATH: "${GF_SERVER_SERVE_FROM_SUB_PATH:-false}"
      GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH: "/var/lib/grafana/dashboards/trivy-security.json"
      GF_SMTP_ENABLED: "${GF_SMTP_ENABLED:-false}"
      GF_SMTP_HOST: "${GF_SMTP_HOST:-smtp.gmail.com:587}"
      GF_SMTP_USER: "${GF_SMTP_USER:-}"
      GF_SMTP_PASSWORD: "${GF_SMTP_PASSWORD:-}"
      GF_SMTP_FROM_ADDRESS: "${GF_SMTP_FROM_ADDRESS:-grafana@eam.local}"
```

Only the two new lines (`GF_SERVER_ROOT_URL` now reads an override var instead of being hardcoded, and the new `GF_SERVER_SERVE_FROM_SUB_PATH`) change behavior — both default to the exact previous values, so local dev (`make up`) is unaffected. On the VM, the deploy script (Task 4) sets `GF_SERVER_ROOT_URL=https://<AZURE_VM_HOST>/grafana/` and `GF_SERVER_SERVE_FROM_SUB_PATH=true` in `.env`.

- [ ] **Step 4: Verify the compose overlay is syntactically valid**

Run (from repo root, no VM needed yet — this only validates YAML merging and variable interpolation):

```bash
CI_REGISTRY_IMAGE=registry.gitlab.com/example/eamsagemcom \
IMAGE_TAG=demo \
AZURE_VM_HOST=eam-demo.westeurope.cloudapp.azure.com \
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.monitoring.yml config --quiet
```

Expected: no output, exit code 0. If it prints a YAML error, fix `docker-compose.prod.yml` or `Caddyfile`'s indentation/keys before continuing — `Caddyfile` isn't YAML so `compose config` won't validate its syntax, only that the volume mount line is well-formed.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.prod.yml Caddyfile docker-compose.monitoring.yml
git commit -m "deploy: add prod compose overlay + Caddy HTTPS reverse proxy"
```

---

### Task 2: One-time Azure resource provisioning script

**Files:**
- Create: `scripts/azure-provision-vm.sh`

**Interfaces:**
- Consumes: nothing (run manually, once, by the developer with `az login` already done).
- Produces: prints the values Task 3 needs to register as GitLab CI/CD variables (`AZURE_VM_HOST`, `ACR_LOGIN_SERVER`, `ACR_USERNAME`, `ACR_PASSWORD`, SSH private key content) and creates the VM Task 5 bootstraps.

- [ ] **Step 1: Write the provisioning script**

```bash
#!/usr/bin/env bash
# One-time Azure resource setup for the 6-day EAM demo deployment.
# Run manually: `az login` first, then `bash scripts/azure-provision-vm.sh`.
# Prints the values to register as GitLab CI/CD variables at the end.
set -euo pipefail

RESOURCE_GROUP="eam-demo-rg"
LOCATION="westeurope"
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

echo "== VM (Standard_B4ms, Ubuntu 22.04) =="
az vm create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$VM_NAME" \
  --image Ubuntu2204 \
  --size Standard_B4ms \
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
```

- [ ] **Step 2: Verify the script is syntactically valid**

Run:

```bash
bash -n scripts/azure-provision-vm.sh
```

Expected: no output, exit code 0 (syntax-only check — this does not require `az` to be installed and does not create any Azure resources).

- [ ] **Step 3: Commit**

```bash
git add scripts/azure-provision-vm.sh
git commit -m "deploy: add one-time Azure VM/ACR provisioning script"
```

- [ ] **Step 4: Actually run it (manual, one-time, real Azure action)**

This step creates real billable Azure resources. Run it yourself when ready to start the 6-day window:

```bash
az login
bash scripts/azure-provision-vm.sh
```

Expected: table output for each resource, ending with the CI/CD variable values block. Keep that output — Task 3 needs it.

---

### Task 3: Register GitLab CI/CD variables

**Files:**
- Create: `docs/azure-demo-ci-variables.md`

**Interfaces:**
- Consumes: the output block from Task 2 Step 4.
- Produces: the GitLab CI/CD variables that Task 4's pipeline stages read (`AZURE_VM_HOST`, `ACR_LOGIN_SERVER`, `ACR_USERNAME`, `ACR_PASSWORD`, `SSH_PRIVATE_KEY`, `DEPLOY_TOKEN_USER`, `DEPLOY_TOKEN_PASSWORD`, every `EAM_*` app secret).

- [ ] **Step 1: Create a GitLab Deploy Token for the VM to pull images**

GitLab → your project → Settings → Repository → Deploy tokens → Add token. Name: `eam-demo-vm-pull`. Scope: `read_registry` only. Copy the generated username/password immediately (shown once).

- [ ] **Step 2: Write the variable checklist doc**

```markdown
# Azure Demo — GitLab CI/CD Variables

Registered at: Project -> Settings -> CI/CD -> Variables.
All rows below: Protected = yes (only runs on protected branches/`Phase_2`
if protected, otherwise unprotect `Phase_2` temporarily for the demo window).
"Masked" secrets must contain no newlines except SSH_PRIVATE_KEY, which
GitLab's masking cannot handle multi-line — leave SSH_PRIVATE_KEY
**unmasked** (Protected only) since it's only ever readable by pipeline jobs
on this project, not printed to job logs by any script in this plan.

| Variable | Masked | Source |
|---|---|---|
| `AZURE_VM_HOST` | no | Task 2 script output |
| `ACR_LOGIN_SERVER` | no | Task 2 script output |
| `ACR_USERNAME` | yes | Task 2 script output (`az acr credential show`) |
| `ACR_PASSWORD` | yes | Task 2 script output (`az acr credential show`) |
| `SSH_PRIVATE_KEY` | no (see above) | Task 2 script output (`cat ~/.ssh/eam_demo_deploy`) |
| `DEPLOY_TOKEN_USER` | yes | Task 3 Step 1 (GitLab Deploy Token username) |
| `DEPLOY_TOKEN_PASSWORD` | yes | Task 3 Step 1 (GitLab Deploy Token password) |
| `EAM_POSTGRES_USER` | yes | not set in local `.env` (falls back to `docker-compose.yml`'s default `postgres`) — generate a real value for the demo, e.g. `openssl rand -hex 8` |
| `EAM_POSTGRES_PASSWORD` | yes | not set in local `.env` (falls back to the default `postgres`) — generate a real value, e.g. `openssl rand -hex 24`. Worth doing even though Postgres isn't publicly reachable (NSG blocks 5432) — cheap to fix, no reason to run a public-cloud VM on the literal word "postgres" |
| `EAM_POSTGRES_DB` | no | `asset_management` (matches local `.env`) |
| `EAM_JWT_SECRET_KEY` | yes | **reuse the exact value already in local `.env`'s `JWT_SECRET_KEY`** — don't retype it here, copy-paste directly from your `.env` file into the GitLab variable field |
| `EAM_MINIO_ROOT_USER` | yes | reuse local `.env`'s `MINIO_ROOT_USER` value |
| `EAM_MINIO_ROOT_PASSWORD` | yes | reuse local `.env`'s `MINIO_ROOT_PASSWORD` value |
| `EAM_OSS_API_KEY` | yes | same value as `EAM_MINIO_ROOT_USER` (matches local `.env`'s `OSS_API_KEY`) |
| `EAM_OSS_SECRET_KEY` | yes | same value as `EAM_MINIO_ROOT_PASSWORD` (matches local `.env`'s `OSS_SECRET_KEY`) |
| `EAM_GRAFANA_USER` | no | reuse local `.env`'s `GRAFANA_USER` |
| `EAM_GRAFANA_PASSWORD` | yes | reuse local `.env`'s `GRAFANA_PASSWORD` — low stakes if left as-is (Grafana sits behind `/grafana/` + its own login, not directly on the internet), but free to strengthen if you'd rather not screenshot a login screen with a guessable password |
| `EAM_GF_SERVER_ROOT_URL` | no | `https://<AZURE_VM_HOST>/grafana/` |
| `EAM_GF_SERVER_SERVE_FROM_SUB_PATH` | no | `true` |
| `EAM_FRONTEND_URL` | no | `https://<AZURE_VM_HOST>` |
| `EAM_GROQ_API_KEY` | yes | reuse local `.env`'s `GROQ_API_KEY` value |
| `EAM_SMTP_PASSWORD` | yes | reuse local `.env`'s `SMTP_PASSWORD` value |

In every "reuse local `.env`" row above: open your own `.env` file and copy the
value directly into the GitLab CI/CD variable field — never type real
secrets into this doc or any other git-tracked file.

Deliberately **not** set (app defaults are fine for a throwaway demo):
`EAM_JWT_ALGORITHM`, `EAM_JWT_EXPIRE_MINUTES`, `EAM_CELERY_BROKER_URL`,
`EAM_SMTP_SERVER`, `EAM_SMTP_PORT`, `EAM_SMTP_USERNAME`, `EAM_FROM_EMAIL`,
`EAM_FROM_NAME`, `EAM_RERANK_ENABLED`, `EAM_HYBRID_ENABLED`,
`EAM_ML_ALLOW_SYNTHETIC_TELEMETRY`.

Verification: after adding all rows, Settings -> CI/CD -> Variables should
list every `EAM_*`, `AZURE_VM_HOST`, `ACR_*`, `SSH_PRIVATE_KEY`, and
`DEPLOY_TOKEN_*` row above.
```

- [ ] **Step 3: Actually register the variables in GitLab (manual, one-time)**

Follow the doc. Verification: the GitLab CI/CD Variables page shows every row from the table.

- [ ] **Step 4: Commit**

```bash
git add docs/azure-demo-ci-variables.md
git commit -m "docs: checklist for Azure demo GitLab CI/CD variables"
```

---

### Task 4: CI deploy pipeline (registry-push, deploy, verify stages)

**Files:**
- Create: `scripts/deploy-to-vm.sh`
- Modify: `.gitlab-ci.yml:16-25` (stages list), append new jobs after `quality-gate` (currently ends at `.gitlab-ci.yml:543`)

**Interfaces:**
- Consumes: `docker-compose.prod.yml`, `Caddyfile` (Task 1); `AZURE_VM_HOST`, `ACR_LOGIN_SERVER`, `ACR_USERNAME`, `ACR_PASSWORD`, `SSH_PRIVATE_KEY`, `DEPLOY_TOKEN_USER`, `DEPLOY_TOKEN_PASSWORD`, `EAM_*` variables (Task 3); the `:ci`-tagged images built by the existing `build-images` job (`.gitlab-ci.yml:268-283`); the VM bootstrapped in Task 5.
- Produces: `demo`-tagged images in both registries; a running deployment on the VM; a pipeline that fails loudly (`verify` job) if the deploy didn't work.

- [ ] **Step 1: Write `scripts/deploy-to-vm.sh`**

```bash
#!/usr/bin/env bash
# Deploys the current registry-pushed :demo images to the Azure demo VM.
# Run by the GitLab CI `deploy` job. Expects these env vars to already be
# set (GitLab CI/CD variables): AZURE_VM_HOST, SSH_PRIVATE_KEY, CI_REGISTRY,
# CI_REGISTRY_IMAGE, DEPLOY_TOKEN_USER, DEPLOY_TOKEN_PASSWORD, plus every
# EAM_* app secret (Task 3).
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
```

- [ ] **Step 2: Verify the script is syntactically valid**

```bash
bash -n scripts/deploy-to-vm.sh
```

Expected: no output, exit code 0.

- [ ] **Step 3: Add the three new stages to `.gitlab-ci.yml`**

Change the `stages:` list at `.gitlab-ci.yml:16-25` from:

```yaml
stages:
  - secret-scan
  - sca-deps
  - test
  - sast
  - build
  - image-scan
  - dast
  - lint
  - gate
```

to:

```yaml
stages:
  - secret-scan
  - sca-deps
  - test
  - sast
  - build
  - image-scan
  - dast
  - lint
  - gate
  - registry-push
  - deploy
  - verify
```

- [ ] **Step 4: Append the three new jobs to the end of `.gitlab-ci.yml`**

Add after the existing `quality-gate` job (after `.gitlab-ci.yml:543`):

```yaml

# ─── Stage 8: Registry Push (Azure demo deployment, ~6-day window) ─────────
# Reuses the :ci images build-images already built. Rebuilds only the
# frontend, since Vite bakes VITE_API_BASE_URL in at build time and the
# :ci frontend was built with a localhost URL — the demo needs the real
# public HTTPS URL baked in instead.

registry-push:
  stage: registry-push
  needs: [quality-gate]
  tags: [local]
  image: docker:24-cli
  script:
    - docker build --build-arg VITE_API_BASE_URL=https://${AZURE_VM_HOST} -t eam-frontend:demo ./app/frontend
    - echo "$CI_REGISTRY_PASSWORD" | docker login $CI_REGISTRY -u $CI_REGISTRY_USER --password-stdin
    - echo "$ACR_PASSWORD" | docker login $ACR_LOGIN_SERVER -u $ACR_USERNAME --password-stdin
    - |
      for pair in "backend|eam-backend:ci" "frontend|eam-frontend:demo" "ml-service|eam-ml-microservice:ci" "rag-service|eam-rag-service:ci"; do
        SVC="${pair%%|*}"
        SRC="${pair#*|}"
        docker tag "$SRC" "$CI_REGISTRY_IMAGE/${SVC}:demo"
        docker push "$CI_REGISTRY_IMAGE/${SVC}:demo"
        docker tag "$SRC" "$ACR_LOGIN_SERVER/${SVC}:demo"
        docker push "$ACR_LOGIN_SERVER/${SVC}:demo"
      done
  rules: *branch-rules
  timeout: 20 minutes
  allow_failure: false

# ─── Stage 9: Deploy (SSH to Azure demo VM) ─────────────────────────────────

deploy:
  stage: deploy
  needs: [registry-push]
  tags: [local]
  image: alpine:3.19
  before_script:
    - apk add --no-cache openssh-client bash git
  script:
    - bash scripts/deploy-to-vm.sh
  rules: *branch-rules
  timeout: 15 minutes
  allow_failure: false

# ─── Stage 10: Verify (curl the live demo URL) ──────────────────────────────

verify:
  stage: verify
  needs: [deploy]
  tags: [local]
  image: alpine:3.19
  before_script:
    - apk add --no-cache curl
  script:
    - |
      for i in $(seq 1 10); do
        if curl -sf "https://${AZURE_VM_HOST}/api/v1/health"; then
          echo "Backend healthy."
          break
        fi
        echo "Attempt $i/10 failed, retrying in 10s..."
        sleep 10
        if [ "$i" -eq 10 ]; then
          echo "FAIL: backend never became healthy at https://${AZURE_VM_HOST}/api/v1/health"
          exit 1
        fi
      done
      curl -sf "https://${AZURE_VM_HOST}/" -o /dev/null && echo "Frontend reachable at https://${AZURE_VM_HOST}/"
  rules: *branch-rules
  timeout: 5 minutes
  allow_failure: false
```

- [ ] **Step 5: Verify the YAML is syntactically valid**

Run:

```bash
docker run --rm -v "$(pwd)/.gitlab-ci.yml:/ci.yml:ro" pipelinecomponents/gitlab-ci-lint:latest gitlab-ci-lint /ci.yml
```

If that image isn't available/practical locally, a lighter check is any YAML parser, e.g.:

```bash
python3 -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))" && echo "YAML OK"
```

Expected: `YAML OK` (this only checks YAML syntax, not GitLab-specific schema — full validation happens when the pipeline actually runs in Task 6).

- [ ] **Step 6: Commit**

```bash
git add scripts/deploy-to-vm.sh .gitlab-ci.yml
git commit -m "deploy: add registry-push/deploy/verify CI stages for Azure demo"
```

---

### Task 5: Bootstrap the VM (Docker, git clone)

**Files:** none (manual SSH session — no repo files change)

**Interfaces:**
- Consumes: VM created in Task 2, SSH key from Task 2.
- Produces: a VM with Docker + Compose plugin installed and the repo cloned to `~/EAMSagemCom`, ready for Task 4's `deploy` job to `git pull` into.

- [ ] **Step 1: Create a GitLab Deploy Token clone URL**

Using the `DEPLOY_TOKEN_USER`/`DEPLOY_TOKEN_PASSWORD` from Task 3 Step 1, and your project's HTTPS clone path (GitLab → your project → Code → Clone → Copy HTTPS, without the `https://` prefix, e.g. `gitlab.com/<namespace>/eamsagemcom.git`):

```bash
CLONE_URL="https://${DEPLOY_TOKEN_USER}:${DEPLOY_TOKEN_PASSWORD}@<your-clone-path>"
```

- [ ] **Step 2: SSH in and bootstrap**

```bash
ssh -i ~/.ssh/eam_demo_deploy azureuser@eam-demo.westeurope.cloudapp.azure.com
```

Then, on the VM:

```bash
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker azureuser
# log out and back in for the group change to take effect, then:
git clone "$CLONE_URL" ~/EAMSagemCom
```

- [ ] **Step 3: Verify**

Log out (`exit`) and back in (so the `docker` group membership applies), then:

```bash
ssh -i ~/.ssh/eam_demo_deploy azureuser@eam-demo.westeurope.cloudapp.azure.com \
  'docker compose version && git -C ~/EAMSagemCom status'
```

Expected: a Docker Compose version string, and `git status` reporting a clean checkout on the expected branch — no `- Files:` changes needed, this step is purely verification.

---

### Task 6: End-to-end pipeline run and screenshot capture

**Files:** none

**Interfaces:**
- Consumes: everything from Tasks 1–5.
- Produces: the actual deliverable — live app + a green pipeline + Azure resources, screenshotted.

- [ ] **Step 1: Trigger the pipeline**

```bash
git push origin Phase_2
```

- [ ] **Step 2: Watch the pipeline in GitLab**

GitLab → your project → CI/CD → Pipelines → the new run. Confirm `registry-push`, `deploy`, and `verify` all go green after the existing stages.

Expected: `verify` job log ends with `Backend healthy.` and `Frontend reachable at https://<AZURE_VM_HOST>/`.

- [ ] **Step 3: Manually confirm and screenshot**

- Open `https://<AZURE_VM_HOST>/` in a browser — confirm the padlock/HTTPS is present, log in, screenshot the app.
- Open `https://<AZURE_VM_HOST>/grafana/` — confirm it loads, screenshot a dashboard.
- Azure Portal → the resource group `eam-demo-rg` — screenshot the VM's overview page (running state, public IP/DNS) and the ACR's repositories page (showing the pushed `demo`-tagged images).
- GitLab → the green pipeline run — screenshot the full stage graph.

- [ ] **Step 4: If `verify` fails**

Check the `deploy` job log first (most likely culprit: a missing/misnamed `EAM_*` variable, or the VM's Docker not yet logged into the GitLab registry). Fix the specific cause, re-push, and re-run — no rollback needed per this plan's Global Constraints; the previous containers keep serving in the meantime.

---

### Task 7: Teardown script (run at the end of the 6-day window)

**Files:**
- Create: `scripts/azure-teardown.sh`

**Interfaces:**
- Consumes: `RESOURCE_GROUP` name from Task 2.
- Produces: all Azure billing stopped.

- [ ] **Step 1: Write the teardown script**

```bash
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
```

- [ ] **Step 2: Verify the script is syntactically valid**

```bash
bash -n scripts/azure-teardown.sh
```

Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add scripts/azure-teardown.sh
git commit -m "deploy: add Azure demo teardown script"
```

- [ ] **Step 4: Actually run it (manual, end of the 6-day window)**

```bash
bash scripts/azure-teardown.sh
az group show --name eam-demo-rg   # re-run after a few minutes to confirm deletion completed
```

Expected: the confirmation command eventually returns a `ResourceGroupNotFound` error — no more billing.
