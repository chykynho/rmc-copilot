@'
# Cole esta célula no final do notebook/script de coleta vROps, depois de gerar:
# df_all_vms_os, df_partitions_selected, df_cpu_hist, df_mem_hist, df_disk_hist,
# df_cpu_log, df_mem_log, df_disk_log e report_file.

from rmc_copilot.resource_timeseries.vrops_duckdb_ingest import save_vrops_collection_from_notebook_globals

duckdb_summary = save_vrops_collection_from_notebook_globals(
    globals(),
    source_file=str(report_file),
    db_path="data/database/rmc_copilot.duckdb",
    replace=True,
)

display(duckdb_summary)
'@
