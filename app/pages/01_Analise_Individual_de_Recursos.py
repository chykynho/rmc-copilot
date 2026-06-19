from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rmc_copilot.resource_analysis.models import ResourceAnalysisRequest
from rmc_copilot.resource_analysis.providers import MockTimeseriesProvider
from rmc_copilot.resource_analysis.duckdb_provider import (
    DuckDBTimeseriesProvider,
    register_report_artifacts,
    register_report_request,
)
from rmc_copilot.resource_analysis.stats_engine import compute_resource_stats
from rmc_copilot.resource_analysis.charts import generate_charts
from rmc_copilot.resource_analysis.narrative import deterministic_narrative, build_llm_prompt
from rmc_copilot.resource_analysis.report_builder import build_markdown_report
from rmc_copilot.resource_analysis.exporters import export_reports, make_zip_bundle
from rmc_copilot.resource_analysis.consolidated_report import ResourceAnalysisItem, export_consolidated_reports

st.set_page_config(page_title="RMC Copilot — Análise Individual", layout="wide")

BV_BLUE = "#0033A0"
BV_GREEN = "#78BE20"

st.markdown(
    f"""
    <div style="border-top:10px solid {BV_BLUE}; border-bottom:4px solid {BV_GREEN}; padding:18px 22px; background:#F2F4F7; margin-bottom:24px;">
      <div style="font-size:28px; font-weight:800; color:{BV_BLUE}; letter-spacing:1px;">BV | RMC Copilot</div>
      <div style="font-size:22px; font-weight:700; color:#1F2937;">Análise Individual de Recursos</div>
      <div style="font-size:13px; color:#4B5563; margin-top:6px;">Etapa 15-F.3 — geração de relatório usando dados reais do DuckDB oficial.</div>
    </div>
    """,
    unsafe_allow_html=True,
)


def _run_label(row: pd.Series) -> str:
    dt = pd.to_datetime(row.get("data_referencia"), errors="coerce")
    dt_txt = dt.strftime("%d/%m/%Y %H:%M") if pd.notna(dt) else "sem data"
    return f"{dt_txt} | {row.get('source_system')} | VMs: {row.get('total_vms')} | {row.get('run_id')}"


def _vm_label(row: pd.Series) -> str:
    cluster = str(row.get("cluster") or "SEM_CLUSTER")
    host = str(row.get("host") or "")
    vm = str(row.get("vm") or "")
    if host and host.lower() not in {"none", "nan"}:
        return f"{vm} | {cluster} | {host}"
    return f"{vm} | {cluster}"


def _format_mime(key: str) -> str:
    return {
        "md": "text/markdown",
        "txt": "text/plain",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
        "zip": "application/zip",
    }.get(key, "application/octet-stream")


with st.sidebar:
    st.header("Configuração")
    modo = st.selectbox("Fonte de dados", ["duckdb_oficial", "local_simulado"], index=0)
    st.caption("DuckDB oficial usa data/database/rmc_copilot.duckdb. Local simulado mantém o mock para testes rápidos.")

    selected_run_id: str | None = None
    duck_provider: DuckDBTimeseriesProvider | None = None
    if modo == "duckdb_oficial":
        duck_provider = DuckDBTimeseriesProvider()
        runs = duck_provider.list_runs()
        if runs.empty:
            st.warning("Nenhuma execução encontrada no DuckDB. Use local_simulado ou carregue a coleta vROps primeiro.")
        else:
            labels = [_run_label(r) for _, r in runs.iterrows()]
            selected = st.selectbox("Execução de coleta", labels, index=0)
            selected_run_id = str(runs.iloc[labels.index(selected)]["run_id"])
            duck_provider = DuckDBTimeseriesProvider(run_id=selected_run_id)
            st.success("DuckDB conectado")

solicitacao = st.text_input("Número da Solicitação de Serviço *", placeholder="Ex.: SOL1809645")

