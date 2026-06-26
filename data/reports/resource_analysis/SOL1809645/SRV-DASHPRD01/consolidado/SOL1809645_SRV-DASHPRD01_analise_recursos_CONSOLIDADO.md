<div style="border-top: 12px solid #0033A0; border-bottom: 5px solid #78BE20; padding: 18px 22px; background: #F2F4F7; font-family: Arial, Helvetica, sans-serif;">
  <div style="font-size: 26px; font-weight: 700; color: #0033A0;">BV</div>
  <div style="font-size: 20px; font-weight: 700; color: #1F2937; margin-top: 4px;">Relatório Consolidado de Análise Individual de Recursos — SRV-DASHPRD01</div>
  <div style="font-size: 12px; color: #1F2937; margin-top: 10px;">Classificação: <strong>PÃŠBLICO</strong></div>
</div>

# Relatório Consolidado de Análise Individual de Recursos — SRV-DASHPRD01

| Campo | Valor |
|:--|:--|
| Solicitação | SOL1809645 |
| Servidor / VM | SRV-DASHPRD01 |
| Período histórico | 90 dias |
| Solicitante | Eduardo Barbosa |
| Analista | Francisco Alves |
| Classificação | PÃŠBLICO |
| Data de geração | 19/06/2026 17:12 |

## Índice

1. Resumo Executivo Consolidado
2. Análises por Recurso
   2.1. Processamento (CPU)
   2.2. Memória (RAM)
   2.3. Disco (Partição C:)
3. Observações

---

## 1. Resumo Executivo Consolidado

Foram avaliados 3 recurso(s) da VM **SRV-DASHPRD01** para a solicitação **SOL1809645**. O ponto de maior atenção identificado foi **Processamento (CPU)**, com diagnóstico **SUPERDIMENSIONADO** e ação recomendada **AVALIAR_REDUÇÃO_RECURSO**.

| Recurso | Diagnóstico | Ação | Média | P95 | Forecast 90d | Capacidade sugerida |
|:--|:--|:--|--:|--:|--:|--:|
| Processamento (CPU) | SUPERDIMENSIONADO | AVALIAR REDUÇÃO | 5.94% | 13.16% | 10.62% | 40.00 % |
| Memória (RAM) | OK | MANTER MONITORAMENTO | 30.51% | 60.55% | 47.33% | Não aplicável |
| Disco (Partição C:) | OK | MANTER MONITORAMENTO | 45.21% | 49.75% | 47.57% | Não aplicável |

## 2. Análises por Recurso

### 2.1. Processamento (CPU)

**Diagnóstico:** SUPERDIMENSIONADO  
**Ação recomendada:** AVALIAR REDUÇÃO  
**Uso médio:** 5.94 % (5.94%)  
**P95:** 13.16 % (13.16%)  
**Forecast 90 dias:** 10.62 % (10.62%)  

#### Resumo Executivo

A análise do recurso Processamento (CPU) da VM SRV-DASHPRD01 indica possível superdimensionamento. A capacidade atual é de 100.00 %, enquanto o uso médio foi de apenas 5.94 % (5.94%) e o P95 ficou em 13.16 % (13.16%). Não há evidência estatística de necessidade de aumento do recurso neste momento.

#### Análise Técnica dos Gráficos

O gráfico de comparação e previsão deve ser usado para verificar se a linha de utilização se aproxima da capacidade total ou da margem de segurança. O gráfico de média móvel ajuda a diferenciar picos isolados de tendência real. A decomposição da série temporal evidencia tendência, sazonalidade e resíduos. O histograma mostra onde o recurso permanece concentrado na maior parte do tempo, e o gráfico de uso por hora identifica janelas recorrentes de maior consumo.

##### A. Comparação e Previsão

![A. Comparação e Previsão](../CPU/graficos/01_CPU_comparacao_previsao.png)

##### B. Histórico com Média Móvel

![B. Histórico com Média Móvel](../CPU/graficos/02_CPU_media_movel.png)

##### C. Decomposição da Série Temporal

![C. Decomposição da Série Temporal](../CPU/graficos/03_CPU_decomposicao.png)

##### D. Distribuição de Uso

![D. Distribuição de Uso](../CPU/graficos/04_CPU_histograma.png)

