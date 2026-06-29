from __future__ import annotations

import argparse
import getpass
import json
import math
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EXPECTED_CLUSTERS = [
    "BV_PRD_01_VxRAIL_RHEL",
    "BV_PRD_02_VxRAIL_Windows",
    "BV_PRD_03_Windows",
    "BV_PRD_03_VxRAIL-VOZ",
    "BV_PRD_04_VxRAIL-XENAPP",
    "BV_PRD_05_VxRAIL_Windows",
    "BV_PRD_06_VxRAIL-VDI",
    "BV_PRD_07_VxRAIL_RHEL",
    "BV_PRD_08_Oracle",
    "BV_PRD_09_SQL",
    "BV_PRD_10_Storage",
]

SCHEMA_SQL = open(Path(__file__).with_name("160_prepare_optimization_schema.py"), encoding="utf-8").read().split('SCHEMA_SQL = r"""',1)[1].split('"""',1)[0]


def log(msg: str):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


def safe_float(v):
    try:
        if v is None or pd.isna(v):
            return None
        x = float(v)
        if not math.isfinite(x):
            return None
        return x
    except Exception:
        return None


def norm_text(s: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s or "").lower()).strip("_")


def parse_dt(value):
    if value in (None, "", "None"):
        return None
    if isinstance(value, (int, float)):
        # vROps normalmente usa epoch ms; aceita epoch s também.
        x = float(value)
        if x > 10_000_000_000:
            x = x / 1000.0
        try:
            return datetime.fromtimestamp(x, tz=timezone.utc).replace(tzinfo=None)
        except Exception:
            return None
    s = str(value).strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    for fmt in [None, "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d"]:
        try:
            if fmt is None:
                return datetime.fromisoformat(s).replace(tzinfo=None)
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (dict, list)):
                out.update(flatten(v, key))
            else:
                out[key] = v
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            key = f"{prefix}[{i}]"
            if isinstance(v, (dict, list)):
                out.update(flatten(v, key))
            else:
                out[key] = v
    return out


class VropsClient:
    def __init__(self, host: str, auth_source: str):
        self.host = host
        self.base_url = f"https://{host}"
        self.auth_source = auth_source
        self.headers = None

    def authenticate(self, username: str, password: str):
        payload = {"username": username, "password": password, "authSource": self.auth_source}
        url = f"{self.base_url}/suite-api/api/auth/token/acquire"
        r = requests.post(url, json=payload, headers={"Content-Type": "application/json", "Accept": "application/json"}, verify=False, timeout=60)
        log(f"Status token: {r.status_code}")
        if r.status_code != 200:
            raise RuntimeError(f"Falha ao obter token vROps {r.status_code}: {r.text[:1000]}")
        data = r.json()
        token = data.get("token") or data.get("auth-token") or data.get("authToken")
        if not token:
            raise RuntimeError("Token vROps não encontrado na resposta")
        self.headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"vRealizeOpsToken {token}"}

    def get(self, endpoint: str, params=None, timeout=120):
        url = f"{self.base_url}{endpoint}"
        r = requests.get(url, headers=self.headers, params=params, verify=False, timeout=timeout)
        if r.status_code != 200:
            raise RuntimeError(f"GET {endpoint} falhou {r.status_code}: {r.text[:1000]}")
        return r.json()

    def get_no_raise(self, endpoint: str, params=None, timeout=120):
        try:
            url = f"{self.base_url}{endpoint}"
            r = requests.get(url, headers=self.headers, params=params, verify=False, timeout=timeout)
            try:
                return r.json(), r.status_code, r.text
            except Exception:
                return None, r.status_code, r.text
        except Exception as exc:
            return None, None, str(exc)


def parse_resources_list(data):
    rows = []
    for res in data.get("resourceList", []) or data.get("resources", []) or []:
        rk = res.get("resourceKey", {}) or {}
        rows.append({
            "identifier": res.get("identifier") or res.get("resourceId") or res.get("id"),
            "name": rk.get("name") or res.get("name"),
            "adapterKindKey": rk.get("adapterKindKey") or res.get("adapterKindKey"),
            "resourceKindKey": rk.get("resourceKindKey") or res.get("resourceKindKey"),
            "raw": res,
        })
    if not rows:
        return pd.DataFrame(columns=["identifier", "name", "adapterKindKey", "resourceKindKey", "raw"])
    return pd.DataFrame(rows).drop_duplicates("identifier").reset_index(drop=True)


