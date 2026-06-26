# Regras de Capacity Planning VMware

## VM superdimensionada em CPU
Uma VM pode ser considerada superdimensionada em CPU quando a média de utilização fica abaixo de 20% e o percentil 95 fica abaixo de 40%.

## VM subdimensionada em CPU
Uma VM pode ser considerada subdimensionada em CPU quando o percentil 95 de utilização fica acima de 85%.

## Memória
Para memória, considerar média, p95, ballooning, swap e comportamento histórico.

## Disco
Para disco, considerar uso acima de 85% como risco operacional.