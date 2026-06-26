# HOTFIX 15F.10.34 — Análise Individual de VM sem erros

## Objetivo

Corrigir o relatório da **Análise Individual de VM/Servidor**, separando definitivamente de FUP.

## Correções

- O relatório passa a se identificar como **Análise Individual de VM**.
- A IA recebe prompt explícito: isto não é FUP.
- A IA só analisa, explica e recomenda; não executa ação.
- A resposta da IA para cada recurso passa por guarda-corpo:
  - bloqueia contradição com status calculado;
  - bloqueia texto sobre o produto RMC Copilot como se fosse o servidor;
  - bloqueia recomendação de aumento quando o status é OTIMIZAÇÃO;
  - bloqueia “sem risco” quando o status é CRÍTICO/RISCO.
- O relatório total consolidado também passa por guarda-corpo.
- HTML usa figuras estáticas em PNG/base64 quando possível, em vez de depender de Plotly bruto.
- O relatório mantém Word, PDF e HTML.

## Estrutura correta

- CPU
- Memória
- Disco/Partição
- Relatório consolidado da VM

Cada recurso segue o modelo SOL1809645:

1. Objetivo da análise
2. Resumo Executivo
3. Análise Detalhada dos Gráficos
   - Comportamento Histórico e Previsão
   - Decomposição da Série Temporal
   - Distribuição do Uso / Histograma
   - Uso Médio por Hora
4. Análise Estatística
5. Conclusão e Recomendação Final

## Como aplicar

```powershell
cd D:\Francisco\Capacitymc-copilot

Expand-Archive .mc_copilot_hotfix_15f_10_34_analise_individual_vm_sem_erros.zip -DestinationPath . -Force
powershell -NoProfile -ExecutionPolicy Bypass -File .\scriptsg_validate_analise_individual_vm_sem_erros.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\_run_dashboard_with_rmc_llm.ps1
```

## Push seletivo depois da validação

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts8_git_push_hotfix_15f_10_34.ps1
```
