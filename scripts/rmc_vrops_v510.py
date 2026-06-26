
import re
import json
import math
import getpass
import logging
from datetime import datetime, timedelta

import requests
import urllib3
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CPU_STATKEY_CANDIDATES = ["cpu|usage_average", "cpu|demand_average", "cpu|usagemhz_average"]
MEM_STATKEY_CANDIDATES = ["mem|usage_average", "mem|guest_usage", "mem|consumed_average", "mem|active_average", "mem|demand_average"]

VALID_GUESTFS_METRICS = {
    "capacity": "capacity_gb",
    "freespace": "free_gb",
    "free": "free_gb",
    "usage": "used_gb",
    "used": "used_gb",
    "usedspace": "used_gb",
}

def setup_logger(log_file):
    logger = logging.getLogger("RMC_VROPS_V510")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    sh = logging.StreamHandler()
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger

def safe_filename(text):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(text)).strip("_")

class VropsClient:
    def __init__(self, host, auth_source="bvnet.bv", logger=None):
        self.host = host
        self.base_url = f"https://{host}"
        self.auth_source = auth_source
        self.token = None
        self.headers = None
        self.logger = logger or logging.getLogger("RMC_VROPS_V510")

    def authenticate(self, username=None, password=None):
        if not username:
            username = input("Usuário vROps: ").strip()
        if not password:
            password = getpass.getpass("Senha vROps: ")

        payload = {"username": username, "password": password, "authSource": self.auth_source}
        r = requests.post(
            f"{self.base_url}/suite-api/api/auth/token/acquire",
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            verify=False,
            timeout=60,
        )
        print("Status token:", r.status_code)
        self.logger.info("Status token: %s", r.status_code)
        if r.status_code != 200:
            raise RuntimeError(f"Falha ao obter token: {r.text[:1500]}")
        data = r.json()
        self.token = data.get("token") or data.get("auth-token") or data.get("authToken")
        if not self.token:
            raise RuntimeError("Token não encontrado.")
        self.headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"vRealizeOpsToken {self.token}"}
        print("✓ Token obtido com sucesso.")
        return True

    def get(self, endpoint, params=None, timeout=120):
        self.logger.info("GET %s params=%s", endpoint, params)
        r = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, params=params, verify=False, timeout=timeout)
        self.logger.info("GET %s status=%s", endpoint, r.status_code)
        if r.status_code != 200:
            raise RuntimeError(f"Erro API {r.status_code}: {r.text[:1500]}")
        return r.json()

    def get_no_raise(self, endpoint, params=None, timeout=120):
        try:
            r = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, params=params, verify=False, timeout=timeout)
            try:
                data = r.json()
            except Exception:
                data = None
            return data, r.status_code, r.text
        except Exception as e:
            return None, None, str(e)

    def parse_resources(self, data):
        rows = []
        for res in data.get("resourceList", []) or data.get("resources", []) or []:
            rk = res.get("resourceKey", {}) or {}
            rows.append({"identifier": res.get("identifier"), "name": rk.get("name") or res.get("name"), "adapterKindKey": rk.get("adapterKindKey"), "resourceKindKey": rk.get("resourceKindKey"), "raw": res})
        return pd.DataFrame(rows)

    def list_resources(self, name=None, page_size=1000, max_pages=100):
        frames = []
        for page in range(max_pages):
            params = {"pageSize": page_size, "page": page}
            if name:
                params["name"] = name
            df = self.parse_resources(self.get("/suite-api/api/resources", params=params))
            if df.empty:
                break
            frames.append(df)
            if len(df) < page_size:
                break
        if not frames:
            return pd.DataFrame(columns=["identifier", "name", "adapterKindKey", "resourceKindKey", "raw"])
        return pd.concat(frames, ignore_index=True).drop_duplicates("identifier").reset_index(drop=True)

    def search_resources_by_name(self, name):
        return self.list_resources(name=name, page_size=200, max_pages=10)

    def get_statkeys(self, resource_id):
        data = self.get(f"/suite-api/api/resources/{resource_id}/statkeys")
        stat_keys = data.get("stat-key", []) or data.get("statKeys", []) or data.get("statKey", []) or data.get("values", [])
        rows = []
        for item in stat_keys:
            key = item.get("key") or item.get("statKey") or item.get("name") if isinstance(item, dict) else str(item)
            rows.append({"key": key, "raw": item})
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.dropna(subset=["key"]).drop_duplicates("key").reset_index(drop=True)
        return df

    def get_stats(self, resource_id, stat_key, days_back=90):
        end = datetime.now()
        start = end - timedelta(days=days_back)
        variants = [
            {"statKey": stat_key, "begin": int(start.timestamp() * 1000), "end": int(end.timestamp() * 1000), "rollUpType": "AVG", "intervalType": "DAYS", "intervalQuantifier": 1},
            {"statKey": stat_key, "begin": int(start.timestamp() * 1000), "end": int(end.timestamp() * 1000)},
        ]
        last = None
        for params in variants:
            try:
                data = self.get(f"/suite-api/api/resources/{resource_id}/stats", params=params)
                last = data
                df = parse_stats_response(data, stat_key)
                if not df.empty:
                    return df, data
            except Exception as e:
                last = {"error": str(e)}
        return pd.DataFrame(), last

