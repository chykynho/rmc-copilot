param(
    [string]$HostName = "mor-vropsprd01.bvnet.bv",
    [string]$User = "",
    [string]$AuthSource = "bvnet.bv"
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "[INFO] Deep probe Aria/vROps - orphaned disks / reclaim" -ForegroundColor Cyan
Write-Host "[REGRA] Somente leitura. Nenhuma acao operacional sera executada." -ForegroundColor Yellow

$script = Join-Path $PSScriptRoot "171_probe_aria_reclaim_orphans_deep.py"

$argsPy = @(
    $script,
    "--host", $HostName,
    "--auth-source", $AuthSource
)

if ($User -ne "") { $argsPy += @("--user", $User) }

python @argsPy
if ($LASTEXITCODE -ne 0) {
    throw "Deep probe Aria/vROps falhou"
}
