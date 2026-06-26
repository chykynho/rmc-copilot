from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

from schema_aliases import CANONICAL_COLUMNS, REQUIRED_MINIMAL, RECOMMENDED


def validate(df: pd.DataFrame) -> Dict[str, object]:
    columns = set(df.columns)
    missing_minimal = [c for c in REQUIRED_MINIMAL if c not in columns]
    missing_recommended = [c for c in RECOMMENDED if c not in columns]

    issues: List[str] = []

    if missing_minimal:
        issues.append(f"Colunas mínimas ausentes: {missing_minimal}")

    if "prioridade" in df.columns:
        valid = {"P0", "P1", "P2", "P3", "P4", ""}
        invalid = sorted(set(df["prioridade"].fillna("").astype(str).str.upper()) - valid)
        if invalid:
            issues.append(f"Prioridades fora do padrão P0-P4: {invalid[:20]}")

    for col in ["cpu_p95", "mem_p95", "disk_used_pct", "datastore_used_pct"]:
        if col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce")
            over_100 = int((numeric > 100).sum())
            below_0 = int((numeric < 0).sum())
            if over_100 or below_0:
                issues.append(f"{col}: {below_0} valores < 0 e {over_100} valores > 100")

    forecast_summary = {}
    for col in ["forecast_30d", "forecast_60d", "forecast_90d"]:
        if col in df.columns:
            forecast_summary[col] = df[col].fillna("").astype(str).str.upper().value_counts().to_dict()

    result = {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "missing_minimal": missing_minimal,
        "missing_recommended": missing_recommended,
        "issues": issues,
        "ok_for_data_rag": not missing_minimal,
        "priority_counts": df["prioridade"].fillna("").astype(str).value_counts().to_dict() if "prioridade" in df.columns else {},
        "forecast_summary": forecast_summary,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida arquivo normalizado do RMC Copilot.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", default="outputs/capacity_validation.json")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    result = validate(df)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== VALIDAÇÃO DO ARQUIVO NORMALIZADO ===")
    print(f"Arquivo: {args.input}")
    print(f"Linhas: {result['rows']}")
    print(f"OK para Data+RAG: {result['ok_for_data_rag']}")
    print(f"Faltando mínimas: {result['missing_minimal'] or 'nenhuma'}")
    print(f"Faltando recomendadas: {result['missing_recommended'] or 'nenhuma'}")
    if result["issues"]:
        print("Issues:")
        for issue in result["issues"]:
            print(f"- {issue}")
    else:
        print("Issues: nenhuma")
    print(f"Resultado salvo em: {out}")


if __name__ == "__main__":
    main()