def parse_stats_response(data, stat_key):
    rows = []
    def add(ts, vals):
        for t, v in zip(ts, vals):
            try:
                rows.append({"stat_key": stat_key, "timestamp_ms": int(t), "date": pd.to_datetime(int(t), unit="ms"), "value": v})
            except Exception:
                pass
    def walk(x):
        if isinstance(x, dict):
            if "timestamps" in x and ("data" in x or "values" in x):
                add(x.get("timestamps", []), x.get("data", x.get("values", [])))
            if "timestamps" in x and "statValues" in x:
                add(x.get("timestamps", []), x.get("statValues", []))
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for i in x:
                walk(i)
    walk(data)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["date", "value"]).drop_duplicates().sort_values("date").reset_index(drop=True)
    return df

def extract_resources(obj):
    rows = []
    def walk(x):
        if isinstance(x, dict):
            if "identifier" in x and isinstance(x.get("resourceKey"), dict):
                rk = x.get("resourceKey", {}) or {}
                rows.append({"identifier": x.get("identifier"), "name": rk.get("name") or x.get("name"), "adapterKindKey": rk.get("adapterKindKey"), "resourceKindKey": rk.get("resourceKindKey"), "raw": x})
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for i in x:
                walk(i)
    walk(obj)
    if not rows:
        return pd.DataFrame(columns=["identifier", "name", "adapterKindKey", "resourceKindKey", "raw"])
    return pd.DataFrame(rows).drop_duplicates("identifier").reset_index(drop=True)

def get_relationship(client, resource_id, rel_type="CHILD", label=None):
    attempts = [(f"/suite-api/api/resources/{resource_id}/relationships", {"relationshipType": rel_type}), (f"/suite-api/api/resources/{resource_id}/relationships/{rel_type}", None)]
    frames = []
    logs = []
    for endpoint, params in attempts:
        data, status, text = client.get_no_raise(endpoint, params=params)
        row = {"label": label, "resource_id": resource_id, "relationship_type": rel_type, "endpoint": endpoint, "params": json.dumps(params, ensure_ascii=False), "status_code": status, "response_preview": str(text)[:500]}
        if status == 200 and data is not None:
            df = extract_resources(data)
            row["resources_found"] = len(df)
            if not df.empty:
                frames.append(df)
        else:
            row["resources_found"] = 0
        logs.append(row)
    out = pd.concat(frames, ignore_index=True).drop_duplicates("identifier").reset_index(drop=True) if frames else pd.DataFrame(columns=["identifier", "name", "adapterKindKey", "resourceKindKey", "raw"])
    return out, pd.DataFrame(logs)

def is_vm(df):
    return df["adapterKindKey"].astype(str).str.upper().eq("VMWARE") & df["resourceKindKey"].astype(str).eq("VirtualMachine")

def is_host(df):
    return df["adapterKindKey"].astype(str).str.upper().eq("VMWARE") & df["resourceKindKey"].astype(str).eq("HostSystem")

def locate_expected_clusters(client, expected_clusters, exclude_patterns):
    located = []
    not_found = []
    for expected in expected_clusters:
        df = client.search_resources_by_name(expected)
        if df.empty:
            not_found.append(expected)
            continue
        df["name_norm"] = df["name"].astype(str).str.strip()
        valid = df[~df["name_norm"].apply(lambda n: any(re.search(p, n, flags=re.I) for p in exclude_patterns))].copy()
        exact = valid[valid["name_norm"].str.lower() == expected.lower()]
        if not exact.empty:
            chosen = exact.iloc[0].to_dict()
            chosen["expected_cluster"] = expected
            chosen["match_type"] = "EXATO"
            located.append(chosen)
            continue
        contains = valid[valid["name_norm"].str.contains(re.escape(expected), case=False, na=False)]
        if not contains.empty:
            chosen = contains.iloc[0].to_dict()
            chosen["expected_cluster"] = expected
            chosen["match_type"] = "CONTAINS"
            located.append(chosen)
        else:
            not_found.append(expected)
    df = pd.DataFrame(located)
    if not df.empty:
        cols = ["expected_cluster", "identifier", "name", "adapterKindKey", "resourceKindKey", "match_type", "raw"]
        df = df[[c for c in cols if c in df.columns]]
    return df, not_found

