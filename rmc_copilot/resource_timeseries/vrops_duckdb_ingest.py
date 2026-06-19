from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

try:
    from rmc_copilot.config import DATABASE_PATH
except Exception:  # pragma: no cover
    DATABASE_PATH = Path("data/database/rmc_copilot.duckdb")

from rmc_copilot.resource_timeseries.duckdb_repository import (
    RESOURCE_TABLES,
    connect,
    create_resource_timeseries_schema,
    insert_dataframe,
    register_collection_run,
)

SOURCE_VROPS_DIRECT = "vrops_direct"
SOURCE_VROPS_EXCEL_IMPORT = "vrops_excel_import"


def _now() -> datetime:
    return datetime.now()


def _is_df(value: Any) -> bool:
    return isinstance(value, pd.DataFrame) and not value.empty


def _first_df(namespace: Mapping[str, Any], names: list[str]) -> pd.DataFrame:
    for name in names:
        value = namespace.get(name)
        if _is_df(value):
            return value.copy()
    return pd.DataFrame()


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text and text.lower() != "nan" else None


def _safe_json(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _numeric(series: pd.Series | Any) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _datetime(series: pd.Series | Any) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _date_only(series: pd.Series | Any) -> pd.Series:
    return _datetime(series).dt.date


def _ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = None
    return out[columns]


def _host_from_inventory(df: pd.DataFrame) -> pd.Series:
    if "host" in df.columns:
        return df["host"]
    if "mapping_parent_name" in df.columns:
        method = df.get("mapping_method", pd.Series([""] * len(df), index=df.index)).astype(str).str.upper()
        # Quando a VM foi mapeada via host, mapping_parent_name é o host ESXi.
        return df["mapping_parent_name"].where(method.str.contains("HOST", na=False), None)
    return pd.Series([None] * len(df), index=df.index)


def make_run_id(source_file: str | Path | None = None, run_id: str | None = None) -> str:
    if run_id:
        return str(run_id)
    if source_file:
        return Path(source_file).stem.replace(" ", "_").replace("(", "").replace(")", "")
    return "vrops_direct_" + datetime.now().strftime("%Y%m%d_%H%M%S")


def delete_resource_run(run_id: str, db_path: str | Path | None = None) -> None:
    """Remove uma execução granular antes de recarregar.

    Não apaga tabelas antigas do RMC Copilot, como analise_vms ou historico_vm_metricas.
    """
    create_resource_timeseries_schema(db_path)
    con = connect(db_path)
    for table in RESOURCE_TABLES:
        try:
            if table == "resource_report_artifacts":
                # Artefatos são resultado de solicitações; não possuem run_id.
                continue
            if table == "resource_report_requests":
                con.execute("DELETE FROM resource_report_requests WHERE source_run_id = ?", [run_id])
                continue
            con.execute(f"DELETE FROM {table} WHERE run_id = ?", [run_id])
        except Exception:
            pass
    con.close()


def normalize_inventory(
    df_inventory: pd.DataFrame,
    run_id: str,
    execution_id: str | None = None,
) -> pd.DataFrame:
    if df_inventory is None or df_inventory.empty:
        return pd.DataFrame()
    df = df_inventory.copy()
    df["run_id"] = run_id
    df["execution_id"] = execution_id or run_id
    df["host"] = _host_from_inventory(df)
    df["created_at"] = _now()

    rename_map = {
        "name": "vm",
        "identifier": "vm_resource_id",
    }
    for old, new in rename_map.items():
        if new not in df.columns and old in df.columns:
            df[new] = df[old]

    cols = [
        "run_id",
        "execution_id",
        "cluster",
        "host",
        "vm",
        "vm_resource_id",
        "adapterKindKey",
        "resourceKindKey",
        "mapping_method",
        "mapping_parent_name",
        "os_family_inferred",
        "power_state",
        "vcpu_count",
        "memory_gb",
        "created_at",
    ]
    out = _ensure_columns(df, cols)
    for col in ["vcpu_count", "memory_gb"]:
        out[col] = _numeric(out[col])
    return out.dropna(subset=["vm", "vm_resource_id"])


def normalize_partitions(
    df_partitions: pd.DataFrame,
    run_id: str,
    execution_id: str | None = None,
    df_disk_hist: pd.DataFrame | None = None,
    df_inventory: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if df_partitions is None or df_partitions.empty:
        return pd.DataFrame()
    df = df_partitions.copy()
    df["run_id"] = run_id
    df["execution_id"] = execution_id or run_id
    df["host"] = _host_from_inventory(df)

    if df_inventory is not None and not df_inventory.empty:
        inv = normalize_inventory(df_inventory, run_id, execution_id)
        if not inv.empty:
            inv = inv[["vm_resource_id", "host"]].drop_duplicates("vm_resource_id")
            df = df.merge(inv, on="vm_resource_id", how="left", suffixes=("", "_inv"))
            df["host"] = df["host"].fillna(df.get("host_inv"))
            df = df.drop(columns=[c for c in ["host_inv"] if c in df.columns])

    if "os_family" not in df.columns and "os_family_inferred" in df.columns:
        df["os_family"] = df["os_family_inferred"]

    if "stat_keys_json" not in df.columns:
        if "keys" in df.columns:
            df["stat_keys_json"] = df["keys"].apply(_safe_json)
        else:
            df["stat_keys_json"] = None

    if df_disk_hist is not None and not df_disk_hist.empty:
        dh = df_disk_hist.copy()
        if "date" in dh.columns:
            dh["date"] = _datetime(dh["date"])
        merge_cols = [c for c in ["vm_resource_id", "partition", "filesystem_path"] if c in dh.columns and c in df.columns]
        if merge_cols and "capacity_gb" in dh.columns:
            cap = (
                dh.groupby(merge_cols, dropna=False)
                .agg(
                    capacity_gb=("capacity_gb", "max"),
                    first_seen=("date", "min") if "date" in dh.columns else ("capacity_gb", "size"),
                    last_seen=("date", "max") if "date" in dh.columns else ("capacity_gb", "size"),
                )
                .reset_index()
            )
            df = df.merge(cap, on=merge_cols, how="left", suffixes=("", "_hist"))
            if "capacity_gb_hist" in df.columns:
                df["capacity_gb"] = df.get("capacity_gb").fillna(df["capacity_gb_hist"])
                df = df.drop(columns=["capacity_gb_hist"])
    if "first_seen" not in df.columns:
        df["first_seen"] = None
    if "last_seen" not in df.columns:
        df["last_seen"] = None

    df["created_at"] = _now()
    cols = [
        "run_id",
        "execution_id",
        "cluster",
        "host",
        "vm",
        "vm_resource_id",
        "os_family",
        "partition",
        "filesystem_path",
        "capacity_gb",
        "first_seen",
        "last_seen",
        "stat_keys_json",
        "created_at",
    ]
    out = _ensure_columns(df, cols)
    out["capacity_gb"] = _numeric(out["capacity_gb"])
    out["first_seen"] = _datetime(out["first_seen"])
    out["last_seen"] = _datetime(out["last_seen"])
    return out.dropna(subset=["vm", "vm_resource_id", "partition"])


def _add_host_from_inventory(df: pd.DataFrame, df_inventory: pd.DataFrame | None) -> pd.DataFrame:
    out = df.copy()
    if "host" not in out.columns:
        out["host"] = None
    if df_inventory is None or df_inventory.empty or "vm_resource_id" not in out.columns:
        return out
    inv = df_inventory.copy()
    inv["host_inv"] = _host_from_inventory(inv)
    inv = inv[["vm_resource_id", "host_inv"]].drop_duplicates("vm_resource_id")
    out = out.merge(inv, on="vm_resource_id", how="left")
    out["host"] = out["host"].fillna(out["host_inv"])
    out = out.drop(columns=["host_inv"])
    return out


def normalize_percent_timeseries(
    df_hist: pd.DataFrame,
    resource_type: str,
    run_id: str,
    execution_id: str | None = None,
    source: str = SOURCE_VROPS_DIRECT,
    df_inventory: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if df_hist is None or df_hist.empty:
        return pd.DataFrame()
    df = df_hist.copy()
    df = _add_host_from_inventory(df, df_inventory)
    if "used_pct" not in df.columns and "value" in df.columns:
        df["used_pct"] = df["value"]
    if "date" not in df.columns and "timestamp" in df.columns:
        df["date"] = df["timestamp"]

    df["timestamp"] = _datetime(df["date"])
    df["date"] = df["timestamp"].dt.date
    df["used_pct"] = _numeric(df["used_pct"])
    df["run_id"] = run_id
    df["execution_id"] = execution_id or run_id
    df["resource_type"] = resource_type.upper().replace("MEMORIA", "MEM").replace("DISCO", "DISK")
    df["subresource"] = "AGREGADO"
    df["metric_name"] = "used_pct"
    df["value"] = df["used_pct"]
    df["unit"] = "%"
    df["used_gb"] = None
    df["free_gb"] = None
    df["capacity_gb"] = None
    if "stat_key" not in df.columns:
        df["stat_key"] = df.get("stat_key_used")
    df["source"] = source
    df["created_at"] = _now()

    cols = [
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
    out = _ensure_columns(df, cols)
    return out.dropna(subset=["timestamp", "vm_resource_id", "resource_type", "used_pct"])


def normalize_disk_timeseries(
    df_disk_hist: pd.DataFrame,
    run_id: str,
    execution_id: str | None = None,
    source: str = SOURCE_VROPS_DIRECT,
    df_inventory: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if df_disk_hist is None or df_disk_hist.empty:
        return pd.DataFrame()
    df = df_disk_hist.copy()
    df = _add_host_from_inventory(df, df_inventory)
    if "date" not in df.columns and "timestamp" in df.columns:
        df["date"] = df["timestamp"]

    df["timestamp"] = _datetime(df["date"])
    df["date"] = df["timestamp"].dt.date
    if "used_pct" not in df.columns:
        if "used_gb" in df.columns and "capacity_gb" in df.columns:
            df["used_pct"] = _numeric(df["used_gb"]) / _numeric(df["capacity_gb"]) * 100
        elif "value" in df.columns:
            df["used_pct"] = df["value"]
    df["used_pct"] = _numeric(df["used_pct"])
    for col in ["used_gb", "free_gb", "capacity_gb"]:
        if col not in df.columns:
            df[col] = None
        df[col] = _numeric(df[col])

    if "subresource" not in df.columns:
        if "partition" in df.columns:
            df["subresource"] = df["partition"].astype(str)
        elif "filesystem_path" in df.columns:
            df["subresource"] = df["filesystem_path"].astype(str)
        else:
            df["subresource"] = "AGREGADO"
    df["subresource"] = df["subresource"].replace({"nan": "AGREGADO", "None": "AGREGADO"}).fillna("AGREGADO")

    df["run_id"] = run_id
    df["execution_id"] = execution_id or run_id
    df["resource_type"] = "DISK"
    df["metric_name"] = "used_pct"
    df["value"] = df["used_pct"]
    df["unit"] = "%"
    if "stat_key" not in df.columns:
        df["stat_key"] = None
    df["source"] = source
    df["created_at"] = _now()

    cols = [
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
    out = _ensure_columns(df, cols)
    return out.dropna(subset=["timestamp", "vm_resource_id", "used_pct"])


def normalize_logs(
    logs: Mapping[str, pd.DataFrame] | None,
    run_id: str,
    execution_id: str | None = None,
) -> pd.DataFrame:
    if not logs:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for component, df in logs.items():
        if df is None or df.empty:
            continue
        for _, row in df.iterrows():
            status = str(row.get("status", "INFO"))
            level = "ERROR" if "ERRO" in status.upper() else "INFO"
            message = status
            if row.get("erro") is not None and str(row.get("erro")) != "nan":
                message = f"{status}: {row.get('erro')}"
            rows.append(
                {
                    "log_id": str(uuid.uuid4()),
                    "run_id": run_id,
                    "execution_id": execution_id or run_id,
                    "component": str(component),
                    "level": level,
                    "message": str(message),
                    "details_json": _safe_json(row.to_dict()),
                    "created_at": _now(),
                }
            )
    return pd.DataFrame(rows)


def save_vrops_collection_to_duckdb(
    *,
    run_id: str,
    execution_id: str | None = None,
    df_inventory: pd.DataFrame | None = None,
    df_partitions: pd.DataFrame | None = None,
    df_cpu_hist: pd.DataFrame | None = None,
    df_mem_hist: pd.DataFrame | None = None,
    df_disk_hist: pd.DataFrame | None = None,
    logs: Mapping[str, pd.DataFrame] | None = None,
    source_file: str | Path | None = None,
    source_system: str = SOURCE_VROPS_DIRECT,
    period_days: int | None = None,
    db_path: str | Path | None = None,
    replace: bool = True,
    notes: str | None = None,
) -> pd.DataFrame:
    """Grava a saída da coleta vROps diretamente no DuckDB oficial.

    Espera os DataFrames já produzidos pelo notebook/script v5.10.x:
    - df_all_vms_os ou df_vms_selected como inventário;
    - df_vm_partitions ou df_partitions_selected como partições;
    - df_cpu_hist, df_mem_hist e df_disk_hist como históricos consolidados.
    """
    execution_id = execution_id or run_id
    create_resource_timeseries_schema(db_path)
    if replace:
        delete_resource_run(run_id, db_path=db_path)

    inventory = normalize_inventory(df_inventory, run_id, execution_id) if df_inventory is not None else pd.DataFrame()
    partitions = normalize_partitions(df_partitions, run_id, execution_id, df_disk_hist, inventory) if df_partitions is not None else pd.DataFrame()
    cpu_ts = normalize_percent_timeseries(df_cpu_hist, "CPU", run_id, execution_id, source_system, inventory) if df_cpu_hist is not None else pd.DataFrame()
    mem_ts = normalize_percent_timeseries(df_mem_hist, "MEM", run_id, execution_id, source_system, inventory) if df_mem_hist is not None else pd.DataFrame()
    disk_ts = normalize_disk_timeseries(df_disk_hist, run_id, execution_id, source_system, inventory) if df_disk_hist is not None else pd.DataFrame()
    log_rows = normalize_logs(logs, run_id, execution_id)

    insert_dataframe("vm_inventory_snapshots", inventory, db_path=db_path)
    insert_dataframe("vm_disk_partitions", partitions, db_path=db_path)
    if not cpu_ts.empty:
        insert_dataframe("vm_resource_timeseries", cpu_ts, db_path=db_path)
    if not mem_ts.empty:
        insert_dataframe("vm_resource_timeseries", mem_ts, db_path=db_path)
    if not disk_ts.empty:
        insert_dataframe("vm_resource_timeseries", disk_ts, db_path=db_path)
    insert_dataframe("resource_collection_logs", log_rows, db_path=db_path)

    register_collection_run(
        run_id=run_id,
        execution_id=execution_id,
        source_system=source_system,
        source_file=str(source_file) if source_file else None,
        started_at=None,
        finished_at=_now(),
        period_days=period_days,
        status="OK",
        total_vms=int(inventory["vm_resource_id"].nunique()) if not inventory.empty else None,
        total_rows_cpu=int(len(cpu_ts)),
        total_rows_mem=int(len(mem_ts)),
        total_rows_disk=int(len(disk_ts)),
        notes=notes,
        db_path=db_path,
        replace=True,
    )

    summary = pd.DataFrame(
        [
            {"tabela": "vm_inventory_snapshots", "linhas": len(inventory)},
            {"tabela": "vm_disk_partitions", "linhas": len(partitions)},
            {"tabela": "vm_resource_timeseries_CPU", "linhas": len(cpu_ts)},
            {"tabela": "vm_resource_timeseries_MEM", "linhas": len(mem_ts)},
            {"tabela": "vm_resource_timeseries_DISK", "linhas": len(disk_ts)},
            {"tabela": "resource_collection_logs", "linhas": len(log_rows)},
        ]
    )
    summary.insert(0, "run_id", run_id)
    return summary


def read_excel_sheet_if_exists(xl: pd.ExcelFile, sheet_candidates: list[str]) -> pd.DataFrame:
    existing = {s.upper(): s for s in xl.sheet_names}
    for name in sheet_candidates:
        if name.upper() in existing:
            return pd.read_excel(xl, sheet_name=existing[name.upper()])
    return pd.DataFrame()


def load_vrops_excel_to_duckdb(
    input_excel: str | Path,
    db_path: str | Path | None = None,
    run_id: str | None = None,
    replace: bool = True,
) -> pd.DataFrame:
    input_excel = Path(input_excel)
    xl = pd.ExcelFile(input_excel)

    summary_sheet = read_excel_sheet_if_exists(xl, ["SUMARIO"])
    period_days = None
    if not summary_sheet.empty and "periodo_dias" in summary_sheet.columns:
        try:
            period_days = int(summary_sheet["periodo_dias"].iloc[0])
        except Exception:
            period_days = None

    rid = make_run_id(input_excel, run_id=run_id)
    inventory = read_excel_sheet_if_exists(xl, ["VMS_INVENTARIO", "VMS_SELECIONADAS"])
    partitions = read_excel_sheet_if_exists(xl, ["PARTICOES_SELECIONADAS", "PARTICOES_INVENTARIO"])
    cpu = read_excel_sheet_if_exists(xl, ["HIST_CPU"])
    mem = read_excel_sheet_if_exists(xl, ["HIST_MEM"])
    disk = read_excel_sheet_if_exists(xl, ["HIST_DISK"])
    logs = {
        "CPU": read_excel_sheet_if_exists(xl, ["LOG_CPU"]),
        "MEM": read_excel_sheet_if_exists(xl, ["LOG_MEM"]),
        "DISK": read_excel_sheet_if_exists(xl, ["LOG_DISK"]),
        "STATKEYS_PARTICOES": read_excel_sheet_if_exists(xl, ["LOG_STATKEYS_PARTICOES"]),
        "RELACIONAMENTO": read_excel_sheet_if_exists(xl, ["LOG_RELACIONAMENTO"]),
    }

    return save_vrops_collection_to_duckdb(
        run_id=rid,
        execution_id=rid,
        df_inventory=inventory,
        df_partitions=partitions,
        df_cpu_hist=cpu,
        df_mem_hist=mem,
        df_disk_hist=disk,
        logs=logs,
        source_file=input_excel,
        source_system=SOURCE_VROPS_EXCEL_IMPORT,
        period_days=period_days,
        db_path=db_path or DATABASE_PATH,
        replace=replace,
        notes="Carga granular importada do Excel legado da coleta vROps. Use apenas como transição; a coleta direta deve chamar save_vrops_collection_from_notebook_globals.",
    )


def save_vrops_collection_from_notebook_globals(
    namespace: Mapping[str, Any],
    *,
    db_path: str | Path | None = None,
    run_id: str | None = None,
    source_file: str | Path | None = None,
    replace: bool = True,
) -> pd.DataFrame:
    """Atalho para ser chamado no fim do notebook vROps v5.10.x.

    Uso no notebook:
        from rmc_copilot.resource_timeseries.vrops_duckdb_ingest import save_vrops_collection_from_notebook_globals
        duckdb_summary = save_vrops_collection_from_notebook_globals(globals(), source_file=str(report_file))
        display(duckdb_summary)
    """
    source_file = source_file or namespace.get("report_file") or namespace.get("REPORT_FILE")
    rid = make_run_id(source_file, run_id=run_id)
    period_days = namespace.get("DAYS_BACK_SELECTED") or namespace.get("periodo_dias")
    try:
        period_days = int(period_days) if period_days is not None else None
    except Exception:
        period_days = None

    inventory = _first_df(namespace, ["df_all_vms_os", "df_vms_selected", "df_all_vms", "df_vms"])
    partitions = _first_df(namespace, ["df_partitions_selected", "df_vm_partitions", "df_partitions"])
    cpu = _first_df(namespace, ["df_cpu_hist", "hist_cpu", "df_hist_cpu"])
    mem = _first_df(namespace, ["df_mem_hist", "hist_mem", "df_hist_mem"])
    disk = _first_df(namespace, ["df_disk_hist", "hist_disk", "df_hist_disk"])
    logs = {
        "CPU": _first_df(namespace, ["df_cpu_log", "log_cpu"]),
        "MEM": _first_df(namespace, ["df_mem_log", "log_mem"]),
        "DISK": _first_df(namespace, ["df_disk_log", "log_disk"]),
        "STATKEYS_PARTICOES": _first_df(namespace, ["df_partition_statkey_log"]),
        "RELACIONAMENTO": _first_df(namespace, ["df_relationship_log"]),
    }

    return save_vrops_collection_to_duckdb(
        run_id=rid,
        execution_id=rid,
        df_inventory=inventory,
        df_partitions=partitions,
        df_cpu_hist=cpu,
        df_mem_hist=mem,
        df_disk_hist=disk,
        logs=logs,
        source_file=source_file,
        source_system=SOURCE_VROPS_DIRECT,
        period_days=period_days,
        db_path=db_path or DATABASE_PATH,
        replace=replace,
        notes="Carga granular gravada diretamente pela coleta vROps/notebook, sem depender do Excel como base oficial.",
    )


def _print_resource_summary(db_path: str | Path | None = None) -> None:
    con = connect(db_path)
    df = con.execute(
        """
        SELECT
            run_id,
            resource_type,
            subresource,
            source,
            COUNT(*) AS linhas,
            COUNT(DISTINCT vm_resource_id) AS vms,
            MIN(timestamp) AS primeira_data,
            MAX(timestamp) AS ultima_data
        FROM vm_resource_timeseries
        GROUP BY run_id, resource_type, subresource, source
        ORDER BY run_id DESC, resource_type, subresource
        """
    ).df()
    print(df.to_string(index=False))
    con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa coleta vROps para o DuckDB granular do RMC Copilot.")
    parser.add_argument("--input-excel", required=True, help="Excel legado gerado pela coleta vROps v5.10.x")
    parser.add_argument("--db-path", default=str(DATABASE_PATH), help="Caminho do DuckDB oficial")
    parser.add_argument("--run-id", default=None, help="Run ID opcional. Se omitido, usa o nome do Excel.")
    parser.add_argument("--no-replace", action="store_true", help="Não remove execução anterior com mesmo run_id")
    args = parser.parse_args()

    summary = load_vrops_excel_to_duckdb(
        input_excel=args.input_excel,
        db_path=args.db_path,
        run_id=args.run_id,
        replace=not args.no_replace,
    )
    print("Carga concluída.")
    print(summary.to_string(index=False))
    print("\nResumo por recurso:")
    _print_resource_summary(args.db_path)


if __name__ == "__main__":
    main()
