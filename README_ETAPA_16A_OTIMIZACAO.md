# Etapa 16A - Otimização de Recursos

Escopo iniciado:

- VMs desligadas / powered off VMs
- Snapshots com mais de 20 dias
- Estrutura para discos candidatos a órfãos
- Nova página Streamlit: `app/pages/16_Otimizacao.py`
- Novas tabelas DuckDB de otimização

Regra fixa:

> A IA só analisa e recomenda. Não executa ação operacional, não remove snapshot, não deleta disco, não desliga VM e não abre chamado automaticamente.

## Aplicação

```powershell
cd D:\Francisco\Capacity\rmc-copilot
Expand-Archive .\rmc_copilot_etapa_16a_otimizacao.zip -DestinationPath . -Force
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\160_prepare_optimization_schema.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\162_validate_optimization_16a.ps1
```

## Coleta vROps

Teste primeiro com poucas VMs:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\161_collect_optimization_vrops.ps1 -MaxVms 50
```

Depois rode completo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\161_collect_optimization_vrops.ps1
```

Com credencial salva:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\161_collect_optimization_vrops.ps1 -SaveCredential
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\161_collect_optimization_vrops.ps1 -UseSavedCredential
```

## Discos órfãos

A Etapa 16A trata discos como **candidatos a órfãos**, não como verdade absoluta. Se houver CSV de inventário de VMDKs candidatos, use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\161_collect_optimization_vrops.ps1 -OrphanCsv .\data\entrada\orphan_disks.csv
```

Colunas aceitas no CSV, em português ou inglês:

- datastore
- vmdk_path / path
- arquivo / file / filename
- tamanho_gb / size_gb
- data_modificacao / modified
- vm_associada_encontrada / vm / vm_name
- cluster
- confianca / confidence

## Dashboard

Rodar normalmente:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\134_run_dashboard_with_rmc_llm.ps1
```

A página aparecerá como `Otimização` no menu lateral do Streamlit.
