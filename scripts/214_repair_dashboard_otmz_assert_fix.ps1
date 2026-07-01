$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

python .\scripts\214_repair_dashboard_otmz_assert_fix.py
if ($LASTEXITCODE -ne 0) {
    throw "Hotfix 16A.14.7 falhou"
}
