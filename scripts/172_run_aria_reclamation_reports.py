from __future__ import annotations

import argparse
import csv
import getpass
import html
import io
import json
import os
import re
import ssl
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import duckdb
import pandas as pd

try:
    import keyring
except Exception:
    keyring = None

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


REPORT_DEFS = {
    "datacenter": {
        "id": "77935eb4-eeec-45bf-b13c-1d7b00bc21c7",
        "name": "Reclamation Report - Datacenter",
        "resource_kind_hint": "Datacenter",
    },
    "clusters": {
        "id": "92bdc75a-423e-40cd-91e8-c97c17902c42",
        "name": "Reclamation Report - vSphere Clusters",
        "resource_kind_hint": "ClusterComputeResource",
    },
}

TERMS_ORPHAN = ["orphan", "orphaned", "orfa", "órf", "vmdk", "unattached", "unused disk", "reclaimable disk", "wasted disk"]
TERMS_RECLAIM = ["reclaim", "reclamation", "reclaimable", "powered off", "poweredoff", "snapshot", "idle", "waste", "wasted", "vmdk", "orphan"]


SCHEMA_SQL = r"""
CREATE TABLE IF NOT EXISTS aria_reclamation_report_exports (
    run_id VARCHAR,
    generated_at TIMESTAMP,
    source VARCHAR,
    report_id VARCHAR,
    report_definition_id VARCHAR,
    report_definition_name VARCHAR,
    resource_kind VARCHAR,
    resource_name VARCHAR,
    resource_id VARCHAR,
    status VARCHAR,
    csv_path VARCHAR,
    pdf_path VARCHAR,
    raw_json VARCHAR
);

CREATE TABLE IF NOT EXISTS aria_reclamation_report_rows (
    run_id VARCHAR,
    generated_at TIMESTAMP,
    report_definition_name VARCHAR,
    resource_kind VARCHAR,
    resource_name VARCHAR,
    row_index INTEGER,
    matched_terms VARCHAR,
    row_text VARCHAR,
    row_json VARCHAR
);

CREATE TABLE IF NOT EXISTS orphan_disk_candidates (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    datastore VARCHAR,
    vmdk_path VARCHAR,
    arquivo VARCHAR,
    tamanho_gb DOUBLE,
    data_modificacao TIMESTAMP,
    idade_dias DOUBLE,
    vm_associada_encontrada VARCHAR,
    cluster VARCHAR,
    status_validacao VARCHAR,
    confianca DOUBLE,
    observacao VARCHAR,
    raw_json VARCHAR
);
"""


def log(msg: str):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


def norm_url(host: str) -> str:
    h = host.strip()
    if not h.startswith("http"):
        h = "https://" + h
    return h.rstrip("/")


def ctx():
    return ssl._create_unverified_context()


def req(base_url, method, path, token=None, body=None, accept="application/json", timeout=120, return_bytes=False):
    url = base_url + path
    data = None
    headers = {"Accept": accept}
    if token:
        headers["Authorization"] = "vRealizeOpsToken " + token
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    r = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(r, context=ctx(), timeout=timeout) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            if return_bytes:
                return resp.status, raw, ctype
            text = raw.decode("utf-8", errors="replace")
            try:
                parsed = json.loads(text) if text.strip() else {}
            except Exception:
                parsed = {"_raw": text}
            return resp.status, parsed, ctype
    except HTTPError as e:
        raw = e.read()
        ctype = e.headers.get("Content-Type", "")
        if return_bytes:
            return e.code, raw, ctype
        text = raw.decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text) if text.strip() else {}
        except Exception:
            parsed = {"_raw": text}
        return e.code, parsed, ctype
    except URLError as e:
        return 0, {"error": str(e)}, ""


def api_get(base_url, path, token):
    # on-prem costuma usar /suite-api/api; fallback /api para compatibilidade com docs Cloud.
    attempts = [path]
    if path.startswith("/suite-api/api/"):
        attempts.append(path.replace("/suite-api/api/", "/api/", 1))
    elif path.startswith("/api/"):
        attempts.append(path.replace("/api/", "/suite-api/api/", 1))
    last = None
    for p in attempts:
        st, data, ctype = req(base_url, "GET", p, token=token)
        last = (st, data, ctype, p)
        if st not in (404, 405):
            return st, data, ctype, p
    return last


