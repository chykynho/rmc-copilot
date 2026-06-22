from __future__ import annotations

from pathlib import Path
from typing import Tuple
import uuid
from datetime import datetime

import pandas as pd

from .models import ResourceAnalysisRequest

try:
    from rmc_copilot.config import DATABASE_PATH
except Exception:  # pragma: no cover
    DATABASE_PATH = Path("data/database/rmc_copilot.duckdb")

from rmc_copilot.resource_timeseries.duckdb_repository import connect


PREFERRED_SOURCES = ("vrops_direct", "vrops_excel_import", "legacy_historico_vm_metricas")


class DuckDBTimeseriesProvider:
    """Provider oficial para relatórios individuais usando o DuckDB do RMC Copilot.

    Regras:
    - usa a execução mais recente de resource_collection_runs, salvo se run_id for informado;
    - prioriza fonte granular vROps direta/importada;
    - CPU/MEM usam percentual quando capacidade real ainda não existe no contrato;
    - DISK usa used_gb/capacity_gb quando a coleta granular trouxe partição real.
    """

    def __init__(self, db_path: str | Path | None = None, run_id: str | None = None):
        self.db_path = Path(db_path) if db_path else Path(DATABASE_PATH)
        self.run_id = run_id
        # Não cria/altera schema no provider. Em Streamlit, múltiplas instâncias podem
        # abrir o DuckDB ao mesmo tempo; operações de catálogo como CREATE OR REPLACE VIEW
        # causam write-write conflict. O schema deve ser inicializado pelos scripts 36/39.

    def list_runs(self) -> pd.DataFrame:
        con = connect(self.db_path)
        df = con.execute(
            """
            SELECT run_id, source_system, status, total_vms, total_rows_cpu, total_rows_mem, total_rows_disk,
                   COALESCE(finished_at, started_at, created_at) AS data_referencia,
                   source_file, notes
            FROM resource_collection_runs
            ORDER BY COALESCE(finished_at, started_at, created_at) DESC
            """
        ).df()
        con.close()
        return df

    def latest_run_id(self) -> str | None:
        if self.run_id:
            return self.run_id
        runs = self.list_runs()
        if runs.empty:
            return None
        # Preferimos coleta granular direta/importada. Legacy fica como fallback.
        preferred = runs[runs["source_system"].isin(["vrops_direct", "vrops_excel_import"])]
        if not preferred.empty:
            return str(preferred.iloc[0]["run_id"])
        return str(runs.iloc[0]["run_id"])

    def list_vms(self, run_id: str | None = None, limit: int = 10000) -> pd.DataFrame:
        rid = run_id or self.latest_run_id()
        if not rid:
            return pd.DataFrame(columns=["cluster", "host", "vm", "vm_resource_id", "os_family_inferred"])
        con = connect(self.db_path)
        df = con.execute(
            """
            WITH inv AS (
                SELECT cluster, host, vm, vm_resource_id, os_family_inferred
                FROM vm_inventory_snapshots
                WHERE run_id = ?
            ), ts AS (
                SELECT cluster, host, vm, vm_resource_id, NULL::VARCHAR AS os_family_inferred
                FROM vm_resource_timeseries
                WHERE run_id = ?
                GROUP BY cluster, host, vm, vm_resource_id
            )
            SELECT * FROM inv
            UNION BY NAME
            SELECT * FROM ts
            ORDER BY cluster, vm
            LIMIT ?
            """,
            [rid, rid, int(limit)],
        ).df()
        con.close()
        if df.empty:
            return df
        return df.drop_duplicates("vm_resource_id").sort_values(["cluster", "vm"]).reset_index(drop=True)

    def list_partitions(
        self,
        vm_resource_id: str | None = None,
        vm: str | None = None,
        run_id: str | None = None,
    ) -> pd.DataFrame:
        rid = run_id or self.latest_run_id()
        if not rid:
            return pd.DataFrame(columns=["partition", "filesystem_path", "capacity_gb", "amostras"])
        where = "run_id = ?"
        params: list[object] = [rid]
        if vm_resource_id:
            where += " AND vm_resource_id = ?"
            params.append(vm_resource_id)
        elif vm:
            where += " AND vm = ?"
            params.append(vm)

        con = connect(self.db_path)
        # Primeiro tenta o cadastro de partições; se estiver vazio, cai para a timeseries.
        parts = con.execute(
            f"""
            SELECT partition, filesystem_path, MAX(capacity_gb) AS capacity_gb, COUNT(*) AS registros
            FROM vm_disk_partitions
            WHERE {where}
            GROUP BY partition, filesystem_path
            ORDER BY partition, filesystem_path
            """,
            params,
        ).df()
        if parts.empty:
            parts = con.execute(
                f"""
                SELECT subresource AS partition,
                       subresource AS filesystem_path,
                       MAX(capacity_gb) AS capacity_gb,
                       COUNT(*) AS registros
                FROM vm_resource_timeseries
                WHERE {where}
                  AND resource_type = 'DISK'
                GROUP BY subresource
                ORDER BY subresource
                """,
                params,
            ).df()
        con.close()
        if parts.empty:
            return parts
        parts["label"] = parts.apply(
            lambda r: f"{r['partition']}" + (f" — {float(r['capacity_gb']):.1f} GB" if pd.notna(r.get("capacity_gb")) else ""),
            axis=1,
        )
        return parts.reset_index(drop=True)

    def _resolve_vm(self, req: ResourceAnalysisRequest, run_id: str) -> tuple[str | None, str | None, str | None]:
        if getattr(req, "vm_resource_id", None):
            return str(req.vm_resource_id), req.vm, None
        con = connect(self.db_path)
        df = con.execute(
            """
            SELECT vm_resource_id, vm, cluster
            FROM (
                SELECT vm_resource_id, vm, cluster FROM vm_inventory_snapshots WHERE run_id = ?
                UNION BY NAME
                SELECT vm_resource_id, vm, cluster FROM vm_resource_timeseries WHERE run_id = ? GROUP BY vm_resource_id, vm, cluster
            )
            WHERE lower(vm) = lower(?)
            LIMIT 2
            """,
            [run_id, run_id, req.vm],
        ).df()
        con.close()
        if df.empty:
            return None, None, None
        return str(df.iloc[0]["vm_resource_id"]), str(df.iloc[0]["vm"]), str(df.iloc[0].get("cluster"))

    def load(self, req: ResourceAnalysisRequest) -> Tuple[pd.DataFrame, pd.DataFrame]:
        run_id = self.latest_run_id()
        if not run_id:
            raise ValueError("Nenhuma execução encontrada em resource_collection_runs.")
        vm_resource_id, vm_name, _cluster = self._resolve_vm(req, run_id)
        if not vm_resource_id:
            raise ValueError(f"VM não encontrada no DuckDB para a execução {run_id}: {req.vm}")

        resource_type = "MEM" if req.resource == "MEM" else req.resource
        subresource = "AGREGADO" if req.resource in {"CPU", "MEM"} else str(req.partition or "").strip()
        if req.resource == "DISK" and not subresource:
            raise ValueError("Partição obrigatória para DISK.")

        con = connect(self.db_path)
        if req.resource == "DISK":
            rows = con.execute(
                """
                SELECT timestamp AS Date,
                       used_gb,
                       capacity_gb,
                       used_pct,
                       source
                FROM vm_resource_timeseries
                WHERE run_id = ?
                  AND vm_resource_id = ?
                  AND resource_type = 'DISK'
                  AND subresource = ?
                  AND timestamp >= (SELECT MAX(timestamp) - (? || ' days')::INTERVAL
                                    FROM vm_resource_timeseries
                                    WHERE run_id = ? AND vm_resource_id = ? AND resource_type = 'DISK' AND subresource = ?)
                ORDER BY timestamp
                """,
                [run_id, vm_resource_id, subresource, int(req.periodo_dias), run_id, vm_resource_id, subresource],
            ).df()
        else:
            rows = con.execute(
                """
                SELECT timestamp AS Date,
                       used_pct,
                       source
                FROM vm_resource_timeseries
                WHERE run_id = ?
                  AND vm_resource_id = ?
                  AND resource_type = ?
                  AND subresource = 'AGREGADO'
                  AND timestamp >= (SELECT MAX(timestamp) - (? || ' days')::INTERVAL
                                    FROM vm_resource_timeseries
                                    WHERE run_id = ? AND vm_resource_id = ? AND resource_type = ? AND subresource = 'AGREGADO')
                ORDER BY timestamp
                """,
                [run_id, vm_resource_id, resource_type, int(req.periodo_dias), run_id, vm_resource_id, resource_type],
            ).df()
        con.close()

        if rows.empty:
            raise ValueError(f"Sem série histórica para {req.vm} / {req.resource} / {subresource} na execução {run_id}.")

        rows["Date"] = pd.to_datetime(rows["Date"], errors="coerce")
        if req.resource == "DISK":
            # Para disco, o contrato granular possui used_gb/free_gb/capacity_gb.
            if rows["used_gb"].notna().any() and rows["capacity_gb"].notna().any():
                usage = rows[["Date", "used_gb"]].rename(columns={"used_gb": "Value"}).dropna()
                cap = rows[["Date", "capacity_gb"]].rename(columns={"capacity_gb": "Value"}).dropna()
                cap["Value"] = pd.to_numeric(cap["Value"], errors="coerce").ffill().bfill()
                usage.attrs["source_unit"] = "GB"
                cap.attrs["source_unit"] = "GB"
            else:
                # Fallback legacy: percentual, sem capacidade em GB.
                usage = rows[["Date", "used_pct"]].rename(columns={"used_pct": "Value"}).dropna()
                cap = usage[["Date"]].copy()
                cap["Value"] = 100.0
                usage.attrs["source_unit"] = "%"
                cap.attrs["source_unit"] = "%"
        else:
            # CPU/MEM no contrato atual estão como percentual. Capacidade operacional real será plugada em etapa futura.
            usage = rows[["Date", "used_pct"]].rename(columns={"used_pct": "Value"}).dropna()
            cap = usage[["Date"]].copy()
            cap["Value"] = 100.0
            usage.attrs["source_unit"] = "%"
            cap.attrs["source_unit"] = "%"

        usage["Value"] = pd.to_numeric(usage["Value"], errors="coerce")
        cap["Value"] = pd.to_numeric(cap["Value"], errors="coerce")
        usage = usage.dropna(subset=["Date", "Value"]).sort_values("Date").reset_index(drop=True)
        cap = cap.dropna(subset=["Date", "Value"]).sort_values("Date").reset_index(drop=True)
        if usage.empty or cap.empty:
            raise ValueError(f"Série sem valores úteis para {req.vm} / {req.resource} / {subresource}.")
        return usage, cap


