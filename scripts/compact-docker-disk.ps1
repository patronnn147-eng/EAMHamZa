<#
.SYNOPSIS
    Shrink Docker Desktop's WSL2 virtual disk back to its real size.

.DESCRIPTION
    docker_data.vhdx grows as images/build cache accumulate but never shrinks
    on its own — `docker prune` frees space INSIDE the file while the file
    itself stays large. This compacts it, returning the empty slack to Windows.

    Non-destructive: no image, container or volume is deleted. Run the prunes
    first (see below) so there is slack to reclaim.

.NOTES
    MUST run elevated (diskpart requires admin).
    Docker Desktop is stopped during compaction and can be restarted after.

    Recommended prune before running this:
        docker builder prune -af
        docker image prune -af
#>

$ErrorActionPreference = 'Stop'

$vhdx = "$env:LOCALAPPDATA\Docker\wsl\disk\docker_data.vhdx"

if (-not (Test-Path $vhdx)) {
    Write-Error "Not found: $vhdx`nDocker Desktop may store it elsewhere — check Settings > Resources > Advanced."
}

$principal = New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Not elevated. Re-run this from an Administrator PowerShell."
}

$before = (Get-Item $vhdx).Length
$freeBefore = (Get-PSDrive C).Free
"vhdx before : {0:N1} GB" -f ($before / 1GB)
"C: free     : {0:N2} GB" -f ($freeBefore / 1GB)

Write-Host "`nStopping Docker Desktop and WSL..." -ForegroundColor Cyan
Get-Process 'Docker Desktop' -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 5
wsl --shutdown
Start-Sleep -Seconds 10

# diskpart cannot take inline commands; it reads a script file.
$script = @"
select vdisk file="$vhdx"
attach vdisk readonly
compact vdisk
detach vdisk
exit
"@
$tmp = Join-Path $env:TEMP "compact_docker_$(Get-Random).txt"
$script | Out-File -FilePath $tmp -Encoding ascii

Write-Host "Compacting (several minutes, no progress bar — let it finish)..." -ForegroundColor Cyan
try {
    diskpart /s $tmp
} finally {
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
}

$after = (Get-Item $vhdx).Length
$freeAfter = (Get-PSDrive C).Free
"`nvhdx after  : {0:N1} GB" -f ($after / 1GB)
"reclaimed   : {0:N1} GB" -f (($before - $after) / 1GB)
"C: free     : {0:N2} GB  (was {1:N2} GB)" -f ($freeAfter / 1GB), ($freeBefore / 1GB)

Write-Host "`nRestarting Docker Desktop..." -ForegroundColor Cyan
Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
Write-Host "Done. Give Docker ~30s, then check with: docker ps" -ForegroundColor Green
