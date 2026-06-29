param(
    [string]$HostName = "mor-vropsprd01.bvnet.bv",
    [string]$AuthSource = "bvnet.bv",
    [string]$User = "",
    [string]$Db = "data\database\rmc_copilot.duckdb"
)
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
Write-Host "[INFO] Coleta Datastores via vROps/Aria API" -ForegroundColor Cyan
Write-Host "[REGRA] Somente leitura. Nenhuma acao operacional sera executada." -ForegroundColor Yellow
$argsPy = @(".\scripts\169_collect_datastores_vrops_api.py", "--host", $HostName, "--auth-source", $AuthSource, "--db", $Db)
if ($User -ne "") { $argsPy += @("--user", $User) }
python @argsPy
if ($LASTEXITCODE -ne 0) { throw "Coleta de datastores via vROps API falhou" }
