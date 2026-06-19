from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

try:
    from rmc_copilot.config import DATABASE_PATH
except Exception:  # pragma: no cover
    DATABASE_PATH = Path("data/database/rmc_copilot.duckdb")


RESOURCE_TABLES = [
    "resource_collection_runs",
    "vm_inventory_snapshots",
    "vm_disk_partitions",
    "vm_resource_timeseries",
    "resource_collection_logs",
    "resource_report_requests",
    "resource_report_artifacts",
]


def _db_path(db_path: str | Path | None = None) -> Path:
    path = Path(db_path) if db_path else Path(DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect(db_path: str | Path | None = None):
    return duckdb.connect(str(_db_path(db_path)))


def create_resource_timeseries_schema(db_path: str | Path | None = None) -> None:
    """Cria as tabelas granulares no DuckDB oficial do RMC Copilot.

    Essa rotina é idempotente: pode ser executada várias vezes sem apagar dados.
    """
    con = connect(db_path)

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS resource_collection_runs (
            run_id VARCHAR,
            execution_id VARCHAR,
            source_system VARCHAR,
            source_file VARCHAR,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            period_days INTEGER,
            status VARCHAR,
            total_vms INTEGER,
            total_rows_cpu INTEGER,
            total_rows_mem INTEGER,
            total_rows_disk INTEGER,
            notes VARCHAR,
            created_at TIMESTAMP
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS vm_inventory_snapshots (
            run_id VARCHAR,
            execution_id VARCHAR,
            cluster VARCHAR,
            host VARCHAR,
            vm VARCHAR,
            vm_resource_id VARCHAR,
            adapterKindKey VARCHAR,
            resourceKindKey VARCHAR,
            mapping_method VARCHAR,
            mapping_parent_name VARCHAR,
            os_family_inferred VARCHAR,
            power_state VARCHAR,
            vcpu_count DOUBLE,
            memory_gb DOUBLE,
            created_at TIMESTAMP
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS vm_disk_partitions (
            run_id VARCHAR,
            execution_id VARCHAR,
            cluster VARCHAR,
            host VARCHAR,
            vm VARCHAR,
            vm_resource_id VARCHAR,
            os_family VARCHAR,
            partition VARCHAR,
            filesystem_path VARCHAR,
            capacity_gb DOUBLE,
            first_seen TIMESTAMP,
            last_seen TIMESTAMP,
            stat_keys_json VARCHAR,
            created_at TIMESTAMP
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS vm_resource_timeseries (
            run_id VARCHAR,
            execution_id VARCHAR,
            timestamp TIMESTAMP,
            date DATE,
            cluster VARCHAR,
            host VARCHAR,
            vm VARCHAR,
            vm_resource_id VARCHAR,
            resource_type VARCHAR,
            subresource VARCHAR,
            metric_name VARCHAR,
            value DOUBLE,
            unit VARCHAR,
            used_pct DOUBLE,
            used_gb DOUBLE,
            free_gb DOUBLE,
            capacity_gb DOUBLE,
            stat_key VARCHAR,
            source VARCHAR,
            created_at TIMESTAMP
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS resource_collection_logs (
            log_id VARCHAR,
            run_id VARCHAR,
            execution_id VARCHAR,
            component VARCHAR,
            level VARCHAR,
            message VARCHAR,
            details_json VARCHAR,
            created_at TIMESTAMP
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS resource_report_requests (
            request_id VARCHAR,
            solicitacao VARCHAR,
            vm VARCHAR,
            vm_resource_id VARCHAR,
            resources VARCHAR,
            partitions VARCHAR,
            period_days INTEGER,
            requested_by VARCHAR,
            analyst VARCHAR,
            classification VARCHAR,
            source_run_id VARCHAR,
            created_at TIMESTAMP
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS resource_report_artifacts (
            artifact_id VARCHAR,
            request_id VARCHAR,
            solicitacao VARCHAR,
            vm VARCHAR,
            artifact_type VARCHAR,
            artifact_path VARCHAR,
            created_at TIMESTAMP
        )
        """
    )

    # Views de conveniência para dashboard/provider.
    con.execute(
        """
        CREATE OR REPLACE VIEW vw_latest_resource_collection_run AS
        SELECT *
        FROM resource_collection_runs
        QUALIFY ROW_NUMBER() OVER (ORDER BY COALESCE(finished_at, started_at, created_at) DESC) = 1
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_latest_vm_resource_timeseries AS
        SELECT t.*
        FROM vm_resource_timeseries t
        INNER JOIN vw_latest_resource_collection_run r
            ON t.run_id = r.run_id
        """
    )

    # Índices ajudam consultas interativas no dashboard.
    for sql in [
        "CREATE INDEX IF NOT EXISTS idx_vm_resource_timeseries_run_vm ON vm_resource_timeseries(run_id, vm_resource_id)",
        "CREATE INDEX IF NOT EXISTS idx_vm_resource_timeseries_vm_resource ON vm_resource_timeseries(vm, resource_type)",
        "CREATE INDEX IF NOT EXISTS idx_vm_inventory_snapshots_run_vm ON vm_inventory_snapshots(run_id, vm_resource_id)",
        "CREATE INDEX IF NOT EXISTS idx_vm_disk_partitions_run_vm ON vm_disk_partitions(run_id, vm_resource_id)",
    ]:
        try:
            con.execute(sql)
        except Exception:
            # Algumas versões do DuckDB podem variar no suporte a índices IF NOT EXISTS.
            pass

    con.close()


def _safe_json(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = pd.to_datetime(out[col], errors="coerce")
        elif out[col].dtype == "object":
            out[col] = out[col].where(out[col].notna(), None)
    return out


def insert_dataframe(
    table_name: str,
    df: pd.DataFrame,
    db_path: str | Path | None = None,
    replace_run_id: str | None = None,
) -> int:
    if df is None or df.empty:
        return 0
    create_resource_timeseries_schema(db_path)
    con = connect(db_path)
    if replace_run_id:
        con.execute(f"DELETE FROM {table_name} WHERE run_id = ?", [replace_run_id])
    tmp = _prepare_dataframe(df)
    con.register("_rmc_tmp_df", tmp)
    con.execute(f"INSERT INTO {table_name} SELECT * FROM _rmc_tmp_df")
    con.close()
    return int(len(tmp))


def register_collection_run(
    run_id: str,
    execution_id: str | None = None,
    source_system: str = "vrops",
    source_file: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    period_days: int | None = None,
    status: str = "OK",
    total_vms: int | None = None,
    total_rows_cpu: int | None = None,
    total_rows_mem: int | None = None,
    total_rows_disk: int | None = None,
    notes: str | None = None,
    db_path: str | Path | None = None,
    replace: bool = True,
) -> None:
    create_resource_timeseries_schema(db_path)
    con = connect(db_path)
    if replace:
        con.execute("DELETE FROM resource_collection_runs WHERE run_id = ?", [run_id])
    row = pd.DataFrame([
        {
            "run_id": run_id,
            "execution_id": execution_id,
            "source_system": source_system,
            "source_file": source_file,
            "started_at": started_at,
            "finished_at": finished_at or datetime.now(),
            "period_days": period_days,
            "status": status,
            "total_vms": total_vms,
            "total_rows_cpu": total_rows_cpu,
            "total_rows_mem": total_rows_mem,
            "total_rows_disk": total_rows_disk,
            "notes": notes,
            "created_at": datetime.now(),
        }
    ])
    con.register("_run_df", row)
    con.execute("INSERT INTO resource_collection_runs SELECT * FROM _run_df")
    con.close()


def migrate_legacy_historico_vm_metricas(
    db_path: str | Path | None = None,
    execution_id: str | None = None,
    replace: bool = True,
) -> pd.DataFrame:
    """Migra a tabela legada historico_vm_metricas para o contrato granular.

    A tabela legada possui apenas percentual por recurso. Por isso:
    - CPU e MEM são gravados como subresource='AGREGADO';
    - DISCO é gravado como subresource='AGREGADO';
    - capacity_gb, used_gb e free_gb ficam nulos.

    A coleta vROps nova deverá popular a mesma tabela com partições e capacidades reais.
    """
    create_resource_timeseries_schema(db_path)
    con = connect(db_path)

    where = ""
    params: list[Any] = []
    if execution_id:
        where = "WHERE execution_id = ?"
        params = [execution_id]

    hist = con.execute(
        f"""
        SELECT execution_id, cluster, vm, vm_resource_id, date, recurso, used_pct
        FROM historico_vm_metricas
        {where}
        """,
        params,
    ).df()

    if hist.empty:
        con.close()
        return pd.DataFrame()

    hist["timestamp"] = pd.to_datetime(hist["date"], errors="coerce")
    hist["date"] = hist["timestamp"].dt.date
    hist["resource_type"] = hist["recurso"].astype(str).str.upper().replace(
        {"MEMORIA": "MEM", "DISCO": "DISK"}
    )
    hist["subresource"] = "AGREGADO"
    hist["metric_name"] = "used_pct"
    hist["value"] = pd.to_numeric(hist["used_pct"], errors="coerce")
    hist["unit"] = "%"
    hist["used_gb"] = None
    hist["free_gb"] = None
    hist["capacity_gb"] = None
    hist["stat_key"] = None
    hist["source"] = "legacy_historico_vm_metricas"
    hist["host"] = None
    hist["created_at"] = datetime.now()
    hist["run_id"] = hist["execution_id"].astype(str)

    out = hist[
        [
            "run_id",
            "execution_id",
            "timestamp",
            "date",
            "cluster",
            "host",
            "vm",
            "vm_resource_id",
            "resource_type",
            "subresource",
            "metric_name",
            "value",
            "unit",
            "used_pct",
            "used_gb",
            "free_gb",
            "capacity_gb",
            "stat_key",
            "source",
            "created_at",
        ]
    ].dropna(subset=["timestamp", "vm_resource_id", "resource_type", "value"])

    run_rows = []
    for run_id, g in out.groupby("run_id"):
        if replace:
            con.execute("DELETE FROM vm_resource_timeseries WHERE run_id = ? AND source = 'legacy_historico_vm_metricas'", [run_id])
            con.execute("DELETE FROM resource_collection_runs WHERE run_id = ? AND source_system = 'legacy_db_migration'", [run_id])
        run_rows.append(
            {
                "run_id": run_id,
                "execution_id": run_id,
                "source_system": "legacy_db_migration",
                "source_file": None,
                "started_at": None,
                "finished_at": datetime.now(),
                "period_days": None,
                "status": "OK",
                "total_vms": int(g["vm_resource_id"].nunique()),
                "total_rows_cpu": int((g["resource_type"] == "CPU").sum()),
                "total_rows_mem": int((g["resource_type"] == "MEM").sum()),
                "total_rows_disk": int((g["resource_type"] == "DISK").sum()),
                "notes": "Migração da tabela legada historico_vm_metricas. DISK sem partição/capacidade nesta origem.",
                "created_at": datetime.now(),
            }
        )

    con.register("_timeseries_out", _prepare_dataframe(out))
    con.execute("INSERT INTO vm_resource_timeseries SELECT * FROM _timeseries_out")

    runs_df = pd.DataFrame(run_rows)
    con.register("_runs_out", runs_df)
    con.execute("INSERT INTO resource_collection_runs SELECT * FROM _runs_out")

    summary = con.execute(
        """
        SELECT run_id, resource_type, COUNT(*) AS linhas, COUNT(DISTINCT vm_resource_id) AS vms
        FROM vm_resource_timeseries
        WHERE source = 'legacy_historico_vm_metricas'
        GROUP BY run_id, resource_type
        ORDER BY run_id, resource_type
        """
    ).df()
    con.close()
    return summary


def inspect_resource_timeseries_schema(db_path: str | Path | None = None) -> dict[str, pd.DataFrame]:
    create_resource_timeseries_schema(db_path)
    con = connect(db_path)
    result: dict[str, pd.DataFrame] = {}
    for table in RESOURCE_TABLES:
        try:
            result[f"{table}__describe"] = con.execute(f"DESCRIBE {table}").df()
            result[f"{table}__count"] = con.execute(f"SELECT COUNT(*) AS linhas FROM {table}").df()
        except Exception as exc:
            result[f"{table}__error"] = pd.DataFrame([{"erro": str(exc)}])
    con.close()
    return result
