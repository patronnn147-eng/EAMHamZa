#!/usr/bin/env bash
# Deploy updated code to AKS (eam-staging). The AKS equivalent of
# `docker compose up --build -d`.
#
#   ./scripts/deploy-aks.sh backend
#   ./scripts/deploy-aks.sh frontend ml-service
#   ./scripts/deploy-aks.sh all
#
# Steps per service: build for linux/amd64 -> push to ACR -> restart the
# deployment. imagePullPolicy is Always and the tag is reused, so a rollout
# restart is what makes the cluster pull the new image.
set -euo pipefail

REGISTRY="eamdemoacr24102.azurecr.io"
TAG="aks-staging"
NS="eam-staging"

# service : build context. celery-worker/celery-beat intentionally absent —
# they run the backend image, so building backend redeploys them too.
declare -A CONTEXT=(
  [backend]="./app/backend"
  [frontend]="./app/frontend"
  [ml-service]="./app/ml-microservice"
  [rag-service]="./app/rag-service"
)
# Deployments to restart once a given image is rebuilt.
declare -A RESTARTS=(
  [backend]="backend celery-worker celery-beat"
  [frontend]="frontend"
  [ml-service]="ml-service"
  [rag-service]="rag-service"
)

usage() { echo "usage: $0 [all|backend|frontend|ml-service|rag-service ...]"; exit 1; }
[ $# -eq 0 ] && usage

if [ "${1:-}" = "all" ]; then
  SERVICES=(backend frontend ml-service rag-service)
else
  SERVICES=("$@")
fi

for svc in "${SERVICES[@]}"; do
  [ -n "${CONTEXT[$svc]:-}" ] || { echo "unknown service: $svc"; usage; }
done

# Docker Desktop drops its ACR token on restart; re-auth is cheap and idempotent.
echo ">> authenticating to ACR"
MSYS_NO_PATHCONV=1 az acr login --name "${REGISTRY%%.*}" >/dev/null

for svc in "${SERVICES[@]}"; do
  echo
  echo "=== $svc : building ==="

  # The frontend bakes its API base URL in at build time. It MUST be empty so
  # the app calls same-origin /api/* paths, which its own nginx proxies. The
  # Dockerfile's default is http://localhost:8000, which silently produces a
  # build that works nowhere but a dev laptop.
  EXTRA=()
  if [ "$svc" = "frontend" ]; then
    EXTRA=(--build-arg "VITE_API_BASE_URL=")
  fi

  docker buildx build --platform linux/amd64 \
    "${EXTRA[@]}" \
    -t "$REGISTRY/$svc:$TAG" \
    --push "${CONTEXT[$svc]}"

  echo "=== $svc : rolling out ==="
  for dep in ${RESTARTS[$svc]}; do
    MSYS_NO_PATHCONV=1 kubectl rollout restart "deployment/$dep" -n "$NS"
  done
  for dep in ${RESTARTS[$svc]}; do
    MSYS_NO_PATHCONV=1 kubectl rollout status "deployment/$dep" -n "$NS" --timeout=300s
  done
done

echo
MSYS_NO_PATHCONV=1 kubectl get pods -n "$NS"
cat <<'EOF'

Done. If a port-forward was open, restart it — it pins to a pod and does not
follow rollouts, so it will keep showing the old (now dead) pod:

    kubectl port-forward svc/frontend 3000:80 -n eam-staging
EOF
