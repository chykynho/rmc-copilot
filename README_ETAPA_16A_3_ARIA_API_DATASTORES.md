# Etapa 16A.3 - Aria/vROps API para Datastores e relatórios de otimização

Correção de direção: o vCenter/pyVmomi coleta VMs desligadas e snapshots. Para datastores, a coleta deve usar a API do Aria/vROps quando ela já expõe os objetos e relatórios.

## Regra

Somente leitura. Nenhuma ação operacional é executada.

## Aplicar

```powershell
cd D:\Francisco\Capacity\rmc-copilot
Expand-Archive .\rmc_copilot_etapa_16a_3_aria_api_datastores.zip -DestinationPath . -Force
```

## Coletar datastores via vROps API

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\169_collect_datastores_vrops_api.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\170_validate_datastores_vrops_api.ps1
```

## Descobrir endpoint/view/report usado pelo Aria para órfãos

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\168_probe_aria_optimization_api.ps1
```

O script grava:

```text
data\debug\aria_optimization_api_probe_YYYYMMDD_HHMMSS.json
data\debug\aria_optimization_api_probe_YYYYMMDD_HHMMSS_summary.txt
```

Envie o `_summary.txt` para fechar a exportação automática do relatório de `orphaned-disks` pelo Aria/vROps, sem CSV manual.

## Observação técnica

A API do Aria/vROps consegue listar recursos Datastore. Porém disco órfão em nível de arquivo VMDK depende de uma destas fontes:

1. Report/View do próprio Aria que já calcula `orphaned-disks`.
2. Browse do datastore no vCenter com permissão `Datastore > Browse datastore`.

Se o Aria já gera o CSV manual, o caminho correto é automatizar a exportação dessa view/report pela API.
