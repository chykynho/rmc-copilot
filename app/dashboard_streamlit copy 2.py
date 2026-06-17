from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

# -----------------------------------------------------------------------------
# Ajuste de path do projeto
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from rmc_copilot.etl import carregar_aba
from rmc_copilot.parser_rmc import consolidar_metricas_vm
from rmc_copilot.analyzer import analisar_capacity_vms
from rmc_copilot.forecasting import consolidar_forecasts, adicionar_risco_futuro
from rmc_copilot.prioritization import aplicar_priorizacao_v04
from rmc_copilot.database import (
    salvar_execucao,
    listar_execucoes,
    carregar_execucoes_com_label,
    carregar_analise_por_execucao,
    carregar_resumo_cluster_por_execucao,
    obter_ultima_execucao,
    comparar_execucoes_vms,
    resumir_comparacao_execucoes,
    comparar_resumo_cluster,
)

CAMINHO_BANCO = PROJECT_ROOT / "data/database/rmc_copilot.duckdb"

# -----------------------------------------------------------------------------
# Configuração da página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="RMC Copilot",
    page_icon="📊",
    layout="wide",
)


# -----------------------------------------------------------------------------
# Estilos simples
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .main-title {
        font-size: 34px;
        font-weight: 700;
        color: #1F4E78;
        margin-bottom: 0px;
    }
    .subtitle {
        font-size: 16px;
        color: #555;
        margin-top: 0px;
        margin-bottom: 20px;
    }
    .section-title {
        font-size: 22px;
        font-weight: 700;
        color: #1F4E78;
        margin-top: 25px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Funções auxiliares
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=True)
def processar_excel(caminho_arquivo: str) -> pd.DataFrame:
    """
    Executa pipeline completo:
    Excel RMC/vROps -> métricas -> análise -> forecast -> priorização.
    """

    arquivo = Path(caminho_arquivo)

    df_vms = carregar_aba(arquivo, "VMS_SELECIONADAS")
    df_cpu = carregar_aba(arquivo, "HIST_CPU")
    df_mem = carregar_aba(arquivo, "HIST_MEM")
    df_disk = carregar_aba(arquivo, "HIST_DISK")

    df_consolidado = consolidar_metricas_vm(
        df_vms=df_vms,
        df_cpu=df_cpu,
        df_mem=df_mem,
        df_disk=df_disk,
    )

    df_analise_v2 = analisar_capacity_vms(df_consolidado)

    df_analise_v3 = consolidar_forecasts(
        df_base=df_analise_v2,
        df_cpu=df_cpu,
        df_mem=df_mem,
        df_disk=df_disk,
    )

    df_analise_v3 = adicionar_risco_futuro(df_analise_v3)

    df_analise_v4 = aplicar_priorizacao_v04(df_analise_v3)

    return df_analise_v4


