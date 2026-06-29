# Etapa 16A.4 - Deep probe Aria/vROps para Orphaned Disks

Este pacote não executa ação operacional.

Objetivo: localizar, pela API do Aria/vROps, onde fica a origem de dados usada pela exportação manual `orphaned-disks`.

## Aplicar

```powershell
cd D:\Francisco\Capacity\rmc-copilot
Expand-Archive .\rmc_copilot_etapa_16a_4_probe_aria_orphans_deep.zip -DestinationPath . -Force
```

## Rodar

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\171_probe_aria_reclaim_orphans_deep.ps1 -User "altran.jsantos@bv.com.br" -AuthSource "bvnet.bv"
```

## Saídas

```text
data\debug\aria_reclaim_orphans_deep_YYYYMMDD_HHMMSS_summary.txt
data\debug\aria_reclaim_orphans_deep_YYYYMMDD_HHMMSS.json
```

Envie o `_summary.txt`. Se o summary apontar um reportDefinition/view/endpoint candidato, a próxima etapa fecha a coleta automática de `orphan_disk_candidates` no DuckDB.