##### E. Uso Médio por Hora

![E. Uso Médio por Hora](../CPU/graficos/05_CPU_uso_por_hora.png)

#### Análise Estatística

No período de 15/03/2026 a 13/06/2026, foram analisadas 91 amostras. A capacidade total considerada foi 100.00 % e a margem de segurança de 80% equivale a 80.00 %. Mínimo: 1.74 %; média: 5.94 %; mediana: 5.08 %; P95: 13.16 %; máximo: 20.87 %. Previsões: 30 dias 8.54 % (8.54%), 60 dias 9.58 % (9.58%), 90 dias 10.62 % (10.62%).

| Métrica | Valor |
|:--|--:|
| Capacidade total | 100.00 % |
| Margem de segurança (80%) | 80.00 % |
| Uso mínimo | 1.74 % |
| Uso médio | 5.94 % (5.94%) |
| Mediana | 5.08 % (5.08%) |
| P95 | 13.16 % (13.16%) |
| Máximo | 20.87 % (20.87%) |
| Forecast 30 dias | 8.54 % (8.54%) |
| Forecast 60 dias | 9.58 % (9.58%) |
| Forecast 90 dias | 10.62 % (10.62%) |
| Capacidade sugerida | 40.00 % |
| Variação sugerida | -60.00 % |

#### Conclusão e Recomendação

Recomenda-se avaliar redução controlada do recurso Processamento (CPU), pois o uso médio e o P95 estão muito abaixo da capacidade alocada. Capacidade atual: 100.00 %. Capacidade técnica sugerida para avaliação: 40.00 %. A redução deve ser feita em janela controlada, com monitoramento após a alteração.

---

### 2.2. Memória (RAM)

**Diagnóstico:** OK  
**Ação recomendada:** MANTER MONITORAMENTO  
**Uso médio:** 30.51 % (30.51%)  
**P95:** 60.55 % (60.55%)  
**Forecast 90 dias:** 47.33 % (47.33%)  

#### Resumo Executivo

A análise do recurso Memória (RAM) da VM SRV-DASHPRD01 indica comportamento operacional estável. A capacidade atual é de 100.00 %, o uso médio foi de 30.51 % (30.51%) e o P95 ficou em 60.55 % (60.55%), dentro da margem de segurança de 80%.

#### Análise Técnica dos Gráficos

O gráfico de comparação e previsão deve ser usado para verificar se a linha de utilização se aproxima da capacidade total ou da margem de segurança. O gráfico de média móvel ajuda a diferenciar picos isolados de tendência real. A decomposição da série temporal evidencia tendência, sazonalidade e resíduos. O histograma mostra onde o recurso permanece concentrado na maior parte do tempo, e o gráfico de uso por hora identifica janelas recorrentes de maior consumo.

##### A. Comparação e Previsão

![A. Comparação e Previsão](../MEM/graficos/01_MEM_comparacao_previsao.png)

##### B. Histórico com Média Móvel

![B. Histórico com Média Móvel](../MEM/graficos/02_MEM_media_movel.png)

##### C. Decomposição da Série Temporal

![C. Decomposição da Série Temporal](../MEM/graficos/03_MEM_decomposicao.png)

##### D. Distribuição de Uso

![D. Distribuição de Uso](../MEM/graficos/04_MEM_histograma.png)

##### E. Uso Médio por Hora

![E. Uso Médio por Hora](../MEM/graficos/05_MEM_uso_por_hora.png)

#### Análise Estatística

No período de 15/03/2026 a 13/06/2026, foram analisadas 91 amostras. A capacidade total considerada foi 100.00 % e a margem de segurança de 80% equivale a 80.00 %. Mínimo: 11.27 %; média: 30.51 %; mediana: 26.60 %; P95: 60.55 %; máximo: 100.00 %. Previsões: 30 dias 39.82 % (39.82%), 60 dias 43.57 % (43.57%), 90 dias 47.33 % (47.33%).

