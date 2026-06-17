from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    import duckdb
except Exception:
    duckdb = None


# =============================================================================
# Path do projeto
# =============================================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# Imports internos
# =============================================================================
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


# =============================================================================
# Configurações
# =============================================================================
CAMINHO_BANCO = PROJECT_ROOT / "data/database/rmc_copilot.duckdb"

ARQUIVO_PADRAO = (
    PROJECT_ROOT
    / "data/raw/rmc_outputs/RMC_Recursos_VM_v5_10_2_20260610_094958.xlsx"
)

st.set_page_config(
    page_title="BV | RMC Copilot",
    page_icon="📊",
    layout="wide",
)


# =============================================================================
# Estilo visual BV
# =============================================================================
def aplicar_estilo_bv():
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #F5F8FC;
        }

        .block-container {
            padding-top: 1.3rem;
            padding-bottom: 2rem;
        }

        .bv-header {
            background: linear-gradient(90deg, #1F3B73 0%, #2E5B9A 55%, #46B5E5 100%);
            padding: 20px 26px;
            border-radius: 18px;
            margin-bottom: 20px;
            color: white;
            box-shadow: 0 4px 16px rgba(31, 59, 115, 0.18);
        }

        .bv-title {
            font-size: 32px;
            font-weight: 800;
            margin: 0;
            letter-spacing: 0.2px;
        }

        .bv-subtitle {
            font-size: 14px;
            opacity: 0.95;
            margin-top: 5px;
        }

        .section-title {
            font-size: 22px;
            font-weight: 800;
            color: #1F3B73;
            margin-top: 26px;
            margin-bottom: 12px;
        }

        .section-subtitle {
            font-size: 14px;
            color: #5B6472;
            margin-top: -6px;
            margin-bottom: 16px;
        }

        .bv-card {
            background: #FFFFFF;
            border-radius: 18px;
            padding: 18px 18px 14px 18px;
            box-shadow: 0 4px 14px rgba(31, 59, 115, 0.08);
            border: 1px solid #E3ECF7;
            margin-bottom: 16px;
        }

        .bv-card-title {
            color: #1F3B73;
            font-weight: 800;
            font-size: 16px;
            margin-bottom: 8px;
        }

        .kpi-card {
            border-radius: 16px;
            padding: 16px 16px;
            color: white;
            box-shadow: 0 4px 12px rgba(31, 59, 115, 0.14);
            min-height: 112px;
        }

        .kpi-blue {
            background: linear-gradient(135deg, #1F3B73, #2E5B9A);
        }

        .kpi-cyan {
            background: linear-gradient(135deg, #2E86C1, #46B5E5);
        }

        .kpi-green {
            background: linear-gradient(135deg, #4FAE5A, #78C27B);
        }

        .kpi-yellow {
            background: linear-gradient(135deg, #D9A441, #E5B95C);
        }

        .kpi-orange {
            background: linear-gradient(135deg, #E67E22, #F39C12);
        }

        .kpi-red {
            background: linear-gradient(135deg, #D9534F, #E57373);
        }

        .kpi-label {
            font-size: 13px;
            font-weight: 700;
            opacity: 0.95;
            margin-bottom: 8px;
        }

        .kpi-value {
            font-size: 32px;
            font-weight: 900;
            line-height: 1.05;
        }

        .kpi-foot {
            font-size: 12px;
            margin-top: 8px;
            opacity: 0.92;
        }

        .summary-box {
            background: #FFFFFF;
            border-radius: 18px;
            padding: 18px 22px;
            border-left: 6px solid #2E5B9A;
            box-shadow: 0 4px 14px rgba(31, 59, 115, 0.08);
            color: #1F2937;
            margin-bottom: 20px;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #DDF0FB 0%, #C7E8F9 100%);
            border-right: 1px solid #D8E6F2;
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span {
            color: #1F3B73 !important;
        }

        div[data-testid="stDataFrame"] {
            background: #FFFFFF;
            border-radius: 16px;
            border: 1px solid #E3ECF7;
            padding: 8px;
            box-shadow: 0 3px 12px rgba(31, 59, 115, 0.06);
        }

        .stButton > button,
        .stDownloadButton > button {
            background: #1F3B73;
            color: white;
            border: none;
            border-radius: 11px;
            padding: 0.45rem 1rem;
            font-weight: 700;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            background: #2E5B9A;
            color: white;
        }

        div[data-baseweb="notification"] {
            border-radius: 12px;
        }

        .stSelectbox,
        .stMultiSelect,
        .stTextInput,
        .stFileUploader {
            border-radius: 12px;
        }

        hr {
            border: none;
            height: 1px;
            background: #B9D9EC;
            margin: 16px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    st.markdown(
        """
        <div class="bv-header">
            <div class="bv-title">BV | RMC Copilot</div>
            <div class="bv-subtitle">
                Capacity Planning VMware • Priorização Operacional • Forecast 30/60/90 dias • Histórico DuckDB
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(label, value, css_class="kpi-blue", foot=""):
    st.markdown(
        f"""
        <div class="kpi-card {css_class}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-foot">{foot}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def formatar_numero(valor):
    try:
        return f"{int(valor):,}".replace(",", ".")
    except Exception:
        return str(valor)


# =============================================================================
# Nomes amigáveis para métricas
# =============================================================================
NOME_PICO_USO = "Pico de uso típico"
NOME_FORECAST = "Previsão de uso"

COLUNAS_VISUAIS = {
    "cpu_p95_pct": "CPU — pico típico de uso (%)",
    "mem_p95_pct": "Memória — pico típico de uso (%)",
    "disk_p95_pct": "Disco — pico típico de uso (%)",
    "cpu_p95_medio": "CPU — pico médio por cluster (%)",
    "mem_p95_medio": "Memória — pico médio por cluster (%)",
    "disk_p95_medio": "Disco — pico médio por cluster (%)",
    "cpu_forecast_30d": "CPU — previsão 30 dias (%)",
    "cpu_forecast_60d": "CPU — previsão 60 dias (%)",
    "cpu_forecast_90d": "CPU — previsão 90 dias (%)",
    "mem_forecast_30d": "Memória — previsão 30 dias (%)",
    "mem_forecast_60d": "Memória — previsão 60 dias (%)",
    "mem_forecast_90d": "Memória — previsão 90 dias (%)",
    "disk_forecast_30d": "Disco — previsão 30 dias (%)",
    "disk_forecast_60d": "Disco — previsão 60 dias (%)",
    "disk_forecast_90d": "Disco — previsão 90 dias (%)",
    "recurso": "Recurso",
    "valor_atual": "Uso atual — pico típico (%)",
    "forecast_30d": "Previsão 30 dias (%)",
    "forecast_60d": "Previsão 60 dias (%)",
    "forecast_90d": "Previsão 90 dias (%)",
    "delta_90d": "Variação até 90 dias (p.p.)",
    "vms_acima_85_90d": "VMs previstas acima de 85% em 90 dias",
    "vms_acima_95_90d": "VMs previstas acima de 95% em 90 dias",
}


def renomear_colunas_visual(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={c: COLUNAS_VISUAIS.get(c, c) for c in df.columns})


# =============================================================================
# Pipeline
# =============================================================================
@st.cache_data(show_spinner=True)
def processar_excel(caminho_arquivo: str) -> pd.DataFrame:
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

    df_v2 = analisar_capacity_vms(df_consolidado)

    df_v3 = consolidar_forecasts(
        df_base=df_v2,
        df_cpu=df_cpu,
        df_mem=df_mem,
        df_disk=df_disk,
    )

    df_v3 = adicionar_risco_futuro(df_v3)

    df_v4 = aplicar_priorizacao_v04(df_v3)

    return df_v4


@st.cache_data(show_spinner=True)
def carregar_execucao_banco(caminho_banco: str, execution_id: str):
    df = carregar_analise_por_execucao(caminho_banco, execution_id)
    resumo = carregar_resumo_cluster_por_execucao(caminho_banco, execution_id)

    return df, resumo


# =============================================================================
# Resumos
# =============================================================================
def criar_resumo_cluster(df: pd.DataFrame) -> pd.DataFrame:
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

    colunas_numericas = [c for c in resumo.columns if c != "cluster"]

    for coluna in colunas_numericas:
        resumo[coluna] = pd.to_numeric(resumo[coluna], errors="coerce").fillna(0)

    resumo["vms_prioritarias"] = (
        resumo["p0_acao_imediata"] + resumo["p1_alta"]
    )

    resumo["pct_vms_prioritarias"] = 0.0
    mask = resumo["total_vms"] > 0

    resumo.loc[mask, "pct_vms_prioritarias"] = (
        resumo.loc[mask, "vms_prioritarias"]
        / resumo.loc[mask, "total_vms"]
        * 100
    )

    resumo = resumo.sort_values(
        ["pct_vms_prioritarias", "p0_acao_imediata", "p1_alta", "score_max"],
        ascending=False,
    )

    return resumo


def gerar_resumo_textual(df: pd.DataFrame, resumo_cluster: pd.DataFrame) -> str:
    total = len(df)

    prioridade_counts = df["prioridade_final"].value_counts()
    status_counts = df["status_geral"].value_counts()
    risco_counts = df["criticidade_futura"].value_counts()

    p0 = int(prioridade_counts.get("P0_ACAO_IMEDIATA", 0))
    p1 = int(prioridade_counts.get("P1_ALTA", 0))

    critico = int(status_counts.get("CRITICO", 0))
    risco = int(status_counts.get("RISCO", 0))
    atencao = int(status_counts.get("ATENCAO", 0))
    otimizacao = int(status_counts.get("OTIMIZACAO", 0))
    ok = int(status_counts.get("OK", 0))
    sem_dados = int(status_counts.get("SEM_DADOS", 0))

    risco_30 = int(risco_counts.get("RISCO_FUTURO_30D", 0))
    risco_60 = int(risco_counts.get("RISCO_FUTURO_60D", 0))
    risco_90 = int(risco_counts.get("RISCO_FUTURO_90D", 0))

    linhas = []
    linhas.append(
        f"Foram analisadas **{formatar_numero(total)} VMs**. "
        f"A fila prioritária contém **{formatar_numero(p0 + p1)} VMs P0/P1**, "
        f"sendo **{formatar_numero(p0)} P0** e **{formatar_numero(p1)} P1**."
    )

    linhas.append(
        f"No status atual, há **{formatar_numero(critico)} críticas**, "
        f"**{formatar_numero(risco)} em risco**, "
        f"**{formatar_numero(atencao)} em atenção**, "
        f"**{formatar_numero(otimizacao)} candidatas a otimização**, "
        f"**{formatar_numero(ok)} OK** e **{formatar_numero(sem_dados)} sem dados**."
    )

    linhas.append(
        f"O forecast indica **{formatar_numero(risco_30)} VMs com risco em 30 dias**, "
        f"**{formatar_numero(risco_60)} em 60 dias** e "
        f"**{formatar_numero(risco_90)} em 90 dias**."
    )

    if not resumo_cluster.empty:
        linhas.append("")
        linhas.append("**Clusters mais relevantes:**")

        for _, row in resumo_cluster.head(3).iterrows():
            linhas.append(
                f"- **{row['cluster']}**: "
                f"{int(row['p0_acao_imediata'])} P0, "
                f"{int(row['p1_alta'])} P1, "
                f"{row['pct_vms_prioritarias']:.1f}% de VMs prioritárias."
            )

    return "\n".join(linhas)


# =============================================================================
# Filtros
# =============================================================================
def filtrar_dataframe(df: pd.DataFrame):
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Filtros")

    recurso_selecionado = st.sidebar.radio(
        "Recurso principal",
        options=["Todos", "CPU", "Memória", "Disco"],
        index=0,
    )

    clusters = sorted(df["cluster"].dropna().unique().tolist())
    categorias = sorted(df["categoria_vm"].dropna().unique().tolist())
    prioridades = sorted(df["prioridade_final"].dropna().unique().tolist())
    acoes = sorted(df["acao_final"].dropna().unique().tolist())
    riscos = sorted(df["criticidade_futura"].dropna().unique().tolist())

    filtro_cluster = st.sidebar.multiselect("Cluster", options=clusters, default=[])
    filtro_categoria = st.sidebar.multiselect("Categoria VM", options=categorias, default=[])
    filtro_prioridade = st.sidebar.multiselect("Prioridade", options=prioridades, default=[])
    filtro_acao = st.sidebar.multiselect("Ação final", options=acoes, default=[])
    filtro_risco = st.sidebar.multiselect("Risco futuro", options=riscos, default=[])

    busca_vm = st.sidebar.text_input("Buscar VM", "")

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

    return df_filtrado, recurso_selecionado


# =============================================================================
# Gráficos
# =============================================================================
CORES_PRIORIDADE = {
    "P0_ACAO_IMEDIATA": "#D9534F",
    "P1_ALTA": "#F08A24",
    "P2_MEDIA": "#D9A441",
    "P3_BAIXA": "#46B5E5",
    "P4_MONITORAR": "#4FAE5A",
}

CORES_RISCO = {
    "RISCO_FUTURO_30D": "#D9534F",
    "RISCO_FUTURO_60D": "#F08A24",
    "RISCO_FUTURO_90D": "#D9A441",
    "SEM_RISCO_FUTURO": "#4FAE5A",
}

CORES_RECURSO = {
    "CPU": "#2E5B9A",
    "Memória": "#F08A24",
    "Disco": "#D9534F",
}


def aplicar_layout_plotly(fig, altura=420, showlegend=True):
    fig.update_layout(
        height=altura,
        paper_bgcolor="white",
        plot_bgcolor="white",
        title_font=dict(size=18, color="#1F3B73"),
        font=dict(color="#374151"),
        margin=dict(l=20, r=20, t=60, b=40),
        showlegend=showlegend,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E5EDF7")
    return fig


def criar_grafico_prioridade(df: pd.DataFrame):
    dados = df["prioridade_final"].value_counts().reset_index()
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
        color="prioridade_final",
        color_discrete_map=CORES_PRIORIDADE,
    )

    fig.update_layout(
        xaxis_title="Prioridade",
        yaxis_title="Quantidade de VMs",
    )

    return aplicar_layout_plotly(fig, altura=420, showlegend=False)


def criar_grafico_risco_futuro(df: pd.DataFrame):
    dados = df["criticidade_futura"].value_counts().reset_index()
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
        color="criticidade_futura",
        color_discrete_map=CORES_RISCO,
    )

    fig.update_layout(
        xaxis_title="Risco futuro",
        yaxis_title="Quantidade de VMs",
    )

    return aplicar_layout_plotly(fig, altura=420, showlegend=False)


def criar_grafico_acao(df: pd.DataFrame):
    dados = df["acao_final"].value_counts().reset_index()
    dados.columns = ["acao_final", "quantidade"]

    fig = px.bar(
        dados,
        x="quantidade",
        y="acao_final",
        orientation="h",
        title="Distribuição por ação final",
        text="quantidade",
        color_discrete_sequence=["#2E5B9A"],
    )

    fig.update_layout(
        xaxis_title="Quantidade de VMs",
        yaxis_title="Ação final",
        yaxis={"categoryorder": "total ascending"},
    )

    return aplicar_layout_plotly(fig, altura=560, showlegend=False)


def criar_grafico_top_clusters(resumo_cluster: pd.DataFrame):
    dados = resumo_cluster.head(10).copy()

    fig = px.bar(
        dados,
        x="vms_prioritarias",
        y="cluster",
        orientation="h",
        title="Top clusters por VMs P0/P1",
        text="vms_prioritarias",
        color="pct_vms_prioritarias",
        color_continuous_scale=["#46B5E5", "#2E5B9A", "#1F3B73"],
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
        yaxis={"categoryorder": "total ascending"},
    )

    return aplicar_layout_plotly(fig, altura=560, showlegend=False)


def criar_grafico_recursos_cluster(resumo_cluster: pd.DataFrame, recurso_selecionado: str):
    dados = resumo_cluster.head(10).copy()

    if dados.empty:
        return None

    if recurso_selecionado == "Todos":
        colunas = {
            "cpu_p95_medio": "CPU",
            "mem_p95_medio": "Memória",
            "disk_p95_medio": "Disco",
        }

        colunas_existentes = [c for c in colunas.keys() if c in dados.columns]

        if not colunas_existentes:
            return None

        dados_long = dados[["cluster"] + colunas_existentes].melt(
            id_vars="cluster",
            value_vars=colunas_existentes,
            var_name="recurso",
            value_name="p95_medio",
        )

        dados_long["recurso"] = dados_long["recurso"].map(colunas)

        fig = px.bar(
            dados_long,
            x="cluster",
            y="p95_medio",
            color="recurso",
            barmode="group",
            title="Pico de uso típico por cluster — CPU, Memória e Disco",
            color_discrete_map=CORES_RECURSO,
        )

        fig.update_layout(
            xaxis_title="Cluster",
            yaxis_title="Pico de uso típico (%)",
        )

        return aplicar_layout_plotly(fig, altura=520, showlegend=True)

    mapa = {
        "CPU": ("cpu_p95_medio", "CPU — pico de uso típico médio por cluster", "#2E5B9A"),
        "Memória": ("mem_p95_medio", "Memória — pico de uso típico médio por cluster", "#F08A24"),
        "Disco": ("disk_p95_medio", "Disco — pico de uso típico médio por cluster", "#D9534F"),
    }

    if recurso_selecionado not in mapa:
        return None

    coluna, titulo, cor = mapa[recurso_selecionado]

    if coluna not in dados.columns:
        return None

    dados = dados.sort_values(coluna, ascending=False)

    fig = px.bar(
        dados,
        x=coluna,
        y="cluster",
        orientation="h",
        title=titulo,
        text=coluna,
        color_discrete_sequence=[cor],
        hover_data=["total_vms", "vms_prioritarias", "score_max"],
    )

    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")

    fig.update_layout(
        xaxis_title="Pico de uso típico (%)",
        yaxis_title="Cluster",
        yaxis={"categoryorder": "total ascending"},
    )

    return aplicar_layout_plotly(fig, altura=560, showlegend=False)


def criar_grafico_top_vms(df: pd.DataFrame, recurso_selecionado: str = "Todos"):
    if recurso_selecionado == "CPU" and "cpu_p95_pct" in df.columns:
        coluna = "cpu_p95_pct"
        titulo = "Top 30 VMs por CPU — pico de uso típico"
        cor = "#2E5B9A"
        dados = df.sort_values(coluna, ascending=False).head(30).copy()

        fig = px.bar(
            dados,
            x=coluna,
            y="vm",
            orientation="h",
            title=titulo,
            text=coluna,
            color_discrete_sequence=[cor],
            hover_data=["cluster", "categoria_vm", "status_cpu", "cpu_forecast_90d", "acao_final"],
        )

        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(xaxis_title="CPU — pico típico de uso (%)", yaxis_title="VM", yaxis={"categoryorder": "total ascending"})
        return aplicar_layout_plotly(fig, altura=760, showlegend=False)

    if recurso_selecionado == "Memória" and "mem_p95_pct" in df.columns:
        coluna = "mem_p95_pct"
        titulo = "Top 30 VMs por Memória — pico de uso típico"
        cor = "#F08A24"
        dados = df.sort_values(coluna, ascending=False).head(30).copy()

        fig = px.bar(
            dados,
            x=coluna,
            y="vm",
            orientation="h",
            title=titulo,
            text=coluna,
            color_discrete_sequence=[cor],
            hover_data=["cluster", "categoria_vm", "status_memoria", "mem_forecast_90d", "acao_final"],
        )

        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(xaxis_title="Memória — pico típico de uso (%)", yaxis_title="VM", yaxis={"categoryorder": "total ascending"})
        return aplicar_layout_plotly(fig, altura=760, showlegend=False)

    if recurso_selecionado == "Disco" and "disk_p95_pct" in df.columns:
        coluna = "disk_p95_pct"
        titulo = "Top 30 VMs por Disco — pico de uso típico"
        cor = "#D9534F"
        dados = df.sort_values(coluna, ascending=False).head(30).copy()

        fig = px.bar(
            dados,
            x=coluna,
            y="vm",
            orientation="h",
            title=titulo,
            text=coluna,
            color_discrete_sequence=[cor],
            hover_data=["cluster", "categoria_vm", "status_disco", "disk_forecast_90d", "acao_final"],
        )

        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(xaxis_title="Disco — pico típico de uso (%)", yaxis_title="VM", yaxis={"categoryorder": "total ascending"})
        return aplicar_layout_plotly(fig, altura=760, showlegend=False)

    dados = df.sort_values("score_prioridade", ascending=False).head(30).copy()

    fig = px.bar(
        dados,
        x="score_prioridade",
        y="vm",
        orientation="h",
        color="prioridade_final",
        title="Top 30 VMs por score de prioridade",
        color_discrete_map=CORES_PRIORIDADE,
        hover_data=[
            "cluster",
            "categoria_vm",
            "status_geral",
            "risco_futuro_90d",
            "acao_final",
            "cpu_p95_pct",
            "mem_p95_pct",
            "disk_p95_pct",
        ],
    )

    fig.update_layout(
        xaxis_title="Score de prioridade",
        yaxis_title="VM",
        yaxis={"categoryorder": "total ascending"},
    )

    return aplicar_layout_plotly(fig, altura=760, showlegend=True)



def obter_mapa_recursos():
    return {
        "CPU": {
            "atual": "cpu_p95_pct",
            "f30": "cpu_forecast_30d",
            "f60": "cpu_forecast_60d",
            "f90": "cpu_forecast_90d",
            "cor": "#2E5B9A",
        },
        "Memória": {
            "atual": "mem_p95_pct",
            "f30": "mem_forecast_30d",
            "f60": "mem_forecast_60d",
            "f90": "mem_forecast_90d",
            "cor": "#F08A24",
        },
        "Disco": {
            "atual": "disk_p95_pct",
            "f30": "disk_forecast_30d",
            "f60": "disk_forecast_60d",
            "f90": "disk_forecast_90d",
            "cor": "#D9534F",
        },
    }


def calcular_tabela_forecast_30_60_90(df: pd.DataFrame, recurso_selecionado: str = "Todos") -> pd.DataFrame:
    """
    Consolida o forecast 30/60/90 dias por recurso.
    Usa média do ambiente filtrado para visão executiva.
    """

    mapa = obter_mapa_recursos()
    recursos = list(mapa.keys()) if recurso_selecionado == "Todos" else [recurso_selecionado]

    linhas = []

    for recurso in recursos:
        cfg = mapa.get(recurso)
        if not cfg:
            continue

        colunas = [cfg["atual"], cfg["f30"], cfg["f60"], cfg["f90"]]
        if not all(c in df.columns for c in colunas):
            continue

        atual = pd.to_numeric(df[cfg["atual"]], errors="coerce")
        f30 = pd.to_numeric(df[cfg["f30"]], errors="coerce")
        f60 = pd.to_numeric(df[cfg["f60"]], errors="coerce")
        f90 = pd.to_numeric(df[cfg["f90"]], errors="coerce")

        linhas.append(
            {
                "recurso": recurso,
                "valor_atual": round(float(atual.mean()), 2) if atual.notna().any() else None,
                "forecast_30d": round(float(f30.mean()), 2) if f30.notna().any() else None,
                "forecast_60d": round(float(f60.mean()), 2) if f60.notna().any() else None,
                "forecast_90d": round(float(f90.mean()), 2) if f90.notna().any() else None,
                "delta_90d": round(float(f90.mean() - atual.mean()), 2) if f90.notna().any() and atual.notna().any() else None,
                "vms_acima_85_90d": int((f90 >= 85).sum()),
                "vms_acima_95_90d": int((f90 >= 95).sum()),
            }
        )

    return pd.DataFrame(linhas)


def criar_grafico_forecast_30_60_90(df: pd.DataFrame, recurso_selecionado: str = "Todos"):
    """
    Gráfico principal de capacity planning: uso atual + previsão 30/60/90 dias.
    Quando recurso = Todos, plota CPU, Memória e Disco juntos.
    Quando recurso = CPU/Memória/Disco, plota somente o recurso selecionado.
    """

    tabela = calcular_tabela_forecast_30_60_90(df, recurso_selecionado)

    if tabela.empty:
        return None

    linhas = []
    for _, row in tabela.iterrows():
        linhas.extend(
            [
                {"recurso": row["recurso"], "periodo": "Atual", "utilizacao_pct": row["valor_atual"]},
                {"recurso": row["recurso"], "periodo": "30 dias", "utilizacao_pct": row["forecast_30d"]},
                {"recurso": row["recurso"], "periodo": "60 dias", "utilizacao_pct": row["forecast_60d"]},
                {"recurso": row["recurso"], "periodo": "90 dias", "utilizacao_pct": row["forecast_90d"]},
            ]
        )

    dados = pd.DataFrame(linhas).dropna(subset=["utilizacao_pct"])
    dados["periodo"] = pd.Categorical(
        dados["periodo"],
        categories=["Atual", "30 dias", "60 dias", "90 dias"],
        ordered=True,
    )
    dados = dados.sort_values(["recurso", "periodo"])

    titulo = "Forecast 30/60/90 dias — CPU, Memória e Disco"
    if recurso_selecionado != "Todos":
        titulo = f"Forecast 30/60/90 dias — {recurso_selecionado}"

    fig = px.line(
        dados,
        x="periodo",
        y="utilizacao_pct",
        color="recurso",
        markers=True,
        title=titulo,
        color_discrete_map=CORES_RECURSO,
    )

    fig.update_traces(line=dict(width=4), marker=dict(size=10))

    fig.add_hline(
        y=85,
        line_dash="dot",
        line_color="#D9A441",
        annotation_text="Atenção 85%",
        annotation_position="top left",
    )
    fig.add_hline(
        y=95,
        line_dash="dot",
        line_color="#D9534F",
        annotation_text="Crítico 95%",
        annotation_position="top left",
    )

    fig.update_layout(
        xaxis_title="Horizonte de previsão",
        yaxis_title="Uso previsto (%)",
        yaxis=dict(range=[0, 105]),
    )

    return aplicar_layout_plotly(fig, altura=520, showlegend=True)


def obter_colunas_top_vms(recurso_selecionado: str):
    colunas_base = [
        "cluster",
        "vm",
        "categoria_vm",
        "status_geral",
        "risco_futuro_90d",
        "score_prioridade",
        "prioridade_final",
        "acao_final",
    ]

    if recurso_selecionado == "CPU":
        colunas_recurso = [
            "status_cpu",
            "cpu_p95_pct",
            "cpu_forecast_30d",
            "cpu_forecast_60d",
            "cpu_forecast_90d",
        ]
    elif recurso_selecionado == "Memória":
        colunas_recurso = [
            "status_memoria",
            "mem_p95_pct",
            "mem_forecast_30d",
            "mem_forecast_60d",
            "mem_forecast_90d",
        ]
    elif recurso_selecionado == "Disco":
        colunas_recurso = [
            "status_disco",
            "disk_p95_pct",
            "disk_forecast_30d",
            "disk_forecast_60d",
            "disk_forecast_90d",
        ]
    else:
        colunas_recurso = [
            "cpu_p95_pct",
            "mem_p95_pct",
            "disk_p95_pct",
            "cpu_forecast_90d",
            "mem_forecast_90d",
            "disk_forecast_90d",
        ]

    return colunas_base + colunas_recurso + ["recomendacao_final"]




# =============================================================================
# Histórico, escopo e drilldown operacional
# =============================================================================
def _coluna_existente(df: pd.DataFrame, candidatos):
    if df is None or df.empty:
        return None
    mapa = {str(c).strip().lower(): c for c in df.columns}
    for c in candidatos:
        if c in df.columns:
            return c
        chave = str(c).strip().lower()
        if chave in mapa:
            return mapa[chave]
    return None


def obter_coluna_host(df: pd.DataFrame):
    return _coluna_existente(
        df,
        [
            "host",
            "Host",
            "host_name",
            "Host Name",
            "esxi",
            "ESXi",
            "mapping_parent_name",
            "parent_host",
            "nome_host",
        ],
    )


def preparar_coluna_host(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    coluna_host = obter_coluna_host(df)
    if coluna_host:
        df["host_visual"] = df[coluna_host].fillna("Host não informado").astype(str)
    else:
        df["host_visual"] = "Host não informado"
    return df


def normalizar_recurso(valor):
    texto = str(valor).strip().upper()
    if texto in ["CPU", "PROCESSADOR"] or "CPU" in texto:
        return "CPU"
    if texto in ["MEM", "MEMORIA", "MEMÓRIA", "MEMORY", "RAM"] or "MEM" in texto or "RAM" in texto:
        return "Memória"
    if texto in ["DISK", "DISCO", "STORAGE"] or "DISK" in texto or "DISCO" in texto or "STORAGE" in texto:
        return "Disco"
    return str(valor)


def normalizar_historico_recurso(df: pd.DataFrame, recurso: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    col_data = _coluna_existente(df, ["date", "data", "timestamp", "time", "datetime"])
    col_used = _coluna_existente(df, ["used_pct", "usage_pct", "valor", "value", "utilizacao_pct"])
    col_cluster = _coluna_existente(df, ["cluster", "Cluster", "cluster_name"])
    col_vm = _coluna_existente(df, ["vm", "VM", "resource", "name", "Nome VM"])
    col_id = _coluna_existente(df, ["vm_resource_id", "resource_id", "id"])
    col_host = obter_coluna_host(df)

    if col_data is None or col_used is None:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[col_data], errors="coerce")
    out["used_pct"] = pd.to_numeric(df[col_used], errors="coerce")
    out["recurso"] = recurso
    out["cluster"] = df[col_cluster].astype(str) if col_cluster else "Cluster não informado"
    out["vm"] = df[col_vm].astype(str) if col_vm else "VM não informada"
    out["vm_resource_id"] = df[col_id].astype(str) if col_id else ""
    out["host_visual"] = df[col_host].astype(str) if col_host else "Host não informado"

    out = out.dropna(subset=["date", "used_pct"])

    return out


@st.cache_data(show_spinner=False)
def carregar_historico_excel(caminho_arquivo: str) -> pd.DataFrame:
    arquivo = Path(caminho_arquivo)
    historicos = []

    try:
        df_cpu = carregar_aba(arquivo, "HIST_CPU")
        historicos.append(normalizar_historico_recurso(df_cpu, "CPU"))
    except Exception:
        pass

    try:
        df_mem = carregar_aba(arquivo, "HIST_MEM")
        historicos.append(normalizar_historico_recurso(df_mem, "Memória"))
    except Exception:
        pass

    try:
        df_disk = carregar_aba(arquivo, "HIST_DISK")
        hist_disk = normalizar_historico_recurso(df_disk, "Disco")
        if not hist_disk.empty:
            # Para disco, uma VM pode ter várias partições. Para capacity, usamos o maior uso do dia.
            chaves = ["date", "cluster", "host_visual", "vm", "vm_resource_id", "recurso"]
            hist_disk = hist_disk.groupby(chaves, dropna=False, as_index=False)["used_pct"].max()
        historicos.append(hist_disk)
    except Exception:
        pass

    historicos = [h for h in historicos if h is not None and not h.empty]
    if not historicos:
        return pd.DataFrame(columns=["date", "used_pct", "recurso", "cluster", "host_visual", "vm", "vm_resource_id"])

    return pd.concat(historicos, ignore_index=True)


def carregar_historico_banco(caminho_banco, execution_id=None) -> pd.DataFrame:
    if duckdb is None or not Path(caminho_banco).exists():
        return pd.DataFrame()

    try:
        con = duckdb.connect(str(caminho_banco), read_only=True)
        tabelas = con.execute("SHOW TABLES").fetchdf()
        nomes_tabelas = tabelas.iloc[:, 0].astype(str).tolist()
        tabela = None
        for nome in nomes_tabelas:
            if "historico" in nome.lower() or "hist" in nome.lower():
                tabela = nome
                break
        if tabela is None:
            con.close()
            return pd.DataFrame()

        cols = con.execute(f"DESCRIBE {tabela}").fetchdf()
        col_names = cols.iloc[:, 0].astype(str).tolist()

        if execution_id and "execution_id" in col_names:
            raw = con.execute(f"SELECT * FROM {tabela} WHERE execution_id = ?", [str(execution_id)]).fetchdf()
        else:
            raw = con.execute(f"SELECT * FROM {tabela}").fetchdf()
        con.close()

        if raw.empty:
            return pd.DataFrame()

        col_recurso = _coluna_existente(raw, ["recurso", "resource", "metric", "tipo_recurso"])
        if col_recurso:
            raw["__recurso_norm"] = raw[col_recurso].map(normalizar_recurso)
            partes = []
            for recurso in ["CPU", "Memória", "Disco"]:
                partes.append(normalizar_historico_recurso(raw[raw["__recurso_norm"] == recurso], recurso))
            partes = [p for p in partes if p is not None and not p.empty]
            return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()

        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def criar_resumo_host(df: pd.DataFrame) -> pd.DataFrame:
    df = preparar_coluna_host(df)
    if df.empty or "host_visual" not in df.columns:
        return pd.DataFrame()

    resumo = (
        df.groupby("host_visual", dropna=False)
        .agg(
            total_vms=("vm", "count"),
            p0_acao_imediata=("prioridade_final", lambda x: (x == "P0_ACAO_IMEDIATA").sum()),
            p1_alta=("prioridade_final", lambda x: (x == "P1_ALTA").sum()),
            score_max=("score_prioridade", "max"),
            score_medio=("score_prioridade", "mean"),
            cpu_pico_uso=("cpu_p95_pct", "mean"),
            memoria_pico_uso=("mem_p95_pct", "mean"),
            disco_pico_uso=("disk_p95_pct", "mean"),
            cpu_previsao_90d=("cpu_forecast_90d", "mean"),
            memoria_previsao_90d=("mem_forecast_90d", "mean"),
            disco_previsao_90d=("disk_forecast_90d", "mean"),
        )
        .reset_index()
        .rename(columns={"host_visual": "host"})
    )

    resumo["vms_prioritarias"] = resumo["p0_acao_imediata"] + resumo["p1_alta"]
    resumo = resumo.sort_values(["vms_prioritarias", "score_max"], ascending=False)
    return resumo


def obter_linha_grid(evento):
    try:
        linhas = evento.selection.rows
        return linhas[0] if linhas else None
    except Exception:
        pass

    try:
        linhas = evento.get("selection", {}).get("rows", [])
        return linhas[0] if linhas else None
    except Exception:
        return None


def filtrar_historico_por_escopo(df_hist: pd.DataFrame, df_scope: pd.DataFrame, tipo_escopo: str, nome_escopo: str) -> pd.DataFrame:
    if df_hist is None or df_hist.empty:
        return pd.DataFrame()

    hist = df_hist.copy()
    df_scope = preparar_coluna_host(df_scope)

    if tipo_escopo == "VM":
        ids = []
        if "vm_resource_id" in df_scope.columns:
            ids = df_scope["vm_resource_id"].dropna().astype(str).unique().tolist()
        if ids and "vm_resource_id" in hist.columns:
            return hist[hist["vm_resource_id"].astype(str).isin(ids)].copy()
        vms = df_scope["vm"].dropna().astype(str).unique().tolist()
        return hist[hist["vm"].astype(str).isin(vms)].copy()

    if tipo_escopo == "Host":
        if "host_visual" in hist.columns:
            por_host = hist[hist["host_visual"].astype(str) == str(nome_escopo)].copy()
            if not por_host.empty:
                return por_host
        vms = df_scope["vm"].dropna().astype(str).unique().tolist()
        return hist[hist["vm"].astype(str).isin(vms)].copy()

    if tipo_escopo == "Cluster":
        return hist[hist["cluster"].astype(str) == str(nome_escopo)].copy()

    vms = df_scope["vm"].dropna().astype(str).unique().tolist() if "vm" in df_scope.columns else []
    return hist[hist["vm"].astype(str).isin(vms)].copy() if vms else hist


def criar_grafico_historico_forecast_escopo(
    df_scope: pd.DataFrame,
    df_hist: pd.DataFrame,
    tipo_escopo: str,
    nome_escopo: str,
    recurso_selecionado: str = "Todos",
):
    mapa = obter_mapa_recursos()
    recursos = list(mapa.keys()) if recurso_selecionado == "Todos" else [recurso_selecionado]
    df_scope = preparar_coluna_host(df_scope)
    hist_scope = filtrar_historico_por_escopo(df_hist, df_scope, tipo_escopo, nome_escopo)

    fig = go.Figure()
    tem_dados = False

    for recurso in recursos:
        cfg = mapa.get(recurso)
        if not cfg:
            continue

        cor = cfg["cor"]
        hist_recurso = pd.DataFrame()
        if hist_scope is not None and not hist_scope.empty:
            hist_recurso = hist_scope[hist_scope["recurso"] == recurso].copy()

        ultima_data = pd.Timestamp.today().normalize()
        ultimo_valor = None

        if not hist_recurso.empty:
            serie = (
                hist_recurso.groupby("date", as_index=False)["used_pct"]
                .mean()
                .sort_values("date")
            )
            if not serie.empty:
                tem_dados = True
                ultima_data = serie["date"].max()
                ultimo_valor = float(serie.loc[serie["date"].idxmax(), "used_pct"])
                fig.add_trace(
                    go.Scatter(
                        x=serie["date"],
                        y=serie["used_pct"],
                        mode="lines",
                        name=f"{recurso} histórico",
                        line=dict(color=cor, width=2),
                    )
                )

        colunas_forecast = [cfg["atual"], cfg["f30"], cfg["f60"], cfg["f90"]]
        if all(c in df_scope.columns for c in colunas_forecast):
            atual = pd.to_numeric(df_scope[cfg["atual"]], errors="coerce").mean()
            f30 = pd.to_numeric(df_scope[cfg["f30"]], errors="coerce").mean()
            f60 = pd.to_numeric(df_scope[cfg["f60"]], errors="coerce").mean()
            f90 = pd.to_numeric(df_scope[cfg["f90"]], errors="coerce").mean()

            base = ultimo_valor if ultimo_valor is not None else atual
            pontos = [
                (ultima_data, base),
                (ultima_data + pd.Timedelta(days=30), f30),
                (ultima_data + pd.Timedelta(days=60), f60),
                (ultima_data + pd.Timedelta(days=90), f90),
            ]
            pontos = [(x, y) for x, y in pontos if pd.notna(y)]

            if len(pontos) >= 2:
                tem_dados = True
                fig.add_trace(
                    go.Scatter(
                        x=[p[0] for p in pontos],
                        y=[float(p[1]) for p in pontos],
                        mode="lines+markers",
                        name=f"{recurso} previsão 30/60/90",
                        line=dict(color=cor, width=4, dash="dash"),
                        marker=dict(size=9),
                    )
                )

    if not tem_dados:
        return None

    fig.add_hline(y=85, line_dash="dot", line_color="#D9A441", annotation_text="Atenção 85%")
    fig.add_hline(y=95, line_dash="dot", line_color="#D9534F", annotation_text="Crítico 95%")

    fig.update_layout(
        title=f"Histórico real + previsão 30/60/90 dias — {tipo_escopo}: {nome_escopo}",
        xaxis_title="Data",
        yaxis_title="Uso (%)",
        yaxis=dict(range=[0, 105]),
        hovermode="x unified",
    )

    return aplicar_layout_plotly(fig, altura=620, showlegend=True)


def criar_tabela_forecast_escopo(df_scope: pd.DataFrame, recurso_selecionado: str):
    tabela = calcular_tabela_forecast_30_60_90(df_scope, recurso_selecionado)
    return renomear_colunas_visual(tabela) if not tabela.empty else tabela




# =============================================================================
# Recursos provisionados, Top 30 clicável e Data Stores
# =============================================================================
COLUNAS_VISUAIS.update(
    {
        "host_visual": "Host",
        "vcpus_total": "vCPU total",
        "memoria_total_gb": "Memória total (GB)",
        "disco_total_gb": "Disco total (GB)",
        "cpu_alocada": "vCPU alocada",
        "memoria_alocada_gb": "Memória alocada (GB)",
        "disco_alocado_gb": "Disco alocado (GB)",
        "cpu_ocupacao_pct": "CPU — ocupação / pico típico (%)",
        "memoria_ocupacao_pct": "Memória — ocupação / pico típico (%)",
        "disco_ocupacao_pct": "Disco — ocupação / pico típico (%)",
        "datastore": "Data store",
        "datastore_total_gb": "Data store — capacidade total (GB)",
        "datastore_usado_gb": "Data store — usado (GB)",
        "datastore_livre_gb": "Data store — livre (GB)",
        "datastore_ocupacao_pct": "Data store — ocupação (%)",
    }
)


def _serie_numerica(df: pd.DataFrame, coluna):
    if coluna is None or coluna not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[coluna], errors="coerce")


def _fmt_valor(valor, unidade=""):
    if valor is None or pd.isna(valor):
        return "N/D"
    try:
        valor = float(valor)
        if abs(valor) >= 1000:
            txt = f"{valor:,.0f}".replace(",", ".")
        else:
            txt = f"{valor:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{txt}{unidade}"
    except Exception:
        return str(valor)


def obter_coluna_host_explicita(df: pd.DataFrame):
    """Host só é considerado disponível quando a coleta trouxe coluna explícita de host/ESXi."""
    return _coluna_existente(
        df,
        [
            "host",
            "Host",
            "host_name",
            "Host Name",
            "esxi",
            "ESXi",
            "parent_host",
            "nome_host",
        ],
    )


def host_esta_disponivel(df: pd.DataFrame) -> bool:
    col = obter_coluna_host_explicita(df)
    if col is None or col not in df.columns:
        return False
    valores = df[col].dropna().astype(str).str.strip()
    valores = valores[valores != ""]
    if valores.empty:
        return False
    ruins = {"host não informado", "na", "none", "null", "nan", "não informado"}
    valores_validos = [v for v in valores.unique().tolist() if v.strip().lower() not in ruins]
    return len(valores_validos) > 0


def obter_colunas_capacidade(df: pd.DataFrame):
    return {
        "cpu": _coluna_existente(
            df,
            [
                "cpu_alloc",
                "cpu_alloc_vcpu",
                "vcpus",
                "vcpu",
                "num_cpu",
                "cpu_count",
                "cpus",
                "vCPU",
                "CPU Allocated",
            ],
        ),
        "mem": _coluna_existente(
            df,
            [
                "mem_alloc_gb",
                "memory_gb",
                "mem_gb",
                "ram_gb",
                "configured_memory_gb",
                "memory_allocated_gb",
                "Memória GB",
                "Memory GB",
            ],
        ),
        "disk": _coluna_existente(
            df,
            [
                "disk_alloc_gb",
                "disk_capacity_gb",
                "capacity_gb",
                "storage_gb",
                "provisioned_gb",
                "Disco GB",
                "Disk GB",
            ],
        ),
    }


def calcular_resumo_recursos(df_scope: pd.DataFrame) -> dict:
    if df_scope is None or df_scope.empty:
        return {
            "vms": 0,
            "vcpus": None,
            "memoria_gb": None,
            "disco_gb": None,
            "cpu_pct": None,
            "mem_pct": None,
            "disk_pct": None,
        }

    cols = obter_colunas_capacidade(df_scope)

    return {
        "vms": int(len(df_scope)),
        "vcpus": _serie_numerica(df_scope, cols["cpu"]).sum(min_count=1),
        "memoria_gb": _serie_numerica(df_scope, cols["mem"]).sum(min_count=1),
        "disco_gb": _serie_numerica(df_scope, cols["disk"]).sum(min_count=1),
        "cpu_pct": _serie_numerica(df_scope, "cpu_p95_pct").mean(),
        "mem_pct": _serie_numerica(df_scope, "mem_p95_pct").mean(),
        "disk_pct": _serie_numerica(df_scope, "disk_p95_pct").mean(),
    }


def render_resumo_recursos(df_scope: pd.DataFrame, titulo: str):
    resumo = calcular_resumo_recursos(df_scope)

    st.markdown(f'<div class="section-title">{titulo}</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    with c1:
        render_kpi_card("VMs", formatar_numero(resumo["vms"]), "kpi-blue", "Quantidade")
    with c2:
        render_kpi_card("vCPU", _fmt_valor(resumo["vcpus"]), "kpi-cyan", "Provisionado")
    with c3:
        render_kpi_card("Memória", _fmt_valor(resumo["memoria_gb"], " GB"), "kpi-orange", "Provisionada")
    with c4:
        render_kpi_card("Disco", _fmt_valor(resumo["disco_gb"], " GB"), "kpi-yellow", "Provisionado")
    with c5:
        render_kpi_card("CPU", _fmt_valor(resumo["cpu_pct"], "%"), "kpi-blue", "Pico típico")
    with c6:
        render_kpi_card("Memória", _fmt_valor(resumo["mem_pct"], "%"), "kpi-orange", "Pico típico")
    with c7:
        render_kpi_card("Disco", _fmt_valor(resumo["disk_pct"], "%"), "kpi-red", "Pico típico")

    cols_cap = obter_colunas_capacidade(df_scope)
    faltantes = []
    if cols_cap["cpu"] is None:
        faltantes.append("vCPU alocada")
    if cols_cap["mem"] is None:
        faltantes.append("memória alocada")
    if cols_cap["disk"] is None:
        faltantes.append("disco provisionado/capacidade")
    if faltantes:
        st.caption("Campos de recurso não encontrados na coleta atual: " + ", ".join(faltantes) + ".")


def obter_colunas_vm_recursos(df: pd.DataFrame, recurso_selecionado: str = "Todos"):
    cols_cap = obter_colunas_capacidade(df)
    colunas = ["cluster"]
    if host_esta_disponivel(df):
        colunas.append(obter_coluna_host_explicita(df))
    colunas += ["vm", "categoria_vm", "prioridade_final", "acao_final", "score_prioridade"]

    for col in [cols_cap["cpu"], cols_cap["mem"], cols_cap["disk"]]:
        if col and col not in colunas:
            colunas.append(col)

    if recurso_selecionado == "CPU":
        colunas += ["status_cpu", "cpu_p95_pct", "cpu_forecast_30d", "cpu_forecast_60d", "cpu_forecast_90d"]
    elif recurso_selecionado == "Memória":
        colunas += ["status_memoria", "mem_p95_pct", "mem_forecast_30d", "mem_forecast_60d", "mem_forecast_90d"]
    elif recurso_selecionado == "Disco":
        colunas += ["status_disco", "disk_p95_pct", "disk_forecast_30d", "disk_forecast_60d", "disk_forecast_90d"]
    else:
        colunas += [
            "status_cpu",
            "cpu_p95_pct",
            "cpu_forecast_90d",
            "status_memoria",
            "mem_p95_pct",
            "mem_forecast_90d",
            "status_disco",
            "disk_p95_pct",
            "disk_forecast_90d",
        ]

    colunas += ["risco_futuro_90d", "recomendacao_final"]
    colunas = [c for c in colunas if c and c in df.columns]
    return list(dict.fromkeys(colunas))


def ordenar_vms_por_recurso(df: pd.DataFrame, recurso_selecionado: str):
    if recurso_selecionado == "CPU" and "cpu_p95_pct" in df.columns:
        return df.sort_values(["cpu_p95_pct", "score_prioridade"], ascending=False)
    if recurso_selecionado == "Memória" and "mem_p95_pct" in df.columns:
        return df.sort_values(["mem_p95_pct", "score_prioridade"], ascending=False)
    if recurso_selecionado == "Disco" and "disk_p95_pct" in df.columns:
        return df.sort_values(["disk_p95_pct", "score_prioridade"], ascending=False)
    return df.sort_values("score_prioridade", ascending=False)


def render_detalhe_vm_recursos(vm_df: pd.DataFrame):
    if vm_df is None or vm_df.empty:
        return

    vm = vm_df.iloc[0]
    cols_cap = obter_colunas_capacidade(vm_df)

    def valor_col(col):
        if col and col in vm_df.columns:
            return vm.get(col)
        return None

    linhas = [
        {
            "Recurso": "CPU",
            "Quantidade provisionada": _fmt_valor(valor_col(cols_cap["cpu"]), " vCPU"),
            "Uso atual — pico típico (%)": _fmt_valor(vm.get("cpu_p95_pct"), "%"),
            "Previsão 30 dias (%)": _fmt_valor(vm.get("cpu_forecast_30d"), "%"),
            "Previsão 60 dias (%)": _fmt_valor(vm.get("cpu_forecast_60d"), "%"),
            "Previsão 90 dias (%)": _fmt_valor(vm.get("cpu_forecast_90d"), "%"),
            "Status": vm.get("status_cpu", ""),
        },
        {
            "Recurso": "Memória",
            "Quantidade provisionada": _fmt_valor(valor_col(cols_cap["mem"]), " GB"),
            "Uso atual — pico típico (%)": _fmt_valor(vm.get("mem_p95_pct"), "%"),
            "Previsão 30 dias (%)": _fmt_valor(vm.get("mem_forecast_30d"), "%"),
            "Previsão 60 dias (%)": _fmt_valor(vm.get("mem_forecast_60d"), "%"),
            "Previsão 90 dias (%)": _fmt_valor(vm.get("mem_forecast_90d"), "%"),
            "Status": vm.get("status_memoria", ""),
        },
        {
            "Recurso": "Disco",
            "Quantidade provisionada": _fmt_valor(valor_col(cols_cap["disk"]), " GB"),
            "Uso atual — pico típico (%)": _fmt_valor(vm.get("disk_p95_pct"), "%"),
            "Previsão 30 dias (%)": _fmt_valor(vm.get("disk_forecast_30d"), "%"),
            "Previsão 60 dias (%)": _fmt_valor(vm.get("disk_forecast_60d"), "%"),
            "Previsão 90 dias (%)": _fmt_valor(vm.get("disk_forecast_90d"), "%"),
            "Status": vm.get("status_disco", ""),
        },
    ]

    st.markdown(f"#### Recursos da VM selecionada — {vm.get('vm', '')}")
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)

    if vm.get("recomendacao_final"):
        st.info(str(vm.get("recomendacao_final")))


def render_top30_vms_clicavel(df_scope: pd.DataFrame, recurso_selecionado: str, key: str):
    if df_scope is None or df_scope.empty:
        st.info("Nenhuma VM disponível para o escopo selecionado.")
        return None, pd.DataFrame()

    df_top = ordenar_vms_por_recurso(df_scope.copy(), recurso_selecionado).head(30).copy()
    colunas = obter_colunas_vm_recursos(df_top, recurso_selecionado)
    df_grid = df_top[colunas].copy()

    evento = st.dataframe(
        renomear_colunas_visual(df_grid),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=key,
    )

    idx = obter_linha_grid(evento)
    if idx is None or idx >= len(df_top):
        return None, df_top

    vm_linha = df_top.iloc[[idx]].copy()
    return vm_linha, df_top


def obter_colunas_datastore(df: pd.DataFrame):
    return {
        "nome": _coluna_existente(
            df,
            [
                "datastore",
                "datastore_name",
                "data_store",
                "ds_name",
                "nome_datastore",
                "Datastore",
                "Data Store",
            ],
        ),
        "capacidade": _coluna_existente(
            df,
            [
                "datastore_capacity_gb",
                "datastore_total_gb",
                "ds_capacity_gb",
                "capacity_datastore_gb",
            ],
        ),
        "usado": _coluna_existente(
            df,
            [
                "datastore_used_gb",
                "ds_used_gb",
                "used_datastore_gb",
                "datastore_usado_gb",
            ],
        ),
        "livre": _coluna_existente(
            df,
            [
                "datastore_free_gb",
                "ds_free_gb",
                "free_datastore_gb",
                "datastore_livre_gb",
            ],
        ),
        "ocupacao": _coluna_existente(
            df,
            [
                "datastore_used_pct",
                "datastore_usage_pct",
                "ds_used_pct",
                "datastore_ocupacao_pct",
            ],
        ),
    }


def render_datastores(df_scope: pd.DataFrame):
    st.markdown('<div class="section-title">Data stores</div>', unsafe_allow_html=True)

    cols = obter_colunas_datastore(df_scope)
    if cols["nome"] is None:
        st.info(
            "Data stores não aparecem porque a coleta atual não trouxe coluna de datastore. "
            "Para incluir esta visão, o coletor precisa trazer pelo menos datastore_name, "
            "datastore_capacity_gb, datastore_used_gb e/ou datastore_used_pct."
        )
        return

    df = df_scope.copy()
    df["datastore"] = df[cols["nome"]].fillna("Datastore não informado").astype(str)

    agg = {"vms": ("vm", "count")}
    if cols["capacidade"]:
        df["datastore_total_gb"] = _serie_numerica(df, cols["capacidade"])
        agg["datastore_total_gb"] = ("datastore_total_gb", "sum")
    if cols["usado"]:
        df["datastore_usado_gb"] = _serie_numerica(df, cols["usado"])
        agg["datastore_usado_gb"] = ("datastore_usado_gb", "sum")
    if cols["livre"]:
        df["datastore_livre_gb"] = _serie_numerica(df, cols["livre"])
        agg["datastore_livre_gb"] = ("datastore_livre_gb", "sum")
    if cols["ocupacao"]:
        df["datastore_ocupacao_pct"] = _serie_numerica(df, cols["ocupacao"])
        agg["datastore_ocupacao_pct"] = ("datastore_ocupacao_pct", "mean")

    resumo = df.groupby("datastore", dropna=False).agg(**agg).reset_index()
    st.dataframe(renomear_colunas_visual(resumo), use_container_width=True, hide_index=True)


# =============================================================================
# Página: Comparação entre execuções
# =============================================================================
def render_pagina_comparacao():
    st.markdown('<div class="section-title">Comparação entre execuções</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">Compare duas coletas salvas no DuckDB para identificar VMs novas, removidas, pioras, melhorias e variações por cluster.</div>',
        unsafe_allow_html=True,
    )

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

    st.markdown('<div class="section-title">Resumo da comparação</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        render_kpi_card("VMs comparadas", formatar_numero(resumo_comp["total_vms_comparadas"]), "kpi-blue", "Total")
    with c2:
        render_kpi_card("Novas", formatar_numero(resumo_comp["vms_novas"]), "kpi-cyan", "Entraram")
    with c3:
        render_kpi_card("Removidas", formatar_numero(resumo_comp["vms_removidas"]), "kpi-yellow", "Saíram")
    with c4:
        render_kpi_card("Pioraram", formatar_numero(resumo_comp["pioraram"] + resumo_comp["pioraram_muito"]), "kpi-red", "Atenção")
    with c5:
        render_kpi_card("Melhoraram", formatar_numero(resumo_comp["melhoraram"] + resumo_comp["melhoraram_muito"]), "kpi-green", "Redução")
    with c6:
        render_kpi_card("Sem mudança", formatar_numero(resumo_comp["sem_mudanca"]), "kpi-blue", "Estáveis")

    st.markdown('<div class="section-title">Mudança de prioridade</div>', unsafe_allow_html=True)

    dados_mudanca = df_comp_vms["mudanca_prioridade"].value_counts().reset_index()
    dados_mudanca.columns = ["mudanca_prioridade", "quantidade"]

    fig_mudanca = px.bar(
        dados_mudanca,
        x="mudanca_prioridade",
        y="quantidade",
        text="quantidade",
        title="Distribuição de mudança de prioridade por VM",
        color_discrete_sequence=["#2E5B9A"],
    )

    fig_mudanca.update_layout(
        xaxis_title="Mudança",
        yaxis_title="Quantidade de VMs",
    )

    st.plotly_chart(aplicar_layout_plotly(fig_mudanca, altura=420, showlegend=False), use_container_width=True)

    st.markdown('<div class="section-title">Clusters com maior aumento de VMs prioritárias</div>', unsafe_allow_html=True)

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
            color_discrete_sequence=["#1F3B73"],
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
            yaxis={"categoryorder": "total ascending"},
        )

        st.plotly_chart(aplicar_layout_plotly(fig_cluster_delta, altura=540, showlegend=False), use_container_width=True)

    st.markdown('<div class="section-title">VMs que pioraram</div>', unsafe_allow_html=True)

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

    if df_pioraram.empty:
        st.info("Nenhuma VM piorou entre as execuções selecionadas.")
    else:
        st.dataframe(
            df_pioraram[colunas_pioraram].sort_values(
                ["delta_score_prioridade", "delta_disk_p95_pct", "delta_mem_p95_pct"],
                ascending=False,
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown('<div class="section-title">VMs novas</div>', unsafe_allow_html=True)

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

    if df_novas.empty:
        st.info("Nenhuma VM nova entre as execuções selecionadas.")
    else:
        st.dataframe(
            df_novas[colunas_novas].sort_values(
                "score_prioridade_atual",
                ascending=False,
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown('<div class="section-title">VMs removidas</div>', unsafe_allow_html=True)

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

    if df_removidas.empty:
        st.info("Nenhuma VM removida entre as execuções selecionadas.")
    else:
        st.dataframe(
            df_removidas[colunas_removidas].sort_values(
                "score_prioridade_anterior",
                ascending=False,
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown('<div class="section-title">Comparação por cluster</div>', unsafe_allow_html=True)

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


# =============================================================================
# Fonte de dados
# =============================================================================
def carregar_dados_dashboard():
    st.sidebar.markdown("### Fonte de dados")

    st.session_state.setdefault("df_historico_metricas", pd.DataFrame())
    st.session_state.setdefault("execution_id_ativo", None)

    modo = st.sidebar.radio(
        "Como carregar os dados?",
        [
            "Ler última execução do banco",
            "Selecionar execução do banco",
            "Usar arquivo padrão",
            "Enviar arquivo Excel",
        ],
    )

    arquivo_processar = None
    df_analise_v4 = None

    if modo == "Ler última execução do banco":
        ultima_execucao = obter_ultima_execucao(CAMINHO_BANCO)

        if ultima_execucao is None:
            st.sidebar.warning("Nenhuma execução encontrada no banco. Use Excel para processar a primeira carga.")
        else:
            st.sidebar.success(f"Última execução carregada:\n\n{ultima_execucao}")
            df_analise_v4, _ = carregar_execucao_banco(str(CAMINHO_BANCO), ultima_execucao)
            st.session_state["execution_id_ativo"] = ultima_execucao
            st.session_state["df_historico_metricas"] = carregar_historico_banco(str(CAMINHO_BANCO), ultima_execucao)

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

            df_analise_v4, _ = carregar_execucao_banco(
                str(CAMINHO_BANCO),
                execution_id_selecionado,
            )
            st.session_state["execution_id_ativo"] = execution_id_selecionado
            st.session_state["df_historico_metricas"] = carregar_historico_banco(str(CAMINHO_BANCO), execution_id_selecionado)

    elif modo == "Usar arquivo padrão":
        if ARQUIVO_PADRAO.exists():
            arquivo_processar = ARQUIVO_PADRAO
            st.sidebar.success("Arquivo padrão encontrado.")
        else:
            st.sidebar.error(f"Arquivo padrão não encontrado: {ARQUIVO_PADRAO}")

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
            st.session_state["df_historico_metricas"] = carregar_historico_excel(str(arquivo_processar))
            st.session_state["execution_id_ativo"] = None

        resumo_para_salvar = criar_resumo_cluster(df_analise_v4)

        salvar_no_banco = st.sidebar.checkbox(
            "Salvar execução no DuckDB",
            value=True,
        )

        observacao_execucao = st.sidebar.text_input(
            "Observação da execução",
            value="Carga via dashboard",
        )

        if salvar_no_banco:
            execution_id_salvo = salvar_execucao(
                caminho_banco=CAMINHO_BANCO,
                df_analise_v4=df_analise_v4,
                resumo_cluster_v04=resumo_para_salvar,
                nome_arquivo=str(arquivo_processar.name),
                observacao=observacao_execucao,
            )
            st.session_state["execution_id_ativo"] = execution_id_salvo
            st.sidebar.success(f"Execução salva:\n\n{execution_id_salvo}")

    return preparar_coluna_host(df_analise_v4)


# =============================================================================
# Página dashboard operacional
# =============================================================================
def render_dashboard_operacional():
    df_analise_v4 = carregar_dados_dashboard()

    df_filtrado, recurso_selecionado = filtrar_dataframe(df_analise_v4)
    df_filtrado = preparar_coluna_host(df_filtrado)

    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        st.stop()

    resumo_cluster = criar_resumo_cluster(df_filtrado)

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

    st.markdown('<div class="section-title">Visão geral</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        render_kpi_card("Total de VMs", formatar_numero(total), "kpi-blue", "Ambiente analisado")
    with c2:
        render_kpi_card("P0 Imediata", formatar_numero(p0), "kpi-red", "Ação imediata")
    with c3:
        render_kpi_card("P1 Alta", formatar_numero(p1), "kpi-orange", "Curto prazo")
    with c4:
        render_kpi_card("P2 Média", formatar_numero(p2), "kpi-yellow", "Acompanhar")
    with c5:
        render_kpi_card("P3 Baixa", formatar_numero(p3), "kpi-cyan", "Otimização")
    with c6:
        render_kpi_card("P4 Monitorar", formatar_numero(p4), "kpi-green", "Baixa criticidade")

    st.markdown('<div class="section-title">Forecast de risco</div>', unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)

    with f1:
        render_kpi_card("Risco 30 dias", formatar_numero(risco_30), "kpi-red", "Atenção imediata")
    with f2:
        render_kpi_card("Risco 60 dias", formatar_numero(risco_60), "kpi-orange", "Planejamento")
    with f3:
        render_kpi_card("Risco 90 dias", formatar_numero(risco_90), "kpi-yellow", "Radar futuro")

    st.markdown('<div class="section-title">Seleção de escopo para análise</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">Escolha se quer analisar por cluster, host ou VM. Host só aparece quando a coleta trouxer coluna explícita de host/ESXi. O gráfico abaixo mostra o escopo escolhido com histórico real e previsão de 30/60/90 dias.</div>',
        unsafe_allow_html=True,
    )

    host_disponivel = host_esta_disponivel(df_filtrado)
    opcoes_escopo = ["Cluster"]
    if host_disponivel:
        opcoes_escopo.append("Host")
    opcoes_escopo.append("VM")

    tipo_drilldown = st.radio(
        "Nível de análise",
        options=opcoes_escopo,
        horizontal=True,
        index=0,
    )

    if not host_disponivel:
        st.caption("Host não será exibido porque a coleta atual não trouxe uma coluna explícita de host/ESXi. Isso evita usar mapeamento incorreto como se fosse host.")

    cluster_selecionado = None
    host_selecionado = None
    vm_selecionada = None
    df_scope = df_filtrado.copy()
    tipo_escopo = "Filtro atual"
    nome_escopo = "Todos os itens filtrados"

    if tipo_drilldown == "Cluster":
        st.markdown("#### Escolha o cluster no grid")
        col_cluster = [
            "cluster",
            "total_vms",
            "p0_acao_imediata",
            "p1_alta",
            "vms_prioritarias",
            "pct_vms_prioritarias",
            "score_max",
            "cpu_p95_medio",
            "mem_p95_medio",
            "disk_p95_medio",
        ]
        col_cluster = [c for c in col_cluster if c in resumo_cluster.columns]
        resumo_cluster_grid = resumo_cluster[col_cluster].copy()
        evento_cluster = st.dataframe(
            renomear_colunas_visual(resumo_cluster_grid),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="grid_cluster_escopo_v2",
        )
        idx_cluster = obter_linha_grid(evento_cluster)
        if idx_cluster is not None and idx_cluster < len(resumo_cluster_grid):
            cluster_selecionado = resumo_cluster_grid.iloc[idx_cluster]["cluster"]
            df_scope = df_filtrado[df_filtrado["cluster"].astype(str) == str(cluster_selecionado)].copy()
            tipo_escopo = "Cluster"
            nome_escopo = str(cluster_selecionado)
        else:
            st.info("Clique em um cluster para ver recursos totais, Top 30 VMs, histórico e forecast desse cluster.")

    elif tipo_drilldown == "Host":
        st.markdown("#### Escolha o host no grid")
        col_host_original = obter_coluna_host_explicita(df_filtrado)
        df_host_base = df_filtrado.copy()
        df_host_base["host_visual"] = df_host_base[col_host_original].fillna("Host não informado").astype(str)
        resumo_host = criar_resumo_host(df_host_base)
        col_host = [
            "host",
            "total_vms",
            "p0_acao_imediata",
            "p1_alta",
            "vms_prioritarias",
            "score_max",
            "cpu_pico_uso",
            "memoria_pico_uso",
            "disco_pico_uso",
        ]
        col_host = [c for c in col_host if c in resumo_host.columns]
        resumo_host_grid = resumo_host[col_host].copy()
        evento_host = st.dataframe(
            renomear_colunas_visual(resumo_host_grid),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="grid_host_escopo_v2",
        )
        idx_host = obter_linha_grid(evento_host)
        if idx_host is not None and idx_host < len(resumo_host_grid):
            host_selecionado = resumo_host_grid.iloc[idx_host]["host"]
            df_scope = df_host_base[df_host_base["host_visual"].astype(str) == str(host_selecionado)].copy()
            tipo_escopo = "Host"
            nome_escopo = str(host_selecionado)
        else:
            st.info("Clique em um host para ver recursos totais, Top 30 VMs, histórico e forecast desse host.")

    elif tipo_drilldown == "VM":
        st.markdown("#### Top 30 VMs — clique em uma VM")
        vm_selecionada, df_top30_vm_global = render_top30_vms_clicavel(
            df_scope=df_filtrado,
            recurso_selecionado=recurso_selecionado,
            key="grid_top30_vm_global_v2",
        )
        render_resumo_recursos(df_top30_vm_global, "Recursos das Top 30 VMs listadas")
        if vm_selecionada is not None and not vm_selecionada.empty:
            df_scope = vm_selecionada.copy()
            tipo_escopo = "VM"
            nome_escopo = str(vm_selecionada.iloc[0]["vm"])
            render_detalhe_vm_recursos(vm_selecionada)
        else:
            st.info("Clique em uma VM da Top 30 para abrir os dados de recursos, ocupação, histórico e forecast.")

    if tipo_drilldown in ["Cluster", "Host"] and not df_scope.empty and tipo_escopo in ["Cluster", "Host"]:
        render_resumo_recursos(df_scope, f"Recursos totais — {tipo_escopo}: {nome_escopo}")
        render_datastores(df_scope)

        st.markdown(f"#### Top 30 VMs dentro do escopo selecionado — {tipo_escopo}: {nome_escopo}")
        vm_top30, df_top30 = render_top30_vms_clicavel(
            df_scope=df_scope,
            recurso_selecionado=recurso_selecionado,
            key=f"grid_top30_{tipo_escopo.lower()}_v2",
        )
        render_resumo_recursos(df_top30, "Recursos das Top 30 VMs listadas")

        if vm_top30 is not None and not vm_top30.empty:
            st.success(f"VM selecionada na Top 30: {vm_top30.iloc[0]['vm']}")
            render_detalhe_vm_recursos(vm_top30)
            df_scope_grafico = vm_top30.copy()
            tipo_grafico = "VM"
            nome_grafico = str(vm_top30.iloc[0]["vm"])
        else:
            df_scope_grafico = df_scope.copy()
            tipo_grafico = tipo_escopo
            nome_grafico = nome_escopo
    else:
        df_scope_grafico = df_scope.copy()
        tipo_grafico = tipo_escopo
        nome_grafico = nome_escopo
        if tipo_escopo == "VM":
            render_datastores(df_scope_grafico)

    st.markdown(f'<div class="section-title">Histórico real + previsão 30/60/90 dias — {tipo_grafico}: {nome_grafico}</div>', unsafe_allow_html=True)

    df_historico = st.session_state.get("df_historico_metricas", pd.DataFrame())
    fig_escopo = criar_grafico_historico_forecast_escopo(
        df_scope=df_scope_grafico,
        df_hist=df_historico,
        tipo_escopo=tipo_grafico,
        nome_escopo=nome_grafico,
        recurso_selecionado=recurso_selecionado,
    )

    if fig_escopo is not None:
        st.plotly_chart(fig_escopo, use_container_width=True)
        tabela_escopo = criar_tabela_forecast_escopo(df_scope_grafico, recurso_selecionado)
        if not tabela_escopo.empty:
            st.dataframe(tabela_escopo, use_container_width=True, hide_index=True)
    else:
        st.warning("Não há histórico/forecast suficiente para montar o gráfico deste escopo.")

    if df_historico is None or df_historico.empty:
        st.info("Histórico detalhado não encontrado no banco. Para ver curva histórica completa, carregue o Excel bruto com HIST_CPU, HIST_MEM e HIST_DISK ou salve uma execução com histórico.")

    st.markdown('<div class="section-title">Resumo executivo automático</div>', unsafe_allow_html=True)

    resumo_textual = gerar_resumo_textual(df_filtrado, resumo_cluster)

    st.markdown(
        f"""
        <div class="summary-box">
        {resumo_textual}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">Visão gráfica</div>', unsafe_allow_html=True)

    g1, g2 = st.columns(2)

    with g1:
        st.plotly_chart(criar_grafico_prioridade(df_filtrado), use_container_width=True)

    with g2:
        st.plotly_chart(criar_grafico_risco_futuro(df_filtrado), use_container_width=True)

    g3, g4 = st.columns(2)

    with g3:
        st.plotly_chart(criar_grafico_top_clusters(resumo_cluster), use_container_width=True)

    with g4:
        st.plotly_chart(criar_grafico_acao(df_filtrado), use_container_width=True)

    fig_recursos = criar_grafico_recursos_cluster(resumo_cluster, recurso_selecionado)
    if fig_recursos is not None:
        st.plotly_chart(fig_recursos, use_container_width=True)

    st.plotly_chart(criar_grafico_top_vms(df_filtrado, recurso_selecionado), use_container_width=True)

    st.markdown('<div class="section-title">Exportação opcional</div>', unsafe_allow_html=True)

    csv = df_filtrado.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Baixar dados filtrados em CSV",
        data=csv,
        file_name="rmc_copilot_dados_filtrados.csv",
        mime="text/csv",
    )


# =============================================================================
# Main
# =============================================================================
def main():
    aplicar_estilo_bv()
    render_header()

    st.sidebar.markdown("## BV | RMC Copilot")
    st.sidebar.caption("Capacity Planning VMware")
    st.sidebar.markdown("---")

    st.sidebar.markdown("### Navegação")

    pagina = st.sidebar.radio(
        "Página",
        [
            "Dashboard operacional",
            "Comparação entre execuções",
        ],
        label_visibility="collapsed",
    )

    st.sidebar.markdown("---")

    if pagina == "Comparação entre execuções":
        render_pagina_comparacao()
    else:
        render_dashboard_operacional()


if __name__ == "__main__":
    main()
