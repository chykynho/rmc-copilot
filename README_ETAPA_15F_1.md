# Etapa 15-F.1 — DuckDB Resource Timeseries

Esta etapa adiciona uma camada profissional de armazenamento granular de recursos no DuckDB oficial do RMC Copilot:

```text
data/database/rmc_copilot.duckdb
```

## Arquivos adicionados

```text
rmc_copilot/resource_timeseries/__init__.py
rmc_copilot/resource_timeseries/duckdb_repository.py
rmc_copilot/resource_timeseries/init_duckdb_schema.py
rmc_copilot/resource_timeseries/migrate_legacy_history.py
rmc_copilot/resource_timeseries/inspect_duckdb_schema.py
scripts/36_init_resource_timeseries_duckdb.ps1
scripts/37_migrate_legacy_historico_metricas.ps1
scripts/38_inspect_resource_timeseries_duckdb.ps1
docs/tecnicos/rmc_duckdb_resource_timeseries_etapa15f.md
```

## Teste rápido

```powershell
cd C:\Projetos\rmc_copilot
.\.rmcllm\Scripts\Activate.ps1

.\scripts\36_init_resource_timeseries_duckdb.ps1
.\scripts\37_migrate_legacy_historico_metricas.ps1
.\scripts\38_inspect_resource_timeseries_duckdb.ps1
```

## Git

```powershell
git add .\rmc_copilot\resource_timeseries
git add .\scripts\36_init_resource_timeseries_duckdb.ps1
git add .\scripts\37_migrate_legacy_historico_metricas.ps1
git add .\scripts\38_inspect_resource_timeseries_duckdb.ps1
git add .\docs\tecnicos\rmc_duckdb_resource_timeseries_etapa15f.md
git add .\README_ETAPA_15F_1.md

git commit -m "Etapa 15F.1 - adiciona resource timeseries no DuckDB"
git push origin main
```

## Observação

O arquivo `.duckdb` não deve ser enviado ao GitHub. Ele fica em `data/database/` e deve continuar protegido por `.gitignore`.
