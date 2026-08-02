<#
.SYNOPSIS
    Shrink Docker Desktop's WSL2 virtual disk back to its real size.

.DESCRIPTION
    docker_data.vhdx grows as images and build cache accumulate but never
    shrinks on its own. "docker prune" frees space INSIDE the file while the
    file itself stays large, so Windows never sees the space back. This
    compacts it and returns the empty slack.

    Non-destructive: no image, container or volume is deleted. Run the prunes
    below first so there is slack to reclaim:
        docker builder prune -af
        docker image prune -af

.NOTES
    MUST run elevated - diskpart requires Administrator.
    ASCII-only on purpose: Windows PowerShell 5.1 reads .ps1 as ANSI unless the
    file has a BOM, so non-ASCII characters here would corrupt and fail to parse.
#>

$ErrorActionPreference = 'Stop'

$vhdx = Join-Path $env:LOCALAPPDATA 'Docker\wsl\disk\docker_data.vhdx'

$principal = New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERROR: not elevated. Re-run from an Administrator PowerShell." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $vhdx)) {
    Write-Host "ERROR: not found: $vhdx" -ForegroundColor Red
    Write-Host "Docker may store it elsewhere. Check Settings > Resources > Advanced." -ForegroundColor Yellow
    exit 1
}

$before     = (Get-Item $vhdx).Length
$freeBefore = (Get-PSDrive C).Free
Write-Host ("vhdx before : {0:N1} GB" -f ($before / 1GB))
Write-Host ("C: free     : {0:N2} GB" -f ($freeBefore / 1GB))

Write-Host ""
Write-Host "Stopping Docker Desktop and WSL..." -ForegroundColor Cyan
Get-Process 'Docker Desktop' -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 5
wsl --shutdown
Start-Sleep -Seconds 10

# diskpart cannot take inline commands - it reads a script file.
$lines = @(
    ('select vdisk file="' + $vhdx + '"'),
    'attach vdisk readonly',
    'compact vdisk',
    'detach vdisk',
    'exit'
)
$tmp = Join-Path $env:TEMP ('compact_docker_' + (Get-Random) + '.txt')
$lines | Out-File -FilePath $tmp -Encoding ascii

Write-Host "Compacting. Several minutes, no progress bar - let it finish." -ForegroundColor Cyan
try {
    diskpart /s $tmp
} finally {
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
}

$after     = (Get-Item $vhdx).Length
$freeAfter = (Get-PSDrive C).Free
Write-Host ""
Write-Host ("vhdx after  : {0:N1} GB" -f ($after / 1GB))
Write-Host ("reclaimed   : {0:N1} GB" -f (($before - $after) / 1GB))
Write-Host ("C: free     : {0:N2} GB  (was {1:N2} GB)" -f ($freeAfter / 1GB), ($freeBefore / 1GB))

Write-Host ""
Write-Host "Restarting Docker Desktop..." -ForegroundColor Cyan
Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
Write-Host "Done. Give Docker about 30s, then check with: docker ps" -ForegroundColor Green
