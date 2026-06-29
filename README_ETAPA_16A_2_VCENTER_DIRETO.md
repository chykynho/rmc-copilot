# Etapa 16A.2 - Otimização com coleta direta vCenter/pyVmomi

Esta etapa corrige a direção da coleta:

- Não depende de CSV manual do Aria.
- Usa vCenter/pyVmomi, seguindo a lógica dos scripts fornecidos pelo Francisco.
- Coleta VMs desligadas, snapshots e candidatos a discos órfãos.
- Grava no DuckDB usado pelo dashboard de Otimização.
- Não executa ação operacional.

## Arquitetura

```text
vCenter API / pyVmomi -> DuckDB -> Streamlit / IA de recomendação
```

## Regra fixa

```text
A IA apenas analisa e recomenda.
Não desliga VM.
Não remove snapshot.
Não deleta disco.
Não abre chamado.
```

## Aplicar

```powershell
cd D:\Francisco\Capacity\rmc-copilot
Expand-Archive .\rmc_copilot_etapa_16a_2_vcenter_direto.zip -DestinationPath . -Force
```

## Instalar dependências, se precisar

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\164_install_optimization_vcenter_deps.ps1
```

## Teste seguro com poucas VMs

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\165_collect_optimization_vcenter.ps1 -MaxVms 50
```

## Teste com snapshots e varredura de órfãos

A varredura de datastores pode demorar.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\165_collect_optimization_vcenter.ps1 -MaxVms 50 -IncludeOrphanScan
```

## Coleta completa

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\165_collect_optimization_vcenter.ps1 -IncludeOrphanScan
```

## Validar

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\166_validate_optimization_vcenter_16a2.ps1
```