def obter_vms_do_cluster(client, cluster_name, cluster_id):
    vm_rows = []
    host_frames = []
    obj_frames = []
    log_frames = []
    cluster_child, log_child = get_relationship(client, cluster_id, "CHILD", f"cluster_child:{cluster_name}")
    log_frames.append(log_child)
    if not cluster_child.empty:
        obj_frames.append(cluster_child.assign(parent_type="ClusterComputeResource", parent_name=cluster_name, parent_id=cluster_id))
    hosts = cluster_child[is_host(cluster_child)].copy() if not cluster_child.empty else pd.DataFrame()
    if hosts.empty:
        cluster_all, log_all = get_relationship(client, cluster_id, "ALL", f"cluster_all_hosts_only:{cluster_name}")
        log_frames.append(log_all)
        if not cluster_all.empty:
            obj_frames.append(cluster_all.assign(parent_type="ClusterComputeResource_ALL_HOSTS_ONLY", parent_name=cluster_name, parent_id=cluster_id))
            hosts = cluster_all[is_host(cluster_all)].copy()
    if not hosts.empty:
        hosts = hosts.drop_duplicates("identifier").reset_index(drop=True)
        hosts["cluster"] = cluster_name
        host_frames.append(hosts)
    direct_vms = cluster_child[is_vm(cluster_child)].copy() if not cluster_child.empty else pd.DataFrame()
    for _, vm in direct_vms.iterrows():
        vm_rows.append({"cluster": cluster_name, "vm": vm["name"], "vm_resource_id": vm["identifier"], "adapterKindKey": vm["adapterKindKey"], "resourceKindKey": vm["resourceKindKey"], "mapping_method": "CLUSTER_CHILD_DIRECT_VM", "mapping_parent_name": cluster_name})
    for _, h in hosts.iterrows():
        host_id = h["identifier"]
        host_name = h["name"]
        for rel_type in ["CHILD", "ALL"]:
            hrel, hlog = get_relationship(client, host_id, rel_type, f"host_{rel_type}:{host_name}")
            log_frames.append(hlog)
            if hrel.empty:
                continue
            obj_frames.append(hrel.assign(parent_type=f"HostSystem_{rel_type}", parent_name=host_name, parent_id=host_id))
            hvms = hrel[is_vm(hrel)].copy()
            for _, vm in hvms.iterrows():
                vm_rows.append({"cluster": cluster_name, "vm": vm["name"], "vm_resource_id": vm["identifier"], "adapterKindKey": vm["adapterKindKey"], "resourceKindKey": vm["resourceKindKey"], "mapping_method": f"HOST_{rel_type}_VM", "mapping_parent_name": host_name})
    vms = pd.DataFrame(vm_rows)
    if not vms.empty:
        vms = vms.drop_duplicates("vm_resource_id").sort_values("vm").reset_index(drop=True)
    hosts_out = pd.concat(host_frames, ignore_index=True).drop_duplicates("identifier").reset_index(drop=True) if host_frames else pd.DataFrame()
    objs_out = pd.concat(obj_frames, ignore_index=True) if obj_frames else pd.DataFrame()
    logs_out = pd.concat(log_frames, ignore_index=True) if log_frames else pd.DataFrame()
    return vms, hosts_out, objs_out, logs_out

def list_resources_limited_v59(client, name, page_size=50, max_pages=1):
    frames = []
    for page in range(max_pages):
        params = {"pageSize": page_size, "page": page}
        if name:
            params["name"] = name
        try:
            data = client.get("/suite-api/api/resources", params=params, timeout=60)
            df = client.parse_resources(data)
            if df.empty:
                break
            df["query_used"] = name
            frames.append(df)
            if len(df) < page_size:
                break
        except Exception:
            break
    if not frames:
        return pd.DataFrame(columns=["identifier", "name", "adapterKindKey", "resourceKindKey", "raw", "query_used"])
    return pd.concat(frames, ignore_index=True).drop_duplicates("identifier").reset_index(drop=True)

def build_safe_cluster_queries_v59(expected_name):
    expected = str(expected_name).strip()
    queries = [expected, expected.replace("_", "-"), expected.replace("-", "_")]
    m = re.search(r"(BV[_-]PRD[_-]\d+)", expected, flags=re.I)
    if m:
        base = m.group(1)
        queries += [base, base.replace("_", "-"), base.replace("-", "_")]
    m2 = re.search(r"(PRD[_-]\d+)", expected, flags=re.I)
    if m2:
        p = m2.group(1)
        queries += [p, p.replace("_", "-"), p.replace("-", "_")]
    parts = re.split(r"[_-]+", expected)
    if len(parts) >= 4:
        q = "_".join(parts[:4])
        queries += [q, q.replace("_", "-")]
    return list(dict.fromkeys([q for q in queries if q and len(q) >= 5]))[:8]

def search_cluster_candidates_v59(client, expected_name, max_candidates=8):
    frames = []
    for q in build_safe_cluster_queries_v59(expected_name):
        df = list_resources_limited_v59(client, q, page_size=50, max_pages=1)
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["identifier", "name", "adapterKindKey", "resourceKindKey", "raw", "query_used"])
    df = pd.concat(frames, ignore_index=True).drop_duplicates("identifier").reset_index(drop=True)
    df["name_str"] = df["name"].astype(str)
    df["kind_str"] = df["resourceKindKey"].astype(str)
    allowed_kind = df["kind_str"].isin(["ClusterComputeResource", "Cluster", "ComputeResource", "vSphere Cluster"])
    df = df[df["adapterKindKey"].astype(str).str.upper().eq("VMWARE") & allowed_kind].copy()
    bad_patterns = [r"^vSAN Cluster", r"^vRealize Operations Cluster", r"^vCenter Deployment", r"^cluster$", r"Cloud Zone", r"Datacenter", r"Datastore", r"Network", r"Portgroup", r"SDDC Health"]
    if not df.empty:
        bad = pd.Series(False, index=df.index)
        for pat in bad_patterns:
            bad = bad | df["name_str"].str.contains(pat, case=False, na=False, regex=True)
        df = df[~bad].copy()
    df["candidate_priority"] = 0
    df.loc[df["kind_str"].eq("ClusterComputeResource"), "candidate_priority"] = 100
    df.loc[df["name_str"].str.lower().eq(str(expected_name).lower()), "candidate_priority"] += 200
    return df.sort_values("candidate_priority", ascending=False).head(max_candidates).reset_index(drop=True)