def api_post(base_url, path, token, body):
    attempts = [path]
    if path.startswith("/suite-api/api/"):
        attempts.append(path.replace("/suite-api/api/", "/api/", 1))
    elif path.startswith("/api/"):
        attempts.append(path.replace("/api/", "/suite-api/api/", 1))
    last = None
    for p in attempts:
        st, data, ctype = req(base_url, "POST", p, token=token, body=body)
        last = (st, data, ctype, p)
        if st not in (404, 405):
            return st, data, ctype, p
    return last


def api_download(base_url, report_id, fmt, token):
    paths = [
        f"/suite-api/api/reports/{quote(report_id)}/download?format={quote(fmt)}",
        f"/api/reports/{quote(report_id)}/download?format={quote(fmt)}",
        f"/suite-api/api/reports/{quote(report_id)}/download",
        f"/api/reports/{quote(report_id)}/download",
    ]
    last = None
    for p in paths:
        st, raw, ctype = req(base_url, "GET", p, token=token, accept="*/*", timeout=300, return_bytes=True)
        last = (st, raw, ctype, p)
        if st == 200 and raw:
            return st, raw, ctype, p
    return last


def acquire_token(base_url, user, pwd, auth_source):
    body = {"username": user, "password": pwd, "authSource": auth_source}
    st, data, _ = req(base_url, "POST", "/suite-api/api/auth/token/acquire", body=body, timeout=60)
    if st not in (200, 201):
        raise RuntimeError(f"Auth falhou HTTP {st}: {data}")
    token = data.get("token") or data.get("value") or data.get("authToken")
    if not token:
        raise RuntimeError(f"Token não encontrado na resposta: {data}")
    return token


def get_password(user):
    env = os.getenv("VROPS_PASS") or os.getenv("ARIA_PASS") or os.getenv("VROPS_PASSWORD")
    if env:
        return env
    if keyring:
        try:
            saved = keyring.get_password("vROps_Access", user)
            if saved:
                log(f"Credencial encontrada no keyring para {user}")
                return saved
        except Exception:
            pass
    return getpass.getpass("Senha vROps/Aria: ")


def extract_list(data, key_candidates):
    if not isinstance(data, dict):
        return []
    for k in key_candidates:
        v = data.get(k)
        if isinstance(v, list):
            return v
    for v in data.values():
        if isinstance(v, list):
            return v
    return []


def get_report_definition(base_url, token, report_def_id):
    st, data, _, path = api_get(base_url, f"/suite-api/api/reportdefinitions/{quote(report_def_id)}", token)
    if st != 200:
        raise RuntimeError(f"Falha ao obter reportDefinition {report_def_id}. HTTP={st} path={path} data={data}")
    return data


def infer_resource_kind(report_def, fallback):
    subjects = report_def.get("subject") or []
    if isinstance(subjects, str):
        subjects = [subjects]
    joined = " ".join(str(s) for s in subjects).lower()

    if "datacenter" in joined:
        return "Datacenter"
    if "cluster" in joined:
        return "ClusterComputeResource"
    if "virtualmachine" in joined or "virtual machine" in joined:
        return "VirtualMachine"
    if "datastore" in joined:
        return "Datastore"

    return fallback


def find_resources(base_url, token, resource_kind, name_filter="", max_resources=0):
    resources = []
    page = 0
    while True:
        qs = urlencode({"adapterKind": "VMWARE", "resourceKind": resource_kind, "page": page, "pageSize": 1000})
        st, data, _, path = api_get(base_url, f"/suite-api/api/resources?{qs}", token)
        if st != 200:
            raise RuntimeError(f"Falha ao listar resources {resource_kind}. HTTP={st} path={path} data={data}")
        items = data.get("resourceList") or []
        resources.extend(items)
        total = (data.get("pageInfo") or {}).get("totalCount")
        if not items or (total is not None and len(resources) >= int(total)):
            break
        page += 1

    def name_of(r):
        return str(((r.get("resourceKey") or {}).get("name")) or r.get("name") or "")

    if name_filter:
        resources = [r for r in resources if name_filter.lower() in name_of(r).lower()]

    if max_resources and max_resources > 0:
        resources = resources[:max_resources]

    return resources