def criar_resumo_cluster(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria resumo por cluster para o dashboard.

    Versão robusta:
    - Trata filtros que retornam DataFrame vazio.
    - Garante conversão numérica das colunas agregadas.
    - Evita divisão por zero.
    """

    colunas_resumo = [
        "cluster",
        "total_vms",
        "p0_acao_imediata",
        "p1_alta",
        "p2_media",
        "p3_baixa",
        "p4_monitorar",
        "criticas",
        "risco_atual",
        "atencao",
        "otimizacao",
        "ok",
        "risco_futuro_30d",
        "risco_futuro_60d",
        "risco_futuro_90d",
        "score_medio",
        "score_max",
        "cpu_p95_medio",
        "mem_p95_medio",
        "disk_p95_medio",
        "cpu_forecast_90d_medio",
        "mem_forecast_90d_medio",
        "disk_forecast_90d_medio",
        "disk_forecast_90d_max",
        "vms_prioritarias",
        "pct_vms_prioritarias",
    ]

    if df.empty:
        return pd.DataFrame(columns=colunas_resumo)

    resumo = (
        df.groupby("cluster", dropna=False)
        .agg(
            total_vms=("vm", "count"),
            p0_acao_imediata=("prioridade_final", lambda x: (x == "P0_ACAO_IMEDIATA").sum()),
            p1_alta=("prioridade_final", lambda x: (x == "P1_ALTA").sum()),
            p2_media=("prioridade_final", lambda x: (x == "P2_MEDIA").sum()),
            p3_baixa=("prioridade_final", lambda x: (x == "P3_BAIXA").sum()),
            p4_monitorar=("prioridade_final", lambda x: (x == "P4_MONITORAR").sum()),
            criticas=("status_geral", lambda x: (x == "CRITICO").sum()),
            risco_atual=("status_geral", lambda x: (x == "RISCO").sum()),
            atencao=("status_geral", lambda x: (x == "ATENCAO").sum()),
            otimizacao=("status_geral", lambda x: (x == "OTIMIZACAO").sum()),
            ok=("status_geral", lambda x: (x == "OK").sum()),
            risco_futuro_30d=("criticidade_futura", lambda x: (x == "RISCO_FUTURO_30D").sum()),
            risco_futuro_60d=("criticidade_futura", lambda x: (x == "RISCO_FUTURO_60D").sum()),
            risco_futuro_90d=("criticidade_futura", lambda x: (x == "RISCO_FUTURO_90D").sum()),
            score_medio=("score_prioridade", "mean"),
            score_max=("score_prioridade", "max"),
            cpu_p95_medio=("cpu_p95_pct", "mean"),
            mem_p95_medio=("mem_p95_pct", "mean"),
            disk_p95_medio=("disk_p95_pct", "mean"),
            cpu_forecast_90d_medio=("cpu_forecast_90d", "mean"),
            mem_forecast_90d_medio=("mem_forecast_90d", "mean"),
            disk_forecast_90d_medio=("disk_forecast_90d", "mean"),
            disk_forecast_90d_max=("disk_forecast_90d", "max"),
        )
        .reset_index()
    )

    colunas_numericas = [
        "total_vms",
        "p0_acao_imediata",
        "p1_alta",
        "p2_media",
        "p3_baixa",
        "p4_monitorar",
        "criticas",
        "risco_atual",
        "atencao",
        "otimizacao",
        "ok",
        "risco_futuro_30d",
        "risco_futuro_60d",
        "risco_futuro_90d",
        "score_medio",
        "score_max",
        "cpu_p95_medio",
        "mem_p95_medio",
        "disk_p95_medio",
        "cpu_forecast_90d_medio",
        "mem_forecast_90d_medio",
        "disk_forecast_90d_medio",
        "disk_forecast_90d_max",
    ]

    for coluna in colunas_numericas:
        if coluna in resumo.columns:
            resumo[coluna] = pd.to_numeric(resumo[coluna], errors="coerce").fillna(0)

    resumo["vms_prioritarias"] = (
        resumo["p0_acao_imediata"] + resumo["p1_alta"]
    )

    resumo["vms_prioritarias"] = pd.to_numeric(
        resumo["vms_prioritarias"],
        errors="coerce"
    ).fillna(0)

    resumo["total_vms"] = pd.to_numeric(
        resumo["total_vms"],
        errors="coerce"
    ).fillna(0)

    resumo["pct_vms_prioritarias"] = 0.0

    mascara_total = resumo["total_vms"] > 0

    resumo.loc[mascara_total, "pct_vms_prioritarias"] = (
        resumo.loc[mascara_total, "vms_prioritarias"]
        / resumo.loc[mascara_total, "total_vms"]
        * 100
    )

    resumo = resumo.sort_values(
        ["pct_vms_prioritarias", "p0_acao_imediata", "p1_alta", "score_max"],
        ascending=False,
    )

    return resumo

def gerar_resumo_textual(df: pd.DataFrame, resumo_cluster: pd.DataFrame) -> str:
    """
    Gera resumo executivo para exibição no dashboard.
    """

    total = len(df)

    prioridade_counts = df["prioridade_final"].value_counts()
    status_counts = df["status_geral"].value_counts()
    risco_counts = df["criticidade_futura"].value_counts()

    p0 = int(prioridade_counts.get("P0_ACAO_IMEDIATA", 0))
    p1 = int(prioridade_counts.get("P1_ALTA", 0))
    p2 = int(prioridade_counts.get("P2_MEDIA", 0))
    p3 = int(prioridade_counts.get("P3_BAIXA", 0))
    p4 = int(prioridade_counts.get("P4_MONITORAR", 0))

    critico = int(status_counts.get("CRITICO", 0))
    risco = int(status_counts.get("RISCO", 0))
    atencao = int(status_counts.get("ATENCAO", 0))
    otimizacao = int(status_counts.get("OTIMIZACAO", 0))
    ok = int(status_counts.get("OK", 0))
    sem_dados = int(status_counts.get("SEM_DADOS", 0))

    risco_30 = int(risco_counts.get("RISCO_FUTURO_30D", 0))
    risco_60 = int(risco_counts.get("RISCO_FUTURO_60D", 0))
    risco_90 = int(risco_counts.get("RISCO_FUTURO_90D", 0))

    top = resumo_cluster.head(3)

    linhas = []
    linhas.append(f"Foram analisadas **{total} VMs**.")
    linhas.append(
        f"A fila prioritária contém **{p0 + p1} VMs P0/P1**, sendo "
        f"**{p0} P0** e **{p1} P1**."
    )
    linhas.append(
        f"No status atual, há **{critico} críticas**, **{risco} em risco**, "
        f"**{atencao} em atenção**, **{otimizacao} candidatas a otimização**, "
        f"**{ok} OK** e **{sem_dados} sem dados**."
    )
    linhas.append(
        f"O forecast indica **{risco_30} VMs com risco em 30 dias**, "
        f"**{risco_60} em 60 dias** e **{risco_90} em 90 dias**."
    )

    linhas.append("")
    linhas.append("**Clusters mais relevantes:**")

    for _, row in top.iterrows():
        linhas.append(
            f"- **{row['cluster']}**: {row['p0_acao_imediata']} P0, "
            f"{row['p1_alta']} P1, "
            f"{row['pct_vms_prioritarias']:.1f}% de VMs prioritárias."
        )

    return "\n".join(linhas)


def filtrar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica filtros da sidebar.
    """

    st.sidebar.header("Filtros")

    clusters = sorted(df["cluster"].dropna().unique().tolist())
    categorias = sorted(df["categoria_vm"].dropna().unique().tolist())
    prioridades = sorted(df["prioridade_final"].dropna().unique().tolist())
    acoes = sorted(df["acao_final"].dropna().unique().tolist())
    riscos = sorted(df["criticidade_futura"].dropna().unique().tolist())

    filtro_cluster = st.sidebar.multiselect(
        "Cluster",
        options=clusters,
        default=[],
    )

    filtro_categoria = st.sidebar.multiselect(
        "Categoria VM",
        options=categorias,
        default=[],
    )

    filtro_prioridade = st.sidebar.multiselect(
        "Prioridade",
        options=prioridades,
        default=[],
    )

    filtro_acao = st.sidebar.multiselect(
        "Ação final",
        options=acoes,
        default=[],
    )

    filtro_risco = st.sidebar.multiselect(
        "Risco futuro",
        options=riscos,
        default=[],
    )

    if not filtro_cluster:
        filtro_cluster = clusters

    if not filtro_categoria:
        filtro_categoria = categorias

    if not filtro_prioridade:
        filtro_prioridade = prioridades

    if not filtro_acao:
        filtro_acao = acoes

    if not filtro_risco:
        filtro_risco = riscos    

    busca_vm = st.sidebar.text_input("Buscar VM", "")

    df_filtrado = df[
        df["cluster"].isin(filtro_cluster)
        & df["categoria_vm"].isin(filtro_categoria)
        & df["prioridade_final"].isin(filtro_prioridade)
        & df["acao_final"].isin(filtro_acao)
        & df["criticidade_futura"].isin(filtro_risco)
    ].copy()

    if busca_vm.strip():
        termo = busca_vm.strip().upper()
        df_filtrado = df_filtrado[
            df_filtrado["vm"].astype(str).str.upper().str.contains(termo, na=False)
        ]

    return df_filtrado


def criar_grafico_prioridade(df: pd.DataFrame):
    dados = (
        df["prioridade_final"]
        .value_counts()
        .reset_index()
    )
    dados.columns = ["prioridade_final", "quantidade"]

    ordem = [
        "P0_ACAO_IMEDIATA",
        "P1_ALTA",
        "P2_MEDIA",
        "P3_BAIXA",
        "P4_MONITORAR",
    ]

    dados["prioridade_final"] = pd.Categorical(
        dados["prioridade_final"],
        categories=ordem,
        ordered=True,
    )

    dados = dados.sort_values("prioridade_final")

    fig = px.bar(
        dados,
        x="prioridade_final",
        y="quantidade",
        title="Distribuição por prioridade final",
        text="quantidade",
    )

    fig.update_layout(
        xaxis_title="Prioridade",
        yaxis_title="Quantidade de VMs",
        height=420,
    )

    return fig


def criar_grafico_acao(df: pd.DataFrame):
    dados = (
        df["acao_final"]
        .value_counts()
        .reset_index()
    )
    dados.columns = ["acao_final", "quantidade"]

    fig = px.bar(
        dados,
        x="quantidade",
        y="acao_final",
        orientation="h",
        title="Distribuição por ação final",
        text="quantidade",
    )

    fig.update_layout(
        xaxis_title="Quantidade de VMs",
        yaxis_title="Ação final",
        height=520,
    )

    return fig


def criar_grafico_risco_futuro(df: pd.DataFrame):
    dados = (
        df["criticidade_futura"]
        .value_counts()
        .reset_index()
    )
    dados.columns = ["criticidade_futura", "quantidade"]

    ordem = [
        "RISCO_FUTURO_30D",
        "RISCO_FUTURO_60D",
        "RISCO_FUTURO_90D",
        "SEM_RISCO_FUTURO",
    ]

    dados["criticidade_futura"] = pd.Categorical(
        dados["criticidade_futura"],
        categories=ordem,
        ordered=True,
    )

    dados = dados.sort_values("criticidade_futura")

    fig = px.bar(
        dados,
        x="criticidade_futura",
        y="quantidade",
        title="Risco futuro 30/60/90 dias",
        text="quantidade",
    )

    fig.update_layout(
        xaxis_title="Risco futuro",
        yaxis_title="Quantidade de VMs",
        height=420,
    )

    return fig


def criar_grafico_top_clusters(resumo_cluster: pd.DataFrame):
    dados = resumo_cluster.head(10).copy()

    fig = px.bar(
        dados,
        x="vms_prioritarias",
        y="cluster",
        orientation="h",
        title="Top clusters por VMs P0/P1",
        text="vms_prioritarias",
        hover_data=[
            "p0_acao_imediata",
            "p1_alta",
            "pct_vms_prioritarias",
            "score_max",
        ],
    )

    fig.update_layout(
        xaxis_title="VMs prioritárias P0/P1",
        yaxis_title="Cluster",
        height=520,
        yaxis={"categoryorder": "total ascending"},
    )

    return fig


def criar_grafico_top_vms(df: pd.DataFrame):
    dados = df.sort_values("score_prioridade", ascending=False).head(30).copy()

    fig = px.bar(
        dados,
        x="score_prioridade",
        y="vm",
        orientation="h",
        color="prioridade_final",
        title="Top 30 VMs por score de prioridade",
        hover_data=[
            "cluster",
            "categoria_vm",
            "status_geral",
            "risco_futuro_90d",
            "acao_final",
        ],
    )

    fig.update_layout(
        xaxis_title="Score de prioridade",
        yaxis_title="VM",
        height=720,
        yaxis={"categoryorder": "total ascending"},
    )

    return fig


@st.cache_data(show_spinner=True)
def carregar_execucao_banco(caminho_banco: str, execution_id: str):
    """
    Carrega uma execução já processada do DuckDB.
    """
    df = carregar_analise_por_execucao(caminho_banco, execution_id)
    resumo = carregar_resumo_cluster_por_execucao(caminho_banco, execution_id)

    return df, resumo


# -----------------------------------------------------------------------------
# Interface
# -----------------------------------------------------------------------------
st.markdown('<div class="main-title">RMC Copilot</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Dashboard local de Capacity Planning VMware — v0.8</div>',
    unsafe_allow_html=True,
)

pagina = st.sidebar.radio(
    "Página",
    [
        "Dashboard operacional",
        "Comparação entre execuções",
    ],
)

# ------------------------------------------------------------------------------------------------
# Bloco da página de comparação
# ------------------------------------------------------------------------------------------------

if pagina == "Comparação entre execuções":
    st.markdown('<div class="section-title">Comparação entre execuções</div>', unsafe_allow_html=True)

    execucoes = carregar_execucoes_com_label(CAMINHO_BANCO)

    if execucoes.empty or len(execucoes) < 2:
        st.warning("É necessário ter pelo menos duas execuções salvas no DuckDB para comparar.")
        st.stop()

    label_para_id = dict(zip(execucoes["label"], execucoes["execution_id"]))

    col_a, col_b = st.columns(2)

    with col_a:
        label_anterior = st.selectbox(
            "Execução anterior",
            options=execucoes["label"].tolist(),
            index=1 if len(execucoes) > 1 else 0,
        )

    with col_b:
        label_atual = st.selectbox(
            "Execução atual",
            options=execucoes["label"].tolist(),
            index=0,
        )

    execution_id_anterior = label_para_id[label_anterior]
    execution_id_atual = label_para_id[label_atual]

    if execution_id_anterior == execution_id_atual:
        st.warning("Selecione duas execuções diferentes.")
        st.stop()

    with st.spinner("Comparando execuções..."):
        df_comp_vms = comparar_execucoes_vms(
            caminho_banco=CAMINHO_BANCO,
            execution_id_anterior=execution_id_anterior,
            execution_id_atual=execution_id_atual,
        )

        df_comp_cluster = comparar_resumo_cluster(
            caminho_banco=CAMINHO_BANCO,
            execution_id_anterior=execution_id_anterior,
            execution_id_atual=execution_id_atual,
        )

    resumo_comp = resumir_comparacao_execucoes(df_comp_vms)

    st.markdown("### Resumo da comparação")

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("VMs comparadas", resumo_comp["total_vms_comparadas"])
    c2.metric("Novas", resumo_comp["vms_novas"])
    c3.metric("Removidas", resumo_comp["vms_removidas"])
    c4.metric("Pioraram", resumo_comp["pioraram"] + resumo_comp["pioraram_muito"])
    c5.metric("Melhoraram", resumo_comp["melhoraram"] + resumo_comp["melhoraram_muito"])
    c6.metric("Sem mudança", resumo_comp["sem_mudanca"])

    st.markdown("### Mudança de prioridade")

    dados_mudanca = (
        df_comp_vms["mudanca_prioridade"]
        .value_counts()
        .reset_index()
    )
    dados_mudanca.columns = ["mudanca_prioridade", "quantidade"]

    fig_mudanca = px.bar(
        dados_mudanca,
        x="mudanca_prioridade",
        y="quantidade",
        text="quantidade",
        title="Distribuição de mudança de prioridade por VM",
    )

    fig_mudanca.update_layout(
        xaxis_title="Mudança",
        yaxis_title="Quantidade de VMs",
        height=420,
    )

    st.plotly_chart(fig_mudanca, use_container_width=True)

    st.markdown("### Clusters com maior aumento de VMs prioritárias")

    if not df_comp_cluster.empty:
        top_delta_clusters = df_comp_cluster.sort_values(
            ["delta_vms_prioritarias", "delta_p0_acao_imediata"],
            ascending=False,
        ).head(10)

        fig_cluster_delta = px.bar(
            top_delta_clusters,
            x="delta_vms_prioritarias",
            y="cluster",
            orientation="h",
            text="delta_vms_prioritarias",
            title="Top clusters por aumento de VMs P0/P1",
            hover_data=[
                "vms_prioritarias_anterior",
                "vms_prioritarias_atual",
                "delta_p0_acao_imediata",
                "delta_p1_alta",
                "delta_score_max",
            ],
        )

        fig_cluster_delta.update_layout(
            xaxis_title="Delta VMs prioritárias",
            yaxis_title="Cluster",
            height=520,
            yaxis={"categoryorder": "total ascending"},
        )

        st.plotly_chart(fig_cluster_delta, use_container_width=True)

    st.markdown("### VMs que pioraram")

    df_pioraram = df_comp_vms[
        df_comp_vms["mudanca_prioridade"].isin(["PIOROU", "PIOROU_MUITO"])
    ].copy()

    colunas_pioraram = [
        "cluster",
        "vm",
        "situacao_vm",
        "prioridade_final_anterior",
        "prioridade_final_atual",
        "mudanca_prioridade",
        "alerta_comparativo",
        "score_prioridade_anterior",
        "score_prioridade_atual",
        "delta_score_prioridade",
        "disk_p95_pct_anterior",
        "disk_p95_pct_atual",
        "delta_disk_p95_pct",
        "mem_p95_pct_anterior",
        "mem_p95_pct_atual",
        "delta_mem_p95_pct",
        "cpu_p95_pct_anterior",
        "cpu_p95_pct_atual",
        "delta_cpu_p95_pct",
    ]

    colunas_pioraram = [c for c in colunas_pioraram if c in df_pioraram.columns]

    st.dataframe(
        df_pioraram[colunas_pioraram].sort_values(
            ["delta_score_prioridade", "delta_disk_p95_pct", "delta_mem_p95_pct"],
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### VMs novas")

    df_novas = df_comp_vms[df_comp_vms["situacao_vm"] == "NOVA"].copy()

    colunas_novas = [
        "cluster",
        "vm",
        "prioridade_final_atual",
        "status_geral_atual",
        "risco_futuro_90d_atual",
        "score_prioridade_atual",
        "acao_final_atual",
        "disk_p95_pct_atual",
        "mem_p95_pct_atual",
        "cpu_p95_pct_atual",
    ]

    colunas_novas = [c for c in colunas_novas if c in df_novas.columns]

    st.dataframe(
        df_novas[colunas_novas].sort_values(
            "score_prioridade_atual",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### VMs removidas")

    df_removidas = df_comp_vms[df_comp_vms["situacao_vm"] == "REMOVIDA"].copy()

    colunas_removidas = [
        "cluster",
        "vm",
        "prioridade_final_anterior",
        "status_geral_anterior",
        "risco_futuro_90d_anterior",
        "score_prioridade_anterior",
        "acao_final_anterior",
    ]

    colunas_removidas = [c for c in colunas_removidas if c in df_removidas.columns]

    st.dataframe(
        df_removidas[colunas_removidas].sort_values(
            "score_prioridade_anterior",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Comparação por cluster")

    st.dataframe(
        df_comp_cluster,
        use_container_width=True,
        hide_index=True,
    )

    csv_comp = df_comp_vms.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Baixar comparação de VMs em CSV",
        data=csv_comp,
        file_name="rmc_copilot_comparacao_vms.csv",
        mime="text/csv",
    )

    st.stop()

# --------------------------------------------------------------------------------------------------

st.sidebar.markdown("## Fonte de dados")

arquivo_padrao = (
    PROJECT_ROOT
    / "data/raw/rmc_outputs/RMC_Recursos_VM_v5_10_2_20260610_094958.xlsx"
)

#modo = st.sidebar.radio(
#    "Como carregar os dados?",
#    ["Usar arquivo padrão", "Enviar arquivo Excel"],
#)

modo = st.sidebar.radio(
    "Como carregar os dados?",
    ["Ler última execução do banco", "Selecionar execução do banco", "Usar arquivo padrão", "Enviar arquivo Excel"],
)

arquivo_processar = None
df_analise_v4 = None
resumo_cluster_precalculado = None

if modo == "Ler última execução do banco":
    ultima_execucao = obter_ultima_execucao(CAMINHO_BANCO)

    if ultima_execucao is None:
        st.sidebar.warning("Nenhuma execução encontrada no banco. Use Excel para processar a primeira carga.")
    else:
        st.sidebar.success(f"Última execução carregada: {ultima_execucao}")

        df_analise_v4, resumo_cluster_precalculado = carregar_execucao_banco(
            str(CAMINHO_BANCO),
            ultima_execucao,
        )

elif modo == "Selecionar execução do banco":
    execucoes = listar_execucoes(CAMINHO_BANCO)

    if execucoes.empty:
        st.sidebar.warning("Nenhuma execução encontrada no banco.")
    else:
        opcoes = execucoes["execution_id"].tolist()

        execution_id_selecionado = st.sidebar.selectbox(
            "Execução",
            options=opcoes,
        )

        df_analise_v4, resumo_cluster_precalculado = carregar_execucao_banco(
            str(CAMINHO_BANCO),
            execution_id_selecionado,
        )

elif modo == "Usar arquivo padrão":
    if arquivo_padrao.exists():
        arquivo_processar = arquivo_padrao
        st.sidebar.success("Arquivo padrão encontrado.")
    else:
        st.sidebar.error(f"Arquivo padrão não encontrado: {arquivo_padrao}")

elif modo == "Enviar arquivo Excel":
    upload = st.sidebar.file_uploader(
        "Envie a saída Excel do RMC/vROps",
        type=["xlsx"],
    )

    if upload is not None:
        temp_dir = PROJECT_ROOT / "data/raw/uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)

        arquivo_temp = temp_dir / upload.name

        with open(arquivo_temp, "wb") as f:
            f.write(upload.getbuffer())

        arquivo_processar = arquivo_temp
        st.sidebar.success("Arquivo enviado com sucesso.")


if df_analise_v4 is None:
    if arquivo_processar is None:
        st.info("Selecione uma execução do banco ou envie um arquivo Excel para iniciar.")
        st.stop()

    with st.spinner("Processando dados do RMC Copilot..."):
        df_analise_v4 = processar_excel(str(arquivo_processar))

    # Recalcula resumo antes de salvar
    resumo_para_salvar = criar_resumo_cluster(df_analise_v4)

    salvar_no_banco = st.sidebar.checkbox(
        "Salvar execução no DuckDB",
        value=True,
    )

    observacao_execucao = st.sidebar.text_input(
        "Observação da execução",
        value="Carga via dashboard v0.7",
    )

    if salvar_no_banco:
        execution_id_salvo = salvar_execucao(
            caminho_banco=CAMINHO_BANCO,
            df_analise_v4=df_analise_v4,
            resumo_cluster_v04=resumo_para_salvar,
            nome_arquivo=str(arquivo_processar.name),
            observacao=observacao_execucao,
        )

        st.sidebar.success(f"Execução salva: {execution_id_salvo}")

df_filtrado = filtrar_dataframe(df_analise_v4)

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado com os filtros selecionados.")
    st.stop()

resumo_cluster = criar_resumo_cluster(df_filtrado)

# -----------------------------------------------------------------------------
# KPIs
# -----------------------------------------------------------------------------
st.markdown('<div class="section-title">KPIs principais</div>', unsafe_allow_html=True)

total = len(df_filtrado)
prioridade_counts = df_filtrado["prioridade_final"].value_counts()
criticidade_counts = df_filtrado["criticidade_futura"].value_counts()

p0 = int(prioridade_counts.get("P0_ACAO_IMEDIATA", 0))
p1 = int(prioridade_counts.get("P1_ALTA", 0))
p2 = int(prioridade_counts.get("P2_MEDIA", 0))
p3 = int(prioridade_counts.get("P3_BAIXA", 0))
p4 = int(prioridade_counts.get("P4_MONITORAR", 0))

risco_30 = int(criticidade_counts.get("RISCO_FUTURO_30D", 0))
risco_60 = int(criticidade_counts.get("RISCO_FUTURO_60D", 0))
risco_90 = int(criticidade_counts.get("RISCO_FUTURO_90D", 0))

st.markdown("### Visão geral")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(label="Total de VMs", value=f"{total:,}".replace(",", "."))

with col2:
    st.metric(label="P0 imediata", value=p0)

with col3:
    st.metric(label="P1 alta", value=p1)

with col4:
    st.metric(label="P2 média", value=p2)

with col5:
    st.metric(label="P3 baixa", value=p3)

with col6:
    st.metric(label="P4 monitorar", value=p4)

st.markdown("### Forecast de risco")

col7, col8, col9 = st.columns(3)

with col7:
    st.metric(label="Risco em 30 dias", value=risco_30)

with col8:
    st.metric(label="Risco em 60 dias", value=risco_60)

with col9:
    st.metric(label="Risco em 90 dias", value=risco_90)

# -----------------------------------------------------------------------------
# Resumo executivo
# -----------------------------------------------------------------------------
st.markdown('<div class="section-title">Resumo executivo automático</div>', unsafe_allow_html=True)

resumo_textual = gerar_resumo_textual(df_filtrado, resumo_cluster)
st.markdown(resumo_textual)

# -----------------------------------------------------------------------------
# Gráficos
# -----------------------------------------------------------------------------
st.markdown('<div class="section-title">Visão gráfica</div>', unsafe_allow_html=True)

g1, g2 = st.columns(2)

with g1:
    st.plotly_chart(criar_grafico_prioridade(df_filtrado), width="stretch")

with g2:
    st.plotly_chart(criar_grafico_risco_futuro(df_filtrado), width="stretch")

g3, g4 = st.columns(2)

with g3:
    st.plotly_chart(criar_grafico_top_clusters(resumo_cluster), width="stretch")

with g4:
    st.plotly_chart(criar_grafico_acao(df_filtrado), width="stretch")

st.plotly_chart(criar_grafico_top_vms(df_filtrado), width="stretch")

# -----------------------------------------------------------------------------
# Tabelas
# -----------------------------------------------------------------------------
st.markdown('<div class="section-title">Top clusters</div>', unsafe_allow_html=True)

st.dataframe(
    resumo_cluster,
    width="stretch",
    hide_index=True,
)

st.markdown('<div class="section-title">Top VMs priorizadas</div>', unsafe_allow_html=True)

colunas_top_vms = [
    "cluster",
    "vm",
    "categoria_vm",
    "status_geral",
    "risco_futuro_90d",
    "score_prioridade",
    "prioridade_final",
    "acao_final",
    "cpu_p95_pct",
    "mem_p95_pct",
    "disk_p95_pct",
    "cpu_forecast_90d",
    "mem_forecast_90d",
    "disk_forecast_90d",
    "recomendacao_final",
]

st.dataframe(
    df_filtrado[colunas_top_vms].sort_values("score_prioridade", ascending=False),
    width="stretch",
    hide_index=True,
)

# -----------------------------------------------------------------------------
# Download
# -----------------------------------------------------------------------------
st.markdown('<div class="section-title">Exportação opcional</div>', unsafe_allow_html=True)

csv = df_filtrado.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Baixar dados filtrados em CSV",
    data=csv,
    file_name="rmc_copilot_dados_filtrados.csv",
    mime="text/csv",
)
