from __future__ import annotations

from pathlib import Path
import os

import duckdb
import pandas as pd
import streamlit as st


st.set_page_config(page_title="Otimização - Discos Órfãos", layout="wide")


def _fmt_tb(gb: float | int | None) -> str:
    try:
        gb = float(gb or 0)
    except Exception:
        gb = 0.0
    if gb >= 1024:
        return f"{gb / 1024:,.2f} TB".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{gb:,.2f} GB".replace(",", "X").replace(".", ",").replace("X", ".")


def _db_path() -> Path:
    env = os.getenv("RMC_DUCKDB_PATH") or os.getenv("RMC_DB_PATH")
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.extend([
        Path("data/database/rmc_copilot.duckdb"),
        Path("../data/database/rmc_copilot.duckdb"),
        Path.cwd() / "data/database/rmc_copilot.duckdb",
    ])
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def _table_exists(con: duckdb.DuckDBPyConnection, name: str) -> bool:
    try:
        return con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
            [name],
        ).fetchone()[0] > 0
    except Exception:
        return False


def _safe_df(con: duckdb.DuckDBPyConnection, sql: str, params=None) -> pd.DataFrame:
    try:
        return con.execute(sql, params or []).fetchdf()
    except Exception as exc:
        st.error(f"Erro ao consultar DuckDB: {exc}")
        return pd.DataFrame()


st.title("Otimização — Discos candidatos a órfãos")
st.caption("Fonte: Aria/vROps Reclamation Report API → DuckDB. Nenhuma ação operacional é executada.")

db = _db_path()

if not db.exists():
    st.error(f"DuckDB não encontrado: {db}")
    st.stop()

con = duckdb.connect(str(db), read_only=True)

try:
    if not _table_exists(con, "orphan_disk_candidates"):
        st.error("Tabela `orphan_disk_candidates` não existe no DuckDB.")
        st.code(
            "powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\172_run_aria_reclamation_reports.ps1 "
            "-User \"altran.jsantos@bv.com.br\" -AuthSource \"bvnet.bv\" -Report clusters -ResourceNameFilter \"BV_PRD\"",
            language="powershell",
        )
        st.stop()

    latest = _safe_df(
        con,
        """
        SELECT
            run_id,
            max(collected_at) AS collected_at,
            count(*) AS candidatos,
            coalesce(sum(tamanho_gb), 0) AS tamanho_gb
        FROM orphan_disk_candidates
        GROUP BY run_id
        ORDER BY collected_at DESC
        LIMIT 1
        """,
    )

    if latest.empty:
        st.warning("Ainda não há candidatos gravados em `orphan_disk_candidates`.")
        st.info("Rode o Reclamation Report via API e depois atualize esta página.")
        st.code(
            "powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\172_run_aria_reclamation_reports.ps1 "
            "-User \"altran.jsantos@bv.com.br\" -AuthSource \"bvnet.bv\" -Report clusters -ResourceNameFilter \"BV_PRD\"",
            language="powershell",
        )
        st.stop()

    run_id = str(latest.iloc[0]["run_id"])
    collected_at = latest.iloc[0]["collected_at"]
    candidatos = int(latest.iloc[0]["candidatos"] or 0)
    tamanho_gb = float(latest.iloc[0]["tamanho_gb"] or 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Candidatos", f"{candidatos}")
    c2.metric("Tamanho potencial", _fmt_tb(tamanho_gb))
    c3.metric("Run", run_id[-8:])
    c4.metric("Fonte", "Aria Reclamation")

    st.caption(f"Última coleta de candidatos: `{run_id}` — `{collected_at}`")

    df = _safe_df(
        con,
        """
        SELECT
            collected_at,
            run_id,
            cluster,
            datastore,
            vmdk_path,
            arquivo,
            tamanho_gb,
            status_validacao,
            confianca,
            vm_associada_encontrada,
            observacao,
            raw_json
        FROM orphan_disk_candidates
        WHERE run_id = ?
        ORDER BY coalesce(tamanho_gb, 0) DESC, cluster, datastore, vmdk_path
        """,
        [run_id],
    )

    with st.expander("Resumo por cluster / origem", expanded=True):
        resumo = _safe_df(
            con,
            """
            SELECT
                coalesce(cluster, 'N/A') AS cluster,
                count(*) AS candidatos,
                coalesce(sum(tamanho_gb), 0) AS tamanho_gb,
                avg(confianca) AS confianca_media
            FROM orphan_disk_candidates
            WHERE run_id = ?
            GROUP BY 1
            ORDER BY candidatos DESC, tamanho_gb DESC
            """,
            [run_id],
        )
        if not resumo.empty:
            resumo["tamanho"] = resumo["tamanho_gb"].apply(_fmt_tb)
            st.dataframe(
                resumo[["cluster", "candidatos", "tamanho", "confianca_media"]],
                use_container_width=True,
                hide_index=True,
            )

    st.subheader("Candidatos a órfãos / reclaim")
    st.warning(
        "Estes itens são candidatos para validação. "
        "Não remover disco sem confirmar vínculo com VM, template, backup, clone ou snapshot."
    )

    if not df.empty:
        df_view = df.copy()
        df_view["tamanho"] = df_view["tamanho_gb"].apply(_fmt_tb)
        cols = [
            "cluster",
            "datastore",
            "vmdk_path",
            "arquivo",
            "tamanho",
            "status_validacao",
            "confianca",
            "vm_associada_encontrada",
            "observacao",
        ]
        existing_cols = [c for c in cols if c in df_view.columns]
        st.dataframe(df_view[existing_cols], use_container_width=True, hide_index=True)

        csv = df_view.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Baixar candidatos a órfãos / reclaim em CSV",
            csv,
            file_name=f"orphan_disk_candidates_{run_id}.csv",
            mime="text/csv",
        )

    with st.expander("Linhas brutas do Reclamation Report usadas como base", expanded=False):
        if _table_exists(con, "aria_reclamation_report_rows"):
            raw_rows = _safe_df(
                con,
                """
                SELECT
                    generated_at,
                    report_definition_name,
                    resource_name,
                    matched_terms,
                    row_text
                FROM aria_reclamation_report_rows
                WHERE run_id = ?
                ORDER BY resource_name, row_index
                """,
                [run_id],
            )
            if raw_rows.empty:
                st.info("Não há linhas brutas para este run_id em `aria_reclamation_report_rows`.")
            else:
                st.dataframe(raw_rows, use_container_width=True, hide_index=True)
        else:
            st.info("Tabela `aria_reclamation_report_rows` não existe.")

    with st.expander("Auditoria de exports CSV/PDF", expanded=False):
        if _table_exists(con, "aria_reclamation_report_exports"):
            exports = _safe_df(
                con,
                """
                SELECT
                    generated_at,
                    report_definition_name,
                    resource_name,
                    status,
                    csv_path,
                    pdf_path
                FROM aria_reclamation_report_exports
                WHERE run_id = ?
                ORDER BY resource_name
                """,
                [run_id],
            )
            st.dataframe(exports, use_container_width=True, hide_index=True)
        else:
            st.info("Tabela `aria_reclamation_report_exports` não existe.")

    st.divider()
    st.caption("Regra fixa: IA apenas recomenda. Não executa desligamento, remoção de snapshot, deleção de disco ou abertura de chamado.")

finally:
    con.close()
