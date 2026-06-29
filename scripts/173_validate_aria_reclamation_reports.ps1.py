from pathlib import Path
import duckdb

db = Path("data/database/rmc_copilot.duckdb")
if not db.exists():
    raise SystemExit(f"[ERRO] DuckDB nao encontrado: {db}")

con = duckdb.connect(str(db))
try:
    latest = con.execute("""
        SELECT run_id, max(generated_at) AS generated_at, count(*) AS exports
        FROM aria_reclamation_report_exports
        GROUP BY run_id
        ORDER BY generated_at DESC
        LIMIT 1
    """).fetchdf()
    if latest.empty:
        raise SystemExit("[ERRO] Nenhum export de Reclamation Report encontrado.")

    run_id = latest.iloc[0]["run_id"]
    print("[OK] Ultimo run de Reclamation Report:")
    print(latest.to_string(index=False))

    rows = con.execute("SELECT count(*) FROM aria_reclamation_report_rows WHERE run_id=?", [run_id]).fetchone()[0]
    orphans = con.execute("SELECT count(*) FROM orphan_disk_candidates WHERE run_id=?", [run_id]).fetchone()[0]
    print(f"[OK] Linhas com termos de reclaim: {rows}")
    print(f"[OK] Candidatos a orfaos derivados do report: {orphans}")

    print("\n[INFO] Top exports:")
    print(con.execute("""
        SELECT report_definition_name, resource_name, status, csv_path, pdf_path
        FROM aria_reclamation_report_exports
        WHERE run_id=?
        LIMIT 20
    """, [run_id]).fetchdf().to_string(index=False))

finally:
    con.close()