def probe_cluster_candidate_fast_v59(client, expected_cluster, candidate_row, max_hosts_to_probe=30):
    cid = candidate_row["identifier"]
    cname = candidate_row["name"]
    logs = []
    vm_rows = []
    child, log_child = get_relationship(client, cid, "CHILD", f"v59_cluster_child:{expected_cluster}:{cname}")
    logs.append(log_child)
    hosts = child[is_host(child)].copy() if not child.empty else pd.DataFrame()
    if hosts.empty:
        allrel, log_all = get_relationship(client, cid, "ALL", f"v59_cluster_all_hosts_only:{expected_cluster}:{cname}")
        logs.append(log_all)
        if not allrel.empty:
            hosts = allrel[is_host(allrel)].copy()
    if not hosts.empty:
        hosts = hosts.drop_duplicates("identifier").head(max_hosts_to_probe).reset_index(drop=True)
    for _, h in hosts.iterrows():
        hchild, hlog = get_relationship(client, h["identifier"], "CHILD", f"v59_host_child:{h['name']}")
        logs.append(hlog)
        hvms = hchild[is_vm(hchild)].copy() if not hchild.empty else pd.DataFrame()
        if hvms.empty:
            hall, hallog = get_relationship(client, h["identifier"], "ALL", f"v59_host_all:{h['name']}")
            logs.append(hallog)
            hvms = hall[is_vm(hall)].copy() if not hall.empty else pd.DataFrame()
        for _, vm in hvms.iterrows():
            vm_rows.append({"expected_cluster": expected_cluster, "candidate_name": cname, "candidate_id": cid, "host": h["name"], "vm": vm["name"], "vm_resource_id": vm["identifier"]})
    vms = pd.DataFrame(vm_rows)
    if not vms.empty:
        vms = vms.drop_duplicates("vm_resource_id").reset_index(drop=True)
    score = (1000 if str(candidate_row.get("resourceKindKey")) == "ClusterComputeResource" else 0) + len(hosts) * 100 + len(vms)
    result = {"expected_cluster": expected_cluster, "candidate_name": cname, "candidate_id": cid, "candidate_kind": candidate_row.get("resourceKindKey"), "query_used": candidate_row.get("query_used"), "hosts_count": len(hosts), "vms_count": len(vms), "score": score}
    logs_df = pd.concat(logs, ignore_index=True) if logs else pd.DataFrame()
    return result, logs_df

def resolve_zero_clusters_v59(client, df_clusters_original, df_current_vms, max_candidates=8):
    current_counts = df_current_vms.groupby("cluster")["vm_resource_id"].nunique().to_dict() if df_current_vms is not None and not df_current_vms.empty else {}
    rows = []
    probe_rows = []
    log_frames = []
    for _, row in df_clusters_original.iterrows():
        expected = row["expected_cluster"]
        current_count = current_counts.get(expected, 0)
        rr = row.to_dict()
        rr["identifier_original"] = row["identifier"]
        rr["name_original"] = row.get("name")
        rr["resolved_by_v59"] = False
        rr["resolved_status_v59"] = "NAO_NECESSARIO" if current_count > 0 else "PENDENTE"
        rr["resolved_vms_count_v59"] = current_count
        rr["resolved_hosts_count_v59"] = None
        rows.append(rr)
        if current_count > 0:
            continue
        candidates = search_cluster_candidates_v59(client, expected, max_candidates=max_candidates)
        original = pd.DataFrame([{"identifier": row["identifier"], "name": row.get("name"), "adapterKindKey": row.get("adapterKindKey"), "resourceKindKey": row.get("resourceKindKey"), "raw": row.get("raw"), "query_used": "original", "candidate_priority": 999}])
        candidates = pd.concat([original, candidates], ignore_index=True).drop_duplicates("identifier").head(max_candidates).reset_index(drop=True)
        best = None
        for _, cand in candidates.iterrows():
            result, logs = probe_cluster_candidate_fast_v59(client, expected, cand)
            probe_rows.append(result)
            if logs is not None and not logs.empty:
                logs["expected_cluster"] = expected
                logs["candidate_name"] = cand.get("name")
                logs["candidate_id"] = cand.get("identifier")
                log_frames.append(logs)
            if best is None or result["score"] > best["result"]["score"]:
                best = {"result": result, "candidate": cand}
            if result["vms_count"] > 0:
                break
        if best is not None:
            bres = best["result"]
            bcand = best["candidate"]
            for r in rows:
                if r["expected_cluster"] == expected:
                    r["identifier"] = bcand["identifier"]
                    r["name"] = bcand["name"]
                    r["resourceKindKey"] = bcand.get("resourceKindKey")
                    r["adapterKindKey"] = bcand.get("adapterKindKey")
                    r["resolved_by_v59"] = True
                    r["resolved_status_v59"] = "OK" if bres["vms_count"] > 0 or bres["hosts_count"] > 0 else "SEM_HOSTS_VMS"
                    r["resolved_vms_count_v59"] = bres["vms_count"]
                    r["resolved_hosts_count_v59"] = bres["hosts_count"]
                    r["resolved_score_v59"] = bres["score"]
                    r["resolved_query_used_v59"] = bcand.get("query_used")
    return pd.DataFrame(rows), pd.DataFrame(probe_rows), (pd.concat(log_frames, ignore_index=True) if log_frames else pd.DataFrame())

