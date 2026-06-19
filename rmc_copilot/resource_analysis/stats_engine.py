from __future__ import annotations

import math
from typing import Optional
import numpy as np
import pandas as pd

from .models import ResourceAnalysisRequest, ResourceStats
from .ptbr_format import format_date_br


def _capacity_latest(capacity_df: pd.DataFrame) -> float:
    if capacity_df is None or capacity_df.empty:
        raise ValueError("DataFrame de capacidade vazio.")
    value = float(pd.to_numeric(capacity_df["Value"], errors="coerce").dropna().iloc[-1])
    if value <= 0:
        raise ValueError("Capacidade total precisa ser maior que zero.")
    return value


def simple_linear_forecast(usage_df: pd.DataFrame, horizon_days: int = 90) -> pd.DataFrame:
    df = usage_df[["Date", "Value"]].dropna().copy().sort_values("Date")
    if len(df) < 2:
        last_date = df["Date"].max() if not df.empty else pd.Timestamp.today()
        last_val = float(df["Value"].iloc[-1]) if not df.empty else 0.0
        dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon_days, freq="D")
        return pd.DataFrame({"Date": dates, "Forecast": [last_val] * horizon_days})
    first = df["Date"].min()
    x = (df["Date"] - first).dt.total_seconds().astype(float) / 86400.0
    y = pd.to_numeric(df["Value"], errors="coerce").astype(float)
    # suaviza com média móvel para evitar pico isolado guiar tudo
    y_smooth = y.rolling(window=min(7, max(2, len(y)//10)), min_periods=1).mean()
    try:
        slope, intercept = np.polyfit(x, y_smooth, 1)
    except Exception:
        slope, intercept = 0.0, float(y.iloc[-1])
    start = df["Date"].max() + pd.Timedelta(days=1)
    dates = pd.date_range(start, periods=horizon_days, freq="D")
    x_future = (dates - first).total_seconds().astype(float) / 86400.0
    preds = intercept + slope * x_future
    preds = np.maximum(preds, 0)
    return pd.DataFrame({"Date": dates, "Forecast": preds})


def _future_value(forecast: pd.DataFrame, day: int) -> float:
    if forecast.empty:
        return 0.0
    idx = min(max(day - 1, 0), len(forecast) - 1)
    return float(forecast["Forecast"].iloc[idx])


def _round_capacity(value: float, resource: str) -> float:
    if resource == "CPU":
        # arredonda para múltiplos de 2 GHz como aproximação operacional
        return float(max(1, math.ceil(value / 2.0) * 2.0))
    if resource in {"MEM", "DISK"}:
        step = 16 if resource == "MEM" else 50
        return float(max(step, math.ceil(value / step) * step))
    return float(value)


def _diagnosis_and_recommendation(req: ResourceAnalysisRequest, capacity: float, mean_pct: float, p95_pct: float, max_pct: float, f90_pct: float, p95: float, f90: float) -> tuple[str, str, Optional[float], Optional[float], str]:
    threshold = float(req.threshold_pct)
    critical_limit = max(90.0, threshold + 10.0)
    driving = max(p95_pct, mean_pct, f90_pct)
    if driving >= critical_limit:
        diagnosis = "CRÍTICO"
        action = "AUMENTAR_RECURSO"
    elif driving >= threshold:
        diagnosis = "ATENÇÃO"
        action = "AVALIAR_AUMENTO_RECURSO"
    elif mean_pct < 20 and p95_pct < 40 and req.resource in {"CPU", "MEM"}:
        diagnosis = "SUPERDIMENSIONADO"
        action = "AVALIAR_REDUÇÃO_RECURSO"
    else:
        diagnosis = "OK"
        action = "MANTER_MONITORAMENTO"

    recommended_capacity: Optional[float] = None
    recommended_delta: Optional[float] = None
    confidence = "Forecast linear simples de 90 dias; usar como apoio, não como única fonte de decisão."

    if action in {"AUMENTAR_RECURSO", "AVALIAR_AUMENTO_RECURSO"}:
        target_usage = max(p95, f90)
        raw_capacity = target_usage / (threshold / 100.0)
        recommended_capacity = max(capacity, _round_capacity(raw_capacity, req.resource))
        recommended_delta = max(0.0, recommended_capacity - capacity)
    elif action == "AVALIAR_REDUÇÃO_RECURSO":
        target_usage = max(p95 * 2.0, capacity * 0.4)
        recommended_capacity = min(capacity, _round_capacity(target_usage, req.resource))
        recommended_delta = recommended_capacity - capacity
    return diagnosis, action, recommended_capacity, recommended_delta, confidence


def compute_resource_stats(req: ResourceAnalysisRequest, usage_df: pd.DataFrame, capacity_df: pd.DataFrame) -> tuple[ResourceStats, pd.DataFrame]:
    if usage_df.empty:
        raise ValueError("DataFrame de uso vazio.")
    usage = usage_df[["Date", "Value"]].dropna().copy().sort_values("Date").reset_index(drop=True)
    capacity = _capacity_latest(capacity_df)
    values = pd.to_numeric(usage["Value"], errors="coerce").dropna()
    if values.empty:
        raise ValueError("Sem valores numéricos úteis para análise.")

    q1 = float(values.quantile(0.25))
    q3 = float(values.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    mean = float(values.mean())
    median = float(values.median())
    maximum = float(values.max())
    minimum = float(values.min())
    p95 = float(values.quantile(0.95))
    std = float(values.std()) if len(values) > 1 else 0.0
    threshold_value = capacity * float(req.threshold_pct) / 100.0

    forecast = simple_linear_forecast(usage, 90)
    f30 = _future_value(forecast, 30)
    f60 = _future_value(forecast, 60)
    f90 = _future_value(forecast, 90)

    mean_pct = mean / capacity * 100.0
    median_pct = median / capacity * 100.0
    maximum_pct = maximum / capacity * 100.0
    p95_pct = p95 / capacity * 100.0
    f30_pct = f30 / capacity * 100.0
    f60_pct = f60 / capacity * 100.0
    f90_pct = f90 / capacity * 100.0

    diagnosis, action, rec_capacity, rec_delta, confidence = _diagnosis_and_recommendation(
        req, capacity, mean_pct, p95_pct, maximum_pct, f90_pct, p95, f90
    )

    stats = ResourceStats(
        resource=req.resource_title,
        unit=req.unit,
        capacity=capacity,
        threshold_pct=float(req.threshold_pct),
        threshold_value=threshold_value,
        start=format_date_br(usage["Date"].min()),
        end=format_date_br(usage["Date"].max()),
        samples=int(len(values)),
        minimum=minimum,
        maximum=maximum,
        mean=mean,
        median=median,
        q1=q1,
        q3=q3,
        p95=p95,
        std=std,
        iqr=iqr,
        lower_outlier=lower,
        upper_outlier=upper,
        mean_pct=mean_pct,
        median_pct=median_pct,
        maximum_pct=maximum_pct,
        p95_pct=p95_pct,
        forecast_30=f30,
        forecast_60=f60,
        forecast_90=f90,
        forecast_30_pct=f30_pct,
        forecast_60_pct=f60_pct,
        forecast_90_pct=f90_pct,
        diagnosis=diagnosis,
        recommendation_action=action,
        recommended_capacity=rec_capacity,
        recommended_delta=rec_delta,
        confidence_note=confidence,
    )
    return stats, forecast
