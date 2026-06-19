param(
    [Parameter(Mandatory=$true)]
    [string]$InputExcel,

    [string]$DatabasePath = "data/database/rmc_copilot.duckdb",

    [string]$RunId = "",

    [switch]$NoReplace
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $InputExcel)) {
    throw "Arquivo Excel não encontrado: $InputExcel"
}

$argsList = @(
    "-m", "rmc_copilot.resource_timeseries.vrops_duckdb_ingest",
    "--input-excel", $InputExcel,
    "--db-path", $DatabasePath
)

if ($RunId -ne "") {
    $argsList += @("--run-id", $RunId)
}

if ($NoReplace) {
    $argsList += "--no-replace"
}

python @argsList