def infer_os_from_statkeys(df_statkeys):
    keys = " ".join(df_statkeys["key"].astype(str).str.lower().head(8000).tolist())
    if "guestfilesystem:/" in keys:
        return "Linux"
    if re.search(r"guestfilesystem:[a-z]:", keys):
        return "Windows"
    return "Unknown"

def parse_guestfilesystem_key(key):
    key = str(key).strip()
    if not key.lower().startswith("guestfilesystem:") or "|" not in key:
        return None
    left, metric = key.rsplit("|", 1)
    metric = metric.lower().strip()
    if metric not in VALID_GUESTFS_METRICS or "_total" in key.lower() or "aggregate" in key.lower():
        return None
    path = left[len("guestfilesystem:"):].strip()
    if not path:
        return None
    if re.match(r"^[A-Za-z]:", path):
        osfam, part = "Windows", path[:2].upper()
    elif path.startswith("/"):
        osfam, part = "Linux", path
    else:
        return None
    mt = VALID_GUESTFS_METRICS[metric]
    return {"key": key, "os_family": osfam, "filesystem_path": path, "partition": part, "metric_name": metric, "metric_type": mt, "is_capacity_match": mt == "capacity_gb", "is_free_match": mt == "free_gb", "is_used_match": mt == "used_gb"}

def build_guest_disk_key_table(df_statkeys):
    rows = []
    for k in df_statkeys["key"].astype(str).tolist():
        parsed = parse_guestfilesystem_key(k)
        if parsed:
            rows.append(parsed)
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["key", "os_family", "filesystem_path", "partition", "metric_name", "metric_type", "is_capacity_match", "is_free_match", "is_used_match"])

def coletar_inventario_vm(client, df_vms):
    parts, logs, keys_all, os_rows = [], [], [], []
    if df_vms.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    for _, row in df_vms.iterrows():
        try:
            stat = client.get_statkeys(row["vm_resource_id"])
            osfam = infer_os_from_statkeys(stat)
            gkeys = build_guest_disk_key_table(stat)
            os_rows.append({"cluster": row["cluster"], "vm": row["vm"], "vm_resource_id": row["vm_resource_id"], "os_family_inferred": osfam})
            logs.append({"cluster": row["cluster"], "vm": row["vm"], "vm_resource_id": row["vm_resource_id"], "total_statkeys": len(stat), "guestfilesystem_validas": len(gkeys), "os_family_inferred": osfam, "status": "OK"})
            if not gkeys.empty:
                tmp = gkeys.copy()
                tmp["cluster"] = row["cluster"]
                tmp["vm"] = row["vm"]
                tmp["vm_resource_id"] = row["vm_resource_id"]
                keys_all.append(tmp)
                grouped = gkeys.groupby(["os_family", "partition", "filesystem_path"], as_index=False).agg(capacity_keys=("is_capacity_match", "sum"), free_keys=("is_free_match", "sum"), used_keys=("is_used_match", "sum"), total_keys=("key", "count"), keys=("key", lambda x: list(x)))
                for _, p in grouped.iterrows():
                    parts.append({"cluster": row["cluster"], "vm": row["vm"], "vm_resource_id": row["vm_resource_id"], "os_family": p["os_family"], "partition": p["partition"], "filesystem_path": p["filesystem_path"], "has_capacity": p["capacity_keys"] > 0, "has_free": p["free_keys"] > 0, "has_used": p["used_keys"] > 0, "capacity_keys": int(p["capacity_keys"]), "free_keys": int(p["free_keys"]), "used_keys": int(p["used_keys"]), "total_keys": int(p["total_keys"]), "keys": p["keys"]})
        except Exception as e:
            logs.append({"cluster": row.get("cluster"), "vm": row.get("vm"), "vm_resource_id": row.get("vm_resource_id"), "status": "ERRO", "erro": str(e)})
    return pd.DataFrame(parts), pd.DataFrame(logs), (pd.concat(keys_all, ignore_index=True) if keys_all else pd.DataFrame()), pd.DataFrame(os_rows)

def select_available_statkey(df_statkeys, candidates):
    keys = df_statkeys["key"].astype(str).tolist()
    available = set(keys)
    for c in candidates:
        if c in available:
            return c
    for c in candidates:
        for k in keys:
            if c.lower() in k.lower():
                return k
    return None

def coletar_percentual(client, df_vms, resource, candidates, days_back):
    rows, logs = [], []
    for _, vm in df_vms.iterrows():
        try:
            stat = client.get_statkeys(vm["vm_resource_id"])
            key = select_available_statkey(stat, candidates)
            if not key:
                logs.append({"resource": resource, "cluster": vm["cluster"], "vm": vm["vm"], "vm_resource_id": vm["vm_resource_id"], "status": "STATKEY_NAO_ENCONTRADA"})
                continue
            hist, raw = client.get_stats(vm["vm_resource_id"], key, days_back)
            logs.append({"resource": resource, "cluster": vm["cluster"], "vm": vm["vm"], "vm_resource_id": vm["vm_resource_id"], "stat_key": key, "rows": len(hist), "status": "OK"})
            if not hist.empty:
                hist["resource"] = resource
                hist["cluster"] = vm["cluster"]
                hist["vm"] = vm["vm"]
                hist["vm_resource_id"] = vm["vm_resource_id"]
                hist["stat_key_used"] = key
                rows.append(hist)
        except Exception as e:
            logs.append({"resource": resource, "cluster": vm.get("cluster"), "vm": vm.get("vm"), "vm_resource_id": vm.get("vm_resource_id"), "status": "ERRO", "erro": str(e)})
    return (pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()), pd.DataFrame(logs)

