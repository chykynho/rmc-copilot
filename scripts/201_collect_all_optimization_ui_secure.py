from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import duckdb

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SERVICE = "RMC_COPILOT_ARIA_UI"

REASONS = {
    "orphaned_disk": {
        "label": "Orphan Disk",
        "summary_key": "orphaned_disk",
        "state_variants": ["orphaned_disk"],
    },
    "idle_vms": {
        "label": "VMs Idle",
        "summary_key": "idle_vms",
        "state_variants": ["idle_vms"],
    },
    "poweredOff_vms": {
        "label": "Powered Off VMs",
        "summary_key": "poweredOff_vms",
        "state_variants": ["poweredOff_vms", "poweredoff_vms", "powered_off_vms"],
    },
    "vm_snapshots": {
        "label": "VM Snapshots",
        "summary_key": "vm_snapshots",
        "state_variants": ["vm_snapshots", "snapshots", "vm_snapshot"],
    },
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS aria_ui_optimization_runs (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    source VARCHAR,
    host VARCHAR,
    dc_id VARCHAR,
    reasons_csv VARCHAR,
    credential_source VARCHAR,
    status VARCHAR,
    message VARCHAR,
    raw_summary_path VARCHAR
);

CREATE TABLE IF NOT EXISTS aria_ui_optimization_reason_runs (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    reason VARCHAR,
    vm_state_used VARCHAR,
    targets_count INTEGER,
    items_count INTEGER,
    total_cpu_vcpus DOUBLE,
    total_memory_gb DOUBLE,
    total_storage_gb DOUBLE,
    total_savings_usd DOUBLE,
    status VARCHAR,
    message VARCHAR,
    raw_json_path VARCHAR
);

CREATE TABLE IF NOT EXISTS aria_ui_optimization_items (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    reason VARCHAR,
    vm_state_used VARCHAR,
    dc_id VARCHAR,
    target_name VARCHAR,
    target_id VARCHAR,
    item_name VARCHAR,
    item_id VARCHAR,
    vmdk_path VARCHAR,
    vmdk_relative_path VARCHAR,
    arquivo VARCHAR,
    volume_uuid VARCHAR,
    cpu_vcpus DOUBLE,
    memory_gb DOUBLE,
    storage_gb DOUBLE,
    size_value DOUBLE,
    size_unit VARCHAR,
    savings_usd DOUBLE,
    days_in_live INTEGER,
    last_access_epoch_ms BIGINT,
    last_access_at TIMESTAMP,
    raw_json VARCHAR
);

CREATE TABLE IF NOT EXISTS aria_ui_orphan_vmdk_runs (
    run_id VARCHAR, collected_at TIMESTAMP, source VARCHAR, host VARCHAR, dc_id VARCHAR,
    datastores_count INTEGER, vmdks_count INTEGER, total_size_gb DOUBLE, total_savings_usd DOUBLE,
    raw_json_path VARCHAR, status VARCHAR, message VARCHAR
);

CREATE TABLE IF NOT EXISTS aria_ui_orphan_vmdk_details (
    run_id VARCHAR, collected_at TIMESTAMP, dc_id VARCHAR,
    datastore_name VARCHAR, datastore_id VARCHAR, volume_uuid VARCHAR,
    vmdk_path VARCHAR, vmdk_relative_path VARCHAR, arquivo VARCHAR,
    size_gb DOUBLE, size_value DOUBLE, size_unit VARCHAR,
    savings_usd DOUBLE, days_in_live INTEGER,
    last_access_epoch_ms BIGINT, last_access_at TIMESTAMP,
    vm_id VARCHAR, raw_json VARCHAR
);

CREATE TABLE IF NOT EXISTS orphan_disk_candidates (
    run_id VARCHAR, collected_at TIMESTAMP, datastore VARCHAR, vmdk_path VARCHAR,
    arquivo VARCHAR, tamanho_gb DOUBLE, data_modificacao TIMESTAMP, idade_dias DOUBLE,
    vm_associada_encontrada VARCHAR, cluster VARCHAR, status_validacao VARCHAR,
    confianca DOUBLE, observacao VARCHAR, raw_json VARCHAR
);

CREATE TABLE IF NOT EXISTS aria_ui_idle_vm_runs (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    source VARCHAR,
    host VARCHAR,
    dc_id VARCHAR,
    clusters_count INTEGER,
    vms_count INTEGER,
    total_cpu_vcpus DOUBLE,
    total_memory_gb DOUBLE,
    total_storage_gb DOUBLE,
    total_savings_usd DOUBLE,
    raw_json_path VARCHAR,
    status VARCHAR,
    message VARCHAR
);

CREATE TABLE IF NOT EXISTS aria_ui_idle_vm_details (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    dc_id VARCHAR,
    cluster_name VARCHAR,
    cluster_id VARCHAR,
    vm_name VARCHAR,
    vm_id VARCHAR,
    cpu_vcpus DOUBLE,
    memory_gb DOUBLE,
    storage_gb DOUBLE,
    savings_usd DOUBLE,
    days_in_live INTEGER,
    last_access_epoch_ms BIGINT,
    last_access_at TIMESTAMP,
    raw_json VARCHAR
);

CREATE TABLE IF NOT EXISTS aria_ui_poweredoff_vm_runs (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    source VARCHAR,
    host VARCHAR,
    dc_id VARCHAR,
    clusters_count INTEGER,
    vms_count INTEGER,
    total_cpu_vcpus DOUBLE,
    total_memory_gb DOUBLE,
    total_storage_gb DOUBLE,
    total_savings_usd DOUBLE,
    raw_json_path VARCHAR,
    status VARCHAR,
    message VARCHAR
);

CREATE TABLE IF NOT EXISTS aria_ui_poweredoff_vm_details (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    dc_id VARCHAR,
    cluster_name VARCHAR,
    cluster_id VARCHAR,
    vm_name VARCHAR,
    vm_id VARCHAR,
    cpu_vcpus DOUBLE,
    memory_gb DOUBLE,
    storage_gb DOUBLE,
    savings_usd DOUBLE,
    days_in_live INTEGER,
    last_access_epoch_ms BIGINT,
    last_access_at TIMESTAMP,
    raw_json VARCHAR
);

CREATE TABLE IF NOT EXISTS aria_ui_snapshot_vm_runs (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    source VARCHAR,
    host VARCHAR,
    dc_id VARCHAR,
    clusters_count INTEGER,
    vms_count INTEGER,
    total_cpu_vcpus DOUBLE,
    total_memory_gb DOUBLE,
    total_storage_gb DOUBLE,
    total_savings_usd DOUBLE,
    raw_json_path VARCHAR,
    status VARCHAR,
    message VARCHAR
);

CREATE TABLE IF NOT EXISTS aria_ui_snapshot_vm_details (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    dc_id VARCHAR,
    cluster_name VARCHAR,
    cluster_id VARCHAR,
    vm_name VARCHAR,
    vm_id VARCHAR,
    cpu_vcpus DOUBLE,
    memory_gb DOUBLE,
    storage_gb DOUBLE,
    savings_usd DOUBLE,
    days_in_live INTEGER,
    last_access_epoch_ms BIGINT,
    last_access_at TIMESTAMP,
    raw_json VARCHAR
);
"""

def log(msg: str):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)

def norm_base(host: str) -> str:
    h = (host or "").strip()
    if not h.startswith("http"):
        h = "https://" + h
    return h.rstrip("/")

def domain_from_host(host: str) -> str:
    return urlparse(norm_base(host)).hostname or host


def sanitize_cookie(raw: str) -> str:
    s = str(raw or "").strip()
    s = s.replace("\ufeff", "").strip()

    # Se o usuário colou Copy as cURL inteiro, extrai só o header Cookie.
    m = re.search(r'(?is)(?:-H\s+)?[\'"]?Cookie\s*:\s*([^\'"\r\n]+)', s)
    if m:
        s = m.group(1).strip()

    # Se colou "Cookie: a=b; c=d", remove o prefixo.
    s = re.sub(r'(?is)^\s*Cookie\s*:\s*', '', s).strip()

    # Remove wrappers comuns.
    s = s.strip().strip('"').strip("'").strip()

    # Remove quebras de linha/continuações que quebram HTTP header.
    s = re.sub(r'[\r\n\t]+', ' ', s)
    s = re.sub(r'\s*;\s*', '; ', s)
    s = re.sub(r'\s+', ' ', s).strip()

    # Remove headers acidentalmente colados junto.
    for bad in ["Authorization:", "Bearer ", "X-CSRF", "JSESSIONID:"]:
        idx = s.lower().find(bad.lower())
        if idx > 0:
            s = s[:idx].strip().rstrip(";").strip()

    return s

def sanitize_token(raw: str) -> str:
    s = str(raw or "").strip()
    s = s.replace("\ufeff", "").strip()
    # Se colou payload inteiro, extrai secureToken.
    m = re.search(r'(?i)(?:^|[&\s])secureToken=([a-f0-9-]{20,})', s)
    if m:
        return m.group(1).strip()
    # Se colou JSON/html simples.
    m = re.search(r'(?i)secureToken["\']?\s*[:=]\s*["\']?([a-f0-9-]{20,})', s)
    if m:
        return m.group(1).strip()
    return s.strip().strip('"').strip("'")

def get_keyring_secret(name: str):
    try:
        import keyring
    except Exception as e:
        return "", f"keyring_indisponivel:{e}"
    try:
        value = keyring.get_password(SERVICE, name) or ""
        return value, "windows_credential_manager" if value else "vazio"
    except Exception as e:
        return "", f"keyring_erro:{e}"

def cookies_from_browser(domain: str):
    try:
        import browser_cookie3
    except Exception as e:
        return "", f"browser_cookie3 não instalado: {e}"

    errors = []
    for name, loader in [("edge", browser_cookie3.edge), ("chrome", browser_cookie3.chrome)]:
        try:
            cj = loader(domain_name=domain)
            pairs = []
            for c in cj:
                if domain in c.domain or c.domain in domain:
                    pairs.append(f"{c.name}={c.value}")
            if pairs:
                return "; ".join(pairs), name
        except Exception as e:
            errors.append(f"{name}: {e}")
    return "", "falha_browser_cookie: " + " | ".join(errors)

def post_ui(base_url: str, cookie: str, form: dict):
    body = urlencode(form).encode("utf-8")
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": base_url,
        "Referer": base_url + "/ui/index.action#optimize/reclaim",
        "User-Agent": "Mozilla/5.0 RMC-Copilot-UI-Reclaim",
    }
    if cookie:
        headers["Cookie"] = cookie
    req = Request(base_url + "/ui/capacityNew.action", data=body, headers=headers, method="POST")
    try:
        with urlopen(req, context=ssl._create_unverified_context(), timeout=240) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except URLError as e:
        return 0, str(e)

def get_url(base_url: str, cookie: str, path: str):
    headers = {"User-Agent": "Mozilla/5.0 RMC-Copilot-UI-Reclaim", "Accept": "*/*"}
    if cookie:
        headers["Cookie"] = cookie
    req = Request(base_url + path, headers=headers, method="GET")
    try:
        with urlopen(req, context=ssl._create_unverified_context(), timeout=90) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)

def parse_json(text: str):
    s = (text or "").strip()
    try:
        return json.loads(s)
    except Exception:
        start, end = s.find("{"), s.rfind("}")
        if start >= 0 and end > start:
            return json.loads(s[start:end + 1])
        raise

def extract_token_from_cookie(cookie: str):
    for pat in [r"(?:^|;\s*)secureToken=([^;]+)", r"(?:^|;\s*)csrfToken=([^;]+)", r"(?:^|;\s*)XSRF-TOKEN=([^;]+)"]:
        m = re.search(pat, cookie or "", re.I)
        if m:
            return m.group(1), "cookie"
    return "", ""

def extract_token_from_text(text: str):
    if not text:
        return "", ""
    patterns = [
        r'secureToken["\']?\s*[:=]\s*["\']([a-f0-9-]{20,})["\']',
        r'name=["\']secureToken["\']\s+value=["\']([^"\']+)["\']',
        r'secureToken=([a-f0-9-]{20,})',
        r'csrfToken["\']?\s*[:=]\s*["\']([a-f0-9-]{20,})["\']',
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group(1), "html_regex"
    return "", ""

def discover_token(base_url: str, cookie: str):
    t, src = extract_token_from_cookie(cookie)
    if t:
        return t, src
    for path in ["/ui/index.action", "/ui/", "/ui/login.action"]:
        _, text = get_url(base_url, cookie, path)
        t, src = extract_token_from_text(text)
        if t:
            return t, f"{src}:{path}"
    return "", "não_encontrado"

def metric_value(metric):
    if not isinstance(metric, dict):
        return None, None
    unit = str(metric.get("metricUnit") or metric.get("metricUnitId") or "").upper()
    try:
        val = float(metric.get("metricValue"))
    except Exception:
        return None, unit
    return val, unit

def metric_to_gb(metric):
    val, unit = metric_value(metric)
    if val is None:
        return None, None, None
    if unit == "TB":
        return val * 1024.0, val, unit
    if unit == "GB":
        return val, val, unit
    if unit == "MB":
        return val / 1024.0, val, unit
    if unit == "KB":
        return val / 1024.0 / 1024.0, val, unit
    if "BYTE" in unit or unit == "B":
        return val / 1024.0 / 1024.0 / 1024.0, val, unit
    return val, val, unit

def parse_path(vmpath):
    path = str(vmpath or "").strip()
    if path.startswith("ds://"):
        path = path[5:]
    m = re.search(r"/vmfs/volumes/([^/]+)/(.+)", path, flags=re.I)
    volume_uuid = m.group(1) if m else None
    rel = m.group(2) if m else None
    arquivo = (rel or path).replace("\\", "/").rsplit("/", 1)[-1]
    return path, volume_uuid, rel, arquivo

def epoch_ms_to_dt(ms):
    try:
        return datetime.fromtimestamp(int(float(ms)) / 1000.0, tz=timezone.utc).replace(tzinfo=None)
    except Exception:
        return None

def pick_metric(row, candidates):
    if not isinstance(row, dict):
        return None
    for c in candidates:
        if c in row:
            return row.get(c)
    lower = {str(k).lower(): k for k in row.keys()}
    for c in candidates:
        k = lower.get(c.lower())
        if k:
            return row.get(k)
    return None

def get_summary(base_url, cookie, token, dc_id):
    form = {
        "mainAction": "getDCReclaimableCapacityAllData",
        "dcId": dc_id,
        "currentComponentInfo": "TODO",
    }
    if token:
        form["secureToken"] = token
    st, text = post_ui(base_url, cookie, form)
    if st != 200:
        raise RuntimeError(f"Resumo falhou HTTP={st}. Resposta inicial: {text[:500]}")
    return parse_json(text)

def get_page(base_url, cookie, token, dc_id, target_id, vm_state, page, start, limit):
    form = {
        "mainAction": "getReclaimableVms",
        "vmState": vm_state,
        "clusterId": target_id,
        "dcId": dc_id,
        "page": str(page),
        "start": str(start),
        "limit": str(limit),
        "sort": '[{"property":"vmName","direction":"DESC"}]',
        "currentComponentInfo": "TODO",
    }
    if token:
        form["secureToken"] = token
    st, text = post_ui(base_url, cookie, form)
    if st != 200:
        raise RuntimeError(f"Detalhe falhou HTTP={st} vmState={vm_state} target={target_id}. Resposta inicial: {text[:500]}")
    return parse_json(text)

def targets_for_reason(summary, reason):
    key = REASONS[reason]["summary_key"]
    clusters = (((summary or {}).get("clustersByReason") or {}).get(key) or {}).get("clusters") or []
    out = []
    for c in clusters:
        if not isinstance(c, dict) or not c.get("clusterId"):
            continue
        out.append({
            "target_name": c.get("clusterName"),
            "target_id": c.get("clusterId"),
            "raw": c,
        })
    return out

def normalize_item(row, reason, vm_state_used, dc_id, target, run_id, collected_at):
    item_name = row.get("vmName") or row.get("name") or row.get("resourceName")
    item_id = row.get("vmId") or row.get("id") or row.get("resourceId")

    path = volume_uuid = rel = arquivo = None
    if reason == "orphaned_disk" or ".vmdk" in str(item_name).lower():
        path, volume_uuid, rel, arquivo = parse_path(item_name)

    cpu_metric = pick_metric(row, ["cpuMetricReclaimable", "cpuMetric", "cpu", "cpuReclaimable"])
    mem_metric = pick_metric(row, ["memoryMetricReclaimable", "memMetricReclaimable", "memoryMetric", "mem", "memoryReclaimable"])
    storage_metric = pick_metric(row, ["storageMetricReclaimable", "diskMetricReclaimable", "storageMetric", "diskspace", "storageReclaimable"])

    cpu_val, _ = metric_value(cpu_metric)
    if cpu_val is None:
        try:
            cpu_val = float(row.get("cpu") or row.get("vcpus") or row.get("cpuCount"))
        except Exception:
            cpu_val = None

    mem_gb, _, _ = metric_to_gb(mem_metric)
    storage_gb, size_value, size_unit = metric_to_gb(storage_metric)

    try:
        savings = float((row.get("savings") or {}).get("metricValue"))
    except Exception:
        savings = None

    try:
        days = int(float(row.get("daysInLive"))) if row.get("daysInLive") is not None else None
    except Exception:
        days = None

    try:
        last_ms = int(float(row.get("lastAccessDate"))) if row.get("lastAccessDate") is not None else None
    except Exception:
        last_ms = None

    return {
        "run_id": run_id,
        "collected_at": collected_at,
        "reason": reason,
        "vm_state_used": vm_state_used,
        "dc_id": dc_id,
        "target_name": target.get("target_name"),
        "target_id": target.get("target_id"),
        "item_name": item_name,
        "item_id": item_id,
        "vmdk_path": path,
        "vmdk_relative_path": rel,
        "arquivo": arquivo,
        "volume_uuid": volume_uuid,
        "cpu_vcpus": cpu_val,
        "memory_gb": mem_gb,
        "storage_gb": storage_gb,
        "size_value": size_value,
        "size_unit": size_unit,
        "savings_usd": savings,
        "days_in_live": days,
        "last_access_epoch_ms": last_ms,
        "last_access_at": epoch_ms_to_dt(last_ms),
        "raw_json": json.dumps(row, ensure_ascii=False, default=str),
    }

def insert_generic(con, r):
    cols = [
        "run_id","collected_at","reason","vm_state_used","dc_id","target_name","target_id",
        "item_name","item_id","vmdk_path","vmdk_relative_path","arquivo","volume_uuid",
        "cpu_vcpus","memory_gb","storage_gb","size_value","size_unit","savings_usd",
        "days_in_live","last_access_epoch_ms","last_access_at","raw_json"
    ]
    con.execute(f"INSERT INTO aria_ui_optimization_items VALUES ({', '.join(['?'] * len(cols))})", [r[c] for c in cols])

def insert_specialized(con, r):
    reason = r["reason"]

    if reason == "orphaned_disk":
        con.execute("""
            INSERT INTO aria_ui_orphan_vmdk_details VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            r["run_id"], r["collected_at"], r["dc_id"], r["target_name"], r["target_id"], r["volume_uuid"],
            r["vmdk_path"], r["vmdk_relative_path"], r["arquivo"], r["storage_gb"], r["size_value"], r["size_unit"],
            r["savings_usd"], r["days_in_live"], r["last_access_epoch_ms"], r["last_access_at"], r["item_id"], r["raw_json"]
        ])
        con.execute("""
            INSERT INTO orphan_disk_candidates (
                run_id, collected_at, datastore, vmdk_path, arquivo, tamanho_gb,
                data_modificacao, idade_dias, vm_associada_encontrada, cluster,
                status_validacao, confianca, observacao, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
        """, [
            r["run_id"], r["collected_at"], r["target_name"], r["vmdk_path"], r["arquivo"], r["storage_gb"],
            r["last_access_at"], r["days_in_live"], r["target_name"],
            "CANDIDATO_A_ORFAO_ARIA_UI_RECLAIM", 0.98,
            "Coletado pela UI do Aria. Validar antes de qualquer remoção.", r["raw_json"]
        ])
        return

    table = {
        "idle_vms": "aria_ui_idle_vm_details",
        "poweredOff_vms": "aria_ui_poweredoff_vm_details",
        "vm_snapshots": "aria_ui_snapshot_vm_details",
    }.get(reason)

    if table:
        con.execute(f"""
            INSERT INTO {table} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            r["run_id"], r["collected_at"], r["dc_id"], r["target_name"], r["target_id"],
            r["item_name"], r["item_id"], r["cpu_vcpus"], r["memory_gb"], r["storage_gb"],
            r["savings_usd"], r["days_in_live"], r["last_access_epoch_ms"], r["last_access_at"], r["raw_json"]
        ])

def try_collect_target(base_url, cookie, token, dc_id, target, reason, limit):
    variants = REASONS[reason]["state_variants"]
    errors = []

    for vm_state in variants:
        rows_all = []
        page, start, got, total = 1, 0, 0, None
        try:
            while True:
                data = get_page(base_url, cookie, token, dc_id, target["target_id"], vm_state, page, start, limit)
                if total is None:
                    try:
                        total = int(data.get("totalCount") or 0)
                    except Exception:
                        total = 0
                rows = data.get("vms") or []
                if not isinstance(rows, list):
                    rows = []
                rows_all.extend(rows)
                got += len(rows)
                log(f"  vmState={vm_state} page={page} start={start} rows={len(rows)} total={total}")
                if not rows or got >= total or len(rows) < limit:
                    break
                page += 1
                start += limit
            # Aceita variante se retornou dados ou se total era zero sem erro.
            return vm_state, rows_all, ""
        except Exception as e:
            errors.append(f"{vm_state}: {e}")

    return variants[0], [], " | ".join(errors)

def collect_reason(base_url, cookie, token, dc_id, con, run_id, collected_at, summary, reason, limit, max_targets, out_dir):
    targets = targets_for_reason(summary, reason)
    if max_targets > 0:
        targets = targets[:max_targets]

    raw_doc = {"run_id": run_id, "reason": reason, "targets": []}
    total_items = 0
    totals = {"cpu": 0.0, "mem": 0.0, "storage": 0.0, "savings": 0.0}
    vm_state_used_global = None
    status = "OK"
    messages = []

    for target in targets:
        log(f"[{reason}] {target['target_name']} | {target['target_id']}")
        vm_state_used, rows, err = try_collect_target(base_url, cookie, token, dc_id, target, reason, limit)
        vm_state_used_global = vm_state_used_global or vm_state_used
        if err:
            status = "ERRO_PARCIAL"
            messages.append(f"{target['target_name']}: {err}")
            log(f"[WARN] {target['target_name']}: {err}")

        inserted = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            r = normalize_item(row, reason, vm_state_used, dc_id, target, run_id, collected_at)
            if reason == "orphaned_disk" and ".vmdk" not in str(r.get("vmdk_path") or "").lower():
                continue
            insert_generic(con, r)
            insert_specialized(con, r)
            totals["cpu"] += float(r["cpu_vcpus"] or 0)
            totals["mem"] += float(r["memory_gb"] or 0)
            totals["storage"] += float(r["storage_gb"] or 0)
            totals["savings"] += float(r["savings_usd"] or 0)
            inserted += 1
        total_items += inserted
        raw_doc["targets"].append({"target": target, "vm_state_used": vm_state_used, "rows": rows})
        log(f"[OK] {target['target_name']}: itens={inserted}")

    raw_path = out_dir / f"aria_ui_{reason}_{run_id}.json"
    raw_path.write_text(json.dumps(raw_doc, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    con.execute("""
        INSERT INTO aria_ui_optimization_reason_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        run_id, collected_at, reason, vm_state_used_global, len(targets), total_items,
        totals["cpu"], totals["mem"], totals["storage"], totals["savings"],
        status if total_items or status != "OK" else "SEM_ITENS",
        " ; ".join(messages) if messages else "OK",
        str(raw_path)
    ])

    if reason == "orphaned_disk":
        con.execute("""
            INSERT INTO aria_ui_orphan_vmdk_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            run_id, collected_at, "ARIA_UI_SECURE_ALL_OPTIMIZATION", base_url, dc_id,
            len(targets), total_items, totals["storage"], totals["savings"], str(raw_path),
            "OK" if total_items else "SEM_VMDKS", "Coleta segura UI orphaned_disk"
        ])
    elif reason == "idle_vms":
        con.execute("""
            INSERT INTO aria_ui_idle_vm_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            run_id, collected_at, "ARIA_UI_SECURE_ALL_OPTIMIZATION", base_url, dc_id,
            len(targets), total_items, totals["cpu"], totals["mem"], totals["storage"], totals["savings"],
            str(raw_path), "OK" if total_items else "SEM_VMS", "Coleta segura UI idle_vms"
        ])
    elif reason == "poweredOff_vms":
        con.execute("""
            INSERT INTO aria_ui_poweredoff_vm_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            run_id, collected_at, "ARIA_UI_SECURE_ALL_OPTIMIZATION", base_url, dc_id,
            len(targets), total_items, totals["cpu"], totals["mem"], totals["storage"], totals["savings"],
            str(raw_path), "OK" if total_items else "SEM_VMS", "Coleta segura UI poweredOff_vms"
        ])
    elif reason == "vm_snapshots":
        con.execute("""
            INSERT INTO aria_ui_snapshot_vm_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            run_id, collected_at, "ARIA_UI_SECURE_ALL_OPTIMIZATION", base_url, dc_id,
            len(targets), total_items, totals["cpu"], totals["mem"], totals["storage"], totals["savings"],
            str(raw_path), "OK" if total_items else "SEM_VMS", "Coleta segura UI vm_snapshots"
        ])

    return total_items, totals, status, messages

