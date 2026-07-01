$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "[INFO] Instalando dependencias seguras" -ForegroundColor Cyan
python -m pip install --upgrade keyring browser-cookie3
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao instalar dependencias"
}
Write-Host "[OK] Dependencias instaladas" -ForegroundColor Green
