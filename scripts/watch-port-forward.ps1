# Keeps `kubectl port-forward svc/frontend 3000:80 -n eam-staging` alive.
#
# A bare port-forward pins to one pod and does not follow rollouts (see
# scripts/deploy-aks.sh's own warning) -- it also just dies outright on
# logoff, sleep, or any network blip. This wraps it in a restart loop so
# http://localhost:3000 stays up across all of that without you noticing.
#
# Not meant to be run by hand -- see register-port-forward-task.ps1, which
# schedules this to start automatically at logon and keeps it running via
# Windows Task Scheduler.

$logDir = Join-Path $PSScriptRoot 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir 'port-forward.log'

function Write-Log($msg) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" | Out-File -FilePath $logFile -Append -Encoding utf8
}

Write-Log "watchdog started"

while ($true) {
    try {
        Write-Log "starting kubectl port-forward"
        & kubectl port-forward svc/frontend 3000:80 -n eam-staging *>> $logFile
        Write-Log "port-forward exited (code $LASTEXITCODE), restarting in 3s"
    } catch {
        Write-Log "port-forward errored: $_"
    }
    Start-Sleep -Seconds 3
}
