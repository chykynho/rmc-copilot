param(
    [string]$HostName = "mor-vropsprd01.bvnet.bv",
    [string]$DcId = "30f49c2a-10b3-4bb2-9c8c-1aef8a486a16",
    [int]$Limit = 200,
    [string]$Reasons = "orphaned_disk,idle_vms,poweredOff_vms,vm_snapshots",
    [int]$MaxTargets = 0,
    [switch]$AllowBrowserCookie,
    [switch]$NoPrompt
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "[INFO] Etapa 16A.14 - Coleta segura de TODOS os itens de otimizacao" -ForegroundColor Cyan
Write-Host "[REGRA] Somente leitura. Nenhuma acao operacional sera executada." -ForegroundColor Yellow
Write-Host "[SEGURANCA] Cookie/secureToken sao lidos do Windows Credential Manager; nao de arquivo texto." -ForegroundColor Yellow

$argsPy = @(
    ".\scripts\201_collect_all_optimization_ui_secure.py",
    "--host", $HostName,
    "--dc-id", $DcId,
    "--limit", "$Limit",
    "--reasons", $Reasons
)
if ($MaxTargets -gt 0) {
    $argsPy += @("--max-targets", "$MaxTargets")
}
if ($AllowBrowserCookie) {
    $argsPy += "--allow-browser-cookie"
}

python @argsPy
if ($LASTEXITCODE -ne 0) {
    throw "Coleta segura de otimizacao falhou"
}
