# Etapa 16A.14 - Segurança + todos os itens de otimização

Corrige dois pontos:

1. **Nada de senha/token/cookie em plain text**
   - Remove uso de `config/local/aria_ui_session.clixml`
   - Usa Windows Credential Manager via Python `keyring`
   - Scheduled Task não recebe segredo por argumento

2. **Coleta todos os itens de otimização**
   - `poweredOff_vms`
   - `vm_snapshots`
   - `idle_vms`
   - `orphaned_disk`

## Aplicar

```powershell
cd D:\Francisco\Capacity\rmc-copilot
Expand-Archive .\rmc_copilot_etapa_16a_14_secure_all_optimization.zip -DestinationPath . -Force
```

## Instalar dependências

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\199_install_secure_optimization_deps.ps1
```

## Remover arquivo antigo de sessão local

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\203_remove_plaintext_aria_session.ps1
```

## Salvar Cookie/secureToken no Windows Credential Manager

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\200_save_aria_ui_secrets_windows.ps1
```

## Teste rápido com 1 alvo por tipo

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\201_collect_all_optimization_ui_secure.ps1 -MaxTargets 1
```

## Validar

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\202_validate_all_optimization_ui_secure.ps1
```

## Rodar completo

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\201_collect_all_optimization_ui_secure.ps1
```

## Streamlit

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\205_patch_streamlit_all_optimization.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\134_run_dashboard_with_rmc_llm.ps1
```

Página criada:

```text
app/pages/91_Otimizacao_Aria.py
```

## Agendamento diário

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\204_register_daily_all_optimization_secure.ps1 -At "07:00"
```

Log:

```text
logs\optimization_ui_secure_daily.log
```

## Observação importante

Cookie/secureToken continuam sendo segredos de sessão e podem expirar. Eles não ficam em plain text, mas podem precisar ser renovados se a sessão do Aria expirar.

Para agendamento 100% robusto sem sessão de navegador, o ideal é o time do Aria liberar endpoint oficial/API para esses quatro itens.
