# Documento técnico - Etapa 16A.2

## Objetivo

Substituir a dependência de CSV manual por coleta direta via vCenter/pyVmomi para:

- VMs desligadas.
- Snapshots, com destaque para snapshots com mais de 20 dias.
- Discos candidatos a órfãos.

## Fontes de inspiração

- `otmzV3.py`: conexão vCenter, VMs desligadas, eventos de desligamento e snapshots.
- `busca_ORPHAN_III.py`: varredura de datastores por VMDK e comparação com VMDKs em uso.

## Tabelas usadas

- `optimization_collection_runs`
- `vm_power_state_snapshots`
- `vm_snapshot_inventory`
- `orphan_disk_candidates`
- `optimization_recommendations`

## Segurança operacional

Nenhuma função executa mudança no ambiente. O coletor apenas lê informações e grava no DuckDB.

Campos de recomendação usam `action_allowed = FALSE`.

## Limitação conhecida

O tamanho individual de snapshot nem sempre é exposto diretamente pelo pyVmomi. O coletor tenta estimar pelo `layoutEx` da VM, mas a recomendação principal usa idade do snapshot e inventário.
