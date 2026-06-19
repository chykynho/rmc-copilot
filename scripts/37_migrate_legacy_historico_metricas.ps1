param(
    [string]$DbPath = "data/database/rmc_copilot.duckdb",
    [string]$ExecutionId = ""
)

if ([string]::IsNullOrWhiteSpace($ExecutionId)) {
    python -m rmc_copilot.resource_timeseries.migrate_legacy_history --db $DbPath
} else {
    python -m rmc_copilot.resource_timeseries.migrate_legacy_history --db $DbPath --execution-id $ExecutionId
}
