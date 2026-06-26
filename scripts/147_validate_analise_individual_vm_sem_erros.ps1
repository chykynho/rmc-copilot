Param([string]$Python="python")
$ErrorActionPreference="Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = Join-Path $ScriptDir "147_validate_analise_individual_vm_sem_erros.py"
Write-Host "[INICIO] Validação hotfix 15F.10.34 Análise Individual de VM" -ForegroundColor Cyan
& $Python $Py
if ($LASTEXITCODE -ne 0) { throw "Validação 15F.10.34 falhou." }
Write-Host "[OK] Validação 15F.10.34 concluída com sucesso." -ForegroundColor Green
