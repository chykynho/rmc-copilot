# RMC Copilot - Etapa 12 - Schema de Dados Reais

## Objetivo

A camada Data+RAG precisa trabalhar com dados reais vindos da coleta do RMC Copilot.

Como as colunas podem variar entre versões, a Etapa 12 define um schema canônico.

## Schema canônico

| Coluna canônica | Significado |
|---|---|
| cluster | Nome do cluster VMware |
| host | Nome do host ESXi |
| vm | Nome da VM |
| datastore | Nome do datastore |
| cpu_p95 | Percentil 95 de CPU |
| mem_p95 | Percentil 95 de memória |
| disk_used_pct | Percentual de disco usado |
| datastore_used_pct | Percentual de datastore usado |
| forecast_30d | Recurso previsto em risco em 30 dias |
| forecast_60d | Recurso previsto em risco em 60 dias |
| forecast_90d | Recurso previsto em risco em 90 dias |
| prioridade | Prioridade final P0/P1/P2/P3/P4 |
| acao | Ação operacional recomendada |

## Regras importantes

1. Perguntas sobre forecast de disco devem filtrar forecast DISK/DISCO.
2. Perguntas sobre forecast de memória devem filtrar forecast MEM/MEMORIA/MEMÓRIA/RAM.
3. Perguntas sobre forecast de CPU devem filtrar forecast CPU/VCPU.
4. Uso atual alto de disco não deve ser confundido com forecast de disco.
5. Prioridade P0/P1 deve prevalecer sobre P2/P3/P4 na ordenação.
6. Rightsizing deve ser conservador e validado por histórico, picos, batch, backup e fechamento mensal.

## Colunas mínimas recomendadas

Para funcionamento básico:

- vm
- cluster
- prioridade

Para análise operacional boa:

- vm
- cluster
- host
- cpu_p95
- mem_p95
- disk_used_pct
- datastore
- datastore_used_pct
- forecast_30d
- forecast_60d
- forecast_90d
- prioridade
- acao
