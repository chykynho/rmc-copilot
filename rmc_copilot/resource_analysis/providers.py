from __future__ import annotations

from pathlib import Path
from typing import Tuple
import numpy as np
import pandas as pd

from .models import ResourceAnalysisRequest
from .data_loader import load_legacy_metric_pair, filter_period


class LegacyMetricChartProvider:
    """Provider compatível com a lógica antiga baseada nos arquivos MetricChart_*.

    Uso atual: enquanto a coleta direta não estiver plugada, permite validar a lógica
    com os CSVs já baixados manualmente.
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)

    def load(self, req: ResourceAnalysisRequest) -> Tuple[pd.DataFrame, pd.DataFrame]:
        usage, capacity, _, _ = load_legacy_metric_pair(self.base_dir, req)
        return filter_period(usage, req.periodo_dias), filter_period(capacity, req.periodo_dias)


class MockTimeseriesProvider:
    """Gera séries locais determinísticas para teste no PC particular.

    O mock foi calibrado para reproduzir os cenários do PDF de referência:
    - CPU: superdimensionada, com picos isolados.
    - MEM: crítica, próxima do limite.
    - DISK C: OK, com folga operacional.
    - DISK E: crítica, acima da margem de segurança.

    Isso não tenta simular o ambiente real; serve para validar interface, gráficos,
    relatório e diagnóstico antes de conectar a base histórica real do RMC.
    """

    def load(self, req: ResourceAnalysisRequest) -> Tuple[pd.DataFrame, pd.DataFrame]:
        days = max(30, int(req.periodo_dias or 90))
        samples_per_day = 4
        n = days * samples_per_day
        dates = pd.date_range(
            pd.Timestamp.today().normalize() - pd.Timedelta(days=days),
            periods=n,
            freq=f"{24 // samples_per_day}h",
        )
        rng = np.random.default_rng(1809645)

        if req.resource == "CPU":
            capacity = 20.75
            base = rng.normal(0.85, 0.25, n)
            spikes = (rng.random(n) > 0.965) * rng.uniform(5.0, 25.0, n)
            values = np.clip(base + spikes, 0.15, capacity * 1.25)

        elif req.resource == "MEM":
            capacity = 48.0
            trend = np.linspace(42.5, 47.8, n)
            noise = rng.normal(0, 0.8, n)
            drops = (rng.random(n) > 0.985) * rng.uniform(8.0, 18.0, n)
            values = np.clip(trend + noise - drops, 0.0, capacity * 1.02)

        elif req.resource == "DISK":
            part = str(req.partition or "").upper().replace(":", "").strip()
            if part == "E":
                capacity = 100.0
                trend = np.linspace(86.0, 93.5, n)
                noise = rng.normal(0, 0.45, n)
                # pequena limpeza no início, depois crescimento gradual
                values = trend + noise
                if n > 20:
                    values[: min(18, n)] += np.linspace(5, 0, min(18, n))
                values = np.clip(values, 0, capacity * 1.05)
            else:
                # C: ou outras partições no mock local seguem cenário OK
                capacity = 179.4
                trend = np.linspace(74.0, 81.0, n)
                noise = rng.normal(0, 1.2, n)
                values = trend + noise
                if n > 40:
                    values[n // 3 : n // 3 + 12] += rng.uniform(2.0, 5.0, 12)
                    values[n // 2 : n // 2 + 16] -= rng.uniform(2.0, 5.0, 16)
                values = np.clip(values, 0, capacity)
        else:
            raise ValueError(f"Recurso não suportado no mock: {req.resource}")

        usage = pd.DataFrame({"Date": dates, "Value": values})
        cap = pd.DataFrame({"Date": dates, "Value": [capacity] * len(dates)})
        return usage, cap


class RmcTimeseriesProvider:
    """Contrato do provider definitivo.

    No ambiente controlado, este provider deve chamar a base interna alimentada pela
    coleta real do RMC/vROps/vCenter. Mantemos a interface aqui para o dashboard e o
    gerador não dependerem de nomes de CSV.
    """

    def __init__(self, store_path: str | Path | None = None):
        self.store_path = Path(store_path) if store_path else None

    def load(self, req: ResourceAnalysisRequest) -> Tuple[pd.DataFrame, pd.DataFrame]:
        raise NotImplementedError(
            "RmcTimeseriesProvider será plugado no ambiente controlado, usando a base histórica real da coleta. "
            "Enquanto isso, use LegacyMetricChartProvider ou MockTimeseriesProvider."
        )

# Provider DuckDB oficial separado para evitar acoplamento forte com o mock/legacy.
try:  # pragma: no cover
    from .duckdb_provider import DuckDBTimeseriesProvider
except Exception:  # pragma: no cover
    DuckDBTimeseriesProvider = None  # type: ignore
