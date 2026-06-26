from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


def read_data(path: str) -> pd.DataFrame:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(p)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(p)
    raise ValueError("chat_data_rag_v3 espera arquivo já normalizado em CSV ou Parquet.")


def norm_text(text: str) -> str:
    return str(text or "").strip().upper()


def detect_cluster(question: str, clusters: List[str]) -> Optional[str]:
    q = question.upper()
    for cluster in sorted([str(c) for c in clusters if str(c).strip()], key=len, reverse=True):
        if cluster.upper() in q:
            return cluster
    m = re.search(r"(BV_PRD_[0-9]{2}[_A-Z0-9\-]+)", q)
    if m:
        return m.group(1)
    return None


def detect_priorities(question: str) -> Optional[List[str]]:
    q = question.upper()
    found = sorted(set(re.findall(r"\bP[0-4]\b", q)))
    if found:
        return found
    if "MAIOR RISCO" in q or "CRITIC" in q or "RISCO" in q:
        return ["P0", "P1"]
    if "RIGHTSIZING" in q or "OTIMIZA" in q or "SUPERDIMENSION" in q:
        return ["P3"]
    return None


def detect_forecast(question: str) -> tuple[Optional[int], Optional[str]]:
    q = question.upper()
    window = None
    if "30" in q:
        window = 30
    elif "60" in q:
        window = 60
    elif "90" in q:
        window = 90

    resource = None
    if any(x in q for x in ["DISCO", "DISK", "STORAGE", "DATASTORE"]):
        resource = "DISK"
    elif any(x in q for x in ["MEMORIA", "MEMÓRIA", "MEMORY", "RAM", "MEM "]):
        resource = "MEM"
    elif any(x in q for x in ["CPU", "VCPU"]):
        resource = "CPU"

    return window, resource


def filter_rows(df: pd.DataFrame, question: str, limit: int = 15) -> tuple[pd.DataFrame, Dict[str, object]]:
    work = df.copy()

    for col in ["prioridade", "cluster", "host", "vm", "datastore", "forecast_30d", "forecast_60d", "forecast_90d", "acao"]:
        if col not in work.columns:
            work[col] = ""

    cluster = detect_cluster(question, work["cluster"].dropna().astype(str).unique().tolist())
    priorities = detect_priorities(question)
    window, resource = detect_forecast(question)

    if cluster:
        work = work[work["cluster"].astype(str).str.upper() == cluster.upper()]

    if window:
        col = f"forecast_{window}d"
        if col in work.columns:
            if resource:
                work = work[work[col].fillna("").astype(str).str.upper().str.contains(resource, regex=False)]
            else:
                work = work[work[col].fillna("").astype(str).str.strip() != ""]

    if priorities:
        work = work[work["prioridade"].fillna("").astype(str).str.upper().isin(priorities)]

    q = question.upper()
    if "RIGHTSIZING" in q or "OTIMIZA" in q or "SUPERDIMENSION" in q:
        # Mantém P3 e também casos de CPU/MEM muito baixos se houver.
        p3 = work["prioridade"].fillna("").astype(str).str.upper().eq("P3")
        cpu_low = pd.to_numeric(work.get("cpu_p95", pd.Series(index=work.index)), errors="coerce").lt(25)
        mem_low = pd.to_numeric(work.get("mem_p95", pd.Series(index=work.index)), errors="coerce").lt(35)
        work = work[p3 | cpu_low | mem_low]

    if "MAIOR RISCO" in q or ("RISCO" in q and not priorities):
        work = work[work["prioridade"].fillna("").astype(str).str.upper().isin(["P0", "P1"])]

    work["_priority_rank"] = work["prioridade"].fillna("").astype(str).str.upper().map(PRIORITY_ORDER).fillna(9)
    for numeric_col in ["datastore_used_pct", "disk_used_pct", "mem_p95", "cpu_p95"]:
        if numeric_col in work.columns:
            work[numeric_col] = pd.to_numeric(work[numeric_col], errors="coerce")

    sort_cols = [c for c in ["_priority_rank", "datastore_used_pct", "disk_used_pct", "mem_p95", "cpu_p95"] if c in work.columns]
    ascending = [True] + [False] * (len(sort_cols) - 1)
    if sort_cols:
        work = work.sort_values(sort_cols, ascending=ascending)

    meta = {
        "cluster_detectado": cluster,
        "prioridades_detectadas": priorities,
        "janela_forecast_detectada": window,
        "recurso_forecast_detectado": resource,
        "linhas_retornadas": int(min(len(work), limit)),
    }

    return work.head(limit).drop(columns=["_priority_rank"], errors="ignore"), meta


