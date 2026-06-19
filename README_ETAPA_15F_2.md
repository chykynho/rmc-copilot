# Etapa 15-F.2 — Coleta vROps gravando no DuckDB oficial

Esta etapa adiciona a camada que grava a coleta vROps diretamente no banco oficial:

```text
data/database/rmc_copilot.duckdb
```

## Arquivos adicionados

```text
rmc_copilot/resource_timeseries/vrops_duckdb_ingest.py
scripts/39_import_vrops_excel_granular_to_duckdb.ps1
scripts/40_print_vrops_duckdb_notebook_cell.ps1
docs/tecnicos/rmc_vrops_duckdb_ingest_etapa15f2.md
README_ETAPA_15F_2.md
```

## Aplicar

Extraia este pacote na raiz:

```text
C:\Projetos\rmc_copilot
```

## Teste rápido com Excel já gerado

```powershell
cd C:\Projetos\rmc_copilot
.\.rmcllm\Scripts\Activate.ps1

.\scripts\39_import_vrops_excel_granular_to_duckdb.ps1 `
  -InputExcel ".\data\raw\rmc_outputs\RMC_Recursos_VM_v5_10_4_4_3_20260615_130005.xlsx"
```

Se o Excel estiver em outro lugar, ajuste o caminho.

## Integração direta no notebook/script vROps

Para imprimir a célula de integração:

```powershell
.\scripts\40_print_vrops_duckdb_notebook_cell.ps1
```

Cole a célula exibida no final do notebook/script de coleta, depois que `df_cpu_hist`, `df_mem_hist`, `df_disk_hist` e `report_file` já existirem.

## Validação

Depois da carga, rode:

```powershell
.\scripts\38_inspect_resource_timeseries_duckdb.ps1
```

E confira:

```text
vm_inventory_snapshots > 0
vm_disk_partitions     > 0
vm_resource_timeseries com source = vrops_direct ou vrops_excel_import
```

## Commit seguro

```powershell
git add .\rmc_copilot\resource_timeseries\vrops_duckdb_ingest.py
git add .\scripts\39_import_vrops_excel_granular_to_duckdb.ps1
git add .\scripts\40_print_vrops_duckdb_notebook_cell.ps1
git add .\docs\tecnicos\rmc_vrops_duckdb_ingest_etapa15f2.md
git add .\README_ETAPA_15F_2.md

git commit -m "Etapa 15F.2 - grava coleta vROps no DuckDB"
git push origin main
```

Não adicione `data/` ao GitHub.
