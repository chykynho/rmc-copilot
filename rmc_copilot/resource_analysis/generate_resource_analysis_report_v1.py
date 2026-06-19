from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Permite executar diretamente no projeto sem instalar pacote
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rmc_copilot.resource_analysis.models import ResourceAnalysisRequest
from rmc_copilot.resource_analysis.data_loader import load_vrops_metric_csv, filter_period
from rmc_copilot.resource_analysis.providers import LegacyMetricChartProvider, MockTimeseriesProvider
from rmc_copilot.resource_analysis.stats_engine import compute_resource_stats
from rmc_copilot.resource_analysis.charts import generate_charts
from rmc_copilot.resource_analysis.narrative import deterministic_narrative, build_llm_prompt
from rmc_copilot.resource_analysis.report_builder import build_markdown_report
from rmc_copilot.resource_analysis.exporters import export_reports, make_zip_bundle, parse_formats


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gera relatório de análise individual de recursos do RMC Copilot.")
    p.add_argument("--solicitacao", required=True, help="Número da solicitação, ex.: SOL1809645")
    p.add_argument("--vm", required=True, help="Nome da VM")
    p.add_argument("--resource", required=True, choices=["CPU", "MEM", "DSK", "DISK", "Partition"], help="Recurso a analisar")
    p.add_argument("--partition", default="", help="Partição quando recurso for DISK/DSK, ex.: C ou E")
    p.add_argument("--periodo-dias", type=int, default=90, help="Período histórico em dias")
    p.add_argument("--solicitante", default="", help="Nome do solicitante")
    p.add_argument("--analista", default="", help="Nome do analista")
    p.add_argument("--classificacao", default="PÚBLICO", help="Classificação do relatório")
    p.add_argument("--threshold-pct", type=float, default=80.0, help="Margem de segurança em percentual")
    p.add_argument("--usage-csv", default="", help="CSV de uso já exportado/normalizado ou vROps MetricChart")
    p.add_argument("--capacity-csv", default="", help="CSV de capacidade total já exportado/normalizado ou vROps MetricChart")
    p.add_argument("--legacy-dir", default="", help="Diretório com arquivos MetricChart_* do modelo antigo")
    p.add_argument("--mock", action="store_true", help="Usa série simulada para teste no PC particular")
    p.add_argument("--out-dir", default="data/reports/resource_analysis", help="Diretório raiz de saída")
    p.add_argument("--save-prompt", action="store_true", help="Salva prompt da LLM para auditoria")
    p.add_argument("--formats", default="md", help="Formatos de saída: md,docx,pdf. Ex.: --formats md,docx,pdf")
    p.add_argument("--zip", action="store_true", help="Gera pacote ZIP com documentos, textos e gráficos.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    req = ResourceAnalysisRequest(
        solicitacao=args.solicitacao,
        vm=args.vm,
        resource=args.resource,
        partition=args.partition,
        periodo_dias=args.periodo_dias,
        solicitante=args.solicitante,
        analista=args.analista,
        classificacao=args.classificacao,
        threshold_pct=args.threshold_pct,
    )
    errors = req.validate()
    if errors:
        for e in errors:
            print(f"ERRO: {e}")
        return 2

    if args.mock:
        usage_df, capacity_df = MockTimeseriesProvider().load(req)
        origem = "mock/local_simulado"
    elif args.usage_csv and args.capacity_csv:
        usage_df = filter_period(load_vrops_metric_csv(args.usage_csv), req.periodo_dias)
        capacity_df = filter_period(load_vrops_metric_csv(args.capacity_csv), req.periodo_dias)
        origem = f"usage={args.usage_csv}; capacity={args.capacity_csv}"
    elif args.legacy_dir:
        usage_df, capacity_df = LegacyMetricChartProvider(args.legacy_dir).load(req)
        origem = f"legacy_dir={args.legacy_dir}"
    else:
        print("ERRO: informe --mock, ou --usage-csv + --capacity-csv, ou --legacy-dir.")
        return 2
    req.origem = origem

    base_out = Path(args.out_dir) / req.safe_solicitacao / req.safe_vm / req.safe_resource
    charts_dir = base_out / "graficos"
    base_out.mkdir(parents=True, exist_ok=True)

    stats, forecast_df = compute_resource_stats(req, usage_df, capacity_df)
    chart_paths = generate_charts(req, usage_df, capacity_df, stats, forecast_df, charts_dir)
    narrative = deterministic_narrative(req, stats)
    requested_formats = parse_formats(args.formats)
    report_path = build_markdown_report(req, stats, narrative, chart_paths, base_out)
    generated_files = {"md": report_path}
    generated_files.update(export_reports(req, stats, narrative, chart_paths, base_out, requested_formats))

    prompt_path = None
    if args.save_prompt:
        prompt_path = base_out / f"{req.safe_solicitacao}_{req.safe_vm}_{req.safe_resource}_llm_prompt.txt"
        prompt_path.write_text(build_llm_prompt(req, stats), encoding="utf-8")
        generated_files["prompt"] = prompt_path

    if args.zip:
        zip_files = list(generated_files.values()) + [Path(p) for p in chart_paths.values()]
        zip_path = base_out / f"{req.safe_solicitacao}_{req.safe_vm}_{req.safe_resource}_pacote_completo.zip"
        make_zip_bundle(zip_path, zip_files, base_out)
        generated_files["zip"] = zip_path

    print("=== RELATÓRIO DE ANÁLISE INDIVIDUAL GERADO ===")
    print(f"Solicitação: {req.solicitacao}")
    print(f"VM: {req.vm}")
    print(f"Recurso: {req.resource_title}")
    print(f"Diagnóstico: {stats.diagnosis}")
    print(f"Ação: {stats.recommendation_action}")
    print(f"Relatório Markdown: {report_path}")
    for fmt, path in generated_files.items():
        if fmt != "md":
            print(f"Arquivo {fmt.upper()}: {path}")
    print(f"Gráficos: {charts_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