def summarize_risk(rows: pd.DataFrame) -> str:
    if rows.empty:
        return "Nenhuma linha encontrada para os filtros detectados."

    parts = []
    if "prioridade" in rows:
        counts = rows["prioridade"].fillna("").astype(str).str.upper().value_counts().to_dict()
        for p in ["P0", "P1", "P2", "P3", "P4"]:
            if counts.get(p, 0):
                parts.append(f"{counts[p]} objeto(s) {p}")

    for col, label in [
        ("datastore_used_pct", "datastore(s)/registros com uso >= 90%"),
        ("disk_used_pct", "VM(s) com disco >= 90%"),
        ("mem_p95", "VM(s) com memória p95 >= 90%"),
        ("cpu_p95", "VM(s) com CPU p95 >= 90%"),
    ]:
        if col in rows:
            vals = pd.to_numeric(rows[col], errors="coerce")
            count = int((vals >= 90).sum())
            if count:
                parts.append(f"{count} {label}")

    return "; ".join(parts) if parts else "Risco identificado pelas prioridades e forecasts retornados."


def row_to_bullet(row: pd.Series) -> str:
    def val(col: str, default: str = "") -> str:
        value = row.get(col, default)
        if pd.isna(value):
            return default
        return str(value)

    return (
        f"- VM {val('vm')} | cluster {val('cluster')} | host {val('host')} | "
        f"prioridade {val('prioridade')} | CPU p95 {val('cpu_p95')}% | "
        f"memória p95 {val('mem_p95')}% | disco {val('disk_used_pct')}% | "
        f"datastore {val('datastore')} {val('datastore_used_pct')}% | "
        f"forecast 30d {val('forecast_30d')} | 60d {val('forecast_60d')} | 90d {val('forecast_90d')} | "
        f"ação {val('acao')}"
    )


def table_markdown(rows: pd.DataFrame) -> str:
    cols = [
        "prioridade",
        "cluster",
        "host",
        "vm",
        "cpu_p95",
        "mem_p95",
        "disk_used_pct",
        "datastore",
        "datastore_used_pct",
        "forecast_30d",
        "forecast_60d",
        "forecast_90d",
        "acao",
    ]
    available = [c for c in cols if c in rows.columns]
    if rows.empty:
        return "_Sem linhas retornadas._"
    view = rows[available].copy()
    rename = {
        "disk_used_pct": "disco_%",
        "datastore_used_pct": "ds_%",
        "acao": "ação",
    }
    view = view.rename(columns=rename)
    return view.to_markdown(index=False)


def safe_answer(question: str, rows: pd.DataFrame, meta: Dict[str, object]) -> str:
    bullets = "\n".join(row_to_bullet(row) for _, row in rows.iterrows()) if not rows.empty else "- Nenhuma evidência estruturada encontrada."
    risk = summarize_risk(rows)

    priorities = sorted(set(rows["prioridade"].fillna("").astype(str).str.upper())) if not rows.empty and "prioridade" in rows else []
    priority_text = ", ".join([p for p in ["P0", "P1", "P2", "P3", "P4"] if p in priorities]) or "não identificada no recorte"

    answer = f"""Diagnóstico
A pergunta foi respondida usando o arquivo normalizado da Etapa 12 combinado com as regras técnicas do RMC Copilot. Pergunta: {question}

Evidências encontradas
{bullets}

Tabela de evidências
{table_markdown(rows)}

Risco
{risk}

Prioridade
Prioridades encontradas no recorte: {priority_text}. Trate P0 primeiro, depois P1, depois P2. P3 indica otimização e P4 indica monitoramento.

Ação recomendada
Validar os objetos listados, conferir histórico 30/60/90 dias, verificar datastore associado, confirmar janela de backup/batch/fechamento e abrir plano de ação para P0/P1. Para P3, executar rightsizing de forma gradual e conservadora.

Limitações da análise
A resposta depende do arquivo normalizado informado. Caso o arquivo original não tenha alguma coluna recomendada, a análise fica limitada. Não misturar forecast específico de DISK/MEM/CPU com uso atual alto do recurso.

Metadados da consulta
- cluster_detectado: {meta.get('cluster_detectado')}
- prioridades_detectadas: {meta.get('prioridades_detectadas')}
- janela_forecast_detectada: {meta.get('janela_forecast_detectada')}
- recurso_forecast_detectado: {meta.get('recurso_forecast_detectado')}
- linhas_retornadas: {meta.get('linhas_retornadas')}
"""
    return answer


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat Data+RAG v3 para arquivo real normalizado.")
    parser.add_argument("--data", required=True, help="CSV/Parquet normalizado")
    parser.add_argument("--index", default=None, help="Mantido para compatibilidade com etapas anteriores")
    parser.add_argument("--model", default="gemma3:1b")
    parser.add_argument("--question", required=True)
    parser.add_argument("--k", type=int, default=8)
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--mode", choices=["safe", "hybrid"], default="safe")
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    df = read_data(args.data)
    rows, meta = filter_rows(df, args.question, limit=args.limit)
    answer = safe_answer(args.question, rows, meta)

    print("\n=== RESPOSTA RMC COPILOT DATA+RAG V3 ===\n")
    print(answer)
    print(f"\n=== MODO USADO: {args.mode if args.mode == 'safe' else 'safe_fallback'} ===")

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "question": args.question,
            "mode": args.mode,
            "answer": answer,
            "meta": meta,
            "rows": rows.to_dict(orient="records"),
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
