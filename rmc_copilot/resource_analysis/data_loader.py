from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple
import os
import pandas as pd

from .models import ResourceAnalysisRequest


DROP_COLS = ["Low DT", "High DT", "Smooth", "Unnamed: 5"]


def _find_case_insensitive(path: Path, name: str) -> Optional[Path]:
    if not path.exists():
        return None
    target = name.lower()
    for item in path.iterdir():
        if item.name.lower() == target:
            return item
    return None


def build_legacy_metricchart_names(req: ResourceAnalysisRequest) -> Tuple[str, str]:
    """Preserva a lógica do notebook antigo para nomes MetricChart_* baixados do vROps."""
    vm = req.vm
    unit = req.unit
    if req.resource == "CPU":
        metric_name = "CPU"
        usage_ext = "Demand"
        total_ext = "Total"
    elif req.resource == "MEM":
        metric_name = "Memory"
        usage_ext = "Guest Usage"
        total_ext = "Total"
    elif req.resource == "DISK":
        metric_name = "Guest File System"
        part = req.partition or "C"
        usage_ext = f"{part}---Partition Utilization"
        total_ext = f"{part}---Partition"
    else:
        raise ValueError(f"Recurso inválido: {req.resource}")
    usage = f"MetricChart_{vm}_{metric_name}-{usage_ext} ({unit}).csv"
    capacity = f"MetricChart_{vm}_{metric_name}-{total_ext} Capacity ({unit}).csv"
    return usage, capacity


def load_vrops_metric_csv(path: str | Path) -> pd.DataFrame:
    """Lê CSV de métrica vROps baixado manualmente ou exportado pela coleta.

    Aceita tanto o formato do notebook antigo, com cabeçalho real após duas linhas,
    quanto CSVs já normalizados com colunas Date/Value.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    # tenta formato vROps antigo primeiro
    last_error: Optional[Exception] = None
    for skiprows in (2, 0):
        try:
            df = pd.read_csv(path, sep=",", encoding="utf-8", skiprows=skiprows)
            if df.empty:
                continue
            break
        except Exception as exc:  # pragma: no cover
            last_error = exc
            df = pd.DataFrame()
    else:
        if last_error:
            raise last_error
        raise ValueError(f"Não foi possível ler CSV: {path}")

    if "Date & Time" in df.columns:
        df = df.rename(columns={"Date & Time": "Date"})
    # normaliza nomes possíveis
    lower = {str(c).strip().lower(): c for c in df.columns}
    if "date" not in lower and "datetime" in lower:
        df = df.rename(columns={lower["datetime"]: "Date"})
    if "value" not in lower:
        # escolhe a primeira coluna numérica que não seja data
        for col in df.columns:
            if str(col).strip().lower() in {"date", "date & time", "datetime"}:
                continue
            series = pd.to_numeric(df[col], errors="coerce")
            if series.notna().sum() > 0:
                df = df.rename(columns={col: "Value"})
                break
    else:
        df = df.rename(columns={lower["value"]: "Value"})

    if "Date" not in df.columns or "Value" not in df.columns:
        raise ValueError(f"CSV precisa conter Date/Date & Time e Value. Colunas encontradas: {list(df.columns)}")

    for col in DROP_COLS:
        if col in df.columns:
            df = df.drop(columns=[col])

    out = df[["Date", "Value"]].copy()
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    try:
        out["Date"] = out["Date"].dt.tz_localize(None)
    except TypeError:
        try:
            out["Date"] = out["Date"].dt.tz_convert(None)
        except Exception:
            pass
    out["Value"] = pd.to_numeric(out["Value"], errors="coerce")
    out = out.dropna(subset=["Date", "Value"]).sort_values("Date").reset_index(drop=True)
    if out.empty:
        raise ValueError(f"CSV sem dados úteis depois da limpeza: {path}")
    return out


def load_legacy_metric_pair(base_dir: str | Path, req: ResourceAnalysisRequest) -> tuple[pd.DataFrame, pd.DataFrame, Path, Path]:
    base_dir = Path(base_dir)
    usage_name, capacity_name = build_legacy_metricchart_names(req)
    usage_path = _find_case_insensitive(base_dir, usage_name)
    cap_path = _find_case_insensitive(base_dir, capacity_name)
    if not usage_path:
        raise FileNotFoundError(f"Arquivo de uso não encontrado em {base_dir}: {usage_name}")
    if not cap_path:
        raise FileNotFoundError(f"Arquivo de capacidade não encontrado em {base_dir}: {capacity_name}")
    return load_vrops_metric_csv(usage_path), load_vrops_metric_csv(cap_path), usage_path, cap_path


def filter_period(df: pd.DataFrame, days: int) -> pd.DataFrame:
    if df.empty or not days:
        return df
    end = df["Date"].max()
    start = end - pd.Timedelta(days=int(days))
    return df[df["Date"] >= start].copy().reset_index(drop=True)