# Auditoria de relatórios: usada pela tela/CLI para registrar solicitações e artefatos gerados.
def register_report_request(
    *,
    solicitacao: str,
    vm: str,
    vm_resource_id: str | None,
    resources: str,
    partitions: str,
    period_days: int,
    requested_by: str,
    analyst: str,
    classification: str,
    source_run_id: str | None,
    db_path: str | Path | None = None,
) -> str:
    request_id = str(uuid.uuid4())
    con = connect(db_path)
    df = pd.DataFrame([
        {
            "request_id": request_id,
            "solicitacao": solicitacao,
            "vm": vm,
            "vm_resource_id": vm_resource_id,
            "resources": resources,
            "partitions": partitions,
            "period_days": int(period_days),
            "requested_by": requested_by,
            "analyst": analyst,
            "classification": classification,
            "source_run_id": source_run_id,
            "created_at": datetime.now(),
        }
    ])
    con.register("_report_request", df)
    con.execute("INSERT INTO resource_report_requests SELECT * FROM _report_request")
    con.close()
    return request_id


def register_report_artifacts(
    *,
    request_id: str,
    solicitacao: str,
    vm: str,
    artifact_paths: list[str | Path],
    db_path: str | Path | None = None,
) -> int:
    if not artifact_paths:
        return 0
    rows = []
    for path in artifact_paths:
        p = Path(path)
        if not p:
            continue
        suffix = p.suffix.lower().lstrip(".") or "file"
        rows.append(
            {
                "artifact_id": str(uuid.uuid4()),
                "request_id": request_id,
                "solicitacao": solicitacao,
                "vm": vm,
                "artifact_type": suffix,
                "artifact_path": str(p),
                "created_at": datetime.now(),
            }
        )
    if not rows:
        return 0
    con = connect(db_path)
    df = pd.DataFrame(rows)
    con.register("_report_artifacts", df)
    con.execute("INSERT INTO resource_report_artifacts SELECT * FROM _report_artifacts")
    con.close()
    return len(rows)
