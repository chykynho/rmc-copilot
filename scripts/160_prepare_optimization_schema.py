from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime

import duckdb

SCHEMA_SQL = r"""
CREATE TABLE IF NOT EXISTS optimization_collection_runs (
    run_id VARCHAR PRIMARY KEY,
    collected_at TIMESTAMP,
    source VARCHAR,
    vrops_host VARCHAR,
    auth_source VARCHAR,
    cluster_filter VARCHAR,
    status VARCHAR,
    message VARCHAR,
    total_vms INTEGER DEFAULT 0,
    total_powered_off_vms INTEGER DEFAULT 0,
    total_snapshots INTEGER DEFAULT 0,
    total_snapshots_over_20d INTEGER DEFAULT 0,
    total_orphan_disk_candidates INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS vm_power_state_snapshots (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    vm_name VARCHAR,
    vm_resource_id VARCHAR,
    cluster VARCHAR,
    host VARCHAR,
    power_state VARCHAR,
    is_powered_off BOOLEAN,
    dias_desligada DOUBLE,
    cpu_count DOUBLE,
    memory_gb DOUBLE,
    disk_provisioned_gb DOUBLE,
    datastore_names VARCHAR,
    ambiente VARCHAR,
    raw_json VARCHAR
);

CREATE TABLE IF NOT EXISTS vm_snapshot_inventory (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    vm_name VARCHAR,
    vm_resource_id VARCHAR,
    cluster VARCHAR,
    host VARCHAR,
    snapshot_name VARCHAR,
    snapshot_created_at TIMESTAMP,
    snapshot_age_days DOUBLE,
    snapshot_size_gb DOUBLE,
    snapshot_count INTEGER,
    datastore VARCHAR,
    status_risco VARCHAR,
    raw_json VARCHAR
);

CREATE TABLE IF NOT EXISTS orphan_disk_candidates (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    datastore VARCHAR,
    vmdk_path VARCHAR,
    arquivo VARCHAR,
    tamanho_gb DOUBLE,
    data_modificacao TIMESTAMP,
    idade_dias DOUBLE,
    vm_associada_encontrada VARCHAR,
    cluster VARCHAR,
    status_validacao VARCHAR,
    confianca DOUBLE,
    observacao VARCHAR,
    raw_json VARCHAR
);

CREATE TABLE IF NOT EXISTS optimization_recommendations (
    run_id VARCHAR,
    created_at TIMESTAMP,
    item_type VARCHAR,
    severity VARCHAR,
    entity_name VARCHAR,
    cluster VARCHAR,
    metric VARCHAR,
    finding VARCHAR,
    recommendation VARCHAR,
    action_allowed BOOLEAN DEFAULT FALSE
);

CREATE OR REPLACE VIEW v_optimization_latest_run AS
SELECT *
FROM optimization_collection_runs
WHERE collected_at = (SELECT max(collected_at) FROM optimization_collection_runs);

CREATE OR REPLACE VIEW v_powered_off_vms_latest AS
SELECT p.*,
       CASE
         WHEN dias_desligada IS NULL THEN 'VALIDAR'
         WHEN dias_desligada >= 90 THEN 'CRITICO'
         WHEN dias_desligada >= 60 THEN 'RISCO'
         WHEN dias_desligada >= 30 THEN 'ATENCAO'
         ELSE 'OBSERVAR'
       END AS status_otimizacao,
       'Validar com o responsável antes de qualquer remoção. A IA apenas recomenda; não executa ação operacional.' AS recomendacao_padrao
FROM vm_power_state_snapshots p
WHERE p.run_id = (SELECT run_id FROM v_optimization_latest_run LIMIT 1)
  AND coalesce(p.is_powered_off, FALSE) = TRUE;

CREATE OR REPLACE VIEW v_snapshots_antigos_latest AS
SELECT s.*,
       CASE
         WHEN snapshot_age_days >= 60 THEN 'CRITICO'
         WHEN snapshot_age_days >= 30 THEN 'RISCO'
         WHEN snapshot_age_days > 20 THEN 'ATENCAO'
         ELSE 'OK'
       END AS status_otimizacao,
       'Validar com o responsável e planejar consolidação/remoção controlada. A IA apenas recomenda; não executa ação operacional.' AS recomendacao_padrao
FROM vm_snapshot_inventory s
WHERE s.run_id = (SELECT run_id FROM v_optimization_latest_run LIMIT 1)
  AND coalesce(s.snapshot_age_days, 0) > 20;

CREATE OR REPLACE VIEW v_orphan_disk_candidates_latest AS
SELECT o.*,
       'VALIDAR' AS status_otimizacao,
       'Disco candidato a órfão. Validar vínculo com VM, template, backup, clone ou snapshot antes de qualquer ação.' AS recomendacao_padrao
FROM orphan_disk_candidates o
WHERE o.run_id = (SELECT run_id FROM v_optimization_latest_run LIMIT 1);
"""

def main():
    ap = argparse.ArgumentParser(description="Etapa 16A - prepara schema DuckDB de Otimização")
    ap.add_argument("--db", default="data/database/rmc_copilot.duckdb")
    args = ap.parse_args()

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.execute(SCHEMA_SQL)
        tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        required = [
            "optimization_collection_runs",
            "vm_power_state_snapshots",
            "vm_snapshot_inventory",
            "orphan_disk_candidates",
            "optimization_recommendations",
        ]
        missing = [t for t in required if t not in tables]
        if missing:
            raise RuntimeError(f"Tabelas não criadas: {missing}")
        print(f"[OK] Schema de otimização preparado em {db_path}")
        print("[OK] Tabelas:", ", ".join(required))
    finally:
        con.close()

if __name__ == "__main__":
    main()
