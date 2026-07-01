$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

python .\scripts\215_validate_dashboard_otmz_assert_fix.py
if ($LASTEXITCODE -ne 0) {
    throw "Validação 16A.14.7 falhou"
}