| Métrica | Valor |
|:--|--:|
| Capacidade total | 100.00 % |
| Margem de segurança (80%) | 80.00 % |
| Uso mínimo | 11.27 % |
| Uso médio | 30.51 % (30.51%) |
| Mediana | 26.60 % (26.60%) |
| P95 | 60.55 % (60.55%) |
| Máximo | 100.00 % (100.00%) |
| Forecast 30 dias | 39.82 % (39.82%) |
| Forecast 60 dias | 43.57 % (43.57%) |
| Forecast 90 dias | 47.33 % (47.33%) |
| Capacidade sugerida | Não aplicável |
| Variação sugerida | Não aplicável |

#### Conclusão e Recomendação

Não há indicação de aumento imediato do recurso Memória (RAM). A recomendação é manter a configuração atual e continuar o monitoramento periódico.

---

### 2.3. Disco (Partição C:)

**Diagnóstico:** OK  
**Ação recomendada:** MANTER MONITORAMENTO  
**Uso médio:** 81.11 GB (45.21%)  
**P95:** 89.25 GB (49.75%)  
**Forecast 90 dias:** 85.33 GB (47.57%)  

#### Resumo Executivo

A análise do recurso Disco (Partição C:) da VM SRV-DASHPRD01 indica comportamento operacional estável. A capacidade atual é de 179.40 GB, o uso médio foi de 81.11 GB (45.21%) e o P95 ficou em 89.25 GB (49.75%), dentro da margem de segurança de 80%.

#### Análise Técnica dos Gráficos

O gráfico de comparação e previsão deve ser usado para verificar se a linha de utilização se aproxima da capacidade total ou da margem de segurança. O gráfico de média móvel ajuda a diferenciar picos isolados de tendência real. A decomposição da série temporal evidencia tendência, sazonalidade e resíduos. O histograma mostra onde o recurso permanece concentrado na maior parte do tempo, e o gráfico de uso por hora identifica janelas recorrentes de maior consumo.

##### A. Comparação e Previsão

![A. Comparação e Previsão](../DISK_C/graficos/01_DISK_C_comparacao_previsao.png)

##### B. Histórico com Média Móvel

![B. Histórico com Média Móvel](../DISK_C/graficos/02_DISK_C_media_movel.png)

##### C. Decomposição da Série Temporal

![C. Decomposição da Série Temporal](../DISK_C/graficos/03_DISK_C_decomposicao.png)

##### D. Distribuição de Uso

![D. Distribuição de Uso](../DISK_C/graficos/04_DISK_C_histograma.png)

##### E. Uso Médio por Hora

![E. Uso Médio por Hora](../DISK_C/graficos/05_DISK_C_uso_por_hora.png)

#### Análise Estatística

No período de 15/03/2026 a 13/06/2026, foram analisadas 91 amostras. A capacidade total considerada foi 179.40 GB e a margem de segurança de 80% equivale a 143.52 GB. Mínimo: 71.69 GB; média: 81.11 GB; mediana: 80.59 GB; P95: 89.25 GB; máximo: 89.36 GB. Previsões: 30 dias 83.32 GB (46.45%), 60 dias 84.33 GB (47.01%), 90 dias 85.33 GB (47.57%).

| Métrica | Valor |
|:--|--:|
| Capacidade total | 179.40 GB |
| Margem de segurança (80%) | 143.52 GB |
| Uso mínimo | 71.69 GB |
| Uso médio | 81.11 GB (45.21%) |
| Mediana | 80.59 GB (44.92%) |
| P95 | 89.25 GB (49.75%) |
| Máximo | 89.36 GB (49.81%) |
| Forecast 30 dias | 83.32 GB (46.45%) |
| Forecast 60 dias | 84.33 GB (47.01%) |
| Forecast 90 dias | 85.33 GB (47.57%) |
| Capacidade sugerida | Não aplicável |
| Variação sugerida | Não aplicável |

#### Conclusão e Recomendação

Não há indicação de aumento imediato do recurso Disco (Partição C:). A recomendação é manter a configuração atual e continuar o monitoramento periódico.

---

## 3. Observações

- A LLM/Data+RAG não calcula os números: ela apenas transforma os indicadores calculados pelo motor estatístico em texto executivo.
- A margem de segurança usada foi de 80% da capacidade total.
- O relatório consolidado reúne as análises individuais em um único documento para facilitar anexos em solicitação, FUP ou comunicação executiva.

---

PÃŠBLICO