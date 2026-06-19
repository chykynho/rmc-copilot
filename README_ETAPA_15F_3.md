# RMC Copilot — Etapa 15-F.3

## Objetivo

Conectar o Gerador de Análise Individual de Recursos ao DuckDB oficial do RMC Copilot.

A partir desta etapa, a página Streamlit `01_Analise_Individual_de_Recursos.py` passa a oferecer duas fontes:

- `duckdb_oficial`: lê dados reais de `data/database/rmc_copilot.duckdb`;
- `local_simulado`: mantém o mock para testes rápidos.

## O que muda

- Lista execuções reais de coleta em `resource_collection_runs`.
- Lista VMs reais de `vm_inventory_snapshots` / `vm_resource_timeseries`.
- Lista partições reais por VM usando `vm_disk_partitions`.
- Gera relatório individual com CPU, MEM e DISK a partir de `vm_resource_timeseries`.
- Registra auditoria em `resource_report_requests` e `resource_report_artifacts`.
- Mantém fallback local simulado.

## Observação técnica

CPU e MEM ainda são lidos como percentual de uso (`used_pct`), porque o contrato atual já tem o histórico percentual do vROps. DISK usa `used_gb`, `free_gb` e `capacity_gb` quando disponíveis na carga granular.

## Como testar no dashboard

```powershell
cd C:\Projetos\rmc_copilot
.\.rmcllm\Scripts\Activate.ps1
streamlit run .\app\dashboard_streamlit.py
```

Na página **Análise Individual de Recursos**, selecione:

1. Fonte de dados: `duckdb_oficial`.
2. Execução de coleta mais recente.
3. VM real.
4. Recursos CPU, MEM e DISK.
5. Partição real, por exemplo `C:` ou `/`.

## Como testar via CLI

```powershell
.\scripts\41_generate_resource_analysis_duckdb.ps1 `
  -Solicitacao "SOL1809645" `
  -VM "SRV-DASHPRD01" `
  -Resources "CPU,MEM,DISK" `
  -Partitions "C:" `
  -Periodo 90 `
  -Solicitante "Eduardo Barbosa" `
  -Analista "Francisco Alves"
```

Se houver VMs duplicadas, use também `-VmResourceId`.

## Commit sugerido

```powershell
git add .\rmc_copilot\resource_analysis\duckdb_provider.py
git add .\rmc_copilot\resource_analysis\providers.py
git add .\rmc_copilot\resource_analysis\models.py
git add .\rmc_copilot\resource_analysis\stats_engine.py
git add .\rmc_copilot\resource_analysis\charts.py
git add .\rmc_copilot\resource_analysis\generate_resource_analysis_consolidated_v1.py
git add .\app\pages\01_Analise_Individual_de_Recursos.py
git add .\scripts\41_generate_resource_analysis_duckdb.ps1
git add .\README_ETAPA_15F_3.md

git commit -m "Etapa 15F.3 - conecta analise individual ao DuckDB"
git push origin main
```

Não adicionar `data/` ao GitHub.
