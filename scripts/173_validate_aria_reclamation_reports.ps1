$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

python .\scripts\173_validate_aria_reclamation_reports.ps1.py
if ($LASTEXITCODE -ne 0) {
    throw "Validacao de Reclamation Reports falhou"
}
