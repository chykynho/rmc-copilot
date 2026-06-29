from __future__ import annotations

import argparse
import getpass
import json
import os
import ssl
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
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

KEYWORDS = [
    "orphan", "órf", "orfa", "orphaned", "disk", "disco", "vmdk",
    "snapshot", "powered", "power", "deslig", "datastore", "storage"
]


def log(msg: str) -> None:
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


def get_password(service_name: str, username: str) -> str:
    env = os.getenv("VROPS_PASS") or os.getenv("VROPS_PASSWORD")
    if env:
        return env
    if keyring:
        try:
            saved = keyring.get_password(service_name, username)
            if saved:
                log(f"Credencial encontrada no keyring para {username}")
                return saved
        except Exception:
            pass
    return getpass.getpass("Senha vROps/Aria: ")


class AriaClient:
    def __init__(self, host: str, token: str | None = None):
        self.host = host.rstrip("/")
        if not self.host.startswith("http"):
            self.host = "https://" + self.host
        self.token = token
        self.ctx = ssl._create_unverified_context()

    def request(self, method: str, path: str, payload=None, accept="application/json"):
        url = self.host + path
        data = None
        headers = {"Accept": accept}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"vRealizeOpsToken {self.token}"
        req = Request(url, data=data, method=method.upper(), headers=headers)
        try:
            with urlopen(req, context=self.ctx, timeout=120) as resp:
                body = resp.read()
                ctype = resp.headers.get("Content-Type", "")
                if "json" in ctype.lower() or (body[:1] in (b"{", b"[")):
                    return resp.status, json.loads(body.decode("utf-8", errors="replace") or "{}")
                return resp.status, body.decode("utf-8", errors="replace")
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = body
            return e.code, {"error": parsed}
        except URLError as e:
            return 0, {"error": str(e)}

    def acquire_token(self, username: str, password: str, auth_source: str) -> str:
        status, data = self.request("POST", "/suite-api/api/auth/token/acquire", {
            "username": username,
            "password": password,
            "authSource": auth_source,
        })
        if status not in (200, 201):
            raise RuntimeError(f"Falha ao obter token. HTTP {status}: {data}")
        token = data.get("token") or data.get("authToken") or data.get("value")
        if not token:
            raise RuntimeError(f"Token não encontrado na resposta: {data}")
        self.token = token
        return token


def find_keyword_hits(obj, path=""):
    hits = []
    try:
        text = ""
        if isinstance(obj, dict):
            for k, v in obj.items():
                hits.extend(find_keyword_hits(v, f"{path}.{k}" if path else str(k)))
            text = json.dumps(obj, ensure_ascii=False, default=str)[:5000]
        elif isinstance(obj, list):
            for i, v in enumerate(obj[:2000]):
                hits.extend(find_keyword_hits(v, f"{path}[{i}]"))
            return hits
        else:
            text = str(obj)
        low = text.lower()
        for kw in KEYWORDS:
            if kw.lower() in low:
                hits.append({"path": path, "keyword": kw, "sample": text[:500]})
                break
    except Exception:
        pass
    return hits


def count_items(data):
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ["resourceList", "resources", "viewDefinitions", "views", "reportDefinitions", "reports", "values", "data", "items"]:
            val = data.get(key)
            if isinstance(val, list):
                return len(val)
        page = data.get("pageInfo") or data.get("page") or {}
        if isinstance(page, dict):
            return page.get("totalCount") or page.get("totalElements") or None
    return None


def main():
    ap = argparse.ArgumentParser(description="Etapa 16A.3 - Probe API Aria/vROps para datastores, views e reports de otimização")
    ap.add_argument("--host", default=os.getenv("VROPS_HOST") or "mor-vropsprd01.bvnet.bv")
    ap.add_argument("--auth-source", default=os.getenv("VROPS_AUTH_SOURCE") or "bvnet.bv")
    ap.add_argument("--user", default=os.getenv("VROPS_USER") or "")
    ap.add_argument("--out-dir", default="data/debug")
    ap.add_argument("--page-size", type=int, default=1000)
    args = ap.parse_args()

    username = args.user.strip() or input("Usuário vROps/Aria: ").strip()
    password = get_password("vROps_Access", username)

    client = AriaClient(args.host)
    log(f"[INICIO] Probe API Aria/vROps | host={args.host} | authSource={args.auth_source}")
    client.acquire_token(username, password, args.auth_source)
    log("[OK] Token obtido")

    endpoints = []
    ps = args.page_size
    endpoints.extend([
        ("resources_datastore_1", f"/suite-api/api/resources?{urlencode({'resourceKind':'Datastore','pageSize':ps})}"),
        ("resources_datastore_2", f"/suite-api/api/resources?{urlencode({'adapterKind':'VMWARE','resourceKind':'Datastore','pageSize':ps})}"),
        ("resources_storagepod", f"/suite-api/api/resources?{urlencode({'resourceKind':'StoragePod','pageSize':ps})}"),
        ("resources_search_orphan", f"/suite-api/api/resources?{urlencode({'name':'orphan','pageSize':100})}"),
        ("adapter_resource_kinds_vmware", "/suite-api/api/adapterkinds/VMWARE/resourcekinds"),
        ("viewdefinitions", "/suite-api/api/viewdefinitions"),
        ("views", "/suite-api/api/views"),
        ("reportdefinitions", "/suite-api/api/reportdefinitions"),
        ("reports", "/suite-api/api/reports"),
        ("supermetrics", "/suite-api/api/supermetrics"),
    ])

    results = {
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "host": args.host,
        "auth_source": args.auth_source,
        "endpoints": {},
        "keyword_hits": [],
        "notes": [
            "Este probe não executa ação operacional.",
            "Objetivo: descobrir onde Aria expõe Datastores e relatórios/views de orphaned disks/snapshots/powered off.",
        ]
    }

    for name, path in endpoints:
        log(f"[GET] {name}: {path}")
        status, data = client.request("GET", path)
        hits = find_keyword_hits(data)
        results["endpoints"][name] = {
            "path": path,
            "status": status,
            "count_hint": count_items(data),
            "data": data,
            "keyword_hits": hits[:100],
        }
        for h in hits[:50]:
            h2 = dict(h)
            h2["endpoint"] = name
            results["keyword_hits"].append(h2)
        log(f"      HTTP={status} count_hint={count_items(data)} hits={len(hits)}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"aria_optimization_api_probe_{stamp}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    summary = out_dir / f"aria_optimization_api_probe_{stamp}_summary.txt"
    lines = []
    lines.append(f"Probe Aria/vROps API - {stamp}")
    lines.append(f"Host: {args.host}")
    lines.append("")
    for name, info in results["endpoints"].items():
        lines.append(f"{name}: HTTP={info['status']} count_hint={info['count_hint']} hits={len(info['keyword_hits'])}")
        for h in info["keyword_hits"][:10]:
            sample = str(h.get("sample", "")).replace("\n", " ")[:220]
            lines.append(f"  - {h.get('keyword')} em {h.get('path')}: {sample}")
    summary.write_text("\n".join(lines), encoding="utf-8")

    log(f"[OK] JSON: {out}")
    log(f"[OK] Resumo: {summary}")
    log("[FIM] Mande o arquivo *_summary.txt se precisar ajustar o endpoint exato de exportação.")


if __name__ == "__main__":
    main()
