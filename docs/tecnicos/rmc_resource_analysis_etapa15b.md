# Etapa 15-B — Gerador de Análise Individual de Recursos

## Objetivo

Converter a lógica do notebook `Analise_CPU_MEM.ipynb` em um serviço integrado ao RMC Copilot, com seleção de VM, recurso e número de solicitação pela interface, sem depender de upload manual de arquivos no produto final.

## O que foi preservado da lógica original

- Número da solicitação de serviço como referência operacional.
- VM analisada.
- Recurso analisado: CPU, memória ou disco/partição.
- Leitura compatível com arquivos `MetricChart_*` do vROps, incluindo `skiprows=2`, `Date & Time` e `Value`.
- Remoção de colunas auxiliares do vROps: `Low DT`, `High DT`, `Smooth`, `Unnamed: 5`.
- Remoção de timezone.
- Cálculo de capacidade total, início/fim da coleta, mínimo, máximo, média, mediana, Q1, Q3, IQR, P95, outliers e percentual médio de uso.
- Margem de segurança de 80%.
- Geração de gráficos: comparação/previsão, média móvel, decomposição, histograma e uso por hora.
- Relatório com resumo executivo, análise dos gráficos, análise estatística, conclusão e recomendação.

## O que foi alterado

- A VM passa a ser selecionada pela interface ou por parâmetro, não digitada dentro do código.
- A solicitação passa a ser campo obrigatório.
- A saída é organizada por solicitação/VM/recurso.
- O relatório recebe cabeçalho padronizado com estilo BV.
- A LLM não calcula números; ela apenas gera narrativa a partir dos indicadores calculados.
- Foi criado modo `local_simulado` para desenvolvimento no PC particular sem acesso ao ambiente controlado.
- Foi criado contrato `RmcTimeseriesProvider` para plugar a coleta real no ambiente controlado.

## Estrutura entregue

```text
src/rmc_resource_analysis/
  models.py
  data_loader.py
  providers.py
  stats_engine.py
  charts.py
  narrative.py
  report_builder.py
  generate_resource_analysis_report_v1.py

src/rmc_security/
  credentials.py

app/pages/
  resource_analysis.py

config/
  resource_analysis.example.yaml
  secrets.example.yaml

scripts/
  29_generate_resource_analysis_mock.ps1
  30_run_resource_analysis_streamlit.ps1
  31_set_rmc_credentials.ps1
```

## Uso no PC particular

```powershell
python .\src\rmc_resource_analysis\generate_resource_analysis_report_v1.py `
  --solicitacao SOL1809645 `
  --vm SRV-DASHPRD01 `
  --resource CPU `
  --periodo-dias 90 `
  --solicitante "Eduardo Barbosa Ferreira" `
  --analista "Francisco Alves" `
  --mock `
  --save-prompt
```

## Uso com arquivos MetricChart antigos

```powershell
python .\src\rmc_resource_analysis\generate_resource_analysis_report_v1.py `
  --solicitacao SOL1809645 `
  --vm SRV-DASHPRD01 `
  --resource DSK `
  --partition E `
  --periodo-dias 90 `
  --legacy-dir "D:\Francisco\Capacity\analises\SOL1809645\SRV-DASHPRD01"
```

## Saída

```text
data/reports/resource_analysis/
└── SOL1809645/
    └── SRV-DASHPRD01/
        └── CPU/
            ├── SOL1809645_SRV-DASHPRD01_CPU_analise_recursos.md
            ├── SOL1809645_SRV-DASHPRD01_CPU_metadata.json
            ├── SOL1809645_SRV-DASHPRD01_CPU_llm_prompt.txt
            └── graficos/
```

## Credenciais

O gerador de relatório não deve guardar senha nem acessar diretamente credenciais em produção. As credenciais pertencem à camada de coleta. Para quando a coleta for usada no ambiente controlado, o patch inclui `src/rmc_security/credentials.py`, que usa `keyring`/Windows Credential Manager.

Nunca versionar:

```text
.env
config/secrets.yaml
config/pipeline.yaml
arquivos reais CSV/XLSX/PARQUET
logs com dados sensíveis
```

## Próxima etapa

A próxima etapa é plugar o `RmcTimeseriesProvider` na base histórica real do RMC Copilot no ambiente controlado, substituindo o modo `local_simulado` e eliminando a necessidade de arquivos `MetricChart_*`.
