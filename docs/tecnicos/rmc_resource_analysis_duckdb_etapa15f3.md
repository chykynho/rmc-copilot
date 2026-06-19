# RMC Copilot — Etapa 15-F.3

## Tema

Conexão do Gerador de Análise Individual de Recursos ao DuckDB oficial.

## Fonte oficial

Banco:

```text
data/database/rmc_copilot.duckdb
```

Tabelas usadas:

```text
resource_collection_runs
vm_inventory_snapshots
vm_disk_partitions
vm_resource_timeseries
resource_report_requests
resource_report_artifacts
```

## Provider

Novo provider:

```python
rmc_copilot.resource_analysis.duckdb_provider.DuckDBTimeseriesProvider
```

Responsabilidades:

- localizar a última execução granular válida;
- listar VMs reais;
- listar partições reais por VM;
- entregar séries no contrato `Date` / `Value` usado pelo motor estatístico;
- priorizar `vrops_direct` e `vrops_excel_import`;
- usar `legacy_historico_vm_metricas` apenas como fallback.

## Regras de unidade

CPU e MEM são carregados como percentual de uso porque a coleta atual armazena `used_pct` para esses recursos no contrato granular.

DISK usa GB quando existem:

```text
used_gb
free_gb
capacity_gb
```

Com isso, os relatórios de disco já passam a refletir capacidade real por partição.

## Auditoria

A tela e a CLI podem registrar:

```text
resource_report_requests
resource_report_artifacts
```

Isso permite rastrear qual solicitação gerou quais arquivos, com qual VM, quais recursos e qual run de origem.

## Próxima evolução

A próxima etapa deve eliminar o uso de Excel como transição e fazer a coleta vROps chamar diretamente:

```python
save_vrops_collection_from_notebook_globals(...)
```

ou uma função equivalente no script de coleta definitivo.
