$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "[INFO] Instalando dependencias de otimizacao vCenter/pyVmomi" -ForegroundColor Cyan
Write-Host "[INFO] Pacote pip correto: pyvmomi" -ForegroundColor Yellow
Write-Host "[INFO] Imports corretos no Python: pyVim e pyVmomi" -ForegroundColor Yellow

$PythonExe = Join-Path (Get-Location) ".rmcllm\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install pyvmomi keyring duckdb pandas openpyxl

& $PythonExe .\scripts\167_check_pyvmomi_import.py
if ($LASTEXITCODE -ne 0) {
    throw "Falha na validacao do import pyVim/pyVmomi"
}

Write-Host "[OK] Dependencias instaladas e import pyVim/pyVmomi validado." -ForegroundColor Green