def resource_id_name(res):
    rid = res.get("identifier") or res.get("id") or res.get("resourceId")
    rk = res.get("resourceKey") or {}
    name = rk.get("name") or res.get("name") or rid
    # Aria resource id usually at identifier field.
    return str(rid), str(name)


def create_report(base_url, token, report_def_id, resource_id):
    body = {"reportDefinitionId": report_def_id, "resourceId": resource_id}
    st, data, _, path = api_post(base_url, "/suite-api/api/reports", token, body)
    if st not in (200, 201, 202):
        raise RuntimeError(f"Create report falhou HTTP={st} path={path} body={body} data={data}")
    rid = data.get("id") or data.get("reportId") or data.get("identifier")
    if not rid:
        raise RuntimeError(f"Create report OK mas id não encontrado: {data}")
    return rid, data, path


def get_report(base_url, token, report_id):
    st, data, _, path = api_get(base_url, f"/suite-api/api/reports/{quote(report_id)}", token)
    return st, data, path


def wait_report(base_url, token, report_id, timeout=900, poll=10):
    started = time.time()
    last = None
    while True:
        st, data, path = get_report(base_url, token, report_id)
        last = (st, data, path)
        status = str(data.get("status") or data.get("state") or "").upper() if isinstance(data, dict) else ""
        if st == 200 and any(x in status for x in ["COMPLETED", "SUCCESS", "FINISHED"]):
            return data
        if st == 200 and any(x in status for x in ["FAILED", "ERROR", "CANCELLED"]):
            raise RuntimeError(f"Report {report_id} falhou status={status} data={data}")
        if time.time() - started > timeout:
            raise TimeoutError(f"Timeout aguardando report {report_id}. Último={last}")
        log(f"Report {report_id}: status={status or 'DESCONHECIDO'}; aguardando {poll}s")
        time.sleep(poll)


def save_report_downloads(base_url, token, report_id, out_dir, base_name):
    out = {"csv": None, "pdf": None, "downloads": []}
    for fmt, ext in [("CSV", ".csv"), ("PDF", ".pdf")]:
        st, raw, ctype, path = api_download(base_url, report_id, fmt, token)
        out["downloads"].append({"format": fmt, "http": st, "content_type": ctype, "path": path, "bytes": len(raw or b"")})
        if st == 200 and raw:
            # If API returns a link as text/json instead of bytes, save it too for debug.
            file_path = out_dir / f"{base_name}_{fmt.lower()}{ext}"
            file_path.write_bytes(raw)
            out[fmt.lower()] = str(file_path)
            log(f"[OK] Download {fmt}: {file_path} ({len(raw)} bytes)")
        else:
            log(f"[WARN] Download {fmt} falhou HTTP={st} path={path}")
    return out


def read_csv_rows(path):
    if not path:
        return []
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return []
    raw = p.read_bytes()
    # Sometimes report comes zipped; leave parse blank.
    if raw[:2] == b"PK":
        return []
    text = raw.decode("utf-8-sig", errors="replace")
    if not text.strip():
        return []
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        sep = dialect.delimiter
    except Exception:
        sep = ","
    try:
        df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str, keep_default_na=False)
    except Exception:
        try:
            df = pd.read_csv(io.StringIO(text), sep=None, engine="python", dtype=str, keep_default_na=False)
        except Exception:
            return [{"_raw": line} for line in text.splitlines() if line.strip()]
    rows = df.to_dict(orient="records")
    return rows


def matched_terms_for_row(row):
    text = html.unescape(json.dumps(row, ensure_ascii=False)).lower()
    terms = sorted(set([t for t in TERMS_RECLAIM if t.lower() in text]))
    return terms


