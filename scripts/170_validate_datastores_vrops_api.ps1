$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
python .\scripts\170_validate_datastores_vrops_api.py
if ($LASTEXITCODE -ne 0) { throw "Validação datastores vROps API falhou" }
