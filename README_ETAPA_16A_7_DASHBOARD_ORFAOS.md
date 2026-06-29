# Etapa 16A.7 - Dashboard para Discos Órfãos / Reclaim

Problema corrigido:

Os dados de `orphan_disk_candidates` já estavam no DuckDB, mas a tela principal de Otimização não lia esses dados. Esta etapa adiciona uma página Streamlit dedicada:

```text
app/pages/16A_Otimizacao_Orfaos.py
```

## Aplicar

```powershell
cd D:\Francisco\Capacity\rmc-copilot
Expand-Archive .\rmc_copilot_etapa_16a_7_dashboard_orfaos.zip -DestinationPath . -Force
```

## Validar dados

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\175_validate_dashboard_orphans_16a7.ps1
```

## Abrir dashboard

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\134_run_dashboard_with_rmc_llm.ps1
```

No menu lateral do Streamlit, abra:

```text
16A Otimizacao Orfaos
```

ou

```text
Otimização - Discos Órfãos
```

## Regra operacional

A página mostra candidatos de reclaim/órfãos. Não executa ação operacional.
A IA apenas recomenda.
