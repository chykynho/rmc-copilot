# RMC Copilot

Assistente local de Capacity Planning VMware.

## Componentes

- Coleta de dados do vROps / Aria Operations
- Motor estatístico de capacity planning
- Análise de CPU, memória, disco, cluster, host, VM e datastore
- Forecast 30/60/90 dias
- Priorização P0/P1/P2/P3/P4
- Dashboard Streamlit
- Persistência em DuckDB

## Estrutura

```text
app/            Dashboard Streamlit
rmc_copilot/    Motor estatístico e regras de análise
scripts/        Scripts de execução
data/           Dados locais, fora do Git
docs/           Documentação
tests/          Testes

## Rodar no Windows

- cd C:\Projetos\rmc_copilot
.\.rmc_win\Scripts\activate
- python -m streamlit run app\dashboard_streamlit.py

ou

- .\scripts\rodar_dashboard.bat

