# Etapa 16A.5 - Reclamation Reports via Aria/vROps API

Objetivo: parar de depender de CSV manual para dados de reclaim/orphan.

O probe 16A.4 encontrou dois report definitions importantes:

- `77935eb4-eeec-45bf-b13c-1d7b00bc21c7` — Reclamation Report - Datacenter
- `92bdc75a-423e-40cd-91e8-c97c17902c42` — Reclamation Report - vSphere Clusters

Esta etapa executa esses reports pela API do Aria/vROps, baixa CSV/PDF e grava metadados no DuckDB.

## Segurança

Somente leitura/geração de relatório. Não remove snapshot, não deleta disco, não desliga VM.

## Aplicar

```powershell
cd D:\Francisco\Capacity\rmc-copilot
Expand-Archive .\rmc_copilot_etapa_16a_5_reclamation_reports_api.zip -DestinationPath . -Force
```

## Teste mínimo

Executa somente 1 recurso de cluster BV_PRD:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\172_run_aria_reclamation_reports.ps1 -User "altran.jsantos@bv.com.br" -AuthSource "bvnet.bv" -Report clusters -ResourceNameFilter "BV_PRD" -MaxResources 1
```

## Coleta para todos os clusters BV_PRD

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\172_run_aria_reclamation_reports.ps1 -User "altran.jsantos@bv.com.br" -AuthSource "bvnet.bv" -Report clusters -ResourceNameFilter "BV_PRD"
```

## Datacenter

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\172_run_aria_reclamation_reports.ps1 -User "altran.jsantos@bv.com.br" -AuthSource "bvnet.bv" -Report datacenter
```

## Validar

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\173_validate_aria_reclamation_reports.ps1
```

## Saída

Os relatórios baixados ficam em:

```text
data\reports\otimizacao\ARIARECL_YYYYMMDD_HHMMSS_xxxxxxxx\
```

Tabelas novas:

- `aria_reclamation_report_exports`
- `aria_reclamation_report_rows`

Se o CSV contiver termos compatíveis com orphan/vmdk, o script cria candidatos em:

- `orphan_disk_candidates`

Ainda assim, tudo continua como candidato/validação, nunca ação automática.
