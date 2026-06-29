from __future__ import annotations

import argparse
import getpass
import html
import json
import os
import re
import ssl
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

try:
    import keyring
except Exception:
    keyring = None

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


TERMS = [
    "orphan", "orphaned", "orfa", "órf", "vmdk", "unused", "unattached",
    "reclaim", "reclamation", "waste", "wasted", "idle", "powered off",
    "poweredoff", "snapshot", "old snapshot", "datastore", "disk"
]


def log(msg: str) -> None:
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


def norm_url(host: str) -> str:
    h = host.strip()
    if not h.startswith("http"):
        h = "https://" + h
    return h.rstrip("/")


def make_context():
    return ssl._create_unverified_context()


def request_json(base_url: str, method: str, path: str, token: str | None = None, body=None, timeout=60):
    url = base_url + path
    data = None
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "vRealizeOpsToken " + token
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, context=make_context(), timeout=timeout) as resp:
            raw = resp.read()
            text = raw.decode("utf-8", errors="replace")
            try:
                parsed = json.loads(text) if text else None
            except Exception:
                parsed = {"_raw": text[:20000]}
            return resp.status, parsed, text
    except HTTPError as e:
        raw = e.read()
        text = raw.decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text) if text else None
        except Exception:
            parsed = {"_raw": text[:20000]}
        return e.code, parsed, text
    except URLError as e:
        return 0, {"error": str(e)}, str(e)


def acquire_token(base_url: str, username: str, password: str, auth_source: str):
    body = {"username": username, "password": password, "authSource": auth_source}
    st, data, text = request_json(base_url, "POST", "/suite-api/api/auth/token/acquire", None, body, timeout=60)
    if st not in (200, 201):
        raise RuntimeError(f"Auth falhou HTTP {st}: {text[:500]}")
    token = data.get("token") or data.get("value") or data.get("authToken")
    if not token:
        raise RuntimeError(f"Auth OK mas token não encontrado: {data}")
    return token


def get_password(service: str, username: str):
    env = os.getenv("VROPS_PASS") or os.getenv("ARIA_PASS") or os.getenv("VROPS_PASSWORD")
    if env:
        return env
    if keyring:
        try:
            saved = keyring.get_password(service, username)
            if saved:
                log(f"Credencial encontrada no keyring para {username}")
                return saved
        except Exception:
            pass
    pwd = getpass.getpass("Senha vROps/Aria: ")
    if keyring and pwd:
        try:
            keyring.set_password(service, username, pwd)
        except Exception:
            pass
    return pwd


def flatten(obj, prefix=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:2000]):
            out.extend(flatten(v, f"{prefix}[{i}]"))
    else:
        try:
            s = str(obj)
        except Exception:
            s = repr(obj)
        out.append((prefix, s))
    return out


def count_hint(data):
    if not isinstance(data, dict):
        return None
    for key_path in [
        ("pageInfo", "totalCount"),
        ("pageInfo", "totalElements"),
        ("pageInfo", "total"),
        ("page_info", "total_count"),
        ("totalCount",),
        ("total",),
        ("count",),
    ]:
        cur = data
        ok = True
        for k in key_path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok:
            return cur
    return None


def extract_items(data):
    if not isinstance(data, dict):
        return []
    for key in [
        "resourceList", "resource-kind", "resourceKinds", "reportDefinitions",
        "reports", "superMetrics", "alertDefinitions", "symptomDefinitions",
        "recommendations", "stat-key", "statKeys", "property", "properties",
        "views", "viewDefinitions", "content"
    ]:
        v = data.get(key)
        if isinstance(v, list):
            return v
    # Sometimes list appears as first list value
    for v in data.values():
        if isinstance(v, list):
            return v
    return []


def object_name(obj):
    if not isinstance(obj, dict):
        return ""
    for path in [
        ["name"],
        ["key"],
        ["id"],
        ["resourceKey", "name"],
        ["resourceKey", "resourceKindKey"],
        ["statKey"],
        ["propertyKey"],
        ["description"]
    ]:
        cur = obj
        for p in path:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                cur = None
                break
        if cur:
            return str(cur)
    return json.dumps(obj, ensure_ascii=False)[:100]