vm_name = ""
vm_resource_id: str | None = None
if modo == "duckdb_oficial" and duck_provider is not None and selected_run_id:
    vm_df = duck_provider.list_vms(run_id=selected_run_id)
    if vm_df.empty:
        st.error("Nenhuma VM encontrada para a execução selecionada.")
        st.stop()
    filtro_vm = st.text_input("Filtrar VM", placeholder="Digite parte do nome da VM")
    vm_filtered = vm_df.copy()
    if filtro_vm.strip():
        mask = vm_filtered["vm"].astype(str).str.contains(filtro_vm.strip(), case=False, na=False)
        vm_filtered = vm_filtered[mask].copy()
    if vm_filtered.empty:
        st.warning("Nenhuma VM encontrada com esse filtro.")
        st.stop()
    vm_filtered = vm_filtered.sort_values(["cluster", "vm"]).reset_index(drop=True)
    vm_labels = [_vm_label(r) for _, r in vm_filtered.iterrows()]
    selected_vm_label = st.selectbox("VM *", vm_labels, index=0)
    vm_row = vm_filtered.iloc[vm_labels.index(selected_vm_label)]
    vm_name = str(vm_row["vm"])
    vm_resource_id = str(vm_row["vm_resource_id"])
    st.caption(f"VM selecionada: `{vm_name}` | resource_id: `{vm_resource_id}`")
else:
    vm_examples = ["SRV-DASHPRD01", "SRV-SQLPRD01", "MOR-APPPRD01", "EQX-APPPRD01"]
    col_vm1, col_vm2 = st.columns([1, 2])
    with col_vm1:
        vm_sugestao = st.selectbox("VM de exemplo", ["Digitar manualmente"] + vm_examples, index=0)
    with col_vm2:
        default_vm = "" if vm_sugestao == "Digitar manualmente" else vm_sugestao
        vm_name = st.text_input("VM *", value=default_vm, placeholder="Ex.: SRV-DASHPRD01")

resources = st.multiselect("Recursos *", ["CPU", "MEM", "DISK"], default=["CPU", "MEM", "DISK"] if modo == "duckdb_oficial" else ["CPU"])

partitions: list[str] = []
if "DISK" in resources:
    if modo == "duckdb_oficial" and duck_provider is not None and vm_resource_id:
        parts_df = duck_provider.list_partitions(vm_resource_id=vm_resource_id, run_id=selected_run_id)
        if parts_df.empty:
            st.warning("A VM selecionada não possui partições de disco no DuckDB para essa execução.")
        else:
            part_labels = parts_df["label"].astype(str).tolist()
            default_idxs = [i for i, p in enumerate(parts_df["partition"].astype(str).tolist()) if p.upper() in {"C:", "/"}]
            default_labels = [part_labels[i] for i in default_idxs[:1]] or part_labels[:1]
            selected_parts = st.multiselect(
                "Partições de disco *",
                part_labels,
                default=default_labels,
                help="Lista real carregada do DuckDB para a VM selecionada.",
            )
            partitions = [str(parts_df.iloc[part_labels.index(lbl)]["partition"]) for lbl in selected_parts]
    else:
        partitions = st.multiselect(
            "Partições de disco *",
            ["C:", "D:", "E:", "Todas"],
            default=["C:"],
            help="Obrigatório quando DISK estiver selecionado. Use Todas para gerar C: e E: no modo simulado.",
        )
        if "Todas" in partitions:
            partitions = ["C:", "E:"]

periodo = st.selectbox("Período histórico", [30, 60, 90, 180, 365], index=2)
col1, col2 = st.columns(2)
with col1:
    solicitante = st.text_input("Solicitante", placeholder="Nome do solicitante")
with col2:
    analista = st.text_input("Analista", value="Francisco Alves")
