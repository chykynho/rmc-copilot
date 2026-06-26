from __future__ import annotations

import re
import unicodedata
from typing import Dict, Iterable, List, Optional


CANONICAL_COLUMNS = [
    "cluster",
    "host",
    "vm",
    "datastore",
    "cpu_p95",
    "mem_p95",
    "disk_used_pct",
    "datastore_used_pct",
    "forecast_30d",
    "forecast_60d",
    "forecast_90d",
    "prioridade",
    "acao",
]


REQUIRED_MINIMAL = ["vm", "cluster", "prioridade"]

RECOMMENDED = [
    "vm",
    "cluster",
    "host",
    "cpu_p95",
    "mem_p95",
    "disk_used_pct",
    "datastore",
    "datastore_used_pct",
    "forecast_30d",
    "forecast_60d",
    "forecast_90d",
    "prioridade",
    "acao",
]


ALIASES: Dict[str, List[str]] = {
    "cluster": [
        "cluster",
        "cluster_name",
        "nome_cluster",
        "nome do cluster",
        "vc_cluster",
        "compute_cluster",
        "cluster_corrigido",
        "cluster_final",
    ],
    "host": [
        "host",
        "hostname",
        "host_name",
        "nome_host",
        "nome do host",
        "esxi",
        "esxi_host",
        "host_esxi",
    ],
    "vm": [
        "vm",
        "vm_name",
        "nome_vm",
        "nome da vm",
        "virtual_machine",
        "virtualmachine",
        "resource_name",
        "nome",
        "maquina_virtual",
        "máquina_virtual",
    ],
    "datastore": [
        "datastore",
        "ds",
        "data_store",
        "nome_datastore",
        "nome do datastore",
        "datastore_name",
        "storage",
    ],
    "cpu_p95": [
        "cpu_p95",
        "cpu p95",
        "cpu_percentil_95",
        "cpu_percentile_95",
        "cpu_usage_p95",
        "cpu_usage_pct_p95",
        "cpu_pct_p95",
        "cpu_uso_p95",
        "cpu_pico_p95",
        "cpu_usage",
        "cpu_pct",
        "cpu%",
    ],
    "mem_p95": [
        "mem_p95",
        "memory_p95",
        "memoria_p95",
        "memória_p95",
        "mem_percentil_95",
        "memory_usage_p95",
        "mem_usage_pct_p95",
        "mem_pct_p95",
        "ram_p95",
        "mem_usage",
        "memory_usage",
        "mem_pct",
        "mem%",
    ],
    "disk_used_pct": [
        "disk_used_pct",
        "disco_usado_pct",
        "disco_uso_pct",
        "disk_usage_pct",
        "disk_pct",
        "disk_used_percent",
        "uso_disco_pct",
        "percentual_disco",
        "disk%",
        "disco%",
        "used_pct",
    ],
    "datastore_used_pct": [
        "datastore_used_pct",
        "ds_used_pct",
        "datastore_usage_pct",
        "datastore_pct",
        "ds_pct",
        "datastore_used_percent",
        "uso_datastore_pct",
        "ds%",
    ],
    "forecast_30d": [
        "forecast_30d",
        "forecast_30",
        "risco_30d",
        "risco_futuro_30d",
        "previsao_30d",
        "previsão_30d",
        "forecast_30_dias",
        "forecast_30dias",
        "30d",
    ],
    "forecast_60d": [
        "forecast_60d",
        "forecast_60",
        "risco_60d",
        "risco_futuro_60d",
        "previsao_60d",
        "previsão_60d",
        "forecast_60_dias",
        "forecast_60dias",
        "60d",
    ],
    "forecast_90d": [
        "forecast_90d",
        "forecast_90",
        "risco_90d",
        "risco_futuro_90d",
        "previsao_90d",
        "previsão_90d",
        "forecast_90_dias",
        "forecast_90dias",
        "90d",
    ],
    "prioridade": [
        "prioridade",
        "prioridade_final",
        "priority",
        "priority_final",
        "classificacao",
        "classificação",
        "severidade",
        "criticidade",
    ],
    "acao": [
        "acao",
        "ação",
        "acao_recomendada",
        "ação_recomendada",
        "recomendacao",
        "recomendação",
        "recommendation",
        "action",
        "next_action",
    ],
}


def normalize_name(name: str) -> str:
    text = str(name).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[%]+", " pct ", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def build_alias_lookup() -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for canonical, values in ALIASES.items():
        lookup[normalize_name(canonical)] = canonical
        for value in values:
            lookup[normalize_name(value)] = canonical
    return lookup


def infer_column_mapping(columns: Iterable[str]) -> Dict[str, str]:
    """Return mapping original_column -> canonical_column."""
    lookup = build_alias_lookup()
    mapping: Dict[str, str] = {}
    used_canonicals = set()

    normalized_to_original = {normalize_name(col): col for col in columns}

    for original in columns:
        normalized = normalize_name(original)
        canonical = lookup.get(normalized)
        if canonical and canonical not in used_canonicals:
            mapping[original] = canonical
            used_canonicals.add(canonical)

    # Heurísticas complementares para nomes compostos
    for original in columns:
        if original in mapping:
            continue
        n = normalize_name(original)

        candidate: Optional[str] = None

        if "cluster" in n:
            candidate = "cluster"
        elif n in {"host", "hostname"} or "esxi" in n or ("host" in n and "ghost" not in n):
            candidate = "host"
        elif n in {"vm", "nome", "resource"} or "vm" in n or "virtual" in n:
            candidate = "vm"
        elif "datastore" in n or n.startswith("ds_") or n == "ds":
            if "pct" in n or "percent" in n or "uso" in n or "used" in n:
                candidate = "datastore_used_pct"
            else:
                candidate = "datastore"
        elif "cpu" in n and ("p95" in n or "95" in n or "pct" in n or "usage" in n or "uso" in n):
            candidate = "cpu_p95"
        elif ("mem" in n or "memory" in n or "ram" in n) and ("p95" in n or "95" in n or "pct" in n or "usage" in n or "uso" in n):
            candidate = "mem_p95"
        elif ("disk" in n or "disco" in n) and ("pct" in n or "percent" in n or "uso" in n or "used" in n):
            candidate = "disk_used_pct"
        elif ("30" in n and ("forecast" in n or "risco" in n or "previs" in n)):
            candidate = "forecast_30d"
        elif ("60" in n and ("forecast" in n or "risco" in n or "previs" in n)):
            candidate = "forecast_60d"
        elif ("90" in n and ("forecast" in n or "risco" in n or "previs" in n)):
            candidate = "forecast_90d"
        elif "prior" in n or "critic" in n or "sever" in n:
            candidate = "prioridade"
        elif "acao" in n or "recomend" in n or "action" in n:
            candidate = "acao"

        if candidate and candidate not in used_canonicals:
            mapping[original] = candidate
            used_canonicals.add(candidate)

    return mapping


def missing_columns(canonical_columns: Iterable[str], required: Iterable[str]) -> List[str]:
    found = set(canonical_columns)
    return [col for col in required if col not in found]