def infer_orphan_fields(row):
    # best effort, preserves complete row in raw_json anyway
    keys = {str(k).lower(): k for k in row.keys()}
    def find_key(*needles):
        for low, orig in keys.items():
            if any(n in low for n in needles):
                return orig
        return None

    datastore_key = find_key("datastore")
    path_key = find_key("path", "caminho", "vmdk", "disk")
    size_key = find_key("size", "tamanho", "gb", "reclaim")
    datastore = row.get(datastore_key) if datastore_key else None
    vmdk_path = row.get(path_key) if path_key else None
    size = None
    if size_key:
        val = str(row.get(size_key) or "").replace(",", ".")
        m = re.search(r"[-+]?\d+(\.\d+)?", val)
        if m:
            try:
                size = float(m.group(0))
            except Exception:
                pass
    return datastore, vmdk_path, size


def ensure_schema(con):
    con.execute(SCHEMA_SQL)


def insert_export(con, row):
    con.execute("""
        INSERT INTO aria_reclamation_report_exports (
            run_id, generated_at, source, report_id, report_definition_id, report_definition_name,
            resource_kind, resource_name, resource_id, status, csv_path, pdf_path, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        row["run_id"], row["generated_at"], "ARIA_REPORT_API", row["report_id"], row["report_definition_id"],
        row["report_definition_name"], row["resource_kind"], row["resource_name"], row["resource_id"],
        row["status"], row.get("csv_path"), row.get("pdf_path"), json.dumps(row.get("raw_json") or {}, ensure_ascii=False, default=str)
    ])


def insert_rows_and_candidates(con, run_id, generated_at, report_name, resource_kind, resource_name, parsed_rows):
    for i, r in enumerate(parsed_rows):
        terms = matched_terms_for_row(r)
        if not terms:
            continue
        row_text = json.dumps(r, ensure_ascii=False)[:8000]
        con.execute("""
            INSERT INTO aria_reclamation_report_rows (
                run_id, generated_at, report_definition_name, resource_kind, resource_name,
                row_index, matched_terms, row_text, row_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            run_id, generated_at, report_name, resource_kind, resource_name, i,
            ",".join(terms), row_text[:2000], json.dumps(r, ensure_ascii=False, default=str)
        ])

        row_blob = row_text.lower()
        if any(t in row_blob for t in TERMS_ORPHAN):
            datastore, vmdk_path, size = infer_orphan_fields(r)
            con.execute("""
                INSERT INTO orphan_disk_candidates (
                    run_id, collected_at, datastore, vmdk_path, arquivo, tamanho_gb, data_modificacao,
                    idade_dias, vm_associada_encontrada, cluster, status_validacao, confianca,
                    observacao, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?)
            """, [
                run_id, generated_at, datastore, vmdk_path, None, size,
                "VALIDAR_ARIA_REPORT", resource_name, "CANDIDATO_A_ORFAO_ARIA_RECLAMATION",
                0.70,
                "Linha do Reclamation Report/API contém termos compatíveis com orphan/vmdk. Validar antes de qualquer remoção.",
                json.dumps(r, ensure_ascii=False, default=str)
            ])


