<div style="border-top: 12px solid #0033A0; border-bottom: 5px solid #78BE20; padding: 18px 22px; background: #F2F4F7; font-family: Arial, Helvetica, sans-serif;">
  <div style="font-size: 26px; font-weight: 700; color: #0033A0;">BV</div>
  <div style="font-size: 20px; font-weight: 700; color: #1F2937; margin-top: 4px;">Relatório de Análise Individual de Recursos — SRV-DASHPRD01</div>
  <div style="font-size: 12px; color: #1F2937; margin-top: 10px;">Classificação: <strong>PÃŠBLICO</strong></div>
</div>

# Relatório de Análise Individual de Recursos — SRV-DASHPRD01

| Campo | Valor |
|:--|:--|
| Solicitação | SOL1809645 |
| Servidor / VM | SRV-DASHPRD01 |
| Recurso | Disco (Partição C:) |
| Período histórico | 90 dias |
| Período analisado | 15/03/2026 a 13/06/2026 |
| Solicitante | Eduardo Barbosa |
| Analista | Francisco Alves |
| Origem dos dados | DuckDB oficial / run_id=RMC_Recursos_VM_v5_10_4_4_3_20260615_130005 |
| Data de geração | 19/06/2026 17:12 |

---

## 1. Resumo Executivo

A análise do recurso Disco (Partição C:) da VM SRV-DASHPRD01 indica comportamento operacional estável. A capacidade atual é de 179.40 GB, o uso médio foi de 81.11 GB (45.21%) e o P95 ficou em 89.25 GB (49.75%), dentro da margem de segurança de 80%.

## 2. Análise Técnica dos Gráficos

O gráfico de comparação e previsão deve ser usado para verificar se a linha de utilização se aproxima da capacidade total ou da margem de segurança. O gráfico de média móvel ajuda a diferenciar picos isolados de tendência real. A decomposição da série temporal evidencia tendência, sazonalidade e resíduos. O histograma mostra onde o recurso permanece concentrado na maior parte do tempo, e o gráfico de uso por hora identifica janelas recorrentes de maior consumo.

### A. Comparação e Previsão

![A. Comparação e Previsão](graficos/01_DISK_C_comparacao_previsao.png)
### B. Histórico com Média Móvel

![B. Histórico com Média Móvel](graficos/02_DISK_C_media_movel.png)
### C. Decomposição da Série Temporal

![C. Decomposição da Série Temporal](graficos/03_DISK_C_decomposicao.png)
### D. Distribuição de Uso

![D. Distribuição de Uso](graficos/04_DISK_C_histograma.png)
### E. Uso Médio por Hora

![E. Uso Médio por Hora](graficos/05_DISK_C_uso_por_hora.png)

## 3. Análise Estatística

No período de 15/03/2026 a 13/06/2026, foram analisadas 91 amostras. A capacidade total considerada foi 179.40 GB e a margem de segurança de 80% equivale a 143.52 GB. Mínimo: 71.69 GB; média: 81.11 GB; mediana: 80.59 GB; P95: 89.25 GB; máximo: 89.36 GB. Previsões: 30 dias 83.32 GB (46.45%), 60 dias 84.33 GB (47.01%), 90 dias 85.33 GB (47.57%).

| Métrica | Valor |
|:--|--:|
| Capacidade total | 179.40 GB |
| Margem de segurança (80%) | 143.52 GB |
| Uso mínimo | 71.69 GB |
| Uso médio | 81.11 GB (45.21%) |
| Mediana | 80.59 GB (44.92%) |
| Q1 | 77.39 GB |
| Q3 | 85.14 GB |
| P95 | 89.25 GB (49.75%) |
| Uso máximo | 89.36 GB (49.81%) |
| Forecast 30 dias | 83.32 GB (46.45%) |
| Forecast 60 dias | 84.33 GB (47.01%) |
| Forecast 90 dias | 85.33 GB (47.57%) |
| Diagnóstico | OK |
| Ação recomendada | MANTER MONITORAMENTO |
| Capacidade sugerida | Não aplicável |
| Variação sugerida | Não aplicável |

## 4. Conclusão e Recomendação

Não há indicação de aumento imediato do recurso Disco (Partição C:). A recomendação é manter a configuração atual e continuar o monitoramento periódico.

## 5. Observações

- A LLM/Data+RAG não calcula os números: ela apenas transforma os indicadores calculados pelo motor estatístico em texto executivo.
- A margem de segurança usada foi de 80% da capacidade total.
- Forecast linear simples de 90 dias; usar como apoio, não como única fonte de decisão.

---

PÃŠBLICO