classificacao = st.selectbox("Classificação", ["PÚBLICO", "INTERNO", "RESTRITO"], index=0)
threshold = st.number_input("Margem de segurança (%)", min_value=1.0, max_value=100.0, value=80.0, step=1.0)
format_labels = st.multiselect(
    "Formatos de saída",
    ["Markdown", "Word", "PDF"],
    default=["Markdown", "Word", "PDF"],
    help="Markdown gera .md com links relativos para a pasta graficos. Word e PDF embutem os gráficos no documento.",
)
format_map = {"Markdown": "md", "Word": "docx", "PDF": "pdf"}
selected_formats = [format_map[x] for x in format_labels]

gerar_consolidado = st.checkbox(
    "Gerar documento consolidado único quando houver mais de um recurso",
    value=True,
    help="Cria um relatório único reunindo CPU, memória e disco, com gráficos embutidos no Word/PDF.",
)

st.caption("Campos marcados com * são obrigatórios. A partição só é exigida quando o recurso DISK estiver selecionado.")

if modo == "duckdb_oficial":
    st.info(
        "CPU e MEM usam o percentual de uso vindo do vROps. DISK usa GB reais por partição quando available no DuckDB. "
        "O histórico antigo agregado permanece apenas como fallback."
    )

if st.button("Gerar relatório", type="primary"):
    if not solicitacao.strip():
        st.error("Informe o número da solicitação de serviço.")
        st.stop()
    if not vm_name.strip():
        st.error("Informe ou selecione a VM.")
        st.stop()
    if not resources:
        st.error("Selecione pelo menos um recurso.")
        st.stop()
    if not selected_formats:
        st.error("Selecione pelo menos um formato de saída.")
        st.stop()
    if "DISK" in resources and not partitions:
        st.error("Selecione pelo menos uma partição quando o recurso DISK estiver marcado.")
        st.stop()

    if modo == "duckdb_oficial":
        if not selected_run_id:
            st.error("Selecione uma execução do DuckDB.")
            st.stop()
        provider = DuckDBTimeseriesProvider(run_id=selected_run_id)
        origem = f"DuckDB oficial / run_id={selected_run_id}"
    else:
        provider = MockTimeseriesProvider()
        origem = "streamlit/local_simulado"

    generated = []
    errors: list[str] = []
    progress = st.progress(0, text="Gerando análise...")
    work_items = []
    for res in resources:
        disk_partitions = partitions if res == "DISK" else [None]
        for part in disk_partitions:
            work_items.append((res, part))

    for idx, (res, part) in enumerate(work_items, start=1):
        req = ResourceAnalysisRequest(
            solicitacao=solicitacao,
            vm=vm_name,
            resource=res,
            partition=part if res == "DISK" else None,
            periodo_dias=int(periodo),
            solicitante=solicitante,
            analista=analista,
            classificacao=classificacao,
            threshold_pct=float(threshold),
            origem=origem,
            vm_resource_id=vm_resource_id,
        )
        req_errors = req.validate()
        if req_errors:
            errors.extend(req_errors)
            continue
        try:
            usage_df, cap_df = provider.load(req)
            stats, forecast_df = compute_resource_stats(req, usage_df, cap_df)
            out_dir = ROOT / "data" / "reports" / "resource_analysis" / req.safe_solicitacao / req.safe_vm / req.safe_resource
            charts = generate_charts(req, usage_df, cap_df, stats, forecast_df, out_dir / "graficos")
            narrative = deterministic_narrative(req, stats)
            report = build_markdown_report(req, stats, narrative, charts, out_dir)
            extra_outputs = export_reports(req, stats, narrative, charts, out_dir, selected_formats)
            prompt_path = out_dir / f"{req.safe_solicitacao}_{req.safe_vm}_{req.safe_resource}_llm_prompt.txt"
            prompt_path.write_text(build_llm_prompt(req, stats), encoding="utf-8")
            generated.append((req, stats, report, charts, extra_outputs, prompt_path))
        except Exception as exc:
            errors.append(f"{res} {part or ''}: {exc}")
        progress.progress(idx / max(1, len(work_items)), text=f"Processado {idx}/{len(work_items)}")

    progress.empty()
    if errors:
        for err in errors:
            st.error(err)
    if not generated:
        st.stop()

    request_id: str | None = None
    if modo == "duckdb_oficial":
        try:
            request_id = register_report_request(
                solicitacao=solicitacao.strip().upper(),
                vm=vm_name,
                vm_resource_id=vm_resource_id,
                resources=",".join(resources),
                partitions=",".join(partitions),
                period_days=int(periodo),
                requested_by=solicitante,
                analyst=analista,
                classification=classificacao,
                source_run_id=selected_run_id,
            )
            st.caption(f"Solicitação registrada no DuckDB: `{request_id}`")
        except Exception as exc:
            st.warning(f"Relatório gerado, mas não foi possível registrar auditoria no DuckDB: {exc}")

    st.success("Relatório(s) gerado(s) com sucesso.")

    all_files: list[Path] = []
    text_files: list[Path] = []
    for req, stats, report, charts, extra_outputs, prompt_path in generated:
        st.divider()
        st.subheader(f"{req.resource_title} — {stats.diagnosis}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ação", stats.recommendation_action)
        c2.metric("Uso médio", f"{stats.mean_pct:.2f}%")
        c3.metric("P95", f"{stats.p95_pct:.2f}%")
        c4.metric("Forecast 90d", f"{stats.forecast_90_pct:.2f}%")

        files_for_this = {
            "Markdown": Path(report),
            "Texto": extra_outputs.get("txt"),
            "Word": extra_outputs.get("docx"),
            "PDF": extra_outputs.get("pdf"),
        }
        all_files.extend([Path(p) for p in files_for_this.values() if p])
        all_files.extend([Path(p) for p in charts.values()])
        text_files.extend([Path(p) for k, p in files_for_this.items() if p and k in {"Markdown", "Texto"}])

        st.write(f"Markdown gerado: `{report}`")
        cols = st.columns(4)
        for file_idx, (label, path) in enumerate(files_for_this.items()):
            if not path or not Path(path).exists():
                continue
            suffix = Path(path).suffix.lower().lstrip(".")
            with open(path, "rb") as f:
                cols[file_idx % 4].download_button(
                    label=f"Baixar {label}",
                    data=f.read(),
                    file_name=Path(path).name,
                    mime=_format_mime(suffix),
                    key=f"download_{req.safe_resource}_{label}",
                )

        with st.expander("Auditoria técnica / prompt LLM", expanded=False):
            st.caption(
                "O prompt LLM é usado apenas para rastreabilidade técnica. "
                "Ele mostra os indicadores enviados para a IA e ajuda a auditar ou ajustar a narrativa. "
                "Não faz parte da entrega operacional normal."
            )
            if prompt_path and Path(prompt_path).exists():
                with open(prompt_path, "rb") as f:
                    st.download_button(
                        label="Baixar prompt LLM",
                        data=f.read(),
                        file_name=Path(prompt_path).name,
                        mime="text/plain",
                        key=f"download_{req.safe_resource}_prompt_llm",
                    )

        chart_cols = st.columns(2)
        with chart_cols[0]:
            if charts.get("comparacao_previsao"):
                st.image(charts["comparacao_previsao"], caption="Comparação e previsão", use_container_width=True)
        with chart_cols[1]:
            if charts.get("histograma"):
                st.image(charts["histograma"], caption="Distribuição de uso", use_container_width=True)

    if generated:
        st.divider()
        st.subheader("Downloads consolidados")
        bundle_root = ROOT / "data" / "reports" / "resource_analysis" / solicitacao.strip().upper() / vm_name.strip()
        texts_zip = bundle_root / f"{solicitacao.strip().upper()}_{vm_name.strip()}_todos_os_textos.zip"
        full_zip = bundle_root / f"{solicitacao.strip().upper()}_{vm_name.strip()}_pacote_completo.zip"
        make_zip_bundle(texts_zip, text_files, bundle_root)
        make_zip_bundle(full_zip, all_files, bundle_root)
        z1, z2 = st.columns(2)
        with open(texts_zip, "rb") as f:
            z1.download_button("Baixar todos os textos (.zip)", f.read(), file_name=texts_zip.name, mime="application/zip")
        with open(full_zip, "rb") as f:
            z2.download_button("Baixar pacote completo: documentos + gráficos (.zip)", f.read(), file_name=full_zip.name, mime="application/zip")

        produced_for_audit = list(all_files) + [texts_zip, full_zip]
        if gerar_consolidado and len(generated) > 1:
            st.divider()
            st.subheader("Relatório consolidado único")
            consolidated_dir = bundle_root / "consolidado"
            items = [
                ResourceAnalysisItem(req=req, stats=stats, narrative=deterministic_narrative(req, stats), chart_paths=charts)
                for req, stats, _report, charts, _extra_outputs, _prompt_path in generated
            ]
            consolidated_outputs = export_consolidated_reports(items, consolidated_dir, selected_formats)
            ccols = st.columns(4)
            label_order = [("Markdown", "md"), ("Texto", "txt"), ("Word", "docx"), ("PDF", "pdf")]
            for out_idx, (label, key) in enumerate(label_order):
                path = consolidated_outputs.get(key)
                if not path or not Path(path).exists():
                    continue
                with open(path, "rb") as f:
                    ccols[out_idx % 4].download_button(
                        label=f"Baixar Consolidado {label}",
                        data=f.read(),
                        file_name=Path(path).name,
                        mime=_format_mime(key),
                        key=f"download_consolidado_{key}",
                    )
            consolidated_zip = bundle_root / f"{solicitacao.strip().upper()}_{vm_name.strip()}_relatorio_consolidado.zip"
            consolidated_all_files = [Path(p) for p in consolidated_outputs.values()]
            for _, _, _, charts, _, _ in generated:
                consolidated_all_files.extend([Path(p) for p in charts.values()])
            make_zip_bundle(consolidated_zip, consolidated_all_files, bundle_root)
            with open(consolidated_zip, "rb") as f:
                st.download_button(
                    "Baixar consolidado completo (.zip)",
                    f.read(),
                    file_name=consolidated_zip.name,
                    mime="application/zip",
                )
            produced_for_audit.extend(consolidated_all_files + [consolidated_zip])
        elif gerar_consolidado:
            st.info("O relatório consolidado único é gerado quando há mais de um recurso/partição na seleção.")

        with st.expander("Auditoria técnica consolidada", expanded=False):
            prompt_files = [Path(p) for _, _, _, _, _, p in generated if p and Path(p).exists()]
            if prompt_files:
                prompts_zip = bundle_root / f"{solicitacao.strip().upper()}_{vm_name.strip()}_prompts_llm_auditoria.zip"
                make_zip_bundle(prompts_zip, prompt_files, bundle_root)
                produced_for_audit.append(prompts_zip)
                with open(prompts_zip, "rb") as f:
                    st.download_button("Baixar prompts LLM de auditoria (.zip)", f.read(), file_name=prompts_zip.name, mime="application/zip")
            else:
                st.info("Nenhum prompt LLM de auditoria foi gerado.")

        if modo == "duckdb_oficial" and request_id:
            try:
                count = register_report_artifacts(
                    request_id=request_id,
                    solicitacao=solicitacao.strip().upper(),
                    vm=vm_name,
                    artifact_paths=produced_for_audit,
                )
                st.caption(f"Artefatos registrados no DuckDB: {count}")
            except Exception as exc:
                st.warning(f"Não foi possível registrar artefatos no DuckDB: {exc}")

st.markdown("---")
st.caption("RMC Copilot — Análise Individual conectada ao DuckDB oficial. Excel permanece apenas como exportação/auditoria.")