def main():
    ap = argparse.ArgumentParser(description="Etapa 16A.5 - executar Reclamation Reports via Aria/vROps API")
    ap.add_argument("--host", default=os.getenv("VROPS_HOST") or "mor-vropsprd01.bvnet.bv")
    ap.add_argument("--user", default=os.getenv("VROPS_USER") or "")
    ap.add_argument("--auth-source", default=os.getenv("VROPS_AUTH_SOURCE") or "bvnet.bv")
    ap.add_argument("--db", default="data/database/rmc_copilot.duckdb")
    ap.add_argument("--out-dir", default="data/reports/otimizacao")
    ap.add_argument("--report", choices=["clusters", "datacenter", "both"], default="clusters")
    ap.add_argument("--resource-name-filter", default="BV_PRD")
    ap.add_argument("--max-resources", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    base_url = norm_url(args.host)
    user = args.user.strip() or input("Usuário vROps/Aria: ").strip()
    pwd = get_password(user)

    generated_at = datetime.now()
    run_id = "ARIARECL_" + generated_at.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    out_dir = Path(args.out_dir) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    log(f"[INICIO] Reclamation Reports API | host={args.host} | report={args.report} | run_id={run_id}")
    log("[REGRA] Somente leitura/geração de relatório. Nenhuma ação operacional será executada.")

    token = acquire_token(base_url, user, pwd, args.auth_source)
    log("[OK] Token adquirido")

    con = duckdb.connect(args.db)
    ensure_schema(con)

    wanted = ["clusters", "datacenter"] if args.report == "both" else [args.report]
    manifest = {"run_id": run_id, "generated_at": str(generated_at), "reports": []}

    try:
        for key in wanted:
            cfg = REPORT_DEFS[key]
            rep_def = get_report_definition(base_url, token, cfg["id"])
            rep_name = rep_def.get("name") or cfg["name"]
            resource_kind = infer_resource_kind(rep_def, cfg["resource_kind_hint"])
            name_filter = args.resource_name_filter if key == "clusters" else ""
            resources = find_resources(base_url, token, resource_kind, name_filter=name_filter, max_resources=args.max_resources)

            log(f"[REPORTDEF] {rep_name} | id={cfg['id']} | resourceKind={resource_kind} | resources={len(resources)} | filtro={name_filter or 'NENHUM'}")
            if not resources:
                log(f"[WARN] Nenhum recurso encontrado para {resource_kind}.")
                continue

            for res in resources:
                resource_id, resource_name = resource_id_name(res)
                if not resource_id or resource_id == "None":
                    log(f"[WARN] Recurso sem ID ignorado: {resource_name}")
                    continue

                safe_res_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", resource_name)[:80]
                safe_rep_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", rep_name)[:80]
                base_name = f"{safe_rep_name}_{safe_res_name}"

                log(f"[CREATE] {rep_name} -> {resource_name} ({resource_id})")
                try:
                    report_id, create_data, create_path = create_report(base_url, token, cfg["id"], resource_id)
                    completed = wait_report(base_url, token, report_id, timeout=args.timeout, poll=10)
                    downloads = save_report_downloads(base_url, token, report_id, out_dir, base_name)
                    parsed_rows = read_csv_rows(downloads.get("csv"))

                    export_row = {
                        "run_id": run_id,
                        "generated_at": generated_at,
                        "report_id": report_id,
                        "report_definition_id": cfg["id"],
                        "report_definition_name": rep_name,
                        "resource_kind": resource_kind,
                        "resource_name": resource_name,
                        "resource_id": resource_id,
                        "status": completed.get("status") or "COMPLETED",
                        "csv_path": downloads.get("csv"),
                        "pdf_path": downloads.get("pdf"),
                        "raw_json": {
                            "create_path": create_path,
                            "create_response": create_data,
                            "completed": completed,
                            "downloads": downloads,
                            "rows_parsed": len(parsed_rows)
                        }
                    }
                    insert_export(con, export_row)
                    insert_rows_and_candidates(con, run_id, generated_at, rep_name, resource_kind, resource_name, parsed_rows)
                    con.commit()

                    manifest["reports"].append(export_row)
                    log(f"[OK] report_id={report_id} rows_parseadas={len(parsed_rows)}")
                except Exception as exc:
                    log(f"[ERRO] Falha em {rep_name} / {resource_name}: {exc}")
                    manifest["reports"].append({
                        "report_definition_id": cfg["id"],
                        "report_definition_name": rep_name,
                        "resource_kind": resource_kind,
                        "resource_name": resource_name,
                        "resource_id": resource_id,
                        "status": "ERROR",
                        "error": str(exc),
                    })
                    continue

        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        # summary
        exports = con.execute("SELECT count(*) FROM aria_reclamation_report_exports WHERE run_id=?", [run_id]).fetchone()[0]
        rows = con.execute("SELECT count(*) FROM aria_reclamation_report_rows WHERE run_id=?", [run_id]).fetchone()[0]
        orphans = con.execute("SELECT count(*) FROM orphan_disk_candidates WHERE run_id=?", [run_id]).fetchone()[0]
        log(f"[OK] run_id={run_id}")
        log(f"[OK] exports={exports} linhas_reclaim={rows} candidatos_orfaos={orphans}")
        log(f"[OK] manifest={manifest_path}")
        log("[FIM] Nenhuma ação operacional executada.")
    finally:
        con.close()


if __name__ == "__main__":
    main()
