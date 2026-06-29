from pathlib import Path
import duckdb

db = Path("data/database/rmc_copilot.duckdb")
if not db.exists():
    raise SystemExit(f"[ERRO] DuckDB nao encontrado: {db}")

con = duckdb.connect(str(db))
try:
    latest = con.execute("""
        SELECT run_id, collected_at, source, total_vms, total_powered_off_vms,
               total_snapshots, total_snapshots_over_20d, total_orphan_disk_candidates
        FROM optimization_collection_runs
        WHERE source='VCENTER_PYVMOMI'
        ORDER BY collected_at DESC
        LIMIT 1
    """).fetchdf()

    if latest.empty:
        raise SystemExit("[ERRO] Nenhuma coleta VCENTER_PYVMOMI encontrada.")

    print("[OK] Ultima coleta VCENTER_PYVMOMI:")
    print(latest.to_string(index=False))

    run_id = latest.iloc[0]["run_id"]
    for table in ["vm_power_state_snapshots", "vm_snapshot_inventory", "orphan_disk_candidates", "optimization_recommendations"]:
        count = con.execute(f"SELECT count(*) FROM {table} WHERE run_id = ?", [run_id]).fetchone()[0]
        print(f"[OK] {table}: {count} registros para run_id={run_id}")

    actions = con.execute("SELECT count(*) FROM optimization_recommendations WHERE run_id=? AND coalesce(action_allowed,false)=true", [run_id]).fetchone()[0]
    if actions:
        raise SystemExit("[ERRO] Existe recomendacao com action_allowed=true. Isso viola a regra da IA.")
    print("[OK] Nenhuma acao operacional habilitada. IA apenas recomenda.")

finally:
    con.close()
