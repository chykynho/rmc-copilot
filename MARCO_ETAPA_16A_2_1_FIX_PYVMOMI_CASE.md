# MARCO_ETAPA_16A_2_1_FIX_PYVMOMI_CASE

Correção do import do pyVmomi/pyVim.

- Pacote pip: `pyvmomi`
- Import correto: `from pyVim.connect import SmartConnect, Disconnect`
- Import correto: `from pyVmomi import vim, vmodl`
- PS1 agora prioriza `.rmcllm\Scripts\python.exe`.
