$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$PythonExe = Join-Path (Get-Location) ".rmcllm\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

& $PythonExe .\scripts\167_check_pyvmomi_import.py
if ($LASTEXITCODE -ne 0) {
    throw "Import pyVim/pyVmomi falhou"
}
