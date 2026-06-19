from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence
import re


RESOURCE_ALIASES = {
    "CPU": "CPU",
    "PROCESSAMENTO": "CPU",
    "MEM": "MEM",
    "MEMORIA": "MEM",
    "MEMÓRIA": "MEM",
    "RAM": "MEM",
    "DSK": "DISK",
    "DISCO": "DISK",
    "DISK": "DISK",
    "PARTITION": "DISK",
    "PARTIÇÃO": "DISK",
    "PARTICAO": "DISK",
}

RESOURCE_LABELS = {
    "CPU": "Processamento (CPU)",
    "MEM": "Memória (RAM)",
    "DISK": "Disco / Partição",
}

RESOURCE_UNITS = {
    "CPU": "GHz",
    "MEM": "GB",
    "DISK": "GB",
}


def normalize_resource(resource: str) -> str:
    key = str(resource or "").strip().upper()
    key = key.replace("Ê", "E").replace("Ó", "O").replace("Í", "I")
    return RESOURCE_ALIASES.get(key, key)


def sanitize_name(value: str, default: str = "NA") -> str:
    value = str(value or "").strip()
    if not value:
        value = default
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value.strip("._-") or default


@dataclass
class ResourceAnalysisRequest:
    solicitacao: str
    vm: str
    resource: str
    partition: Optional[str] = None
    periodo_dias: int = 90
    solicitante: str = ""
    analista: str = ""
    classificacao: str = "PÚBLICO"
    threshold_pct: float = 80.0
    origem: str = "RMC Copilot"
    vm_resource_id: Optional[str] = None

    def __post_init__(self) -> None:
        self.solicitacao = str(self.solicitacao or "").strip().upper()
        self.vm = str(self.vm or "").strip()
        self.resource = normalize_resource(self.resource)
        self.partition = str(self.partition or "").strip() or None
        self.classificacao = str(self.classificacao or "PÚBLICO").strip().upper()
        self.vm_resource_id = str(self.vm_resource_id or "").strip() or None
        self.periodo_dias = int(self.periodo_dias or 90)
        # Não preencher partição automaticamente.
        # Para DISK, a partição deve ser informada explicitamente na tela/CLI
        # para evitar gerar relatório incorreto sem intenção do usuário.

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.solicitacao:
            errors.append("Número da solicitação é obrigatório.")
        if not self.vm:
            errors.append("VM é obrigatória.")
        if self.resource not in {"CPU", "MEM", "DISK"}:
            errors.append("Recurso deve ser CPU, MEM ou DISK.")
        if self.resource == "DISK" and not self.partition:
            errors.append("Partição é obrigatória quando o recurso é Disco.")
        if self.periodo_dias <= 0:
            errors.append("Período histórico deve ser maior que zero.")
        return errors

    @property
    def resource_title(self) -> str:
        if self.resource == "DISK":
            return f"Disco (Partição {self.partition})"
        return RESOURCE_LABELS.get(self.resource, self.resource)

    @property
    def unit(self) -> str:
        return RESOURCE_UNITS.get(self.resource, "")

    @property
    def safe_solicitacao(self) -> str:
        return sanitize_name(self.solicitacao, "SOL")

    @property
    def safe_vm(self) -> str:
        return sanitize_name(self.vm, "VM")

    @property
    def safe_resource(self) -> str:
        suffix = f"_{sanitize_name(self.partition)}" if self.resource == "DISK" else ""
        return f"{self.resource}{suffix}"

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class ResourceStats:
    resource: str
    unit: str
    capacity: float
    threshold_pct: float
    threshold_value: float
    start: str
    end: str
    samples: int
    minimum: float
    maximum: float
    mean: float
    median: float
    q1: float
    q3: float
    p95: float
    std: float
    iqr: float
    lower_outlier: float
    upper_outlier: float
    mean_pct: float
    median_pct: float
    maximum_pct: float
    p95_pct: float
    forecast_30: float
    forecast_60: float
    forecast_90: float
    forecast_30_pct: float
    forecast_60_pct: float
    forecast_90_pct: float
    diagnosis: str
    recommendation_action: str
    recommended_capacity: Optional[float] = None
    recommended_delta: Optional[float] = None
    confidence_note: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)
