# Técnico - 16A.14

Segurança:
- Não usar `config/local/aria_ui_session.clixml`.
- Segredos no Windows Credential Manager via `keyring`.
- Scheduled Task sem Cookie/secureToken em argumento.

Coleta:
- Endpoint `/ui/capacityNew.action`
- `mainAction=getDCReclaimableCapacityAllData`
- `mainAction=getReclaimableVms`

Reasons:
- `poweredOff_vms`
- `vm_snapshots`
- `idle_vms`
- `orphaned_disk`

Tabelas principais:
- `aria_ui_optimization_runs`
- `aria_ui_optimization_reason_runs`
- `aria_ui_optimization_items`

Tabelas compatíveis:
- `orphan_disk_candidates`
- `aria_ui_orphan_vmdk_*`
- `aria_ui_idle_vm_*`
- `aria_ui_poweredoff_vm_*`
- `aria_ui_snapshot_vm_*`