def list_resources(client: VropsClient, page_size=1000, max_pages=1000):
    frames = []
    for page in range(max_pages):
        data = client.get("/suite-api/api/resources", params={"pageSize": page_size, "page": page})
        df = parse_resources_list(data)
        if df.empty:
            break
        frames.append(df)
        log(f"Recursos página {page}: {len(df)}")
        if len(df) < page_size:
            break
    if not frames:
        return pd.DataFrame(columns=["identifier", "name", "adapterKindKey", "resourceKindKey", "raw"])
    return pd.concat(frames, ignore_index=True).drop_duplicates("identifier").reset_index(drop=True)


def get_properties(client: VropsClient, rid: str):
    # Endpoints variam por versão; tenta os formatos comuns.
    attempts = [
        f"/suite-api/api/resources/{rid}/properties",
        f"/suite-api/api/resources/{rid}/properties/latest",
    ]
    for ep in attempts:
        data, status, text = client.get_no_raise(ep, timeout=90)
        if status == 200 and data is not None:
            return data
    return {}


def first_by_key(flat: dict, patterns: list[str]):
    for pat in patterns:
        rx = re.compile(pat, re.I)
        for k, v in flat.items():
            if rx.search(str(k)) and v not in (None, ""):
                return v
    return None


def extract_power_state(flat: dict, raw: dict):
    val = first_by_key(flat, [r"power.?state", r"runtime.*power", r"summary.*power"])
    if val is None:
        raw_flat = flatten(raw)
        val = first_by_key(raw_flat, [r"power.?state", r"runtime.*power"])
    if val is None:
        # Procura valor textual de power state em qualquer campo.
        for v in list(flat.values())[:5000]:
            s = str(v).lower()
            if "poweredoff" in s or "powered_off" in s or "powered off" in s:
                return "poweredOff"
            if "poweredon" in s or "powered_on" in s or "powered on" in s:
                return "poweredOn"
    return str(val) if val is not None else None


def is_powered_off(power_state: str | None) -> bool:
    s = norm_text(power_state)
    return any(x in s for x in ["poweredoff", "powered_off", "power_off", "off", "stopped", "desligada", "desligado"])


def extract_resource_numbers(flat: dict):
    cpu = safe_float(first_by_key(flat, [r"num.?cpu", r"cpu.?count", r"vcpu", r"config.*cpu", r"summary.*cpu"]))
    mem = safe_float(first_by_key(flat, [r"memory.*gb", r"memoria.*gb", r"mem.*gb", r"memory.*mb", r"mem.*mb", r"configured.*memory"]))
    if mem and mem > 1024:
        mem = mem / 1024.0
    disk = safe_float(first_by_key(flat, [r"provisioned.*gb", r"disk.*provision", r"storage.*provision", r"disk.*gb", r"storage.*gb"]))
    return cpu, mem, disk


def find_inventory_map(con):
    # Best effort: procura tabelas já existentes com nome de VM, cluster e host.
    mapping = {}
    try:
        tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
    except Exception:
        return mapping

    candidate_tables = [t for t in tables if any(x in t.lower() for x in ["vm", "invent", "allocation", "selecionadas"])]
    for t in candidate_tables:
        try:
            df_cols = con.execute(f"DESCRIBE SELECT * FROM {q(t)}").fetchdf()
            cols = list(df_cols["column_name"])
            low = {c.lower(): c for c in cols}
            name_col = next((c for c in cols if c.lower() in ["vm_name", "name", "vm", "nome_vm", "servidor"] or "vm" in c.lower() and "name" in c.lower()), None)
            cluster_col = next((c for c in cols if "cluster" in c.lower()), None)
            host_col = next((c for c in cols if c.lower() in ["host", "host_name", "esxi"] or "host" in c.lower()), None)
            rid_col = next((c for c in cols if "resource" in c.lower() and "id" in c.lower()), None)
            if not name_col:
                continue
            select_cols = [name_col]
            if cluster_col: select_cols.append(cluster_col)
            if host_col: select_cols.append(host_col)
            if rid_col: select_cols.append(rid_col)
            sql = "SELECT DISTINCT " + ", ".join(q(c) for c in select_cols) + f" FROM {q(t)} LIMIT 50000"
            df = con.execute(sql).fetchdf()
            for _, row in df.iterrows():
                name = str(row.get(name_col) or "").strip().upper()
                if not name:
                    continue
                mapping.setdefault(name, {})
                if cluster_col and row.get(cluster_col) is not None:
                    mapping[name]["cluster"] = str(row.get(cluster_col))
                if host_col and row.get(host_col) is not None:
                    mapping[name]["host"] = str(row.get(host_col))
                if rid_col and row.get(rid_col) is not None:
                    mapping[name]["resource_id"] = str(row.get(rid_col))
        except Exception:
            continue
    return mapping


