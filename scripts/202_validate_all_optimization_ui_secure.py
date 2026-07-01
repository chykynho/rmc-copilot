from pathlib import Path
import duckdb

DB = Path("data/database/rmc_copilot.duckdb")
if not DB.exists():
    raise SystemExit(f"[ERRO] DuckDB não encontrado: {DB}")

con = duckdb.connect(str(DB))
try:
    print("[OK] Últimos runs consolidados:")
    runs = con.execute("""
        SELECT run_id, collected_at, reasons_csv, status, message
        FROM aria_ui_optimization_runs
        ORDER BY collected_at DESC
        LIMIT 5
    """).fetchdf()
    print(runs.to_string(index=False))

    if runs.empty:
        raise SystemExit("[ERRO] Nenhum run consolidado encontrado.")

    run_id = runs.iloc[0]["run_id"]

    print("\n[OK] Resumo por tipo:")
    df = con.execute("""
        SELECT reason, vm_state_used, targets_count, items_count,
               total_cpu_vcpus, total_memory_gb, total_storage_gb, total_savings_usd,
               status, message
        FROM aria_ui_optimization_reason_runs
        WHERE run_id = ?
        ORDER BY reason
    """, [run_id]).fetchdf()
    print(df.to_string(index=False))

    print("\n[OK] Resumo por alvo:")
    df2 = con.execute("""
        SELECT reason, target_name, count(*) AS itens,
               sum(cpu_vcpus) AS cpu_vcpus,
               sum(memory_gb) AS memory_gb,
               sum(storage_gb) AS storage_gb,
               sum(savings_usd) AS savings_usd
        FROM aria_ui_optimization_items
        WHERE run_id = ?
        GROUP BY reason, target_name
        ORDER BY reason, storage_gb DESC NULLS LAST, itens DESC
    """, [run_id]).fetchdf()
    print(df2.to_string(index=False))

finally:
    con.close()
