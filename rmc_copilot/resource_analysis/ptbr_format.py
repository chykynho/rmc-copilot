from __future__ import annotations

from datetime import datetime, date
from typing import Any
import re
import pandas as pd


_RE_BR_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_RE_BR_DATETIME = re.compile(r"^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}(:\d{2})?$")
_RE_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_datetime(value: Any) -> pd.Timestamp | None:
    """Converte datas de forma previsível, sem warnings do pandas.

    Ordem suportada:
    - pandas Timestamp / datetime / date
    - DD/MM/AAAA
    - DD/MM/AAAA HH:MM ou HH:MM:SS
    - AAAA-MM-DD
    - demais formatos parseáveis, preferindo dayfirst=True por padrão pt-BR
    """
    if value is None or value == "":
        return None

    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value

    if isinstance(value, datetime):
        return pd.Timestamp(value)

    if isinstance(value, date):
        return pd.Timestamp(value)

    text = str(value).strip()
    if not text:
        return None

    try:
        if _RE_BR_DATE.match(text):
            return pd.to_datetime(text, format="%d/%m/%Y", errors="raise")

        if _RE_BR_DATETIME.match(text):
            fmt = "%d/%m/%Y %H:%M:%S" if len(text.split()[-1].split(":")) == 3 else "%d/%m/%Y %H:%M"
            return pd.to_datetime(text, format=fmt, errors="raise")

        if _RE_ISO_DATE.match(text):
            return pd.to_datetime(text, format="%Y-%m-%d", errors="raise")

        # Fallback pt-BR: evita ambiguidade de 03/04/2026 como mês/dia.
        return pd.to_datetime(text, errors="raise", dayfirst=True)
    except Exception:
        return None


def format_date_br(value: Any) -> str:
    """Formata datas em pt-BR: DD/MM/AAAA.

    Aceita pandas Timestamp, datetime/date, strings ISO (AAAA-MM-DD), strings
    brasileiras (DD/MM/AAAA) ou outros formatos parseáveis pelo pandas.
    Se não conseguir converter, devolve o texto original.
    """
    if value is None or value == "":
        return ""

    original = str(value).strip()
    ts = _parse_datetime(value)
    if ts is None or pd.isna(ts):
        return original
    return ts.strftime("%d/%m/%Y")


def format_datetime_br(value: Any) -> str:
    """Formata data/hora em pt-BR: DD/MM/AAAA HH:MM."""
    if value is None or value == "":
        return ""

    original = str(value).strip()
    ts = _parse_datetime(value)
    if ts is None or pd.isna(ts):
        return original
    return ts.strftime("%d/%m/%Y %H:%M")


def period_br(start: Any, end: Any) -> str:
    start_br = format_date_br(start)
    end_br = format_date_br(end)
    if start_br and end_br:
        return f"{start_br} a {end_br}"
    return start_br or end_br
