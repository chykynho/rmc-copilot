from pathlib import Path
import duckdb

db = Path("data/database/rmc_copilot.duckdb")
if not db.exists():
    raise SystemExit(f"[ERRO] DuckDB não encontrado: {db}")
con = duckdb.connect(str(db))
try:
    row = con.execute("""
        SELECT run_id, collected_at, source, total_datastores, message
        FROM datastore_collection_runs
        ORDER BY collected_at DESC
        LIMIT 1
    """).fetchdf()
    if row.empty:
        raise SystemExit("[ERRO] Nenhuma coleta de datastore encontrada.")
    print("[OK] Última coleta de datastore:")
    print(row.to_string(index=False))
    run_id = row.iloc[0]["run_id"]
    top = con.execute("""
        SELECT name, resource_id, adapter_kind, resource_kind
        FROM datastore_inventory_vrops
        WHERE run_id=?
        ORDER BY name
        LIMIT 20
    """, [run_id]).fetchdf()
    print("[OK] Amostra de datastores:")
    print(top.to_string(index=False))
finally:
    con.close()
