from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

try:
    import duckdb
except Exception:
    duckdb = None

from schema_aliases import CANONICAL_COLUMNS, infer_column_mapping, missing_columns, REQUIRED_MINIMAL, RECOMMENDED


def read_any(path: str, table: Optional[str] = None) -> pd.DataFrame:
    p = Path(path)
    suffix = p.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(p)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(p)
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(p)
    if suffix in {".duckdb", ".db"}:
        if duckdb is None:
            raise RuntimeError("DuckDB não está instalado. Rode: pip install duckdb")
        con = duckdb.connect(str(p), read_only=True)
        if not table:
            tables = con.execute("SHOW TABLES").fetchdf()
            if tables.empty:
                raise RuntimeError("Nenhuma tabela encontrada no DuckDB.")
            table = str(tables.iloc[0, 0])
        df = con.execute(f"SELECT * FROM {table}").fetchdf()
        con.close()
        return df

    raise ValueError(f"Formato não suportado: {suffix}")


def normalize_priority(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip().upper()
    if text in {"P0", "CRITICO", "CRÍTICO", "CRITICAL", "TRATAR_IMEDIATO"}:
        return "P0"
    if text in {"P1", "RISCO", "ALTO", "HIGH", "ANALISAR_CURTO_PRAZO"}:
        return "P1"
    if text in {"P2", "ATENCAO", "ATENÇÃO", "MEDIO", "MÉDIO", "PLANEJAR_60D"}:
        return "P2"
    if text in {"P3", "OTIMIZACAO", "OTIMIZAÇÃO", "RIGHTSIZING", "VALIDAR_RIGHTSIZING"}:
        return "P3"
    if text in {"P4", "OK", "MONITORAMENTO", "MANTER_MONITORAMENTO"}:
        return "P4"
    return text


def normalize_forecast_value(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().upper()
    if text in {"", "NONE", "NAN", "NA", "SEM_RISCO", "SEM_RISCO_90D"}:
        return ""
    # Formatos como 30D_DISK, DISK_30D, risco DISK etc.
    found = []
    if "DISK" in text or "DISCO" in text or "STORAGE" in text:
        found.append("DISK")
    if "MEM" in text or "MEMORIA" in text or "MEMÓRIA" in text or "RAM" in text:
        found.append("MEM")
    if "CPU" in text or "VCPU" in text:
        found.append("CPU")
    if found:
        return "|".join(dict.fromkeys(found))
    return text


def to_number_percent(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("%", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return pd.NA


def normalize_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, Dict[str, str]]:
    mapping = infer_column_mapping(df.columns)
    out = pd.DataFrame()

    for original, canonical in mapping.items():
        if canonical in out.columns:
            continue
        out[canonical] = df[original]

    for col in CANONICAL_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    for col in ["cpu_p95", "mem_p95", "disk_used_pct", "datastore_used_pct"]:
        out[col] = out[col].map(to_number_percent)

    for col in ["forecast_30d", "forecast_60d", "forecast_90d"]:
        out[col] = out[col].map(normalize_forecast_value)

    out["prioridade"] = out["prioridade"].map(normalize_priority)

    for col in ["cluster", "host", "vm", "datastore", "acao"]:
        out[col] = out[col].fillna("").astype(str).str.strip()

    out = out[CANONICAL_COLUMNS]
    return out, mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="Normaliza arquivo real para schema canônico do RMC Copilot.")
    parser.add_argument("--input", required=True, help="CSV, Parquet, XLSX ou DuckDB")
    parser.add_argument("--table", default=None, help="Tabela DuckDB, se aplicável")
    parser.add_argument("--out", default="outputs/capacity_normalized.csv")
    parser.add_argument("--profile-out", default="outputs/capacity_normalization_profile.json")
    args = parser.parse_args()

    df = read_any(args.input, table=args.table)
    normalized, mapping = normalize_dataframe(df)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(out, index=False, encoding="utf-8-sig")

    profile = {
        "input": args.input,
        "output": str(out),
        "rows_in": int(df.shape[0]),
        "rows_out": int(normalized.shape[0]),
        "mapping": mapping,
        "canonical_columns": list(normalized.columns),
        "missing_minimal": missing_columns(normalized.columns[normalized.notna().any()].tolist(), REQUIRED_MINIMAL),
        "missing_recommended": missing_columns(normalized.columns[normalized.notna().any()].tolist(), RECOMMENDED),
        "priority_counts": normalized["prioridade"].fillna("").astype(str).value_counts().to_dict(),
        "forecast_30d_counts": normalized["forecast_30d"].fillna("").astype(str).value_counts().to_dict(),
    }
    profile_out = Path(args.profile_out)
    profile_out.parent.mkdir(parents=True, exist_ok=True)
    profile_out.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== NORMALIZAÇÃO CONCLUÍDA ===")
    print(f"Entrada: {args.input}")
    print(f"Saída: {out}")
    print(f"Linhas: {normalized.shape[0]}")
    print("Mapeamento:")
    for original, canonical in mapping.items():
        print(f"- {original} -> {canonical}")
    print(f"Perfil salvo em: {profile_out}")


if __name__ == "__main__":
    main()
