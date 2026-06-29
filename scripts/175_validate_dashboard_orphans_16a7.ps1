$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "[INFO] Etapa 16A.7 - Validando dados e pagina de Discos Orfaos" -ForegroundColor Cyan
Write-Host "[REGRA] Somente leitura. Nenhuma acao operacional sera executada." -ForegroundColor Yellow

python .\scripts\175_validate_dashboard_orphans_16a7.py

if ($LASTEXITCODE -ne 0) {
    throw "Validacao 16A.7 falhou"
}