def text_contains_terms(text: str):
    low = html.unescape(text.lower())
    return [t for t in TERMS if t.lower() in low]


def summarize_matches(label: str, status: int, data):
    flat = flatten(data) if data is not None else []
    matches = []
    for path, value in flat:
        combined = f"{path}: {value}"
        terms = text_contains_terms(combined)
        if terms:
            matches.append({"path": path, "value": value[:600], "terms": terms})
        if len(matches) >= 120:
            break
    return {
        "label": label,
        "http": status,
        "count_hint": count_hint(data),
        "hits": len(matches),
        "matches": matches[:50],
    }


def fetch_all_reportdefs(base_url, token):
    st, data, _ = request_json(base_url, "GET", "/suite-api/api/reportdefinitions?page=0&pageSize=1000", token)
    return st, data


def fetch_reportdef_details(base_url, token, report_id):
    paths = [
        f"/suite-api/api/reportdefinitions/{quote(str(report_id))}",
        f"/suite-api/api/reportdefinitions/{quote(str(report_id))}/content",
    ]
    results = []
    for p in paths:
        st, data, _ = request_json(base_url, "GET", p, token)
        results.append({"path": p, "http": st, "data": data})
    return results


def main():
    ap = argparse.ArgumentParser(description="Deep probe Aria/vROps para localizar origem de orphaned disks/reclaim")
    ap.add_argument("--host", default=os.getenv("VROPS_HOST") or "mor-vropsprd01.bvnet.bv")
    ap.add_argument("--user", default=os.getenv("VROPS_USER") or "")
    ap.add_argument("--auth-source", default=os.getenv("VROPS_AUTH_SOURCE") or "bvnet.bv")
    ap.add_argument("--out-dir", default="data/debug")
    args = ap.parse_args()

    base_url = norm_url(args.host)
    user = args.user.strip() or input("Usuário vROps/Aria: ").strip()
    pwd = get_password("vROps_Access", user)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    log(f"[INICIO] Deep probe Aria/vROps | host={args.host} | authSource={args.auth_source}")
    token = acquire_token(base_url, user, pwd, args.auth_source)
    log("[OK] Token adquirido")

    probes = []

    endpoints = {
        "resources_datastore": "/suite-api/api/resources?adapterKind=VMWARE&resourceKind=Datastore&page=0&pageSize=1000",
        "resources_storagepod": "/suite-api/api/resources?adapterKind=VMWARE&resourceKind=StoragePod&page=0&pageSize=1000",
        "resources_orphan_name": "/suite-api/api/resources?name=orphan&page=0&pageSize=1000",
        "resources_vmdk_name": "/suite-api/api/resources?name=vmdk&page=0&pageSize=1000",
        "resources_reclaim_name": "/suite-api/api/resources?name=reclaim&page=0&pageSize=1000",
        "adapter_kinds_vmware": "/suite-api/api/adapterkinds/VMWARE/resourcekinds",
        "datastore_statkeys": "/suite-api/api/adapterkinds/VMWARE/resourcekinds/Datastore/statkeys",
        "datastore_properties": "/suite-api/api/adapterkinds/VMWARE/resourcekinds/Datastore/properties",
        "storagepod_statkeys": "/suite-api/api/adapterkinds/VMWARE/resourcekinds/StoragePod/statkeys",
        "storagepod_properties": "/suite-api/api/adapterkinds/VMWARE/resourcekinds/StoragePod/properties",
        "vm_statkeys": "/suite-api/api/adapterkinds/VMWARE/resourcekinds/VirtualMachine/statkeys",
        "vm_properties": "/suite-api/api/adapterkinds/VMWARE/resourcekinds/VirtualMachine/properties",
        "reportdefinitions": "/suite-api/api/reportdefinitions?page=0&pageSize=1000",
        "reports": "/suite-api/api/reports?page=0&pageSize=1000",
        "supermetrics": "/suite-api/api/supermetrics?page=0&pageSize=1000",
        "alertdefinitions": "/suite-api/api/alertdefinitions?page=0&pageSize=1000",
        "recommendations": "/suite-api/api/recommendations?page=0&pageSize=1000",
        # Known sometimes-404 endpoints; useful to prove availability.
        "viewdefinitions": "/suite-api/api/viewdefinitions?page=0&pageSize=1000",
        "views": "/suite-api/api/views?page=0&pageSize=1000",
        # Common internal guesses; read-only probe.
        "internal_reclaim_1": "/suite-api/internal/reclaim",
        "internal_reclaim_2": "/suite-api/internal/reclamation",
        "internal_ui_reclaim_1": "/ui/api/reclamation",
        "internal_ui_reclaim_2": "/ui/api/reclaim",
        "internal_ui_views": "/ui/api/views",
    }

    raw = {"generated_at": ts, "host": args.host, "auth_source": args.auth_source, "probes": {}}
    summaries = []

    for label, path in endpoints.items():
        log(f"[PROBE] {label}")
        st, data, text = request_json(base_url, "GET", path, token, timeout=90)
        raw["probes"][label] = {"path": path, "http": st, "data": data}
        summaries.append(summarize_matches(label, st, data))

    # Deep search report definitions by matching terms in name/description/content
    report_data = raw["probes"].get("reportdefinitions", {}).get("data")
    report_items = extract_items(report_data)
    candidate_reports = []
    for r in report_items:
        blob = json.dumps(r, ensure_ascii=False)
        terms = text_contains_terms(blob)
        if terms:
            rid = r.get("id") or r.get("uuid") or r.get("key")
            candidate_reports.append({
                "id": rid,
                "name": r.get("name"),
                "description": r.get("description"),
                "terms": sorted(set(terms)),
                "raw": r,
            })

    raw["candidate_reports"] = candidate_reports[:200]

    # Fetch details for top candidates; focus on orphan/reclaim/disk/snapshot/powered terms
    details = []
    for cand in candidate_reports[:30]:
        rid = cand.get("id")
        if not rid:
            continue
        log(f"[REPORTDEF] detalhe {cand.get('name')} ({rid})")
        for det in fetch_reportdef_details(base_url, token, rid):
            details.append({"report": cand, **det})
            summaries.append(summarize_matches("reportdef_detail_" + str(cand.get("name"))[:50], det["http"], det["data"]))
    raw["candidate_report_details"] = details

    json_path = out_dir / f"aria_reclaim_orphans_deep_{ts}.json"
    summary_path = out_dir / f"aria_reclaim_orphans_deep_{ts}_summary.txt"

    json_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    lines = []
    lines.append(f"Deep Probe Aria/vROps - {ts}")
    lines.append(f"Host: {args.host}")
    lines.append("")
    for s in summaries:
        lines.append(f"{s['label']}: HTTP={s['http']} count_hint={s['count_hint']} hits={s['hits']}")
        for m in s["matches"][:12]:
            val = re.sub(r"\s+", " ", m["value"])
            lines.append(f"  - termos={','.join(m['terms'])} em {m['path']}: {val[:240]}")
        lines.append("")

    lines.append("Candidate report definitions:")
    if not candidate_reports:
        lines.append("  - nenhum candidato por termos encontrado")
    else:
        for c in candidate_reports[:50]:
            lines.append(f"  - id={c.get('id')} | name={c.get('name')} | terms={','.join(c.get('terms') or [])}")
    lines.append("")
    lines.append(f"JSON completo: {json_path}")
    summary_path.write_text("\n".join(lines), encoding="utf-8")

    log(f"[OK] Summary: {summary_path}")
    log(f"[OK] JSON: {json_path}")
    log("[FIM] Probe somente leitura. Nenhuma ação operacional executada.")


if __name__ == "__main__":
    main()
