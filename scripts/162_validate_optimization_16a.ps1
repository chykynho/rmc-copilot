param(
    [string]$DbPath = "data\database\rmc_copilot.duckdb"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$Python = ".\.rmcllm\Scripts\python.exe"
if (!(Test-Path $Python)) { $Python = "python" }

& $Python ".\scripts\162_validate_optimization_16a.py" --db $DbPath
exit $LASTEXITCODE
