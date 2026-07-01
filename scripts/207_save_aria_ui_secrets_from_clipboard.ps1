$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "[INFO] Salvar Cookie/secureToken pelo Clipboard no Windows Credential Manager" -ForegroundColor Cyan
Write-Host "[SEGURANCA] Nada sera salvo em arquivo texto e nada sera exibido no console." -ForegroundColor Yellow
Write-Host "[SEGURANCA] O segredo fica temporariamente no Clipboard apenas enquanto voce copia; o script limpa no final." -ForegroundColor Yellow

function Get-ClipboardTextSafe {
    try {
        return (Get-Clipboard -Raw)
    }
    catch {
        throw "Nao consegui ler o Clipboard. Copie o texto novamente e tente outra vez."
    }
}

Read-Host "1/2 - Copie o secureToken para a area de transferencia e pressione ENTER aqui"
$secureToken = Get-ClipboardTextSafe

if ([string]::IsNullOrWhiteSpace($secureToken)) {
    throw "Clipboard vazio para secureToken"
}

Write-Host "[OK] secureToken lido do Clipboard, sem exibir valor." -ForegroundColor Green

Read-Host "2/2 - Agora copie o Cookie de Headers > Request Headers > Cookie e pressione ENTER aqui"
$cookie = Get-ClipboardTextSafe

if ([string]::IsNullOrWhiteSpace($cookie)) {
    throw "Clipboard vazio para Cookie"
}

Write-Host "[OK] Cookie lido do Clipboard, sem exibir valor." -ForegroundColor Green

$env:RMC_ARIA_SECURE_TOKEN_IN = $secureToken
$env:RMC_ARIA_COOKIE_IN = $cookie

try {
    python .\scripts\207_save_aria_ui_secrets_from_clipboard.py
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao salvar segredos no Windows Credential Manager"
    }
}
finally {
    Remove-Item Env:\RMC_ARIA_SECURE_TOKEN_IN -ErrorAction SilentlyContinue
    Remove-Item Env:\RMC_ARIA_COOKIE_IN -ErrorAction SilentlyContinue
    try { Clear-Clipboard } catch {}
}

Write-Host "[OK] Clipboard limpo." -ForegroundColor Green
