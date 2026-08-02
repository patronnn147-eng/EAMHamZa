<#
.SYNOPSIS
    Deploy updated code to AKS (eam-staging). The AKS equivalent of
    "docker compose up --build -d".

.EXAMPLE
    .\scripts\deploy-aks.ps1 backend
    .\scripts\deploy-aks.ps1 frontend,ml-service
    .\scripts\deploy-aks.ps1 all

.DESCRIPTION
    Per service: build for linux/amd64 -> push to ACR -> restart the
    deployment. The image tag is reused, so the cluster only picks up a new
    build when the deployment restarts (imagePullPolicy is Always).

.NOTES
    ASCII-only on purpose: Windows PowerShell 5.1 reads .ps1 as ANSI unless the
    file has a BOM, so non-ASCII characters would corrupt and fail to parse.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string[]] $Services
)

$ErrorActionPreference = 'Stop'

$Registry = 'eamdemoacr24102.azurecr.io'
$Tag      = 'aks-staging'
$Namespace = 'eam-staging'

# Build context per service. celery-worker/celery-beat are deliberately absent:
# they run the backend image, so building backend redeploys them too.
$Context = @{
    'backend'     = './app/backend'
    'frontend'    = './app/frontend'
    'ml-service'  = './app/ml-microservice'
    'rag-service' = './app/rag-service'
}
# Deployments to restart once a given image is rebuilt.
$Restarts = @{
    'backend'     = @('backend', 'celery-worker', 'celery-beat')
    'frontend'    = @('frontend')
    'ml-service'  = @('ml-service')
    'rag-service' = @('rag-service')
}

if ($Services.Count -eq 1 -and $Services[0] -eq 'all') {
    $Services = @('backend', 'frontend', 'ml-service', 'rag-service')
}

foreach ($svc in $Services) {
    if (-not $Context.ContainsKey($svc)) {
        Write-Host "Unknown service: $svc" -ForegroundColor Red
        Write-Host "Valid: all, backend, frontend, ml-service, rag-service" -ForegroundColor Yellow
        exit 1
    }
}

# Run from the repo root regardless of where the script was invoked.
Set-Location (Split-Path $PSScriptRoot -Parent)

# Docker Desktop drops its ACR token on restart; re-auth is cheap and idempotent.
Write-Host ">> authenticating to ACR" -ForegroundColor Cyan
az acr login --name $Registry.Split('.')[0] | Out-Null
if ($LASTEXITCODE -ne 0) { throw "az acr login failed" }

foreach ($svc in $Services) {
    Write-Host ""
    Write-Host "=== $svc : building ===" -ForegroundColor Cyan

    # The frontend bakes its API base URL in at build time. It MUST be empty so
    # the app calls same-origin /api/* paths, which its own nginx proxies. The
    # Dockerfile default (http://localhost:8000) builds an app that works
    # nowhere but a dev laptop.
    $buildArgs = @(
        'buildx', 'build', '--platform', 'linux/amd64',
        '-t', "$Registry/$svc`:$Tag", '--push'
    )
    if ($svc -eq 'frontend') {
        $buildArgs += @('--build-arg', 'VITE_API_BASE_URL=')
    }
    $buildArgs += $Context[$svc]

    & docker @buildArgs
    if ($LASTEXITCODE -ne 0) { throw "build failed for $svc" }

    Write-Host "=== $svc : rolling out ===" -ForegroundColor Cyan
    foreach ($dep in $Restarts[$svc]) {
        kubectl rollout restart "deployment/$dep" -n $Namespace
    }
    foreach ($dep in $Restarts[$svc]) {
        kubectl rollout status "deployment/$dep" -n $Namespace --timeout=300s
    }
}

Write-Host ""
kubectl get pods -n $Namespace

Write-Host ""
Write-Host "Done. If a port-forward was open, restart it - it pins to a pod and" -ForegroundColor Yellow
Write-Host "does not follow rollouts, so it keeps showing the old, now dead pod:" -ForegroundColor Yellow
Write-Host "    kubectl port-forward svc/frontend 3000:80 -n eam-staging" -ForegroundColor Yellow
