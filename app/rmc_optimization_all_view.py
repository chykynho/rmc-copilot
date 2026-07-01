from __future__ import annotations

import subprocess
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DB_DEFAULT = "data/database/rmc_copilot.duckdb"

REASON_LABELS = {
    "orphaned_disk": "Orphan Disk",
    "idle_vms": "VMs Idle",
    "poweredOff_vms": "Powered Off VMs",
    "vm_snapshots": "Snapshots",
}

def _connect(db_path: str = DB_DEFAULT):
    return duckdb.connect(db_path, read_only=True)

def _has_table(con, table: str) -> bool:
    try:
        return con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [table]).fetchone()[0] > 0
    except Exception:
        return False

def _fmt(n, dec=1):
    try:
        return f"{float(n):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "-"

def render_all_optimization_panel(db_path: str = DB_DEFAULT):
    st.header("OTMZ")
    st.caption("Coleta consolidada: Powered Off, Snapshots, VMs Idle e Orphan Disk. Somente leitura; nenhuma ação operacional é executada.")

    cbtn, cinfo = st.columns([1, 3])
    with cbtn:
        if st.button("Buscar OTMZ agora", type="primary"):
            with st.spinner("Coletando todos os itens de otimização pela UI do Aria..."):
                cmd = [
                    "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", ".\\scripts\\201_collect_all_optimization_ui_secure.ps1",
                    "-NoPrompt"
                ]
                proc = subprocess.run(cmd, cwd=str(Path.cwd()), capture_output=True, text=True, timeout=3600)
                if proc.returncode == 0:
                    st.success("Coleta concluída.")
                    st.code((proc.stdout or "")[-5000:])
                else:
                    st.error("Falha na coleta. Verifique Windows Credential Manager / sessão do Aria.")
                    st.code(((proc.stdout or "") + "\n" + (proc.stderr or ""))[-7000:])

    db = Path(db_path)
    if not db.exists():
        st.warning(f"DuckDB não encontrado: {db_path}")
        return

    con = _connect(db_path)
    try:
        if not _has_table(con, "aria_ui_optimization_reason_runs"):
            st.info("Ainda não há coleta consolidada de otimização.")
            return

        runs = con.execute("""
            SELECT run_id, collected_at, reasons_csv, status, message
            FROM aria_ui_optimization_runs
            ORDER BY collected_at DESC
            LIMIT 10
        """).fetchdf() if _has_table(con, "aria_ui_optimization_runs") else pd.DataFrame()

        if not runs.empty:
            latest_run_id = runs.iloc[0]["run_id"]
            st.caption(f"Último run: {latest_run_id} | {runs.iloc[0]['collected_at']} | status={runs.iloc[0]['status']}")
        else:
            latest_run_id = con.execute("""
                SELECT run_id FROM aria_ui_optimization_reason_runs ORDER BY collected_at DESC LIMIT 1
            """).fetchone()[0]

        resumo = con.execute("""
            SELECT reason, items_count, total_cpu_vcpus, total_memory_gb,
                   total_storage_gb, total_savings_usd, status
            FROM aria_ui_optimization_reason_runs
            WHERE run_id = ?
            ORDER BY reason
        """, [latest_run_id]).fetchdf()

        st.subheader("Resumo")
        if not resumo.empty:
            total_itens = int(resumo["items_count"].fillna(0).sum())
            total_storage = float(resumo["total_storage_gb"].fillna(0).sum())
            total_savings = float(resumo["total_savings_usd"].fillna(0).sum())
            total_cpu = float(resumo["total_cpu_vcpus"].fillna(0).sum())
            total_mem = float(resumo["total_memory_gb"].fillna(0).sum())

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Itens", total_itens)
            m2.metric("Storage GB", _fmt(total_storage, 1))
            m3.metric("Savings US$", _fmt(total_savings, 2))
            m4.metric("vCPUs", _fmt(total_cpu, 0))
            m5.metric("Memória GB", _fmt(total_mem, 1))

            resumo_show = resumo.copy()
            resumo_show["tipo"] = resumo_show["reason"].map(REASON_LABELS).fillna(resumo_show["reason"])
            st.dataframe(resumo_show[["tipo", "items_count", "total_cpu_vcpus", "total_memory_gb", "total_storage_gb", "total_savings_usd", "status"]], use_container_width=True, hide_index=True)

        items = con.execute("""
            SELECT reason, target_name, item_name, vmdk_path, arquivo,
                   cpu_vcpus, memory_gb, storage_gb, savings_usd,
                   days_in_live, last_access_at
            FROM aria_ui_optimization_items
            WHERE run_id = ?
        """, [latest_run_id]).fetchdf()

        if items.empty:
            st.warning("Run encontrado, mas sem itens de detalhe.")
            return

        tabs = st.tabs(["Todos", "Powered Off", "Snapshots", "VMs Idle", "Orphan Disk"])

        def show_reason(tab, reason=None):
            with tab:
                df = items.copy()
                if reason:
                    df = df[df["reason"] == reason]
                busca = st.text_input("Buscar", key=f"busca_{reason or 'todos'}")
                if busca:
                    mask = (
                        df["item_name"].astype(str).str.contains(busca, case=False, na=False) |
                        df["vmdk_path"].astype(str).str.contains(busca, case=False, na=False) |
                        df["target_name"].astype(str).str.contains(busca, case=False, na=False)
                    )
                    df = df[mask]
                targets = sorted([x for x in df["target_name"].dropna().unique()])
                sel = st.multiselect("Cluster/Datastore", targets, default=targets, key=f"target_{reason or 'todos'}")
                if sel:
                    df = df[df["target_name"].isin(sel)]

                st.dataframe(
                    df.sort_values(["storage_gb", "savings_usd"], ascending=[False, False]),
                    use_container_width=True,
                    hide_index=True,
                )
                st.download_button(
                    "Baixar CSV filtrado",
                    data=df.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"otimizacao_{reason or 'todos'}.csv",
                    mime="text/csv",
                    key=f"csv_{reason or 'todos'}",
                )

        show_reason(tabs[0], None)
        show_reason(tabs[1], "poweredOff_vms")
        show_reason(tabs[2], "vm_snapshots")
        show_reason(tabs[3], "idle_vms")
        show_reason(tabs[4], "orphaned_disk")

        with st.expander("Histórico de runs"):
            if not runs.empty:
                st.dataframe(runs, use_container_width=True, hide_index=True)

    finally:
        con.close()

if __name__ == "__main__":
    st.set_page_config(page_title="RMC Copilot - OTMZ", layout="wide")
    render_all_optimization_panel()
