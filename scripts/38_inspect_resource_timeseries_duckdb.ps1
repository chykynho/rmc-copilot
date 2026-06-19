param(
    [string]$DbPath = "data/database/rmc_copilot.duckdb"
)

python -m rmc_copilot.resource_timeseries.inspect_duckdb_schema --db $DbPath