def q(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def classify_snapshot(age):
    x = safe_float(age)
    if x is None:
        return "VALIDAR"
    if x >= 60:
        return "CRITICO"
    if x >= 30:
        return "RISCO"
    if x > 20:
        return "ATENCAO"
    return "OK"


def extract_snapshot_rows(vm_name, rid, cluster, host, flat, raw, collected_at, run_id):
    rows = []
    # Primeiro tenta chaves explícitas de count/age/create/size.
    count = safe_float(first_by_key(flat, [r"snapshot.*count", r"num.*snapshot"]))
    created = first_by_key(flat, [r"snapshot.*created", r"snapshot.*create", r"snapshot.*time", r"snapshot.*date"])
    age = safe_float(first_by_key(flat, [r"snapshot.*age", r"snapshot.*days", r"snapshot.*idade"]))
    size = safe_float(first_by_key(flat, [r"snapshot.*size.*gb", r"snapshot.*gb", r"snapshot.*size"]))
    snap_name = first_by_key(flat, [r"snapshot.*name"])

    created_dt = parse_dt(created)
    if age is None and created_dt:
        age = (datetime.now() - created_dt).total_seconds() / 86400.0
    if size and size > 10_000_000:
        size = size / (1024.0 ** 3)

    # Se encontrou alguma evidência real de snapshot, grava um registro consolidado.
    if any(v not in (None, "", 0) for v in [count, created, age, size, snap_name]):
        rows.append({
            "run_id": run_id,
            "collected_at": collected_at,
            "vm_name": vm_name,
            "vm_resource_id": rid,
            "cluster": cluster,
            "host": host,
            "snapshot_name": str(snap_name or "SNAPSHOT_DETECTADO_PELO_VROPS"),
            "snapshot_created_at": created_dt,
            "snapshot_age_days": age,
            "snapshot_size_gb": size,
            "snapshot_count": int(count) if count is not None else 1,
            "datastore": str(first_by_key(flat, [r"datastore", r"storage.*name"]) or ""),
            "status_risco": classify_snapshot(age),
            "raw_json": json.dumps({"snapshot_keys": {k: str(v) for k, v in flat.items() if "snapshot" in k.lower()}}, ensure_ascii=False)[:20000],
        })
    return rows


def import_orphan_csv(path, run_id, collected_at):
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV de discos órfãos não encontrado: {p}")
    df = pd.read_csv(p, sep=None, engine="python")
    rows = []
    for _, r in df.iterrows():
        raw = {str(k): (None if pd.isna(v) else v) for k, v in r.to_dict().items()}
        lower = {norm_text(k): k for k in raw.keys()}
        def pick(*names):
            for n in names:
                k = lower.get(norm_text(n))
                if k:
                    return raw.get(k)
            return None
        mod = parse_dt(pick("data_modificacao", "modified", "last_modified", "mtime"))
        age = None
        if mod:
            age = (datetime.now() - mod).total_seconds() / 86400.0
        rows.append({
            "run_id": run_id,
            "collected_at": collected_at,
            "datastore": str(pick("datastore") or ""),
            "vmdk_path": str(pick("vmdk_path", "path", "arquivo", "file") or ""),
            "arquivo": str(pick("arquivo", "file", "filename") or ""),
            "tamanho_gb": safe_float(pick("tamanho_gb", "size_gb", "gb")),
            "data_modificacao": mod,
            "idade_dias": age,
            "vm_associada_encontrada": str(pick("vm_associada_encontrada", "vm", "vm_name") or ""),
            "cluster": str(pick("cluster") or ""),
            "status_validacao": "CANDIDATO_A_ORFAO",
            "confianca": safe_float(pick("confianca", "confidence")) or 0.50,
            "observacao": "Candidato importado para validação. Não executar remoção automática.",
            "raw_json": json.dumps(raw, ensure_ascii=False)[:20000],
        })
    return rows


def insert_df(con, table, rows):
    if not rows:
        return 0
    df = pd.DataFrame(rows)
    con.register("_tmp_insert", df)
    con.execute(f"INSERT INTO {table} SELECT * FROM _tmp_insert")
    con.unregister("_tmp_insert")
    return len(df)


def main():
    ap = argparse.ArgumentParser(description="Etapa 16A - coleta otimização via vROps")
    ap.add_argument("--host", default="mor-vropsprd01.bvnet.bv")
    ap.add_argument("--auth-source", default="bvnet.bv")
    ap.add_argument("--username", default="")
    ap.add_argument("--password", default=os.environ.get("RMC_VROPS_PASSWORD", ""))
    ap.add_argument("--cluster", default="ALL", help="Filtro lógico; enriquecimento usa inventário local quando existir")
    ap.add_argument("--db", default="data/database/rmc_copilot.duckdb")
    ap.add_argument("--max-vms", type=int, default=0, help="0 = sem limite")
    ap.add_argument("--orphan-csv", default="", help="CSV opcional de candidatos a disco órfão")
    args = ap.parse_args()

    if not args.username:
        args.username = input("Usuário vROps: ").strip()
    if not args.password:
        args.password = getpass.getpass("Senha vROps: ")

    run_id = "OPT16A_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    collected_at = datetime.now()
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute(SCHEMA_SQL)

    total_vms = total_off = total_snaps = total_snaps_20 = total_orphans = 0
    status = "OK"
    message = "Coleta concluída."

    try:
        inventory_map = find_inventory_map(con)
        log(f"Inventário local para enriquecimento: {len(inventory_map)} VMs")

        client = VropsClient(args.host, args.auth_source)
        client.authenticate(args.username, args.password)

        resources = list_resources(client)
        vms = resources[
            resources["adapterKindKey"].astype(str).str.upper().eq("VMWARE")
            & resources["resourceKindKey"].astype(str).str.contains("VirtualMachine|VM", case=False, na=False)
        ].copy()
        if args.max_vms and args.max_vms > 0:
            vms = vms.head(args.max_vms)
        total_vms = len(vms)
        log(f"VMs VMware encontradas: {total_vms}")

        power_rows = []
        snap_rows = []
        for i, row in vms.reset_index(drop=True).iterrows():
            vm_name = str(row.get("name") or "").strip()
            rid = str(row.get("identifier") or "").strip()
            if not vm_name or not rid:
                continue
            if i % 100 == 0:
                log(f"Processando VM {i+1}/{total_vms}: {vm_name}")
            props = get_properties(client, rid)
            flat = flatten(props)
            raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
            inv = inventory_map.get(vm_name.upper(), {})
            cluster = inv.get("cluster", "")
            host = inv.get("host", "")
            power_state = extract_power_state(flat, raw)
            off = is_powered_off(power_state)
            if off:
                total_off += 1
            cpu, mem, disk = extract_resource_numbers(flat)
            off_date = parse_dt(first_by_key(flat, [r"power.*off.*time", r"powered.*off.*time", r"shutdown.*time", r"last.*powered.*off"]))
            dias = None
            if off and off_date:
                dias = (datetime.now() - off_date).total_seconds() / 86400.0
            ds_names = first_by_key(flat, [r"datastore.*name", r"storage.*name"])
            power_rows.append({
                "run_id": run_id,
                "collected_at": collected_at,
                "vm_name": vm_name,
                "vm_resource_id": rid,
                "cluster": cluster,
                "host": host,
                "power_state": power_state,
                "is_powered_off": bool(off),
                "dias_desligada": dias,
                "cpu_count": cpu,
                "memory_gb": mem,
                "disk_provisioned_gb": disk,
                "datastore_names": str(ds_names or ""),
                "ambiente": "PRD" if str(cluster).upper().startswith("BV_PRD") else "",
                "raw_json": json.dumps({"properties_sample": {k: str(v) for k, v in list(flat.items())[:300]}}, ensure_ascii=False)[:20000],
            })
            sr = extract_snapshot_rows(vm_name, rid, cluster, host, flat, raw, collected_at, run_id)
            snap_rows.extend(sr)

        total_snaps = insert_df(con, "vm_snapshot_inventory", snap_rows)
        total_snaps_20 = len([r for r in snap_rows if safe_float(r.get("snapshot_age_days")) and safe_float(r.get("snapshot_age_days")) > 20])
        insert_df(con, "vm_power_state_snapshots", power_rows)
        orphan_rows = import_orphan_csv(args.orphan_csv, run_id, collected_at) if args.orphan_csv else []
        total_orphans = insert_df(con, "orphan_disk_candidates", orphan_rows)

    except Exception as exc:
        status = "ERRO"
        message = str(exc)
        log(f"[ERRO] {message}")
        raise
    finally:
        con.execute(
            "INSERT OR REPLACE INTO optimization_collection_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [run_id, collected_at, "vROps API", args.host, args.auth_source, args.cluster, status, message,
             int(total_vms), int(total_off), int(total_snaps), int(total_snaps_20), int(total_orphans)]
        )
        con.close()

    log(f"[OK] run_id={run_id}")
    log(f"[OK] VMs={total_vms} | powered_off={total_off} | snapshots={total_snaps} | snapshots>20d={total_snaps_20} | discos_candidatos={total_orphans}")
    log("[IMPORTANTE] Nenhuma ação operacional foi executada. A coleta só registra dados para análise e recomendação.")

if __name__ == "__main__":
    main()
