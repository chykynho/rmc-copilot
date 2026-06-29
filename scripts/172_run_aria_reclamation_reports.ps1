param(
    [string]$HostName = "mor-vropsprd01.bvnet.bv",
    [string]$User = "",
    [string]$AuthSource = "bvnet.bv",
    [string]$Report = "clusters",
    [string]$ResourceNameFilter = "BV_PRD",
    [int]$MaxResources = 0,
    [int]$Timeout = 900
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "[INFO] Etapa 16A.5 - Reclamation Reports via Aria/vROps API" -ForegroundColor Cyan
Write-Host "[REGRA] Somente leitura/geracao de relatorio. Nenhuma acao operacional sera executada." -ForegroundColor Yellow

$script = Join-Path $PSScriptRoot "172_run_aria_reclamation_reports.py"

$argsPy = @(
    $script,
    "--host", $HostName,
    "--auth-source", $AuthSource,
    "--report", $Report,
    "--resource-name-filter", $ResourceNameFilter,
    "--timeout", "$Timeout"
)

if ($User -ne "") { $argsPy += @("--user", $User) }
if ($MaxResources -gt 0) { $argsPy += @("--max-resources", "$MaxResources") }

python @argsPy
if ($LASTEXITCODE -ne 0) {
    throw "Execucao dos Reclamation Reports via Aria/vROps API falhou"
}
