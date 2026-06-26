from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

import pandas as pd

from chat_data_rag_v3 import filter_rows, read_data, safe_answer


def load_questions(path: str) -> List[Dict[str, object]]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def contains_all(text: str, terms: List[str]) -> bool:
    t = text.upper()
    return all(str(term).upper() in t for term in terms)


def contains_none(text: str, terms: List[str]) -> bool:
    t = text.upper()
    return all(str(term).upper() not in t for term in terms)


def row_validation(rows: pd.DataFrame, q: Dict[str, object]) -> bool:
    expected_vms = [str(x).upper() for x in q.get("expected_vms", [])]
    forbidden_vms = [str(x).upper() for x in q.get("forbidden_vms", [])]
    strict_resource = q.get("strict_forecast_resource")
    strict_window = q.get("strict_forecast_window")

    text_rows = " ".join(rows.astype(str).to_dict(orient="records").__repr__().upper().split())

    if expected_vms and not all(vm in text_rows for vm in expected_vms):
        return False
    if forbidden_vms and any(vm in text_rows for vm in forbidden_vms):
        return False

    if strict_resource and strict_window:
        col = f"forecast_{strict_window}d"
        if col not in rows.columns or rows.empty:
            return False
        values = rows[col].fillna("").astype(str).str.upper().tolist()
        return all(str(strict_resource).upper() in v for v in values)

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Avalia Data+RAG v3 com arquivo normalizado.")
    parser.add_argument("--data", required=True)
    parser.add_argument("--index", default=None)
    parser.add_argument("--model", default="gemma3:1b")
    parser.add_argument("--questions", required=True)
    parser.add_argument("--prompt", default=None)
    parser.add_argument("--out", default="outputs/data_rag_eval_results_v3.jsonl")
    parser.add_argument("--k", type=int, default=8)
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--mode", choices=["safe", "hybrid"], default="safe")
    parser.add_argument("--show-failures", action="store_true")
    args = parser.parse_args()

    df = read_data(args.data)
    questions = load_questions(args.questions)

    results = []
    ok_count = 0
    rows_ok_count = 0
    strict_ok_count = 0
    forbidden_ok_count = 0

    for q in questions:
        question = str(q["question"])
        rows, meta = filter_rows(df, question, limit=args.limit)
        answer = safe_answer(question, rows, meta)

        criteria = contains_all(answer, [str(x) for x in q.get("must_include", [])])
        forbidden = contains_none(answer, [str(x) for x in q.get("must_not_include", [])])
        rows_ok = len(rows) >= int(q.get("min_rows", 1))
        strict_ok = row_validation(rows, q)
        ok = criteria and forbidden and rows_ok and strict_ok

        if ok:
            ok_count += 1
        if rows_ok:
            rows_ok_count += 1
        if strict_ok:
            strict_ok_count += 1
        if forbidden:
            forbidden_ok_count += 1

        status = "OK" if ok else "FALHOU"
        print(
            f"{q.get('id')} | {status} | criteria={'OK' if criteria else 'FALHOU'} | "
            f"forbidden={'OK' if forbidden else 'FALHOU'} | rows={'OK' if rows_ok else 'FALHOU'} ({len(rows)}) | "
            f"strict_rows={'OK' if strict_ok else 'FALHOU'} | mode={args.mode} | {question}"
        )

        if args.show_failures and not ok:
            print("\n--- RESPOSTA QUE FALHOU ---")
            print(answer)
            print("--- FIM ---\n")

        results.append({
            "id": q.get("id"),
            "question": question,
            "ok": ok,
            "criteria_ok": criteria,
            "forbidden_ok": forbidden,
            "rows_ok": rows_ok,
            "strict_rows_ok": strict_ok,
            "rows_returned": int(len(rows)),
            "meta": meta,
            "answer": answer,
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    total = len(questions)
    print("\n=== RESULTADO DATA+RAG V3 ===")
    print(f"Perguntas: {total}")
    print(f"Aprovadas: {ok_count}")
    print(f"Consultas com linhas suficientes: {rows_ok_count}")
    print(f"Validação de exclusão OK: {forbidden_ok_count}")
    print(f"Validação estrita de VMs/forecast OK: {strict_ok_count}")
    print(f"Taxa resposta: {ok_count / total * 100:.1f}%")
    print(f"Taxa consulta estruturada: {rows_ok_count / total * 100:.1f}%")
    print(f"Resultado salvo em: {out}")


if __name__ == "__main__":
    main()
