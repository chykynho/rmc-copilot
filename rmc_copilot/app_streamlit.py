import sys
import os

# Adicionar o diretório pai ao path para que o módulo rmc_copilot seja encontrado
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd

from rmc_copilot.metrics import resumo_estatistico_vm
from rmc_copilot.analyzer import analisar_vms
from rmc_copilot.analyzer import gerar_recomendacao_vm


st.set_page_config(
    page_title="RMC Copilot",
    layout="wide"
)

st.title("RMC Copilot — Capacity Planning VMware")

arquivo = st.file_uploader("Envie a planilha PAC/RMC", type=["xlsx"])

if arquivo:
    xls = pd.ExcelFile(arquivo)
    aba = st.selectbox("Selecione a aba", xls.sheet_names)

    df = pd.read_excel(arquivo, sheet_name=aba)
    st.subheader("Prévia dos dados")
    st.dataframe(df.head())

    st.warning("Nesta primeira versão, selecione manualmente as colunas.")

    coluna_vm = st.selectbox("Coluna da VM", df.columns)
    coluna_cpu = st.selectbox("Coluna CPU %", df.columns)
    coluna_memoria = st.selectbox("Coluna Memória %", df.columns)
    coluna_disco = st.selectbox("Coluna Disco %", df.columns)

    if st.button("Analisar VMs"):
        resumo = resumo_estatistico_vm(
            df=df,
            coluna_vm=coluna_vm,
            coluna_cpu=coluna_cpu,
            coluna_memoria=coluna_memoria,
            coluna_disco=coluna_disco
        )

        analise = analisar_vms(resumo)
        analise["recomendacao"] = analise.apply(gerar_recomendacao_vm, axis=1)

        st.subheader("Resultado da análise")
        st.dataframe(analise)