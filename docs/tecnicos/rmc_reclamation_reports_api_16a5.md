# Técnico - Etapa 16A.5

O report API do Aria/vROps permite gerar relatórios com `reportDefinitionId` e `resourceId`.

O fluxo implementado:

1. Autentica no Aria/vROps.
2. Busca o report definition.
3. Infere o resource kind pelo subject do report definition.
4. Lista recursos do tipo:
   - ClusterComputeResource para `Reclamation Report - vSphere Clusters`.
   - Datacenter para `Reclamation Report - Datacenter`.
5. Executa `POST /suite-api/api/reports`.
6. Aguarda conclusão via `GET /suite-api/api/reports/{id}`.
7. Baixa CSV/PDF via `GET /suite-api/api/reports/{id}/download?format=CSV/PDF`.
8. Grava metadados no DuckDB.
9. Faz parsing best-effort do CSV para linhas de reclaim/orphan.

Nenhuma ação operacional é executada.
