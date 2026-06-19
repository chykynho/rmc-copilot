# RMC Copilot — Etapa 15-F.2

## Gravação direta da coleta vROps no DuckDB oficial

Esta etapa muda a arquitetura da coleta para o padrão de produto:

```text
vROps / vCenter
      ↓
Coleta RMC
      ↓
DuckDB oficial: data/database/rmc_copilot.duckdb
      ↓
Dashboard / relatórios / forecast / LLM Data+RAG
      ↓
Exportações: Excel, CSV, Parquet, DOCX, PDF
```

O Excel deixa de ser a base principal. Ele continua existindo como exportação/auditoria.

## Tabelas gravadas

A etapa grava nas tabelas criadas na 15-F.1:

- `resource_collection_runs`
- `vm_inventory_snapshots`
- `vm_disk_partitions`
- `vm_resource_timeseries`
- `resource_collection_logs`

## Tabela principal

`vm_resource_timeseries` recebe:

- CPU agregado por timestamp
- MEM agregado por timestamp
- DISK por partição/filesystem quando disponível
- `used_pct`
- `used_gb`
- `free_gb`
- `capacity_gb`
- `cluster`
- `host`
- `vm`
- `vm_resource_id`
- `stat_key`
- `source`

## Uso direto no notebook vROps

Depois da célula que gera o Excel `report_file`, adicione:

```python
from rmc_copilot.resource_timeseries.vrops_duckdb_ingest import save_vrops_collection_from_notebook_globals

duckdb_summary = save_vrops_collection_from_notebook_globals(
    globals(),
    source_file=str(report_file),
    db_path="data/database/rmc_copilot.duckdb",
    replace=True,
)

display(duckdb_summary)
```

A função detecta automaticamente os DataFrames do notebook v5.10.x:

- `df_all_vms_os`, `df_vms_selected`, `df_all_vms`
- `df_partitions_selected`, `df_vm_partitions`
- `df_cpu_hist`
- `df_mem_hist`
- `df_disk_hist`
- `df_cpu_log`, `df_mem_log`, `df_disk_log`
- `df_partition_statkey_log`
- `df_relationship_log`

## Importação transitória de Excel legado

Para testar com um Excel já gerado:

```powershell
.\scripts\39_import_vrops_excel_granular_to_duckdb.ps1 `
  -InputExcel ".\data\raw\rmc_outputs\RMC_Recursos_VM_v5_10_4_4_3_20260615_130005.xlsx"
```

Isso importa as abas:

- `VMS_INVENTARIO` ou `VMS_SELECIONADAS`
- `PARTICOES_SELECIONADAS` ou `PARTICOES_INVENTARIO`
- `HIST_CPU`
- `HIST_MEM`
- `HIST_DISK`
- `LOG_CPU`
- `LOG_MEM`
- `LOG_DISK`

## Importante

A importação por Excel é apenas transição. A forma oficial para o produto é a gravação direta usando `save_vrops_collection_from_notebook_globals()` ou `save_vrops_collection_to_duckdb()` dentro da coleta.
