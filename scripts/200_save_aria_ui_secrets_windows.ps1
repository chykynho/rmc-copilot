$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "[INFO] Salvando Cookie/secureToken no Windows Credential Manager" -ForegroundColor Cyan
Write-Host "[SEGURANCA] Nao salva em arquivo texto." -ForegroundColor Yellow

python .\scripts\200_save_aria_ui_secrets_windows.py
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao salvar segredos no Windows Credential Manager"
}
