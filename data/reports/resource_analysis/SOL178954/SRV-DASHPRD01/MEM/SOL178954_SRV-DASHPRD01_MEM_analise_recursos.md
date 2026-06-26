<div style="border-top: 12px solid #0033A0; border-bottom: 5px solid #78BE20; padding: 18px 22px; background: #F2F4F7; font-family: Arial, Helvetica, sans-serif;">
  <div style="font-size: 26px; font-weight: 700; color: #0033A0;">BV</div>
  <div style="font-size: 20px; font-weight: 700; color: #1F2937; margin-top: 4px;">Relatório de Análise Individual de Recursos — SRV-DASHPRD01</div>
  <div style="font-size: 12px; color: #1F2937; margin-top: 10px;">Classificação: <strong>PÚBLICO</strong></div>
</div>

# Relatório de Análise Individual de Recursos — SRV-DASHPRD01

| Campo | Valor |
|:--|:--|
| Solicitação | SOL178954 |
| Servidor / VM | SRV-DASHPRD01 |
| Recurso | Memória (RAM) |
| Período histórico | 90 dias |
| Período analisado | 20/03/2026 a 17/06/2026 |
| Analista | Francisco Alves |
| Origem dos dados | streamlit/local_simulado |
| Data de geração | 18/06/2026 23:13 |

---

## 1. Resumo Executivo

A análise do recurso Memória (RAM) da VM SRV-DASHPRD01 indica cenário crítico de capacidade. O uso médio foi de 44.99 GB (93.74%), o P95 foi de 47.88 GB (99.74%) e a previsão de 90 dias aponta 53.31 GB (111.07%). O comportamento viola ou se aproxima fortemente da margem de segurança de 80%.

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

No período de 20/03/2026 a 17/06/2026, foram analisadas 360 amostras. A capacidade total considerada foi 48.00 GB e a margem de segurança de 80% equivale a 38.40 GB. Mínimo: 26.41 GB; média: 44.99 GB; mediana: 45.09 GB; P95: 47.88 GB; máximo: 48.96 GB. Previsões: 30 dias 49.59 GB (103.32%), 60 dias 51.45 GB (107.19%), 90 dias 53.31 GB (111.07%).

| Métrica | Valor |
|:--|--:|
| Capacidade total | 48.00 GB |
| Margem de segurança (80%) | 38.40 GB |
| Uso mínimo | 26.41 GB |
| Uso médio | 44.99 GB (93.74%) |
| Mediana | 45.09 GB (93.93%) |
| Q1 | 43.77 GB |
| Q3 | 46.62 GB |
| P95 | 47.88 GB (99.74%) |
| Uso máximo | 48.96 GB (102.00%) |
| Forecast 30 dias | 49.59 GB (103.32%) |
| Forecast 60 dias | 51.45 GB (107.19%) |
| Forecast 90 dias | 53.31 GB (111.07%) |
| Diagnóstico | CRÍTICO |
| Ação recomendada | AUMENTAR RECURSO |
| Capacidade sugerida | 80.00 GB |
| Variação sugerida | 32.00 GB |

## 4. Conclusão e Recomendação

Recomenda-se avaliar aumento do recurso Memória (RAM). Capacidade atual: 48.00 GB. Capacidade sugerida: 80.00 GB (variação estimada de 32.00 GB). A recomendação deve ser validada com o responsável da aplicação antes da alteração em produção.

## 5. Observações

- A LLM/Data+RAG não calcula os números: ela apenas transforma os indicadores calculados pelo motor estatístico em texto executivo.
- A margem de segurança usada foi de 80% da capacidade total.
- Forecast linear simples de 90 dias; usar como apoio, não como única fonte de decisão.

---

PÚBLICO
