# Técnico - 16A.7 Dashboard Orphans

Os dados de órfãos/reclaim são gerados pela etapa 16A.5 em:

- `aria_reclamation_report_exports`
- `aria_reclamation_report_rows`
- `orphan_disk_candidates`

Esta etapa adiciona uma página Streamlit independente em `app/pages`, evitando alterar a tela principal e reduzindo risco de regressão.

A página lê o último `run_id` em `orphan_disk_candidates` e exibe:

- cards de quantidade e tamanho potencial;
- resumo por cluster;
- tabela de candidatos;
- linhas brutas do Reclamation Report;
- auditoria de CSV/PDF baixados.

Regra fixa: somente leitura.
