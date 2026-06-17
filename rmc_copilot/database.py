from pathlib import Path
from datetime import datetime

import duckdb
import pandas as pd


def conectar_banco(caminho_banco: str | Path):
    caminho_banco = Path(caminho_banco)
    caminho_banco.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(caminho_banco))


def preparar_dataframe_para_duckdb(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for coluna in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[coluna]):
            df[coluna] = pd.to_datetime(df[coluna], errors="coerce")
        elif df[coluna].dtype == "object":
            df[coluna] = df[coluna].astype(str)
    return df


def criar_tabelas_base(con):
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS execucoes (
            execution_id VARCHAR,
            nome_arquivo VARCHAR,
            data_execucao TIMESTAMP,
            total_vms INTEGER,
            observacao VARCHAR
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS analise_vms (
            execution_id VARCHAR,
            cluster VARCHAR,
            vm VARCHAR,
            vm_resource_id VARCHAR,
            categoria_vm VARCHAR,
            status_geral VARCHAR,
            status_cpu VARCHAR,
            status_memoria VARCHAR,
            status_disco VARCHAR,
            risco_futuro_90d VARCHAR,
            criticidade_futura VARCHAR,
            score_prioridade DOUBLE,
            prioridade_final VARCHAR,
            acao_final VARCHAR,
            cpu_media_pct DOUBLE,
            cpu_p95_pct DOUBLE,
            cpu_max_pct DOUBLE,
            mem_media_pct DOUBLE,
            mem_p95_pct DOUBLE,
            mem_max_pct DOUBLE,
            disk_media_pct DOUBLE,
            disk_p95_pct DOUBLE,
            disk_max_pct DOUBLE,
            cpu_forecast_30d DOUBLE,
            cpu_forecast_60d DOUBLE,
            cpu_forecast_90d DOUBLE,
            mem_forecast_30d DOUBLE,
            mem_forecast_60d DOUBLE,
            mem_forecast_90d DOUBLE,
            disk_forecast_30d DOUBLE,
            disk_forecast_60d DOUBLE,
            disk_forecast_90d DOUBLE,
            recomendacao_final VARCHAR
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS resumo_cluster (
            execution_id VARCHAR,
            cluster VARCHAR,
            total_vms INTEGER,
            p0_acao_imediata INTEGER,
            p1_alta INTEGER,
            p2_media INTEGER,
            p3_baixa INTEGER,
            p4_monitorar INTEGER,
            criticas INTEGER,
            risco_atual INTEGER,
            atencao INTEGER,
            otimizacao INTEGER,
            ok INTEGER,
            risco_futuro_30d INTEGER,
            risco_futuro_60d INTEGER,
            risco_futuro_90d INTEGER,
            score_medio DOUBLE,
            score_max DOUBLE,
            cpu_p95_medio DOUBLE,
            mem_p95_medio DOUBLE,
            disk_p95_medio DOUBLE,
            cpu_forecast_90d_medio DOUBLE,
            mem_forecast_90d_medio DOUBLE,
            disk_forecast_90d_medio DOUBLE,
            disk_forecast_90d_max DOUBLE,
            vms_prioritarias INTEGER,
            pct_vms_prioritarias DOUBLE
        )
        """
    )


def criar_tabela_historico_metricas(con):
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS historico_vm_metricas (
            execution_id VARCHAR,
            cluster VARCHAR,
            vm VARCHAR,
            vm_resource_id VARCHAR,
            date TIMESTAMP,
            recurso VARCHAR,
            used_pct DOUBLE
        )
        """
    )


def gerar_execution_id(nome_arquivo: str | Path) -> str:
    agora = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_base = Path(nome_arquivo).stem.replace(" ", "_").replace("(", "").replace(")", "")
    return f"{nome_base}_{agora}"


def salvar_execucao(
    caminho_banco: str | Path,
    df_analise_v4: pd.DataFrame,
    resumo_cluster_v04: pd.DataFrame,
    nome_arquivo: str,
    observacao: str = "",
) -> str:
    execution_id = gerar_execution_id(nome_arquivo)
    data_execucao = datetime.now()

    con = conectar_banco(caminho_banco)
    criar_tabelas_base(con)

    df_execucao = pd.DataFrame(
        [
            {
                "execution_id": execution_id,
                "nome_arquivo": str(nome_arquivo),
                "data_execucao": data_execucao,
                "total_vms": int(len(df_analise_v4)),
                "observacao": observacao,
            }
        ]
    )
    con.register("df_execucao_tmp", df_execucao)
    con.execute("INSERT INTO execucoes SELECT * FROM df_execucao_tmp")

    colunas_analise = [
        "cluster", "vm", "vm_resource_id", "categoria_vm", "status_geral",
        "status_cpu", "status_memoria", "status_disco", "risco_futuro_90d",
        "criticidade_futura", "score_prioridade", "prioridade_final", "acao_final",
        "cpu_media_pct", "cpu_p95_pct", "cpu_max_pct", "mem_media_pct",
        "mem_p95_pct", "mem_max_pct", "disk_media_pct", "disk_p95_pct",
        "disk_max_pct", "cpu_forecast_30d", "cpu_forecast_60d",
        "cpu_forecast_90d", "mem_forecast_30d", "mem_forecast_60d",
        "mem_forecast_90d", "disk_forecast_30d", "disk_forecast_60d",
        "disk_forecast_90d", "recomendacao_final",
    ]
    df_analise_salvar = df_analise_v4.copy()
    for coluna in colunas_analise:
        if coluna not in df_analise_salvar.columns:
            df_analise_salvar[coluna] = None
    df_analise_salvar = df_analise_salvar[colunas_analise]
    df_analise_salvar.insert(0, "execution_id", execution_id)
    df_analise_salvar = preparar_dataframe_para_duckdb(df_analise_salvar)

    con.register("df_analise_tmp", df_analise_salvar)
    con.execute("INSERT INTO analise_vms SELECT * FROM df_analise_tmp")

    colunas_cluster = [
        "cluster", "total_vms", "p0_acao_imediata", "p1_alta", "p2_media",
        "p3_baixa", "p4_monitorar", "criticas", "risco_atual", "atencao",
        "otimizacao", "ok", "risco_futuro_30d", "risco_futuro_60d",
        "risco_futuro_90d", "score_medio", "score_max", "cpu_p95_medio",
        "mem_p95_medio", "disk_p95_medio", "cpu_forecast_90d_medio",
        "mem_forecast_90d_medio", "disk_forecast_90d_medio",
        "disk_forecast_90d_max", "vms_prioritarias", "pct_vms_prioritarias",
    ]
    df_cluster_salvar = resumo_cluster_v04.copy()
    for coluna in colunas_cluster:
        if coluna not in df_cluster_salvar.columns:
            df_cluster_salvar[coluna] = None
    df_cluster_salvar = df_cluster_salvar[colunas_cluster]
    df_cluster_salvar.insert(0, "execution_id", execution_id)
    df_cluster_salvar = preparar_dataframe_para_duckdb(df_cluster_salvar)

    con.register("df_cluster_tmp", df_cluster_salvar)
    con.execute("INSERT INTO resumo_cluster SELECT * FROM df_cluster_tmp")
    con.close()
    return execution_id


def preparar_historico_metricas_para_banco(
    execution_id: str,
    df_cpu: pd.DataFrame,
    df_mem: pd.DataFrame,
    df_disk: pd.DataFrame,
) -> pd.DataFrame:
    historicos = []

    cpu = df_cpu.copy()
    cpu["date"] = pd.to_datetime(cpu["date"], errors="coerce")
    cpu["used_pct"] = pd.to_numeric(cpu["used_pct"], errors="coerce")
    cpu["recurso"] = "CPU"
    cpu = cpu[["cluster", "vm", "vm_resource_id", "date", "recurso", "used_pct"]].dropna(
        subset=["cluster", "vm", "vm_resource_id", "date", "used_pct"]
    )
    historicos.append(cpu)

    mem = df_mem.copy()
    mem["date"] = pd.to_datetime(mem["date"], errors="coerce")
    mem["used_pct"] = pd.to_numeric(mem["used_pct"], errors="coerce")
    mem["recurso"] = "MEMORIA"
    mem = mem[["cluster", "vm", "vm_resource_id", "date", "recurso", "used_pct"]].dropna(
        subset=["cluster", "vm", "vm_resource_id", "date", "used_pct"]
    )
    historicos.append(mem)

    disk = df_disk.copy()
    disk["date"] = pd.to_datetime(disk["date"], errors="coerce")
    disk["used_pct"] = pd.to_numeric(disk["used_pct"], errors="coerce")
    disk = disk.dropna(subset=["cluster", "vm", "vm_resource_id", "date", "used_pct"])
    disk_vm = (
        disk.groupby(["cluster", "vm", "vm_resource_id", "date"])
        .agg(used_pct=("used_pct", "max"))
        .reset_index()
    )
    disk_vm["recurso"] = "DISCO"
    disk_vm = disk_vm[["cluster", "vm", "vm_resource_id", "date", "recurso", "used_pct"]]
    historicos.append(disk_vm)

    df_hist = pd.concat(historicos, ignore_index=True)
    df_hist.insert(0, "execution_id", execution_id)
    df_hist["date"] = pd.to_datetime(df_hist["date"], errors="coerce")
    df_hist["used_pct"] = pd.to_numeric(df_hist["used_pct"], errors="coerce")
    for col in ["execution_id", "cluster", "vm", "vm_resource_id", "recurso"]:
        df_hist[col] = df_hist[col].astype(str)
    return df_hist


def salvar_historico_metricas(
    caminho_banco: str | Path,
    execution_id: str,
    df_cpu: pd.DataFrame,
    df_mem: pd.DataFrame,
    df_disk: pd.DataFrame,
):
    con = conectar_banco(caminho_banco)
    criar_tabelas_base(con)
    criar_tabela_historico_metricas(con)

    df_hist = preparar_historico_metricas_para_banco(execution_id, df_cpu, df_mem, df_disk)
    con.register("df_hist_tmp", df_hist)
    con.execute("INSERT INTO historico_vm_metricas SELECT * FROM df_hist_tmp")
    con.close()


def listar_execucoes(caminho_banco: str | Path) -> pd.DataFrame:
    con = conectar_banco(caminho_banco)
    criar_tabelas_base(con)
    df = con.execute(
        """
        SELECT execution_id, nome_arquivo, data_execucao, total_vms, observacao
        FROM execucoes
        ORDER BY data_execucao DESC
        """
    ).df()
    con.close()
    return df


def carregar_execucoes_com_label(caminho_banco: str | Path) -> pd.DataFrame:
    df = listar_execucoes(caminho_banco)
    if df.empty:
        return df
    df = df.copy()
    df["data_execucao"] = pd.to_datetime(df["data_execucao"], errors="coerce")
    df["label"] = (
        df["data_execucao"].dt.strftime("%Y-%m-%d %H:%M:%S")
        + " | "
        + df["execution_id"].astype(str)
        + " | VMs: "
        + df["total_vms"].astype(str)
    )
    return df


def carregar_analise_por_execucao(caminho_banco: str | Path, execution_id: str) -> pd.DataFrame:
    con = conectar_banco(caminho_banco)
    criar_tabelas_base(con)
    df = con.execute(
        "SELECT * FROM analise_vms WHERE execution_id = ?",
        [execution_id],
    ).df()
    con.close()
    return df


def carregar_resumo_cluster_por_execucao(caminho_banco: str | Path, execution_id: str) -> pd.DataFrame:
    con = conectar_banco(caminho_banco)
    criar_tabelas_base(con)
    df = con.execute(
        "SELECT * FROM resumo_cluster WHERE execution_id = ?",
        [execution_id],
    ).df()
    con.close()
    return df


def carregar_historico_vm(caminho_banco: str | Path, execution_id: str, vm_resource_id: str) -> pd.DataFrame:
    con = conectar_banco(caminho_banco)
    criar_tabelas_base(con)
    criar_tabela_historico_metricas(con)
    df = con.execute(
        """
        SELECT execution_id, cluster, vm, vm_resource_id, date, recurso, used_pct
        FROM historico_vm_metricas
        WHERE execution_id = ? AND vm_resource_id = ?
        ORDER BY date, recurso
        """,
        [execution_id, vm_resource_id],
    ).df()
    con.close()
    return df


def obter_ultima_execucao(caminho_banco: str | Path) -> str | None:
    execucoes = listar_execucoes(caminho_banco)
    if execucoes.empty:
        return None
    return execucoes.iloc[0]["execution_id"]


def comparar_execucoes_vms(
    caminho_banco: str | Path,
    execution_id_anterior: str,
    execution_id_atual: str,
) -> pd.DataFrame:
    df_ant = carregar_analise_por_execucao(caminho_banco, execution_id_anterior)
    df_atual = carregar_analise_por_execucao(caminho_banco, execution_id_atual)
    if df_ant.empty or df_atual.empty:
        return pd.DataFrame()

    colunas = [
        "cluster", "vm", "vm_resource_id", "categoria_vm", "status_geral",
        "prioridade_final", "acao_final", "risco_futuro_90d", "criticidade_futura",
        "score_prioridade", "cpu_p95_pct", "mem_p95_pct", "disk_p95_pct",
        "cpu_forecast_90d", "mem_forecast_90d", "disk_forecast_90d",
    ]
    for col in colunas:
        if col not in df_ant.columns:
            df_ant[col] = None
        if col not in df_atual.columns:
            df_atual[col] = None

    df_ant = df_ant[colunas].copy()
    df_atual = df_atual[colunas].copy()

    df_comp = df_ant.merge(
        df_atual,
        on="vm_resource_id",
        how="outer",
        suffixes=("_anterior", "_atual"),
        indicator=True,
    )
    df_comp["situacao_vm"] = df_comp["_merge"].map(
        {"left_only": "REMOVIDA", "right_only": "NOVA", "both": "EXISTENTE"}
    )
    df_comp["vm"] = df_comp["vm_atual"].fillna(df_comp["vm_anterior"])
    df_comp["cluster"] = df_comp["cluster_atual"].fillna(df_comp["cluster_anterior"])

    numeric_cols = [
        "score_prioridade", "cpu_p95_pct", "mem_p95_pct", "disk_p95_pct",
        "cpu_forecast_90d", "mem_forecast_90d", "disk_forecast_90d",
    ]
    for col in numeric_cols:
        a = f"{col}_anterior"
        b = f"{col}_atual"
        df_comp[a] = pd.to_numeric(df_comp[a], errors="coerce")
        df_comp[b] = pd.to_numeric(df_comp[b], errors="coerce")
        df_comp[f"delta_{col}"] = df_comp[b] - df_comp[a]

    ordem = {
        "P4_MONITORAR": 1,
        "P3_BAIXA": 2,
        "P2_MEDIA": 3,
        "P1_ALTA": 4,
        "P0_ACAO_IMEDIATA": 5,
    }
    df_comp["nivel_prioridade_anterior"] = df_comp["prioridade_final_anterior"].map(ordem)
    df_comp["nivel_prioridade_atual"] = df_comp["prioridade_final_atual"].map(ordem)
    df_comp["delta_nivel_prioridade"] = (
        df_comp["nivel_prioridade_atual"] - df_comp["nivel_prioridade_anterior"]
    )

    def classificar_mudanca(row):
        if row.get("situacao_vm") == "NOVA":
            return "VM_NOVA"
        if row.get("situacao_vm") == "REMOVIDA":
            return "VM_REMOVIDA"
        delta = row.get("delta_nivel_prioridade")
        if pd.isna(delta):
            return "SEM_COMPARACAO"
        if delta >= 2:
            return "PIOROU_MUITO"
        if delta == 1:
            return "PIOROU"
        if delta == 0:
            return "SEM_MUDANCA"
        if delta == -1:
            return "MELHOROU"
        if delta <= -2:
            return "MELHOROU_MUITO"
        return "SEM_COMPARACAO"

    df_comp["mudanca_prioridade"] = df_comp.apply(classificar_mudanca, axis=1)

    def classificar_alerta(row):
        if row.get("mudanca_prioridade") in ["PIOROU_MUITO", "PIOROU"]:
            return "ATENCAO_PRIORIDADE"
        if pd.notna(row.get("delta_score_prioridade")) and row["delta_score_prioridade"] >= 20:
            return "ATENCAO_SCORE"
        if pd.notna(row.get("delta_disk_p95_pct")) and row["delta_disk_p95_pct"] >= 10:
            return "AUMENTO_DISCO"
        if pd.notna(row.get("delta_mem_p95_pct")) and row["delta_mem_p95_pct"] >= 10:
            return "AUMENTO_MEMORIA"
        if pd.notna(row.get("delta_cpu_p95_pct")) and row["delta_cpu_p95_pct"] >= 20:
            return "AUMENTO_CPU"
        return "SEM_ALERTA"

    df_comp["alerta_comparativo"] = df_comp.apply(classificar_alerta, axis=1)
    return df_comp


def resumir_comparacao_execucoes(df_comp: pd.DataFrame) -> dict:
    if df_comp.empty:
        return {
            "total_vms_comparadas": 0,
            "vms_novas": 0,
            "vms_removidas": 0,
            "vms_existentes": 0,
            "pioraram": 0,
            "pioraram_muito": 0,
            "melhoraram": 0,
            "melhoraram_muito": 0,
            "sem_mudanca": 0,
        }
    mudancas = df_comp["mudanca_prioridade"].value_counts()
    situacoes = df_comp["situacao_vm"].value_counts()
    return {
        "total_vms_comparadas": int(len(df_comp)),
        "vms_novas": int(situacoes.get("NOVA", 0)),
        "vms_removidas": int(situacoes.get("REMOVIDA", 0)),
        "vms_existentes": int(situacoes.get("EXISTENTE", 0)),
        "pioraram": int(mudancas.get("PIOROU", 0)),
        "pioraram_muito": int(mudancas.get("PIOROU_MUITO", 0)),
        "melhoraram": int(mudancas.get("MELHOROU", 0)),
        "melhoraram_muito": int(mudancas.get("MELHOROU_MUITO", 0)),
        "sem_mudanca": int(mudancas.get("SEM_MUDANCA", 0)),
    }


def comparar_resumo_cluster(
    caminho_banco: str | Path,
    execution_id_anterior: str,
    execution_id_atual: str,
) -> pd.DataFrame:
    ant = carregar_resumo_cluster_por_execucao(caminho_banco, execution_id_anterior)
    atual = carregar_resumo_cluster_por_execucao(caminho_banco, execution_id_atual)
    if ant.empty or atual.empty:
        return pd.DataFrame()

    colunas = [
        "cluster", "total_vms", "p0_acao_imediata", "p1_alta", "p2_media",
        "p3_baixa", "p4_monitorar", "criticas", "risco_atual",
        "risco_futuro_30d", "risco_futuro_60d", "risco_futuro_90d",
        "score_medio", "score_max", "vms_prioritarias", "pct_vms_prioritarias",
    ]
    for col in colunas:
        if col not in ant.columns:
            ant[col] = None
        if col not in atual.columns:
            atual[col] = None

    comp = ant[colunas].merge(
        atual[colunas],
        on="cluster",
        how="outer",
        suffixes=("_anterior", "_atual"),
        indicator=True,
    )
    comp["situacao_cluster"] = comp["_merge"].map(
        {"left_only": "REMOVIDO", "right_only": "NOVO", "both": "EXISTENTE"}
    )

    metricas = [c for c in colunas if c != "cluster"]
    for metrica in metricas:
        a = f"{metrica}_anterior"
        b = f"{metrica}_atual"
        comp[a] = pd.to_numeric(comp[a], errors="coerce").fillna(0)
        comp[b] = pd.to_numeric(comp[b], errors="coerce").fillna(0)
        comp[f"delta_{metrica}"] = comp[b] - comp[a]

    comp = comp.sort_values(
        ["delta_vms_prioritarias", "delta_p0_acao_imediata", "delta_score_max"],
        ascending=False,
    )
    return comp