def consolidar_percentual(df_raw):
    if df_raw.empty:
        return pd.DataFrame()
    df = df_raw.copy()
    df["day"] = df["date"].dt.floor("D")
    return df.groupby(["resource", "cluster", "vm", "vm_resource_id", "day"], as_index=False)["value"].mean().rename(columns={"day": "date", "value": "used_pct"}).sort_values(["resource", "cluster", "vm", "date"]).reset_index(drop=True)

def coletar_historico_particoes(client, df_partitions_selected, days_back):
    rows, logs = [], []
    if df_partitions_selected.empty:
        return pd.DataFrame(), pd.DataFrame()
    for _, p in df_partitions_selected.iterrows():
        keys = p["keys"]
        if isinstance(keys, str):
            try:
                keys = json.loads(keys.replace("'", '"'))
            except Exception:
                keys = []
        for stat_key in keys:
            parsed = parse_guestfilesystem_key(stat_key)
            if not parsed:
                continue
            try:
                hist, raw = client.get_stats(p["vm_resource_id"], stat_key, days_back)
                logs.append({"resource": "DISK", "cluster": p["cluster"], "vm": p["vm"], "vm_resource_id": p["vm_resource_id"], "filesystem_path": p["filesystem_path"], "stat_key": stat_key, "metric_type": parsed["metric_type"], "rows": len(hist), "status": "OK"})
                if not hist.empty:
                    hist["resource"] = "DISK"
                    hist["cluster"] = p["cluster"]
                    hist["vm"] = p["vm"]
                    hist["vm_resource_id"] = p["vm_resource_id"]
                    hist["os_family"] = p["os_family"]
                    hist["partition"] = p["partition"]
                    hist["filesystem_path"] = p["filesystem_path"]
                    hist["metric_type"] = parsed["metric_type"]
                    rows.append(hist)
            except Exception as e:
                logs.append({"resource": "DISK", "cluster": p.get("cluster"), "vm": p.get("vm"), "vm_resource_id": p.get("vm_resource_id"), "filesystem_path": p.get("filesystem_path"), "stat_key": stat_key, "status": "ERRO", "erro": str(e)})
    return (pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()), pd.DataFrame(logs)

def consolidate_disk_history(df_raw, threshold_pct):
    if df_raw.empty:
        return pd.DataFrame()
    data = df_raw.copy()
    data["day"] = data["date"].dt.floor("D")
    group_cols = ["cluster", "vm", "vm_resource_id", "os_family", "partition", "filesystem_path", "day"]
    used = data[data["metric_type"] == "used_gb"].groupby(group_cols, as_index=False)["value"].mean().rename(columns={"day": "date", "value": "used_gb"})
    cap = data[data["metric_type"] == "capacity_gb"].groupby(group_cols, as_index=False)["value"].mean().rename(columns={"day": "date", "value": "capacity_gb"})
    free = data[data["metric_type"] == "free_gb"].groupby(group_cols, as_index=False)["value"].mean().rename(columns={"day": "date", "value": "free_gb"})
    merge_cols = ["cluster", "vm", "vm_resource_id", "os_family", "partition", "filesystem_path", "date"]
    df = used.merge(cap, on=merge_cols, how="outer").merge(free, on=merge_cols, how="outer")
    df = df.sort_values(["cluster", "vm", "filesystem_path", "date"]).reset_index(drop=True)
    df["capacity_gb"] = df.groupby(["vm_resource_id", "filesystem_path"])["capacity_gb"].ffill().bfill()
    mask_used = df["used_gb"].isna() & df["capacity_gb"].notna() & df["free_gb"].notna()
    df.loc[mask_used, "used_gb"] = df.loc[mask_used, "capacity_gb"] - df.loc[mask_used, "free_gb"]
    mask_free = df["free_gb"].isna() & df["capacity_gb"].notna() & df["used_gb"].notna()
    df.loc[mask_free, "free_gb"] = df.loc[mask_free, "capacity_gb"] - df.loc[mask_free, "used_gb"]
    df["used_pct"] = df["used_gb"] / df["capacity_gb"] * 100
    df["free_pct"] = df["free_gb"] / df["capacity_gb"] * 100
    df["threshold_pct"] = threshold_pct
    df["threshold_gb"] = df["capacity_gb"] * threshold_pct / 100
    df["crash_100_gb"] = df["capacity_gb"]
    return df

