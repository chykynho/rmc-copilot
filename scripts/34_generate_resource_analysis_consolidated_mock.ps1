# RMC Copilot - Gerador de Análise Individual Consolidado
# Executar a partir da raiz do projeto C:\Projetos\rmc_copilot
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
