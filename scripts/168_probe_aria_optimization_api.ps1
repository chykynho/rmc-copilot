param(
    [string]$HostName = "mor-vropsprd01.bvnet.bv",
    [string]$AuthSource = "bvnet.bv",
    [string]$User = "",
    [string]$OutDir = "data\debug"
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "[INFO] Etapa 16A.3 - Probe API Aria/vROps para Datastores/Optimization" -ForegroundColor Cyan
Write-Host "[REGRA] Somente leitura. Nenhuma acao operacional sera executada." -ForegroundColor Yellow

$argsPy = @(
    ".\scripts\168_probe_aria_optimization_api.py",
    "--host", $HostName,
    "--auth-source", $AuthSource,
    "--out-dir", $OutDir
)
if ($User -ne "") { $argsPy += @("--user", $User) }

python @argsPy
if ($LASTEXITCODE -ne 0) { throw "Probe API Aria/vROps falhou" }