def forecast_percent_one(df, threshold, horizons=[30, 60, 90], max_event_days=3650):
    df = df.dropna(subset=["used_pct"]).copy().sort_values("date")
    base = {c: df[c].iloc[0] if c in df.columns and len(df) else None for c in ["resource", "cluster", "vm", "vm_resource_id"]}
    if len(df) < 2:
        base.update({"status": "DADOS_INSUFICIENTES", "risco": "INDEFINIDO"})
        return pd.DataFrame(), base
    df["date"] = pd.to_datetime(df["date"])
    df["days"] = (df["date"] - df["date"].min()).dt.days
    model = LinearRegression().fit(df[["days"]], df["used_pct"])
    slope = float(model.coef_[0])
    last_date = pd.to_datetime(df["date"].max())
    last = float(df.loc[df["date"].idxmax(), "used_pct"])
    maxh = max(horizons)
    future_days = np.arange(int(df["days"].max()) + 1, int(df["days"].max()) + 1 + maxh)
    future_dates = [df["date"].min() + timedelta(days=int(d)) for d in future_days]
    vals = model.predict(pd.DataFrame({"days": future_days}))
    fcst = pd.DataFrame({**base, "date": future_dates, "forecast_used_pct": vals, "threshold_pct": threshold, "crash_100_pct": 100})
    fcst["forecast_days_ahead"] = (fcst["date"] - last_date).dt.days
    summ = dict(base)
    summ.update({"threshold_pct": threshold, "last_date": last_date, "last_used_pct": last, "slope_pct_day": slope, "slope_pct_month": slope * 30, "above_threshold_now": last >= threshold})
    for h in horizons:
        td = last_date + timedelta(days=h)
        day = (td - df["date"].min()).days
        pred = float(model.predict(pd.DataFrame({"days": [day]}))[0])
        summ[f"forecast_{h}d_used_pct"] = pred
        summ[f"forecast_{h}d_above_threshold"] = pred >= threshold
        summ[f"forecast_{h}d_crash"] = pred >= 100
    return fcst, summ

def rodar_forecast_percentual(df_hist, threshold, horizons=[30, 60, 90]):
    frames, rows = [], []
    if not df_hist.empty:
        for _, g in df_hist.groupby(["resource", "cluster", "vm"]):
            f, s = forecast_percent_one(g, threshold, horizons)
            if not f.empty:
                frames.append(f)
            rows.append(s)
    summ = pd.DataFrame(rows)
    fcst = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    above = summ[(summ.get("above_threshold_now", False) == True) | (summ.get("forecast_30d_above_threshold", False) == True) | (summ.get("forecast_60d_above_threshold", False) == True) | (summ.get("forecast_90d_above_threshold", False) == True)].copy() if not summ.empty else pd.DataFrame()
    return fcst, summ, above


# =============================================================================
# v5.10 - Correção explícita para DatastoreFolder selecionado como cluster
# =============================================================================

VALID_CLUSTER_RESOURCE_KINDS_V510 = {
    "ClusterComputeResource",
    "Cluster",
    "ComputeResource",
    "vSphere Cluster",
}

INVALID_CLUSTER_RESOURCE_KINDS_V510 = {
    "DatastoreFolder",
    "VMFolder",
    "Folder",
    "Datastore",
    "StoragePod",
    "DistributedVirtualPortgroup",
    "Network",
    "Datacenter",
}


def is_valid_compute_cluster_kind_v510(kind):
    return str(kind) in VALID_CLUSTER_RESOURCE_KINDS_V510


def is_invalid_cluster_kind_v510(kind):
    return str(kind) in INVALID_CLUSTER_RESOURCE_KINDS_V510


def search_compute_cluster_candidates_v510(client, expected_name, max_candidates=10):
    """
    Busca candidatos de cluster computacional sem aceitar DatastoreFolder.

    Importante:
    - não usa termos genéricos como PRD, VxRAIL, RHEL, Windows ou SQL isolados;
    - usa apenas nome completo e prefixos específicos como BV_PRD_01 / PRD_01;
    - retorna somente resourceKindKey compatível com cluster computacional.
    """
    candidates = search_cluster_candidates_v59(
        client,
        expected_name,
        max_candidates=max_candidates
    )

    if candidates.empty:
        return candidates

    candidates = candidates[
        candidates["resourceKindKey"].astype(str).apply(is_valid_compute_cluster_kind_v510)
    ].copy()

    # Reforço: nunca aceitar DatastoreFolder/VMFolder como candidato.
    candidates = candidates[
        ~candidates["resourceKindKey"].astype(str).apply(is_invalid_cluster_kind_v510)
    ].copy()

    return candidates.reset_index(drop=True)


