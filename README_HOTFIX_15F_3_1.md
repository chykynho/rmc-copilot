# Hotfix 15-F.3.1 — Streamlit + DuckDB catalog conflict

## Correções

1. Remove criação/alteração de schema no `DuckDBTimeseriesProvider.__init__`.
2. Remove criação/alteração de schema nas funções de auditoria do relatório.
3. Mantém a inicialização do schema nos scripts próprios: `36_init_resource_timeseries_duckdb.ps1` e `39_import_vrops_excel_granular_to_duckdb.ps1`.
4. Atualiza `st.image(..., use_container_width=True)` para `st.image(..., width="stretch")`.

## Motivo

O Streamlit pode instanciar a página/provider mais de uma vez durante navegação/rerun. Como o provider chamava `CREATE OR REPLACE VIEW` via `create_resource_timeseries_schema`, o DuckDB podia gerar:

`TransactionContext Error: Catalog write-write conflict on alter with View vw_latest_resource_collection_run`

O provider agora é apenas leitura; escrita de schema fica restrita à inicialização/importação.

## Aplicar

Extraia o ZIP na raiz do projeto:

`C:\Projetos\rmc_copilot`

Teste:

```powershell
cd C:\Projetos\rmc_copilot
.\.rmcllm\Scripts\Activate.ps1
streamlit run .\app\dashboard_streamlit.py
```

## Commit

```powershell
git add .\rmc_copilot\resource_analysis\duckdb_provider.py
git add .\app\pages\01_Analise_Individual_de_Recursos.py
git add .\README_HOTFIX_15F_3_1.md

git commit -m "Hotfix 15F.3.1 - evita conflito de schema DuckDB no Streamlit"
git push origin main
```
