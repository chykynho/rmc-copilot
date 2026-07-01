param(
    [string]$At = "07:00",
    [string]$TaskName = "RMC Copilot - Coleta Otimizacao Aria UI Segura"
)

$ErrorActionPreference = "Stop"

$project = (Get-Location).Path
$script = Join-Path $project "scripts\201_collect_all_optimization_ui_secure.ps1"
$log = Join-Path $project "logs\optimization_ui_secure_daily.log"

New-Item -ItemType Directory -Path (Join-Path $project "logs") -Force | Out-Null

$args = "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -NoPrompt"
$cmdArgs = "/c powershell.exe $args >> `"$log`" 2>&1"

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmdArgs -WorkingDirectory $project
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel LeastPrivilege

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null

Write-Host "[OK] Tarefa agendada: $TaskName às $At" -ForegroundColor Green
Write-Host "[OK] Log: $log" -ForegroundColor Green
Write-Host "[INFO] A tarefa usa Windows Credential Manager; nenhum segredo fica no argumento da task." -ForegroundColor Yellow
