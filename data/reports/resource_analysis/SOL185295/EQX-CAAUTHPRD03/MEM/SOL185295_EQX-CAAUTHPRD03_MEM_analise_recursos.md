<div style="border-top: 12px solid #0033A0; border-bottom: 5px solid #78BE20; padding: 18px 22px; background: #F2F4F7; font-family: Arial, Helvetica, sans-serif;">
  <div style="font-size: 26px; font-weight: 700; color: #0033A0;">BV</div>
  <div style="font-size: 20px; font-weight: 700; color: #1F2937; margin-top: 4px;">Relatório de Análise Individual de Recursos — EQX-CAAUTHPRD03</div>
  <div style="font-size: 12px; color: #1F2937; margin-top: 10px;">Classificação: <strong>PÚBLICO</strong></div>
</div>

# Relatório de Análise Individual de Recursos — EQX-CAAUTHPRD03

| Campo | Valor |
|:--|:--|
| Solicitação | SOL185295 |
| Servidor / VM | EQX-CAAUTHPRD03 |
| Recurso | Memória (RAM) |
| Período histórico | 90 dias |
| Período analisado | 15/03/2026 a 13/06/2026 |
| Analista | Francisco Alves |
| Origem dos dados | DuckDB oficial / run_id=RMC_Recursos_VM_v5_10_4_4_3_20260615_130005 |
| Data de geração | 19/06/2026 17:09 |

---

## 1. Resumo Executivo

A análise do recurso Memória (RAM) da VM EQX-CAAUTHPRD03 indica comportamento operacional estável. A capacidade atual é de 100.00 %, o uso médio foi de 30.00 % (30.00%) e o P95 ficou em 32.13 % (32.13%), dentro da margem de segurança de 80%.

## 2. Análise Técnica dos Gráficos

O gráfico de comparação e previsão deve ser usado para verificar se a linha de utilização se aproxima da capacidade total ou da margem de segurança. O gráfico de média móvel ajuda a diferenciar picos isolados de tendência real. A decomposição da série temporal evidencia tendência, sazonalidade e resíduos. O histograma mostra onde o recurso permanece concentrado na maior parte do tempo, e o gráfico de uso por hora identifica janelas recorrentes de maior consumo.

### A. Comparação e Previsão

![A. Comparação e Previsão](graficos/01_MEM_comparacao_previsao.png)
### B. Histórico com Média Móvel

![B. Histórico com Média Móvel](graficos/02_MEM_media_movel.png)
### C. Decomposição da Série Temporal

![C. Decomposição da Série Temporal](graficos/03_MEM_decomposicao.png)
### D. Distribuição de Uso

![D. Distribuição de Uso](graficos/04_MEM_histograma.png)
### E. Uso Médio por Hora

![E. Uso Médio por Hora](graficos/05_MEM_uso_por_hora.png)

## 3. Análise Estatística

No período de 15/03/2026 a 13/06/2026, foram analisadas 91 amostras. A capacidade total considerada foi 100.00 % e a margem de segurança de 80% equivale a 80.00 %. Mínimo: 27.19 %; média: 30.00 %; mediana: 30.57 %; P95: 32.13 %; máximo: 32.37 %. Previsões: 30 dias 26.56 % (26.56%), 60 dias 25.15 % (25.15%), 90 dias 23.74 % (23.74%).

| Métrica | Valor |
|:--|--:|
| Capacidade total | 100.00 % |
| Margem de segurança (80%) | 80.00 % |
| Uso mínimo | 27.19 % |
| Uso médio | 30.00 % (30.00%) |
| Mediana | 30.57 % (30.57%) |
| Q1 | 28.62 % |
| Q3 | 31.13 % |
| P95 | 32.13 % (32.13%) |
| Uso máximo | 32.37 % (32.37%) |
| Forecast 30 dias | 26.56 % (26.56%) |
| Forecast 60 dias | 25.15 % (25.15%) |
| Forecast 90 dias | 23.74 % (23.74%) |
| Diagnóstico | OK |
| Ação recomendada | MANTER MONITORAMENTO |
| Capacidade sugerida | Não aplicável |
| Variação sugerida | Não aplicável |

## 4. Conclusão e Recomendação

Não há indicação de aumento imediato do recurso Memória (RAM). A recomendação é manter a configuração atual e continuar o monitoramento periódico.

## 5. Observações

- A LLM/Data+RAG não calcula os números: ela apenas transforma os indicadores calculados pelo motor estatístico em texto executivo.
- A margem de segurança usada foi de 80% da capacidade total.
- Forecast linear simples de 90 dias; usar como apoio, não como única fonte de decisão.

---

PÚBLICO
