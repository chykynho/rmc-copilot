# RMC Copilot — Etapa 15-F.1

## Armazenamento granular de recursos no DuckDB oficial

Esta etapa adiciona ao banco oficial `data/database/rmc_copilot.duckdb` uma camada de tabelas para histórico granular de recursos.

O objetivo é deixar de usar Excel como base operacional do produto. Excel, CSV e Parquet continuam úteis como exportação, mas a fonte oficial passa a ser o DuckDB.

## Tabelas adicionadas

- `resource_collection_runs`: controle das execuções de coleta granular.
- `vm_inventory_snapshots`: inventário de VMs por execução.
- `vm_disk_partitions`: partições/filesystems detectados por VM.
- `vm_resource_timeseries`: tabela principal de séries temporais de CPU, memória e disco.
- `resource_collection_logs`: logs estruturados da coleta.
- `resource_report_requests`: solicitações de relatórios individuais.
- `resource_report_artifacts`: artefatos gerados por solicitação.

## Tabela principal

A tabela `vm_resource_timeseries` suporta CPU, memória e disco em formato único:

```text
timestamp
cluster
host
vm
vm_resource_id
resource_type       CPU / MEM / DISK
subresource         AGREGADO, C:, D:, /, /var etc.
metric_name         used_pct, used_gb, free_gb, capacity_gb, usage_mhz
value
unit
used_pct
used_gb
free_gb
capacity_gb
stat_key
source
```

## Compatibilidade com o banco atual

O banco atual já possui a tabela legada `historico_vm_metricas`, com:

```text
execution_id
cluster
vm
vm_resource_id
date
recurso
used_pct
```

Esta etapa inclui um migrador para carregar essa tabela legada em `vm_resource_timeseries`. Como a origem legada não contém partição nem capacidade, o disco migrado fica como `subresource = AGREGADO`.

A coleta vROps da próxima etapa deverá popular `vm_resource_timeseries` diretamente com partições e capacidades reais.

## Comandos

Inicializar schema:

```powershell
.\scripts\36_init_resource_timeseries_duckdb.ps1
```

Migrar histórico legado:

```powershell
.\scripts\37_migrate_legacy_historico_metricas.ps1
```

Inspecionar tabelas:

```powershell
.\scripts\38_inspect_resource_timeseries_duckdb.ps1
```

## Próxima etapa

A Etapa 15-F.2 deve adaptar a coleta vROps para gravar diretamente no DuckDB, sem depender do Excel como intermediário.
