$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

python .\scripts\166_validate_optimization_vcenter_16a2.py
if ($LASTEXITCODE -ne 0) {
    throw "Validacao 16A.2 falhou"
}
