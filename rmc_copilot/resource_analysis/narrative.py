from __future__ import annotations

from typing import Dict, List, Optional
import json

from .models import ResourceAnalysisRequest, ResourceStats
from .ptbr_format import period_br


def _fmt(value: Optional[float], unit: str = "", digits: int = 2) -> str:
    if value is None:
        return "não aplicável"
    try:
        return f"{float(value):.{digits}f}{(' ' + unit) if unit else ''}"
    except Exception:
        return str(value)


def _fmt_pct(value: Optional[float]) -> str:
    return _fmt(value, "%", 2).replace(" %", "%")


def build_llm_prompt(req: ResourceAnalysisRequest, stats: ResourceStats) -> str:
    """Prompt seguro: LLM só pode narrar números já calculados."""
    payload = {"solicitacao": req.to_dict(), "estatisticas": stats.to_dict()}
    return f"""
Você é um analista de infraestrutura, VMware e Capacity Planning.
Gere uma análise executiva em português, clara para público não técnico, com base EXCLUSIVA nos números JSON abaixo.
Não invente valores, datas, nomes, capacidades, percentuais ou recomendações fora do JSON.
Use seções: Resumo Executivo, Análise Técnica, Análise Estatística, Conclusão e Recomendação.
Use datas no padrão português do Brasil: DD/MM/AAAA.
Explique a margem de segurança de {stats.threshold_pct:.0f}%.

JSON:
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()


def deterministic_narrative(req: ResourceAnalysisRequest, stats: ResourceStats) -> Dict[str, str]:
    unit = stats.unit
    resource = req.resource_title
    vm = req.vm
    threshold = stats.threshold_pct

    if stats.diagnosis == "CRÍTICO":
        executive = (
            f"A análise do recurso {resource} da VM {vm} indica cenário crítico de capacidade. "
            f"O uso médio foi de {_fmt(stats.mean, unit)} ({_fmt_pct(stats.mean_pct)}), o P95 foi de {_fmt(stats.p95, unit)} "
            f"({_fmt_pct(stats.p95_pct)}) e a previsão de 90 dias aponta {_fmt(stats.forecast_90, unit)} "
            f"({_fmt_pct(stats.forecast_90_pct)}). O comportamento viola ou se aproxima fortemente da margem de segurança de {threshold:.0f}%."
        )
    elif stats.diagnosis == "ATENÇÃO":
        executive = (
            f"A análise do recurso {resource} da VM {vm} indica necessidade de acompanhamento e avaliação técnica. "
            f"O uso médio foi de {_fmt(stats.mean, unit)} ({_fmt_pct(stats.mean_pct)}) e o P95 foi de {_fmt(stats.p95, unit)} "
            f"({_fmt_pct(stats.p95_pct)}). O recurso já pressiona a margem de segurança de {threshold:.0f}% ou pode ultrapassá-la no horizonte analisado."
        )
    elif stats.diagnosis == "SUPERDIMENSIONADO":
        executive = (
            f"A análise do recurso {resource} da VM {vm} indica possível superdimensionamento. "
            f"A capacidade atual é de {_fmt(stats.capacity, unit)}, enquanto o uso médio foi de apenas {_fmt(stats.mean, unit)} "
            f"({_fmt_pct(stats.mean_pct)}) e o P95 ficou em {_fmt(stats.p95, unit)} ({_fmt_pct(stats.p95_pct)}). "
            f"Não há evidência estatística de necessidade de aumento do recurso neste momento."
        )
    else:
        executive = (
            f"A análise do recurso {resource} da VM {vm} indica comportamento operacional estável. "
            f"A capacidade atual é de {_fmt(stats.capacity, unit)}, o uso médio foi de {_fmt(stats.mean, unit)} "
            f"({_fmt_pct(stats.mean_pct)}) e o P95 ficou em {_fmt(stats.p95, unit)} ({_fmt_pct(stats.p95_pct)}), dentro da margem de segurança de {threshold:.0f}%."
        )

    graphics = (
        "O gráfico de comparação e previsão deve ser usado para verificar se a linha de utilização se aproxima da capacidade total ou da margem de segurança. "
        "O gráfico de média móvel ajuda a diferenciar picos isolados de tendência real. "
        "A decomposição da série temporal evidencia tendência, sazonalidade e resíduos. "
        "O histograma mostra onde o recurso permanece concentrado na maior parte do tempo, e o gráfico de uso por hora identifica janelas recorrentes de maior consumo."
    )

    stats_text = (
        f"No período de {period_br(stats.start, stats.end)}, foram analisadas {stats.samples} amostras. "
        f"A capacidade total considerada foi {_fmt(stats.capacity, unit)} e a margem de segurança de {threshold:.0f}% equivale a {_fmt(stats.threshold_value, unit)}. "
        f"Mínimo: {_fmt(stats.minimum, unit)}; média: {_fmt(stats.mean, unit)}; mediana: {_fmt(stats.median, unit)}; "
        f"P95: {_fmt(stats.p95, unit)}; máximo: {_fmt(stats.maximum, unit)}. "
        f"Previsões: 30 dias {_fmt(stats.forecast_30, unit)} ({_fmt_pct(stats.forecast_30_pct)}), "
        f"60 dias {_fmt(stats.forecast_60, unit)} ({_fmt_pct(stats.forecast_60_pct)}), "
        f"90 dias {_fmt(stats.forecast_90, unit)} ({_fmt_pct(stats.forecast_90_pct)})."
    )

    if stats.recommendation_action in {"AUMENTAR_RECURSO", "AVALIAR_AUMENTO_RECURSO"}:
        recommendation = (
            f"Recomenda-se avaliar aumento do recurso {resource}. "
            f"Capacidade atual: {_fmt(stats.capacity, unit)}. Capacidade sugerida: {_fmt(stats.recommended_capacity, unit)} "
            f"(variação estimada de {_fmt(stats.recommended_delta, unit)}). "
            "A recomendação deve ser validada com o responsável da aplicação antes da alteração em produção."
        )
    elif stats.recommendation_action == "AVALIAR_REDUÇÃO_RECURSO":
        recommendation = (
            f"Recomenda-se avaliar redução controlada do recurso {resource}, pois o uso médio e o P95 estão muito abaixo da capacidade alocada. "
            f"Capacidade atual: {_fmt(stats.capacity, unit)}. Capacidade técnica sugerida para avaliação: {_fmt(stats.recommended_capacity, unit)}. "
            "A redução deve ser feita em janela controlada, com monitoramento após a alteração."
        )
    else:
        recommendation = (
            f"Não há indicação de aumento imediato do recurso {resource}. A recomendação é manter a configuração atual e continuar o monitoramento periódico."
        )

    return {
        "resumo_executivo": executive,
        "analise_graficos": graphics,
        "analise_estatistica": stats_text,
        "conclusao_recomendacao": recommendation,
    }
