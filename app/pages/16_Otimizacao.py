from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st

try:
    import duckdb
except Exception:
    duckdb = None

st.set_page_config(page_title="Otimização - RMC Copilot", layout="wide")
st.title("Otimização de Recursos")
st.caption("VMs desligadas, snapshots antigos e discos candidatos a órfãos. A IA recomenda; não executa ação operacional.")

DB_PATH = Path("data/database/rmc_copilot.duckdb")


def load_df(sql: str) -> pd.DataFrame:
    if duckdb is None:
        st.error("Biblioteca duckdb não está instalada no ambiente.")
        return pd.DataFrame()
    if not DB_PATH.exists():
        st.warning(f"Banco DuckDB não encontrado: {DB_PATH}")
        return pd.DataFrame()
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return con.execute(sql).fetchdf()
    except Exception as exc:
        st.warning(f"Consulta não disponível ainda: {exc}")
        return pd.DataFrame()
    finally:
        con.close()

runs = load_df("SELECT * FROM optimization_collection_runs ORDER BY collected_at DESC LIMIT 20")
if runs.empty:
    st.info("Nenhuma coleta de otimização encontrada. Rode scripts\\160_prepare_optimization_schema.ps1 e depois scripts\\161_collect_optimization_vrops.ps1.")
    st.stop()

latest = runs.iloc[0]
st.subheader("Última coleta")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("VMs", int(latest.get("total_vms") or 0))
c2.metric("VMs desligadas", int(latest.get("total_powered_off_vms") or 0))
c3.metric("Snapshots", int(latest.get("total_snapshots") or 0))
c4.metric("Snapshots > 20d", int(latest.get("total_snapshots_over_20d") or 0))
c5.metric("Discos candidatos", int(latest.get("total_orphan_disk_candidates") or 0))
st.caption(f"Run: {latest.get('run_id')} | Coletado em: {latest.get('collected_at')} | Fonte: {latest.get('source')}")

powered = load_df("SELECT * FROM v_powered_off_vms_latest")
snaps = load_df("SELECT * FROM v_snapshots_antigos_latest")
orphans = load_df("SELECT * FROM v_orphan_disk_candidates_latest")

clusters = sorted(set([str(x) for df in [powered, snaps, orphans] for x in (df.get("cluster", pd.Series(dtype=str)).dropna().unique() if not df.empty else []) if str(x).strip()]))
colf1, colf2 = st.columns([2, 2])
cluster_filter = colf1.multiselect("Cluster", clusters)
search = colf2.text_input("Buscar VM / arquivo / datastore", "")


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if cluster_filter and "cluster" in out.columns:
        out = out[out["cluster"].astype(str).isin(cluster_filter)]
    if search:
        s = search.upper()
        mask = pd.Series(False, index=out.index)
        for col in out.columns:
            if out[col].dtype == object:
                mask = mask | out[col].astype(str).str.upper().str.contains(s, na=False)
        out = out[mask]
    return out

powered_f = apply_filters(powered)
snaps_f = apply_filters(snaps)
orphans_f = apply_filters(orphans)

t1, t2, t3 = st.tabs(["VMs desligadas", "Snapshots > 20 dias", "Discos candidatos a órfãos"])

with t1:
    st.subheader("VMs desligadas")
    st.caption("O objetivo é identificar oportunidade de otimização. Não há ação automática de desligamento, remoção ou abertura de chamado.")
    if powered_f.empty:
        st.success("Nenhuma VM desligada encontrada na última coleta, ou a informação de power state não veio do vROps.")
    else:
        cols = [c for c in ["status_otimizacao", "vm_name", "cluster", "host", "power_state", "dias_desligada", "cpu_count", "memory_gb", "disk_provisioned_gb", "recomendacao_padrao"] if c in powered_f.columns]
        st.dataframe(powered_f[cols], use_container_width=True, hide_index=True)
        st.download_button("Baixar CSV - VMs desligadas", powered_f.to_csv(index=False).encode("utf-8-sig"), "vms_desligadas.csv", "text/csv")

with t2:
    st.subheader("Snapshots antigos")
    st.caption("Regra inicial: >20 dias = atenção, >30 dias = risco, >60 dias = crítico.")
    if snaps_f.empty:
        st.success("Nenhum snapshot com mais de 20 dias encontrado na última coleta, ou a informação de snapshot não veio do vROps.")
    else:
        cols = [c for c in ["status_otimizacao", "vm_name", "cluster", "host", "snapshot_name", "snapshot_created_at", "snapshot_age_days", "snapshot_size_gb", "snapshot_count", "recomendacao_padrao"] if c in snaps_f.columns]
        st.dataframe(snaps_f[cols], use_container_width=True, hide_index=True)
        st.download_button("Baixar CSV - Snapshots antigos", snaps_f.to_csv(index=False).encode("utf-8-sig"), "snapshots_antigos.csv", "text/csv")

with t3:
    st.subheader("Discos candidatos a órfãos")
    st.caption("Candidato a órfão não é confirmação. É obrigatório validar vínculo com VM, template, backup, clone ou snapshot antes de qualquer ação.")
    if orphans_f.empty:
        st.info("Nenhum candidato importado. Para discos órfãos, a Etapa 16A deixa o schema pronto e aceita CSV opcional na coleta.")
    else:
        cols = [c for c in ["status_otimizacao", "datastore", "arquivo", "vmdk_path", "tamanho_gb", "data_modificacao", "idade_dias", "cluster", "confianca", "recomendacao_padrao"] if c in orphans_f.columns]
        st.dataframe(orphans_f[cols], use_container_width=True, hide_index=True)
        st.download_button("Baixar CSV - Discos candidatos", orphans_f.to_csv(index=False).encode("utf-8-sig"), "discos_candidatos_orfaos.csv", "text/csv")

st.divider()
st.info("Regra de segurança: esta tela não executa ação operacional. A IA e o dashboard apenas analisam e recomendam validação.")
