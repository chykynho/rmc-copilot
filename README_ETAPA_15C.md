# Etapa 15-C — Integração do Gerador de Análise Individual ao projeto principal

Este patch move o módulo validado no projeto `rmc_copilot_llm_starter` para dentro do projeto principal `C:\Projetos\rmc_copilot`.

## O que entra

- `rmc_copilot/resource_analysis/`: motor da análise individual de recursos.
- `rmc_copilot/security/credentials.py`: utilitário para uso futuro com keyring/Windows Credential Manager.
- `app/pages/resource_analysis.py`: página Streamlit independente para análise individual.
- `requirements-resource-analysis.txt`: dependências específicas do módulo.
- `config/resource_analysis.example.yaml`: configuração exemplo.
- `scripts/34_generate_resource_analysis_consolidated_mock.ps1`: teste CLI consolidado.
- `scripts/35_run_resource_analysis_page.ps1`: execução da página Streamlit.

## Como testar no PC particular

```powershell
cd C:\Projetos\rmc_copilot
.\.rmcllm\Scripts\Activate.ps1
pip install -r .\requirements-resource-analysis.txt

python -m rmc_copilot.resource_analysis.generate_resource_analysis_consolidated_v1 `
  --solicitacao SOL1809645 `
  --vm SRV-DASHPRD01 `
  --resources CPU,MEM,DISK `
  --partitions C:,E: `
  --periodo 90 `
  --solicitante "Eduardo Barbosa" `
  --analista "Francisco Alves" `
  --mock `
  --save-prompt `
  --formats md,docx,pdf `
  --zip
```

## Como abrir a tela

```powershell
streamlit run .\app\pages\resource_analysis.py
```

## Saída esperada

- CPU: `SUPERDIMENSIONADO / AVALIAR_REDUÇÃO_RECURSO`
- MEM: `CRÍTICO / AUMENTAR_RECURSO`
- DISK C: `OK / MANTER_MONITORAMENTO`
- DISK E: `CRÍTICO / AUMENTAR_RECURSO`

Os relatórios saem em:

```text
data/reports/resource_analysis/<SOL>/<VM>/
```

## GitHub

Não use `git add .` neste momento, porque o repositório já possui arquivos não rastreados de etapas anteriores. Faça add somente dos arquivos da Etapa 15-C.

```powershell
git checkout -b etapa15c-resource-analysis-main

git add rmc_copilot/resource_analysis

git add rmc_copilot/security

git add app/pages/resource_analysis.py

git add config/resource_analysis.example.yaml config/secrets.example.yaml

git add docs/tecnicos/rmc_resource_analysis_etapa15b.md

git add requirements-resource-analysis.txt

git add scripts/34_generate_resource_analysis_consolidated_mock.ps1 scripts/35_run_resource_analysis_page.ps1

git add README_ETAPA_15C.md

git commit -m "Etapa 15C - integra gerador de analise individual de recursos"

git push origin etapa15c-resource-analysis-main
```

## Ambiente controlado

Ainda não é necessário usar o PC do ambiente controlado. Esta etapa continua em `local_simulado`.
