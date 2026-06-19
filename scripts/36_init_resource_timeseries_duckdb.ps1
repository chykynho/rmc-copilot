param(
    [string]$DbPath = "data/database/rmc_copilot.duckdb"
)

Write-Host "Inicializando schema granular no DuckDB: $DbPath"
python -m rmc_copilot.resource_timeseries.init_duckdb_schema --db $DbPath
