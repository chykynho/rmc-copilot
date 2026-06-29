from __future__ import annotations

import argparse, getpass, json, os, ssl, sys, uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import duckdb

try:
    import keyring
except Exception:
    keyring = None

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCHEMA = """
CREATE TABLE IF NOT EXISTS datastore_inventory_vrops (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    source VARCHAR,
    vrops_host VARCHAR,
    resource_id VARCHAR,
    name VARCHAR,
    adapter_kind VARCHAR,
    resource_kind VARCHAR,
    resource_status VARCHAR,
    raw_json VARCHAR
);
CREATE TABLE IF NOT EXISTS datastore_collection_runs (
    run_id VARCHAR PRIMARY KEY,
    collected_at TIMESTAMP,
    source VARCHAR,
    vrops_host VARCHAR,
    status VARCHAR,
    total_datastores INTEGER,
    message VARCHAR
);
"""


def log(msg): print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)

def get_password(service_name, username):
    env = os.getenv("VROPS_PASS") or os.getenv("VROPS_PASSWORD")
    if env: return env
    if keyring:
        try:
            saved = keyring.get_password(service_name, username)
            if saved:
                log(f"Credencial encontrada no keyring para {username}")
                return saved
        except Exception: pass
    return getpass.getpass("Senha vROps/Aria: ")

class Client:
    def __init__(self, host):
        self.host = host.rstrip("/")
        if not self.host.startswith("http"): self.host = "https://" + self.host
        self.token = None
        self.ctx = ssl._create_unverified_context()
    def req(self, method, path, payload=None):
        data = None
        headers = {"Accept":"application/json"}
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        if self.token: headers["Authorization"] = "vRealizeOpsToken " + self.token
        r = Request(self.host + path, data=data, method=method, headers=headers)
        try:
            with urlopen(r, context=self.ctx, timeout=120) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return resp.status, json.loads(body) if body.strip().startswith(("{","[")) else body
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return e.code, body
        except URLError as e:
            return 0, str(e)
    def auth(self, user, pwd, auth_source):
        st, data = self.req("POST", "/suite-api/api/auth/token/acquire", {"username":user,"password":pwd,"authSource":auth_source})
        if st not in (200,201): raise RuntimeError(f"Auth falhou HTTP {st}: {data}")
        self.token = data.get("token") or data.get("authToken") or data.get("value")
        if not self.token: raise RuntimeError(f"Token nao encontrado: {data}")


def extract_resources(data):
    if isinstance(data, list): return data
    if not isinstance(data, dict): return []
    for key in ["resourceList", "resources", "resource", "items", "values"]:
        val = data.get(key)
        if isinstance(val, list): return val
    return []


def get_name(r):
    return r.get("resourceKey", {}).get("name") or r.get("name") or r.get("identifier") or "N/A"

def get_id(r):
    return r.get("identifier") or r.get("id") or r.get("resourceId") or r.get("resourceKey", {}).get("resourceId")

def get_adapter(r):
    return r.get("resourceKey", {}).get("adapterKindKey") or r.get("adapterKindKey") or r.get("adapterKind")

def get_kind(r):
    return r.get("resourceKey", {}).get("resourceKindKey") or r.get("resourceKindKey") or r.get("resourceKind")


def main():
    ap = argparse.ArgumentParser(description="Coleta datastores via vROps/Aria API")
    ap.add_argument("--host", default=os.getenv("VROPS_HOST") or "mor-vropsprd01.bvnet.bv")
    ap.add_argument("--auth-source", default=os.getenv("VROPS_AUTH_SOURCE") or "bvnet.bv")
    ap.add_argument("--user", default=os.getenv("VROPS_USER") or "")
    ap.add_argument("--db", default="data/database/rmc_copilot.duckdb")
    ap.add_argument("--page-size", type=int, default=1000)
    args = ap.parse_args()

    user = args.user.strip() or input("Usuário vROps/Aria: ").strip()
    pwd = get_password("vROps_Access", user)
    c = Client(args.host)
    log(f"[INICIO] Datastores via vROps API | host={args.host}")
    c.auth(user, pwd, args.auth_source)

    all_resources = []
    page = 0
    while True:
        q = urlencode({"adapterKind":"VMWARE", "resourceKind":"Datastore", "page":page, "pageSize":args.page_size})
        st, data = c.req("GET", f"/suite-api/api/resources?{q}")
        if st != 200: raise RuntimeError(f"Falha resources Datastore HTTP {st}: {data}")
        resources = extract_resources(data)
        log(f"Página {page}: {len(resources)} datastores")
        all_resources.extend(resources)
        if len(resources) < args.page_size: break
        page += 1
        if page > 100: break

    run_id = "DSVROPS_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    collected_at = datetime.now()
    db = Path(args.db); db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    try:
        con.execute(SCHEMA)
        rows = []
        for r in all_resources:
            rows.append([run_id, collected_at, "VROPS_API", args.host, get_id(r), get_name(r), get_adapter(r), get_kind(r), str(r.get("resourceStatusStates") or r.get("status") or ""), json.dumps(r, ensure_ascii=False, default=str)])
        con.executemany("""
            INSERT INTO datastore_inventory_vrops
            (run_id,collected_at,source,vrops_host,resource_id,name,adapter_kind,resource_kind,resource_status,raw_json)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, rows)
        con.execute("""
            INSERT INTO datastore_collection_runs
            (run_id,collected_at,source,vrops_host,status,total_datastores,message)
            VALUES (?,?,?,?,?,?,?)
        """, [run_id, collected_at, "VROPS_API", args.host, "OK", len(rows), "Coleta de recursos Datastore via vROps API. Somente leitura."])
    finally:
        con.close()
    log(f"[OK] run_id={run_id} datastores={len(all_resources)}")
    log("[FIM] Nenhuma ação operacional executada.")

if __name__ == "__main__": main()
