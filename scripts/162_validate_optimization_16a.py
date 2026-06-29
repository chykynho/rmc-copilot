from __future__ import annotations

import argparse
from pathlib import Path
import duckdb

REQUIRED_TABLES = [
    "optimization_collection_runs",
    "vm_power_state_snapshots",
    "vm_snapshot_inventory",
    "orphan_disk_candidates",
    "optimization_recommendations",
]
REQUIRED_FILES = [
    "scripts/160_prepare_optimization_schema.py",
    "scripts/160_prepare_optimization_schema.ps1",
    "scripts/161_collect_optimization_vrops.py",
    "scripts/161_collect_optimization_vrops.ps1",
    "app/pages/16_Otimizacao.py",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/database/rmc_copilot.duckdb")
    args = ap.parse_args()

    missing_files = [f for f in REQUIRED_FILES if not Path(f).exists()]
    if missing_files:
        raise SystemExit("Arquivos ausentes: " + ", ".join(missing_files))

    con = duckdb.connect(args.db)
    try:
        tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        missing = [t for t in REQUIRED_TABLES if t not in tables]
        if missing:
            raise SystemExit("Tabelas ausentes: " + ", ".join(missing))
        print("[OK] Etapa 16A validada")
        print("[OK] Tabelas:", ", ".join(REQUIRED_TABLES))
    finally:
        con.close()

if __name__ == "__main__":
    main()
