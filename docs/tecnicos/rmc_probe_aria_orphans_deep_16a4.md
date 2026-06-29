# Técnico - 16A.4 Deep Probe Aria/vROps

O probe anterior confirmou:
- Datastores existem como `resourceKind=Datastore`.
- StoragePods existem.
- Busca por recurso `orphan` não retorna objetos.
- `viewdefinitions` e `views` retornam 404 nesse ambiente.
- `reportdefinitions` existe.

Este probe aprofunda:
- statkeys/properties de Datastore, StoragePod e VirtualMachine;
- report definitions;
- reports;
- supermetrics;
- alert/recommendation definitions;
- alguns endpoints internos comuns, somente GET/read-only.

A saída serve para identificar a rota viável para automatizar a coleta de discos órfãos sem CSV manual.
