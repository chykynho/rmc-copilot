$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

python .\scripts\202_validate_all_optimization_ui_secure.py
if ($LASTEXITCODE -ne 0) {
    throw "Validacao da coleta segura falhou"
}
