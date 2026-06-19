from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rmc_copilot.resource_analysis.models import ResourceAnalysisRequest
from rmc_copilot.resource_analysis.providers import MockTimeseriesProvider
from rmc_copilot.resource_analysis.stats_engine import compute_resource_stats
from rmc_copilot.resource_analysis.charts import generate_charts
from rmc_copilot.resource_analysis.narrative import deterministic_narrative, build_llm_prompt
from rmc_copilot.resource_analysis.report_builder import build_markdown_report
from rmc_copilot.resource_analysis.exporters import export_reports, make_zip_bundle, parse_formats
from rmc_copilot.resource_analysis.consolidated_report import ResourceAnalysisItem, export_consolidated_reports


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gera relatório consolidado de análise individual de recursos do RMC Copilot.")
    p.add_argument("--solicitacao", required=True, help="Número da solicitação, ex.: SOL1809645")
    p.add_argument("--vm", required=True, help="Nome da VM")
    p.add_argument("--resources", default="CPU,MEM,DISK", help="Recursos separados por vírgula. Ex.: CPU,MEM,DISK")
    p.add_argument("--partitions", default="C:,E:", help="Partições quando DISK for usado. Ex.: C:,E:")
    p.add_argument("--periodo", "--periodo-dias", dest="periodo_dias", type=int, default=90, help="Período histórico em dias")
    p.add_argument("--solicitante", default="", help="Nome do solicitante")
    p.add_argument("--analista", default="", help="Nome do analista")
    p.add_argument("--classificacao", default="PÚBLICO", help="Classificação do relatório")
    p.add_argument("--threshold-pct", type=float, default=80.0, help="Margem de segurança em percentual")
    p.add_argument("--mock", action="store_true", help="Usa série simulada para teste no PC particular")
    p.add_argument("--out-dir", default="data/reports/resource_analysis", help="Diretório raiz de saída")
    p.add_argument("--save-prompt", action="store_true", help="Salva prompts da LLM para auditoria")
    p.add_argument("--formats", default="md,docx,pdf", help="Formatos: md,docx,pdf")
    p.add_argument("--zip", action="store_true", help="Gera ZIP consolidado com documentos e gráficos")
    return p.parse_args()


def _split(value: str) -> list[str]:
    return [x.strip() for x in str(value or "").replace(";", ",").split(",") if x.strip()]


def main() -> int:
    args = parse_args()
    if not args.mock:
        print("ERRO: nesta versão consolidada local, use --mock. O provider real será plugado no ambiente controlado.")
        return 2
    resources = [r.upper().strip() for r in _split(args.resources)] or ["CPU", "MEM", "DISK"]
    partitions = _split(args.partitions) or ["C:"]
    selected_formats = parse_formats(args.formats)
    provider = MockTimeseriesProvider()
    generated_files: list[Path] = []
    chart_files: list[Path] = []
    prompt_files: list[Path] = []
    items: list[ResourceAnalysisItem] = []

    for res in resources:
        parts = partitions if res in {"DISK", "DSK", "PARTITION"} else [None]
        for part in parts:
            req = ResourceAnalysisRequest(
                solicitacao=args.solicitacao,
                vm=args.vm,
                resource=res,
                partition=part if res in {"DISK", "DSK", "PARTITION"} else None,
                periodo_dias=args.periodo_dias,
                solicitante=args.solicitante,
                analista=args.analista,
                classificacao=args.classificacao,
                threshold_pct=args.threshold_pct,
                origem="cli/local_simulado",
            )
            errors = req.validate()
            if errors:
                for e in errors:
                    print(f"ERRO: {e}")
                return 2
            usage_df, cap_df = provider.load(req)
            stats, forecast_df = compute_resource_stats(req, usage_df, cap_df)
            out_dir = Path(args.out_dir) / req.safe_solicitacao / req.safe_vm / req.safe_resource
            charts = generate_charts(req, usage_df, cap_df, stats, forecast_df, out_dir / "graficos")
            narrative = deterministic_narrative(req, stats)
            md = build_markdown_report(req, stats, narrative, charts, out_dir)
            extra = export_reports(req, stats, narrative, charts, out_dir, selected_formats)
            generated_files.append(Path(md))
            generated_files.extend(Path(p) for p in extra.values())
            chart_files.extend(Path(p) for p in charts.values())
            if args.save_prompt:
                prompt_path = out_dir / f"{req.safe_solicitacao}_{req.safe_vm}_{req.safe_resource}_llm_prompt.txt"
                prompt_path.write_text(build_llm_prompt(req, stats), encoding="utf-8")
                prompt_files.append(prompt_path)
            items.append(ResourceAnalysisItem(req=req, stats=stats, narrative=narrative, chart_paths=charts))
            print(f"{req.resource_title}: {stats.diagnosis} / {stats.recommendation_action}")

    bundle_root = Path(args.out_dir) / items[0].req.safe_solicitacao / items[0].req.safe_vm
    consolidated_dir = bundle_root / "consolidado"
    consolidated = export_consolidated_reports(items, consolidated_dir, selected_formats)
    print("\n=== RELATÓRIO CONSOLIDADO GERADO ===")
    for k, p in consolidated.items():
        print(f"{k.upper()}: {p}")

    if args.zip:
        zip_path = bundle_root / f"{items[0].req.safe_solicitacao}_{items[0].req.safe_vm}_relatorio_consolidado_completo.zip"
        make_zip_bundle(zip_path, list(consolidated.values()) + generated_files + chart_files, bundle_root)
        print(f"ZIP: {zip_path}")
        if prompt_files:
            prompts_zip = bundle_root / f"{items[0].req.safe_solicitacao}_{items[0].req.safe_vm}_prompts_llm_auditoria.zip"
            make_zip_bundle(prompts_zip, prompt_files, bundle_root)
            print(f"ZIP auditoria: {prompts_zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