def main():
    ap = argparse.ArgumentParser(description="Etapa 16A.14 - coleta segura de todos os itens de otimização pela UI do Aria")
    ap.add_argument("--host", default=os.getenv("ARIA_UI_HOST") or "mor-vropsprd01.bvnet.bv")
    ap.add_argument("--dc-id", default=os.getenv("ARIA_UI_DC_ID") or "30f49c2a-10b3-4bb2-9c8c-1aef8a486a16")
    ap.add_argument("--db", default="data/database/rmc_copilot.duckdb")
    ap.add_argument("--out-dir", default="data/debug")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--reasons", default="orphaned_disk,idle_vms,poweredOff_vms,vm_snapshots")
    ap.add_argument("--max-targets", type=int, default=0)
    ap.add_argument("--cookie", default=os.getenv("ARIA_UI_COOKIE") or "")
    ap.add_argument("--secure-token", default=os.getenv("ARIA_UI_SECURE_TOKEN") or "")
    ap.add_argument("--allow-browser-cookie", action="store_true")
    ap.add_argument("--no-keyring", action="store_true")
    args = ap.parse_args()

    base_url = norm_base(args.host)
    domain = domain_from_host(args.host)
    collected_at = datetime.now()
    run_id = "ARIAUIALL_" + collected_at.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cookie = sanitize_cookie(args.cookie)
    token = sanitize_token(args.secure_token)
    credential_source = []

    if not args.no_keyring:
        if not cookie:
            cookie, src = get_keyring_secret("cookie")
            cookie = sanitize_cookie(cookie)
            credential_source.append(f"cookie={src}")
        if not token:
            token, src = get_keyring_secret("secureToken")
            token = sanitize_token(token)
            credential_source.append(f"secureToken={src}")

    if not cookie and args.allow_browser_cookie:
        log(f"[AUTO] Tentando ler Cookie do Edge/Chrome para domínio {domain}")
        cookie, src = cookies_from_browser(domain)
        cookie = sanitize_cookie(cookie)
        credential_source.append(f"browser_cookie={src}")

    if cookie and not token:
        log("[AUTO] Tentando descobrir secureToken pela sessão da UI")
        token, src = discover_token(base_url, cookie)
        token = sanitize_token(token)
        credential_source.append(f"discover_token={src}")

    if not cookie:
        raise SystemExit("[ERRO] Cookie não disponível. Salve no Windows Credential Manager com scripts\\200_save_aria_ui_secrets_windows.ps1.")
    if any(x in cookie.lower() for x in ['cookie:', '\\r', '\\n', '-h ']):
        raise SystemExit('[ERRO] Cookie ainda parece conter prefixo/header/cURL. Rode novamente scripts\\200_save_aria_ui_secrets_windows.ps1 e cole só o valor após Cookie:.')
    if len(cookie) < 20 or '=' not in cookie:
        raise SystemExit('[ERRO] Cookie salvo parece inválido/curto. Salve novamente o Cookie completo da aba Headers > Request Headers.')
    log(f"[OK] Cookie carregado do cofre: {len(cookie)} caracteres, {cookie.count(';') + 1} pares aproximados")
    if token:
        log('[OK] secureToken carregado do cofre')
    if not token:
        log("[WARN] secureToken não encontrado. Vou tentar chamar o endpoint sem secureToken.")

    reasons = [x.strip() for x in args.reasons.split(",") if x.strip()]
    invalid = [r for r in reasons if r not in REASONS]
    if invalid:
        raise SystemExit(f"[ERRO] Reason inválido: {invalid}. Válidos: {list(REASONS.keys())}")

    log(f"[INICIO] Coleta segura todos os itens de otimização | run_id={run_id}")
    log("[REGRA] Somente leitura. Nenhuma ação operacional será executada.")
    log(f"[INFO] reasons={','.join(reasons)}")

    con = duckdb.connect(args.db)
    con.execute(SCHEMA_SQL)

    status = "OK"
    messages = []
    try:
        summary = get_summary(base_url, cookie, token, args.dc_id)
        summary_path = out_dir / f"aria_ui_summary_all_{run_id}.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        grand_total = 0
        for reason in reasons:
            total_items, totals, st, msg = collect_reason(
                base_url, cookie, token, args.dc_id, con, run_id, collected_at,
                summary, reason, args.limit, args.max_targets, out_dir
            )
            grand_total += total_items
            if st != "OK":
                status = "ERRO_PARCIAL" if status == "OK" else status
                messages.extend(msg)
            log(f"[RESUMO] {reason}: itens={total_items} cpu={totals['cpu']:.2f} mem_gb={totals['mem']:.2f} storage_gb={totals['storage']:.2f} savings_usd={totals['savings']:.2f}")

        con.execute("""
            INSERT INTO aria_ui_optimization_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            run_id, collected_at, "ARIA_UI_SECURE_ALL_OPTIMIZATION", args.host, args.dc_id,
            ",".join(reasons), ";".join(credential_source), status,
            " ; ".join(messages) if messages else f"OK total_itens={grand_total}",
            str(summary_path)
        ])
        con.commit()

        log(f"[OK] run_id={run_id}")
        log(f"[OK] total_itens={grand_total}")
        log("[FIM] Nenhuma ação operacional executada.")
    except Exception as e:
        try:
            con.execute("""
                INSERT INTO aria_ui_optimization_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                run_id, collected_at, "ARIA_UI_SECURE_ALL_OPTIMIZATION", args.host, args.dc_id,
                ",".join(reasons), ";".join(credential_source), "ERRO", str(e), ""
            ])
            con.commit()
        except Exception:
            pass
        raise
    finally:
        con.close()

if __name__ == "__main__":
    main()
