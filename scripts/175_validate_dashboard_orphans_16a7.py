from __future__ import annotations

from pathlib import Path
import duckdb

DB = Path("data/database/rmc_copilot.duckdb")

SQL = r"""
CREATE OR REPLACE VIEW v_orphan_disk_candidates_latest AS
WITH latest AS (
    SELECT run_id
    FROM orphan_disk_candidates
    ORDER BY collected_at DESC
    LIMIT 1
)
SELECT o.*,
       'VALIDAR' AS status_otimizacao,
       'Disco candidato a órfão/reclaim. Validar vínculo com VM, template, backup, clone ou snapshot antes de qualquer ação. A IA apenas recomenda.' AS recomendacao_padrao
FROM orphan_disk_candidates o
WHERE o.run_id = (SELECT run_id FROM latest);

CREATE OR REPLACE VIEW v_optimization_orphan_summary_latest AS
SELECT
    run_id,
    max(collected_at) AS collected_at,
    count(*) AS candidatos,
    coalesce(sum(tamanho_gb), 0) AS tamanho_gb,
    count(DISTINCT coalesce(cluster, 'N/A')) AS clusters
FROM v_orphan_disk_candidates_latest
GROUP BY run_id;
"""

def table_exists(con, name):
    return con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
        [name],
    ).fetchone()[0] > 0

def main():
    if not DB.exists():
        raise SystemExit(f"[ERRO] DuckDB não encontrado: {DB}")

    con = duckdb.connect(str(DB))
    try:
        if not table_exists(con, "orphan_disk_candidates"):
            raise SystemExit("[ERRO] Tabela orphan_disk_candidates não existe.")

        total = con.execute("SELECT count(*) FROM orphan_disk_candidates").fetchone()[0]
        if total == 0:
            raise SystemExit("[ERRO] Tabela orphan_disk_candidates existe, mas está vazia.")

        con.execute(SQL)

        latest = con.execute("""
            SELECT run_id, max(collected_at) AS collected_at, count(*) AS candidatos, coalesce(sum(tamanho_gb),0) AS tamanho_gb
            FROM orphan_disk_candidates
            GROUP BY run_id
            ORDER BY collected_at DESC
            LIMIT 1
        """).fetchdf()

        print("[OK] Último run de candidatos a órfãos/reclaim:")
        print(latest.to_string(index=False))

        print("\n[OK] Resumo da view:")
        print(con.execute("SELECT * FROM v_optimization_orphan_summary_latest").fetchdf().to_string(index=False))

        print("\n[INFO] Top 20 candidatos:")
        print(con.execute("""
            SELECT cluster, datastore, vmdk_path, arquivo, tamanho_gb, status_validacao, confianca, observacao
            FROM v_orphan_disk_candidates_latest
            ORDER BY coalesce(tamanho_gb,0) DESC, cluster
            LIMIT 20
        """).fetchdf().to_string(index=False))

        print("\n[OK] Página adicionada em app/pages/16A_Otimizacao_Orfaos.py")
        print("[OK] Abra o dashboard e procure a página: Otimização - Discos Órfãos")

    finally:
        con.close()

if __name__ == "__main__":
    main()
