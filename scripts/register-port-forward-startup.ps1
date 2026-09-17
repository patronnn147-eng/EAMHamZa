# Non-admin alternative to register-port-forward-task.ps1. Task Scheduler
# registration needs elevation this account doesn't have, so instead this
# drops a shortcut in the per-user Startup folder -- the standard no-admin
# way to run something at logon on Windows. Windows itself launches it next
# time you log in; no scheduled task, no elevation, no terminal window.
#
#   .\scripts\register-port-forward-startup.ps1

$scriptPath = Join-Path $PSScriptRoot 'watch-port-forward.ps1'
$startupDir = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupDir 'EAM-PortForward.lnk'

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = (Get-Command powershell.exe).Source
$shortcut.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.WindowStyle = 7  # minimized
$shortcut.Description = 'Keeps eam-staging port-forward (localhost:3000) alive'
$shortcut.Save()

Write-Host "Startup shortcut created: $shortcutPath"
Write-Host "It will run automatically next time you log in to Windows."
Write-Host ""
Write-Host "To remove: Remove-Item '$shortcutPath'"
