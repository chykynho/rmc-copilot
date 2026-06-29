# RMC Copilot - Etapa 16A - Otimização

## Objetivo

Adicionar uma frente de otimização separada de FUP e separada da Análise Individual de VM.

## Itens cobertos

### 1. VMs desligadas

A coleta registra o estado de energia da VM quando o vROps disponibiliza essa propriedade. O dashboard lista VMs desligadas como oportunidade de validação e possível liberação futura de recursos.

### 2. Snapshots antigos

A coleta tenta detectar propriedades de snapshot no vROps. A classificação inicial é:

- `ATENCAO`: snapshot com mais de 20 dias
- `RISCO`: snapshot com 30 dias ou mais
- `CRITICO`: snapshot com 60 dias ou mais

### 3. Discos candidatos a órfãos

Discos órfãos exigem validação cuidadosa. A Etapa 16A cria tabela e dashboard para candidatos, mas não confirma exclusão. A importação por CSV é opcional.

## Tabelas criadas

- `optimization_collection_runs`
- `vm_power_state_snapshots`
- `vm_snapshot_inventory`
- `orphan_disk_candidates`
- `optimization_recommendations`

## Views criadas

- `v_optimization_latest_run`
- `v_powered_off_vms_latest`
- `v_snapshots_antigos_latest`
- `v_orphan_disk_candidates_latest`

## Regra de segurança

A IA no RMC Copilot é restrita a relatórios e recomendações. Não executa ações operacionais.
