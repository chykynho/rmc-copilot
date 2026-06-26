from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd

try:
    import duckdb
except Exception:
    duckdb = None

from schema_aliases import infer_column_mapping, missing_columns, REQUIRED_MINIMAL, RECOMMENDED


def read_any(path: str, table: str | None = None, limit: int | None = None) -> pd.DataFrame:
    p = Path(path)
    suffix = p.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(p)
    elif suffix in {".parquet", ".pq"}:
        df = pd.read_parquet(p)
    elif suffix in {".xlsx", ".xlsm", ".xls"}:
        df = pd.read_excel(p)
    elif suffix in {".duckdb", ".db"}:
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
    else:
        raise ValueError(f"Formato não suportado: {suffix}")

    if limit:
        return df.head(limit)
    return df


def series_profile(s: pd.Series) -> Dict[str, Any]:
    non_null = s.dropna()
    result: Dict[str, Any] = {
        "dtype": str(s.dtype),
        "non_null": int(non_null.shape[0]),
        "nulls": int(s.shape[0] - non_null.shape[0]),
        "sample_values": [str(x) for x in non_null.astype(str).head(5).tolist()],
    }
    if pd.api.types.is_numeric_dtype(s):
        result.update({
            "min": None if non_null.empty else float(non_null.min()),
            "max": None if non_null.empty else float(non_null.max()),
            "mean": None if non_null.empty else float(non_null.mean()),
        })
    else:
        result["unique_sample"] = [str(x) for x in non_null.astype(str).drop_duplicates().head(10).tolist()]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Cria perfil de arquivo real do RMC Copilot.")
    parser.add_argument("--input", required=True, help="CSV, Parquet, XLSX ou DuckDB")
    parser.add_argument("--table", default=None, help="Tabela DuckDB, se aplicável")
    parser.add_argument("--out", default="outputs/profile_capacity_file.json")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    df = read_any(args.input, table=args.table, limit=args.limit)
    mapping = infer_column_mapping(df.columns)

    canonical_found = list(mapping.values())
    profile = {
        "input": args.input,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "original_columns": list(map(str, df.columns)),
        "inferred_mapping_original_to_canonical": mapping,
        "canonical_found": canonical_found,
        "missing_minimal": missing_columns(canonical_found, REQUIRED_MINIMAL),
        "missing_recommended": missing_columns(canonical_found, RECOMMENDED),
        "columns_profile": {str(col): series_profile(df[col]) for col in df.columns},
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== PERFIL DO ARQUIVO ===")
    print(f"Arquivo: {args.input}")
    print(f"Linhas: {df.shape[0]}")
    print(f"Colunas: {df.shape[1]}")
    print("")
    print("Mapeamento inferido:")
    for original, canonical in mapping.items():
        print(f"- {original} -> {canonical}")
    print("")
    print(f"Faltando mínimas: {profile['missing_minimal'] or 'nenhuma'}")
    print(f"Faltando recomendadas: {profile['missing_recommended'] or 'nenhuma'}")
    print(f"Perfil salvo em: {out}")


if __name__ == "__main__":
    main()
