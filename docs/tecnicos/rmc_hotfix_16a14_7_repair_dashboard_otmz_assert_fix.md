# Hotfix 16A.14.7 - Reparo definitivo OTMZ/menu

Corrige o erro do hotfix 16A.14.6:

```text
ASSERT falhou: import OTMZ global ainda existe
```

O assert estava errado: o import dentro da função `render_otimizacao_unificada()` é correto.
O que não pode existir é import global no topo quebrando o `from ... import (...)`.

Este hotfix:

- restaura automaticamente um backup válido do dashboard;
- remove imports OTMZ globais/quebrados;
- preserva `def main()`;
- substitui apenas `render_otimizacao_unificada()`;
- faz `Otimização` carregar `OTMZ`;
- cria/valida `app/rmc_otmz_menu_view.py`;
- move páginas soltas para `app/pages_disabled`;
- compila antes de gravar e valida depois.

Não altera coleta, DuckDB, credenciais, LLM ou agendamento.

## Aplicar

```powershell
cd D:\Francisco\Capacity\rmc-copilot
Expand-Archive .\rmc_copilot_hotfix_16a_14_7_repair_dashboard_otmz_assert_fix.zip -DestinationPath . -Force
```

## Rodar

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\214_repair_dashboard_otmz_assert_fix.ps1
```

## Validar

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\215_validate_dashboard_otmz_assert_fix.ps1
```

## Subir

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\134_run_dashboard_with_rmc_llm.ps1
```

Resultado esperado:

```text
Otimização -> OTMZ
```
