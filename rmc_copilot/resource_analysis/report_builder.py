from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Dict
import json

from .models import ResourceAnalysisRequest, ResourceStats
from .ptbr_format import period_br

BV_BLUE = "#0033A0"
BV_GREEN = "#78BE20"
BV_LIGHT_GRAY = "#F2F4F7"
BV_DARK = "#1F2937"


def _rel(path: str | Path, base: str | Path) -> str:
    try:
        return Path(path).relative_to(Path(base)).as_posix()
    except Exception:
        return Path(path).as_posix()


def _fmt(value, unit: str = "") -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.2f}{(' ' + unit) if unit else ''}"
    except Exception:
        return str(value)


def _fmt_pct(value) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return str(value)


def _is_blank(value) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text == "" or text.lower() in {"nan", "none", "null"}


def _fmt_optional_capacity(value, unit: str = "") -> str:
    if _is_blank(value):
        return "Não aplicável"
    try:
        return f"{float(value):.2f}{(' ' + unit) if unit else ''}"
    except Exception:
        return str(value)


def _human_action(value: str) -> str:
    text = str(value or "").strip().replace("_", " ")
    mapping = {
        "AVALIAR REDUÇÃO RECURSO": "AVALIAR REDUÇÃO",
        "AVALIAR REDUCAO RECURSO": "AVALIAR REDUÇÃO",
    }
    return mapping.get(text.upper(), text)


def _human_diagnosis(value: str) -> str:
    return str(value or "").strip().replace("_", " ")


def build_markdown_report(req: ResourceAnalysisRequest, stats: ResourceStats, narrative: Dict[str, str], chart_paths: Dict[str, str], out_dir: str | Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    title = f"Relatório de Análise Individual de Recursos — {req.vm}"
    md_path = out_dir / f"{req.safe_solicitacao}_{req.safe_vm}_{req.safe_resource}_analise_recursos.md"

    header = f"""
<div style="border-top: 12px solid {BV_BLUE}; border-bottom: 5px solid {BV_GREEN}; padding: 18px 22px; background: {BV_LIGHT_GRAY}; font-family: Arial, Helvetica, sans-serif;">
  <div style="font-size: 26px; font-weight: 700; color: {BV_BLUE};">BV</div>
  <div style="font-size: 20px; font-weight: 700; color: {BV_DARK}; margin-top: 4px;">{title}</div>
  <div style="font-size: 12px; color: {BV_DARK}; margin-top: 10px;">Classificação: <strong>{req.classificacao}</strong></div>
</div>
""".strip()

    meta_lines = [
        ("Solicitação", req.solicitacao),
        ("Servidor / VM", req.vm),
        ("Recurso", req.resource_title),
        ("Período histórico", f"{req.periodo_dias} dias"),
        ("Período analisado", period_br(stats.start, stats.end)),
        ("Solicitante", req.solicitante or ""),
        ("Analista", req.analista or ""),
        ("Origem dos dados", req.origem),
        ("Data de geração", generated_at),
    ]
    meta_table = "\n".join([f"| {k} | {v} |" for k, v in meta_lines if v])

    charts_md = []
    for label, key in [
        ("A. Comparação e Previsão", "comparacao_previsao"),
        ("B. Histórico com Média Móvel", "media_movel"),
        ("C. Decomposição da Série Temporal", "decomposicao"),
        ("D. Distribuição de Uso", "histograma"),
        ("E. Uso Médio por Hora", "uso_por_hora"),
    ]:
        if key in chart_paths:
            charts_md.append(f"### {label}\n\n![{label}]({_rel(chart_paths[key], out_dir)})")

    stats_table = f"""
| Métrica | Valor |
|:--|--:|
| Capacidade total | {_fmt(stats.capacity, stats.unit)} |
| Margem de segurança ({stats.threshold_pct:.0f}%) | {_fmt(stats.threshold_value, stats.unit)} |
| Uso mínimo | {_fmt(stats.minimum, stats.unit)} |
| Uso médio | {_fmt(stats.mean, stats.unit)} ({_fmt_pct(stats.mean_pct)}) |
| Mediana | {_fmt(stats.median, stats.unit)} ({_fmt_pct(stats.median_pct)}) |
| Q1 | {_fmt(stats.q1, stats.unit)} |
| Q3 | {_fmt(stats.q3, stats.unit)} |
| P95 | {_fmt(stats.p95, stats.unit)} ({_fmt_pct(stats.p95_pct)}) |
| Uso máximo | {_fmt(stats.maximum, stats.unit)} ({_fmt_pct(stats.maximum_pct)}) |
| Forecast 30 dias | {_fmt(stats.forecast_30, stats.unit)} ({_fmt_pct(stats.forecast_30_pct)}) |
| Forecast 60 dias | {_fmt(stats.forecast_60, stats.unit)} ({_fmt_pct(stats.forecast_60_pct)}) |
| Forecast 90 dias | {_fmt(stats.forecast_90, stats.unit)} ({_fmt_pct(stats.forecast_90_pct)}) |
| Diagnóstico | {_human_diagnosis(stats.diagnosis)} |
| Ação recomendada | {_human_action(stats.recommendation_action)} |
| Capacidade sugerida | {_fmt_optional_capacity(stats.recommended_capacity, stats.unit)} |
| Variação sugerida | {_fmt_optional_capacity(stats.recommended_delta, stats.unit)} |
""".strip()

    content = f"""{header}

# {title}

| Campo | Valor |
|:--|:--|
{meta_table}

---

## 1. Resumo Executivo

{narrative['resumo_executivo']}

## 2. Análise Técnica dos Gráficos

{narrative['analise_graficos']}

{chr(10).join(charts_md)}

## 3. Análise Estatística

{narrative['analise_estatistica']}

{stats_table}

## 4. Conclusão e Recomendação

{narrative['conclusao_recomendacao']}

## 5. Observações

- A LLM/Data+RAG não calcula os números: ela apenas transforma os indicadores calculados pelo motor estatístico em texto executivo.
- A margem de segurança usada foi de {stats.threshold_pct:.0f}% da capacidade total.
- {stats.confidence_note}

---

{req.classificacao}
"""
    md_path.write_text(content, encoding="utf-8")
    (out_dir / f"{req.safe_solicitacao}_{req.safe_vm}_{req.safe_resource}_metadata.json").write_text(
        json.dumps({"request": req.to_dict(), "stats": stats.to_dict(), "charts": chart_paths}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return md_path