def resolve_invalid_cluster_kinds_v510(client, df_clusters_selected, max_candidates=10):
    """
    Corrige clusters selecionados que foram resolvidos como DatastoreFolder ou outro
    tipo não computacional.

    Fluxo:
    1. Se já é ClusterComputeResource, mantém.
    2. Se é DatastoreFolder/VMFolder/Folder, busca candidatos computacionais.
    3. Testa candidatos com prova de hosts/VMs.
    4. Substitui identifier/name pelo candidato que realmente aponta para HostSystem/VMs.
    """
    resolved_rows = []
    probe_rows = []
    log_frames = []

    for _, row in df_clusters_selected.iterrows():
        expected = row["expected_cluster"]
        current_kind = str(row.get("resourceKindKey"))

        rr = row.to_dict()
        rr["identifier_original"] = row.get("identifier")
        rr["name_original"] = row.get("name")
        rr["resourceKindKey_original"] = row.get("resourceKindKey")
        rr["pre_resolve_status_v510"] = "JA_E_CLUSTER_COMPUTACIONAL"
        rr["pre_resolve_changed_v510"] = False
        rr["pre_resolve_hosts_v510"] = None
        rr["pre_resolve_vms_v510"] = None
        rr["pre_resolve_observacao_v510"] = ""

        if is_valid_compute_cluster_kind_v510(current_kind):
            resolved_rows.append(rr)
            continue

        rr["pre_resolve_status_v510"] = f"TIPO_INVALIDO_{current_kind}"
        rr["pre_resolve_observacao_v510"] = (
            f"O objeto localizado para {expected} é {current_kind}; "
            "isso representa pasta/armazenamento, não cluster computacional."
        )

        candidates = search_compute_cluster_candidates_v510(
            client,
            expected,
            max_candidates=max_candidates
        )

        if candidates.empty:
            rr["pre_resolve_status_v510"] = "SEM_CANDIDATO_CLUSTER_COMPUTACIONAL"
            resolved_rows.append(rr)
            continue

        best = None

        for _, cand in candidates.iterrows():
            try:
                result, logs = probe_cluster_candidate_fast_v59(
                    client,
                    expected,
                    cand
                )
                probe_rows.append(result)

                if logs is not None and not logs.empty:
                    logs["expected_cluster"] = expected
                    logs["candidate_name"] = cand.get("name")
                    logs["candidate_id"] = cand.get("identifier")
                    log_frames.append(logs)

                if best is None or result["score"] > best["result"]["score"]:
                    best = {
                        "result": result,
                        "candidate": cand
                    }

                if result["vms_count"] > 0:
                    break

            except Exception as e:
                probe_rows.append({
                    "expected_cluster": expected,
                    "candidate_name": cand.get("name"),
                    "candidate_id": cand.get("identifier"),
                    "candidate_kind": cand.get("resourceKindKey"),
                    "query_used": cand.get("query_used"),
                    "hosts_count": 0,
                    "vms_count": 0,
                    "score": -999999,
                    "erro": str(e),
                })

        if best is None:
            rr["pre_resolve_status_v510"] = "ERRO_AO_TESTAR_CANDIDATOS"
            resolved_rows.append(rr)
            continue

        bres = best["result"]
        bcand = best["candidate"]

        rr["identifier"] = bcand["identifier"]
        rr["name"] = bcand["name"]
        rr["adapterKindKey"] = bcand.get("adapterKindKey")
        rr["resourceKindKey"] = bcand.get("resourceKindKey")
        rr["pre_resolve_changed_v510"] = True
        rr["pre_resolve_hosts_v510"] = bres.get("hosts_count")
        rr["pre_resolve_vms_v510"] = bres.get("vms_count")
        rr["pre_resolve_score_v510"] = bres.get("score")
        rr["pre_resolve_query_used_v510"] = bcand.get("query_used")

        if bres.get("hosts_count", 0) > 0 or bres.get("vms_count", 0) > 0:
            rr["pre_resolve_status_v510"] = "CORRIGIDO"
        else:
            rr["pre_resolve_status_v510"] = "CANDIDATO_SEM_HOSTS_VMS"

        resolved_rows.append(rr)

    df_resolved = pd.DataFrame(resolved_rows)
    df_probe = pd.DataFrame(probe_rows)
    df_logs = pd.concat(log_frames, ignore_index=True) if log_frames else pd.DataFrame()

    return df_resolved, df_probe, df_logs


def locate_expected_clusters_strict_v510(client, expected_clusters, exclude_patterns):
    """
    Localizador preferencial:
    - retorna ClusterComputeResource quando existir;
    - não escolhe DatastoreFolder como se fosse cluster;
    - se só encontrar DatastoreFolder, mantém o registro, mas marca para correção posterior.
    """
    df, missing = locate_expected_clusters(client, expected_clusters, exclude_patterns)

    if df.empty:
        return df, missing

    rows = []
    extra_missing = []

    for _, row in df.iterrows():
        expected = row["expected_cluster"]
        kind = str(row.get("resourceKindKey"))

        if is_valid_compute_cluster_kind_v510(kind):
            rows.append(row.to_dict())
            continue

        # Tenta achar cluster computacional imediatamente
        candidates = search_compute_cluster_candidates_v510(client, expected, max_candidates=5)

        if not candidates.empty:
            cand = candidates.iloc[0].to_dict()
            rr = row.to_dict()
            rr["identifier_original"] = row.get("identifier")
            rr["name_original"] = row.get("name")
            rr["resourceKindKey_original"] = row.get("resourceKindKey")
            rr["identifier"] = cand.get("identifier")
            rr["name"] = cand.get("name")
            rr["adapterKindKey"] = cand.get("adapterKindKey")
            rr["resourceKindKey"] = cand.get("resourceKindKey")
            rr["match_type"] = "CORRIGIDO_KIND_CLUSTER_COMPUTE"
            rows.append(rr)
        else:
            # Mantém para a célula de pré-resolução/prova explicar o problema
            rr = row.to_dict()
            rr["match_type"] = f"EXATO_MAS_TIPO_INVALIDO_{kind}"
            rows.append(rr)

    return pd.DataFrame(rows), missing
