from __future__ import annotations

def render_otmz_panel():
    import sys
    from pathlib import Path

    app_dir = Path(__file__).resolve().parent
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))

    try:
        from rmc_optimization_all_view import render_all_optimization_panel
        render_all_optimization_panel()
    except Exception as exc:
        import streamlit as st
        st.header("OTMZ")
        st.error("Falha ao carregar a tela OTMZ.")
        st.exception(exc)
        st.info("Erro restrito à UI. Coleta, DuckDB e credenciais não foram alterados.")
