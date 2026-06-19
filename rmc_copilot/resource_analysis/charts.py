from __future__ import annotations

from pathlib import Path
from typing import Dict
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

try:
    from statsmodels.tsa.seasonal import seasonal_decompose
except Exception:  # pragma: no cover
    seasonal_decompose = None

from .models import ResourceAnalysisRequest, ResourceStats

BV_BLUE = "#0033A0"
BV_GREEN = "#78BE20"
BV_GRAY = "#6E6E6E"
BV_LIGHT_GRAY = "#E6E7E8"
BV_RED = "#C8102E"


def _format_date_axis(ax) -> None:
    """Exibe datas nos gráficos no padrão pt-BR (DD/MM)."""
    try:
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=7))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
        ax.figure.autofmt_xdate(rotation=0, ha="center")
    except Exception:
        pass


def _safe_title(req: ResourceAnalysisRequest) -> str:
    return req.resource_title.replace("/", "-").replace(":", "-")


def _save(fig, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def generate_charts(req: ResourceAnalysisRequest, usage_df: pd.DataFrame, capacity_df: pd.DataFrame, stats: ResourceStats, forecast_df: pd.DataFrame, out_dir: str | Path) -> Dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    usage = usage_df[["Date", "Value"]].copy().sort_values("Date")
    capacity = float(stats.capacity)
    unit = req.unit
    title = _safe_title(req)
    paths: Dict[str, str] = {}

    # 1. Comparação e previsão
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    ax.plot(usage["Date"], usage["Value"], label="Uso real", color=BV_BLUE, linewidth=1.2)
    ax.plot(forecast_df["Date"], forecast_df["Forecast"], label="Previsão 90 dias", color=BV_BLUE, linestyle="--", linewidth=1.1)
    ax.axhline(capacity, label="Capacidade atual", color=BV_GREEN, linewidth=1.2)
    ax.axhline(stats.threshold_value, label=f"Margem {stats.threshold_pct:.0f}%", color=BV_RED, linestyle=":", linewidth=1.1)
    ax.axvline(usage["Date"].max(), color=BV_GRAY, linestyle=":", linewidth=1.0, label="Início previsão")
    ax.set_title(f"Comparação e Previsão — {req.resource_title}")
    ax.set_xlabel("Data")
    ax.set_ylabel(unit)
    _format_date_axis(ax)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    paths["comparacao_previsao"] = _save(fig, out / f"01_{req.safe_resource}_comparacao_previsao.png")

    # 2. Uso + média móvel
    rolling = usage["Value"].rolling(window=min(7, max(2, len(usage)//10)), min_periods=1).mean()
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    ax.plot(usage["Date"], usage["Value"], label="Uso real", color=BV_BLUE, linewidth=0.9, alpha=0.7)
    ax.plot(usage["Date"], rolling, label="Média móvel", color=BV_GREEN, linewidth=1.5)
    ax.set_title(f"Histórico com Média Móvel — {req.resource_title}")
    ax.set_xlabel("Data")
    ax.set_ylabel(unit)
    _format_date_axis(ax)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    paths["media_movel"] = _save(fig, out / f"02_{req.safe_resource}_media_movel.png")

    # 3. Decomposição
    fig = None
    try:
        if seasonal_decompose is not None and len(usage) >= 8:
            period = 24 if len(usage) >= 24 * 2 else min(7, max(2, len(usage)//4))
            res = seasonal_decompose(usage.set_index("Date")["Value"], model="additive", period=period)
            fig = res.plot()
            fig.set_size_inches(10.5, 6.2)
            for ax in fig.axes:
                _format_date_axis(ax)
                ax.grid(True, alpha=0.2)
    except Exception:
        fig = None
    if fig is None:
        fig, axes = plt.subplots(4, 1, figsize=(10.5, 6.2), sharex=True)
        series = usage.set_index("Date")["Value"]
        trend = series.rolling(window=min(7, max(2, len(series)//10)), min_periods=1).mean()
        resid = series - trend
        axes[0].plot(series.index, series.values, color=BV_BLUE); axes[0].set_title("Série Original", fontsize=9)
        axes[1].plot(trend.index, trend.values, color=BV_GREEN); axes[1].set_title("Tendência", fontsize=9)
        axes[2].plot(series.index, [0]*len(series), color=BV_GRAY); axes[2].set_title("Sazonalidade", fontsize=9)
        axes[3].plot(resid.index, resid.values, color=BV_RED); axes[3].set_title("Resíduos", fontsize=9)
        for ax in axes:
            _format_date_axis(ax)
            ax.grid(True, alpha=0.2)
    paths["decomposicao"] = _save(fig, out / f"03_{req.safe_resource}_decomposicao.png")

    # 4. Histograma
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    ax.hist(usage["Value"], bins=30, color=BV_BLUE, alpha=0.75, edgecolor="white")
    ax.axvline(stats.mean, color=BV_GREEN, linestyle="--", label="Média")
    ax.axvline(stats.p95, color=BV_RED, linestyle=":", label="P95")
    ax.set_title(f"Distribuição de Uso — {req.resource_title}")
    ax.set_xlabel(unit)
    ax.set_ylabel("Frequência")
    ax.grid(True, alpha=0.2)
    ax.legend(fontsize=8)
    paths["histograma"] = _save(fig, out / f"04_{req.safe_resource}_histograma.png")

    # 5. Uso médio por hora
    tmp = usage.copy()
    tmp["Hour"] = pd.to_datetime(tmp["Date"]).dt.hour
    hourly = tmp.groupby("Hour", as_index=True)["Value"].mean().reindex(range(24), fill_value=0)
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    ax.bar(hourly.index, hourly.values, color=BV_BLUE)
    ax.set_title(f"Uso Médio por Hora — {req.resource_title}")
    ax.set_xlabel("Hora")
    ax.set_ylabel(unit)
    ax.set_xticks(range(0, 24, 1))
    ax.grid(axis="y", alpha=0.2)
    paths["uso_por_hora"] = _save(fig, out / f"05_{req.safe_resource}_uso_por_hora.png")

    return paths
