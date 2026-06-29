# Etapa 16A.2.1 - Correção pyVmomi / pyVim

O pacote pip é `pyvmomi`, mas os módulos importados no código são sensíveis a maiúsculas/minúsculas:

```python
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
```

## Aplicar

```powershell
cd D:\Francisco\Capacity\rmc-copilot
Expand-Archive .\rmc_copilot_etapa_16a_2_1_fix_pyvmomi_case.zip -DestinationPath . -Force
```

## Verificar import

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\167_check_pyvmomi_import.ps1
```

## Instalar dependências se necessário

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\164_install_optimization_vcenter_deps.ps1
```

## Rodar coleta de teste

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\165_collect_optimization_vcenter.ps1 -MaxVms 50
```
