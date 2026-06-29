param(
    [string]$Db = "data\database\rmc_copilot.duckdb",
    [string]$VCenterHost = "srv-vcsprd01",
    [string]$User = "",
    [string]$Cluster = "",
    [int]$MaxVms = 0,
    [int]$DaysBackPowerOff = 365,
    [int]$SnapshotWarningDays = 20,
    [switch]$IncludeOrphanScan,
    [string]$DatastoreFilter = ""
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "[INFO] Etapa 16A.2 - Coleta direta vCenter/pyVmomi" -ForegroundColor Cyan
Write-Host "[REGRA] IA/coleta nao executa acao operacional; apenas coleta dados para relatorio/recomendacao." -ForegroundColor Yellow

$script = Join-Path $PSScriptRoot "165_collect_optimization_vcenter.py"

$argsPy = @(
    $script,
    "--db", $Db,
    "--vcenter-host", $VCenterHost,
    "--days-back-poweroff", "$DaysBackPowerOff",
    "--snapshot-warning-days", "$SnapshotWarningDays"
)

if ($User -ne "") { $argsPy += @("--user", $User) }
if ($Cluster -ne "") { $argsPy += @("--cluster", $Cluster) }
if ($MaxVms -gt 0) { $argsPy += @("--max-vms", "$MaxVms") }
if ($IncludeOrphanScan) { $argsPy += "--include-orphan-scan" }
if ($DatastoreFilter -ne "") { $argsPy += @("--datastore-filter", $DatastoreFilter) }

$PythonExe = Join-Path (Get-Location) ".rmcllm\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) { $PythonExe = "python" }

& $PythonExe @argsPy
if ($LASTEXITCODE -ne 0) {
    throw "Falha na coleta vCenter/pyVmomi 16A.2"
}
