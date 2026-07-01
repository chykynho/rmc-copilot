$ErrorActionPreference = "Stop"

$plain = Join-Path (Get-Location) "config\local\aria_ui_session.clixml"

if (Test-Path $plain) {
    Remove-Item $plain -Force
    Write-Host "[OK] Removido arquivo antigo com sessao local: $plain" -ForegroundColor Green
}
else {
    Write-Host "[OK] Arquivo antigo nao existe: $plain" -ForegroundColor Green
}

Write-Host "[INFO] Verifique se config/local esta no .gitignore." -ForegroundColor Yellow
