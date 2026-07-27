# Azure Demo — GitLab CI/CD Variables

Registered at: Project -> Settings -> CI/CD -> Variables.
All rows below: Protected = yes (only runs on protected branches/`Phase_2`
if protected, otherwise unprotect `Phase_2` temporarily for the demo window).
"Masked" secrets must contain no newlines except SSH_PRIVATE_KEY, which
GitLab's masking cannot handle multi-line — leave SSH_PRIVATE_KEY
**unmasked** (Protected only) since it's only ever readable by pipeline jobs
on this project, not printed to job logs by any script in this plan.

## Deploy Token (do this first)

GitLab -> your project -> Settings -> Repository -> Deploy tokens -> Add
token. Name: `eam-demo-vm-pull`. Scope: `read_registry` only. Copy the
generated username/password immediately (shown once) — these become
`DEPLOY_TOKEN_USER` / `DEPLOY_TOKEN_PASSWORD` below.

## Variables

| Variable | Masked | Source |
|---|---|---|
| `AZURE_VM_HOST` | no | `scripts/azure-provision-vm.sh` output |
| `ACR_LOGIN_SERVER` | no | `scripts/azure-provision-vm.sh` output |
| `ACR_USERNAME` | yes | `scripts/azure-provision-vm.sh` output (`az acr credential show`) |
| `ACR_PASSWORD` | yes | `scripts/azure-provision-vm.sh` output (`az acr credential show`) |
| `SSH_PRIVATE_KEY` | no (see above) | `scripts/azure-provision-vm.sh` output (`cat ~/.ssh/eam_demo_deploy`) |
| `DEPLOY_TOKEN_USER` | yes | Deploy Token step above |
| `DEPLOY_TOKEN_PASSWORD` | yes | Deploy Token step above |
| `EAM_POSTGRES_USER` | yes | not set in local `.env` (falls back to `docker-compose.yml`'s default `postgres`) — generate a real value for the demo, e.g. `openssl rand -hex 8` |
| `EAM_POSTGRES_PASSWORD` | yes | not set in local `.env` (falls back to the default `postgres`) — generate a real value, e.g. `openssl rand -hex 24`. Worth doing even though Postgres isn't publicly reachable — cheap to fix, no reason to run a public-cloud VM on the literal word "postgres" |
| `EAM_POSTGRES_DB` | no | `asset_management` (matches local `.env`) |
| `EAM_JWT_SECRET_KEY` | yes | **reuse the exact value already in local `.env`'s `JWT_SECRET_KEY`** — copy-paste directly from your `.env` file into the GitLab variable field |
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

In every "reuse local `.env`" row above: open your own `.env` file and copy
the value directly into the GitLab CI/CD variable field — never type real
secrets into this doc or any other git-tracked file.

Deliberately **not** set (app defaults are fine for a throwaway demo):
`EAM_JWT_ALGORITHM`, `EAM_JWT_EXPIRE_MINUTES`, `EAM_CELERY_BROKER_URL`,
`EAM_SMTP_SERVER`, `EAM_SMTP_PORT`, `EAM_SMTP_USERNAME`, `EAM_FROM_EMAIL`,
`EAM_FROM_NAME`, `EAM_RERANK_ENABLED`, `EAM_HYBRID_ENABLED`,
`EAM_ML_ALLOW_SYNTHETIC_TELEMETRY`.

## Verification

After adding all rows, Settings -> CI/CD -> Variables should list every
`EAM_*`, `AZURE_VM_HOST`, `ACR_*`, `SSH_PRIVATE_KEY`, and `DEPLOY_TOKEN_*`
row above.
