from __future__ import annotations

import argparse
import getpass
import json
import math
import os
import re
import ssl
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pandas as pd

try:
    import keyring
except Exception:
    keyring = None

try:
    from pyVim.connect import SmartConnect, Disconnect
    from pyVmomi import vim, vmodl
except Exception as exc:
    raise SystemExit(
        "pyVmomi não está instalado ou o import está incorreto. Rode: "
        "powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\164_install_optimization_vcenter_deps.ps1"
    ) from exc

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


SCHEMA_SQL = r"""
CREATE TABLE IF NOT EXISTS optimization_collection_runs (
    run_id VARCHAR PRIMARY KEY,
    collected_at TIMESTAMP,
    source VARCHAR,
    vrops_host VARCHAR,
    auth_source VARCHAR,
    cluster_filter VARCHAR,
    status VARCHAR,
    message VARCHAR,
    total_vms INTEGER DEFAULT 0,
    total_powered_off_vms INTEGER DEFAULT 0,
    total_snapshots INTEGER DEFAULT 0,
    total_snapshots_over_20d INTEGER DEFAULT 0,
    total_orphan_disk_candidates INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS vm_power_state_snapshots (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    vm_name VARCHAR,
    vm_resource_id VARCHAR,
    cluster VARCHAR,
    host VARCHAR,
    power_state VARCHAR,
    is_powered_off BOOLEAN,
    dias_desligada DOUBLE,
    cpu_count DOUBLE,
    memory_gb DOUBLE,
    disk_provisioned_gb DOUBLE,
    datastore_names VARCHAR,
    ambiente VARCHAR,
    raw_json VARCHAR
);

CREATE TABLE IF NOT EXISTS vm_snapshot_inventory (
    run_id VARCHAR,
    collected_at TIMESTAMP,
    vm_name VARCHAR,
    vm_resource_id VARCHAR,
    cluster VARCHAR,
    host VARCHAR,
    snapshot_name VARCHAR,
    snapshot_created_at TIMESTAMP,
    snapshot_age_days DOUBLE,
    snapshot_size_gb DOUBLE,
    snapshot_count INTEGER,
    datastore VARCHAR,
    status_risco VARCHAR,
    raw_json VARCHAR
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

CREATE TABLE IF NOT EXISTS optimization_recommendations (
    run_id VARCHAR,
    created_at TIMESTAMP,
    item_type VARCHAR,
    severity VARCHAR,
    entity_name VARCHAR,
    cluster VARCHAR,
    metric VARCHAR,
    finding VARCHAR,
    recommendation VARCHAR,
    action_allowed BOOLEAN DEFAULT FALSE
);

CREATE OR REPLACE VIEW v_optimization_latest_run AS
SELECT *
FROM optimization_collection_runs
WHERE collected_at = (SELECT max(collected_at) FROM optimization_collection_runs);

CREATE OR REPLACE VIEW v_powered_off_vms_latest AS
SELECT p.*,
       CASE
         WHEN dias_desligada IS NULL THEN 'VALIDAR'
         WHEN dias_desligada >= 90 THEN 'CRITICO'
         WHEN dias_desligada >= 60 THEN 'RISCO'
         WHEN dias_desligada >= 30 THEN 'ATENCAO'
         ELSE 'OBSERVAR'
       END AS status_otimizacao,
       'Validar com o responsável antes de qualquer remoção. A IA apenas recomenda; não executa ação operacional.' AS recomendacao_padrao
FROM vm_power_state_snapshots p
WHERE p.run_id = (SELECT run_id FROM v_optimization_latest_run LIMIT 1)
  AND coalesce(p.is_powered_off, FALSE) = TRUE;

CREATE OR REPLACE VIEW v_snapshots_antigos_latest AS
SELECT s.*,
       CASE
         WHEN snapshot_age_days >= 60 THEN 'CRITICO'
         WHEN snapshot_age_days >= 30 THEN 'RISCO'
         WHEN snapshot_age_days > 20 THEN 'ATENCAO'
         ELSE 'OK'
       END AS status_otimizacao,
       'Validar com o responsável e planejar consolidação/remoção controlada. A IA apenas recomenda; não executa ação operacional.' AS recomendacao_padrao
FROM vm_snapshot_inventory s
WHERE s.run_id = (SELECT run_id FROM v_optimization_latest_run LIMIT 1)
  AND coalesce(s.snapshot_age_days, 0) > 20;

CREATE OR REPLACE VIEW v_orphan_disk_candidates_latest AS
SELECT o.*,
       'VALIDAR' AS status_otimizacao,
       'Disco candidato a órfão. Validar vínculo com VM, template, backup, clone ou snapshot antes de qualquer ação.' AS recomendacao_padrao
FROM orphan_disk_candidates o
WHERE o.run_id = (SELECT run_id FROM v_optimization_latest_run LIMIT 1);
"""


def log(msg: str) -> None:
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


def safe_float(value):
    try:
        if value is None:
            return None
        x = float(value)
        if not math.isfinite(x):
            return None
        return x
    except Exception:
        return None


def to_naive_dt(value):
    if not value:
        return None
    try:
        if getattr(value, "tzinfo", None) is not None:
            return value.replace(tzinfo=None)
        return value
    except Exception:
        return None


def norm_path(path: str) -> str:
    return re.sub(r"\s+", " ", str(path or "").strip()).lower()


def get_cluster(vm) -> str:
    try:
        host = getattr(vm.runtime, "host", None)
        parent = getattr(host, "parent", None)
        if isinstance(parent, vim.ClusterComputeResource):
            return parent.name
        if isinstance(parent, vim.ComputeResource):
            return parent.name
    except Exception:
        pass
    return "N/A"


def get_host(vm) -> str:
    try:
        return vm.runtime.host.name if vm.runtime and vm.runtime.host else "N/A"
    except Exception:
        return "N/A"


def get_datastores(vm) -> str:
    try:
        return ", ".join(ds.name for ds in vm.datastore) if vm.datastore else "N/A"
    except Exception:
        return "N/A"


def get_disk_total_gb(vm) -> float:
    total = 0.0
    try:
        if not getattr(vm, "config", None):
            return 0.0
        for device in vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualDisk):
                total += float(device.capacityInKB or 0) / (1024 * 1024)
    except Exception:
        pass
    return round(total, 2)


def get_snapshot_layout_size_gb(vm) -> float:
    """
    Estimativa best-effort.
    O snapshot tree traz data/nome, mas tamanho por snapshot nem sempre vem no pyVmomi.
    Quando disponível, soma arquivos de snapshot/delta no layoutEx.
    """
    total_bytes = 0
    try:
        layout = getattr(vm, "layoutEx", None)
        if not layout or not getattr(layout, "file", None):
            return 0.0
        for f in layout.file:
            name = str(getattr(f, "name", "") or "").lower()
            ftype = str(getattr(f, "type", "") or "").lower()
            if (
                "snapshot" in ftype
                or "delta" in ftype
                or name.endswith("-delta.vmdk")
                or name.endswith("-sesparse.vmdk")
                or ".vmsn" in name
                or ".vmsd" in name
            ):
                total_bytes += int(getattr(f, "size", 0) or 0)
    except Exception:
        return 0.0
    return round(total_bytes / (1024 ** 3), 2)


def collect_snapshot_tree(nodes, vm_name: str, vm, collected_at: datetime, warning_days: int):
    rows = []
    total_estimated_size = get_snapshot_layout_size_gb(vm)

    def walk(node_list, depth=0):
        for node in node_list or []:
            created = to_naive_dt(getattr(node, "createTime", None))
            age = None
            if created:
                age = round((collected_at - created).total_seconds() / 86400, 2)
            if age is None:
                status = "VALIDAR"
            elif age >= 60:
                status = "CRITICO"
            elif age >= 30:
                status = "RISCO"
            elif age > warning_days:
                status = "ATENCAO"
            else:
                status = "OK"

            rows.append({
                "snapshot_name": getattr(node, "name", "") or "",
                "snapshot_created_at": created,
                "snapshot_age_days": age,
                "status_risco": status,
                "description": getattr(node, "description", "") or "",
                "state": str(getattr(node, "state", "") or ""),
                "depth": depth,
            })
            walk(getattr(node, "childSnapshotList", []) or [], depth + 1)

    try:
        if getattr(vm, "snapshot", None) and getattr(vm.snapshot, "rootSnapshotList", None):
            walk(vm.snapshot.rootSnapshotList)
    except Exception:
        return []

    count = len(rows)
    per_snapshot_size = round(total_estimated_size / count, 2) if count and total_estimated_size else 0.0
    for r in rows:
        r["snapshot_count"] = count
        r["snapshot_size_gb"] = per_snapshot_size
        r["raw_json"] = json.dumps({
            "description": r.pop("description", ""),
            "state": r.pop("state", ""),
            "depth": r.pop("depth", 0),
            "vm": vm_name,
            "estimated_total_snapshot_layout_gb": total_estimated_size,
            "size_note": "Estimativa baseada no layoutEx da VM quando disponível; pyVmomi nem sempre expõe tamanho individual por snapshot."
        }, ensure_ascii=False, default=str)
    return rows


def find_last_poweroff_event(content, vm, days_back: int):
    try:
        event_manager = content.eventManager
        spec = vim.event.EventFilterSpec()
        spec.entity = vim.event.EventFilterSpec.ByEntity(
            entity=vm,
            recursion=vim.event.EventFilterSpec.RecursionOption.self
        )
        spec.eventTypeId = ["VmPoweredOffEvent", "VmStoppedEvent"]
        spec.time = vim.event.EventFilterSpec.ByTime()
        spec.time.beginTime = datetime.now() - timedelta(days=days_back)
        spec.time.endTime = datetime.now()
        events = event_manager.QueryEvents(spec)
        if not events:
            return None
        events = sorted(events, key=lambda e: e.createdTime, reverse=True)
        return to_naive_dt(events[0].createdTime)
    except Exception:
        return None


def wait_for_task(task, timeout=1800, poll=0.5):
    waited = 0.0
    while task.info.state in (vim.TaskInfo.State.queued, vim.TaskInfo.State.running):
        time.sleep(poll)
        waited += poll
        if waited >= timeout:
            raise TimeoutError("Task excedeu o tempo limite.")
    if task.info.state == vim.TaskInfo.State.error:
        raise task.info.error
    return task.info.result


def collect_used_vmdk_paths(vms) -> set[str]:
    used = set()
    for vm in vms:
        try:
            if not getattr(vm, "config", None):
                continue
            for dev in vm.config.hardware.device:
                if isinstance(dev, vim.vm.device.VirtualDisk):
                    backing = getattr(dev, "backing", None)
                    fn = getattr(backing, "fileName", None)
                    if fn:
                        used.add(norm_path(fn))
        except Exception:
            continue
    return used


def derived_descriptor_from_extent(full_path: str) -> str | None:
    """
    [DS] folder/vm-flat.vmdk -> [DS] folder/vm.vmdk
    [DS] folder/vm-000001-delta.vmdk -> [DS] folder/vm-000001.vmdk
    """
    p = full_path
    low = p.lower()
    for suffix in ["-flat.vmdk", "-delta.vmdk", "-sesparse.vmdk", "-ctk.vmdk"]:
        if low.endswith(suffix):
            return p[: -len(suffix)] + ".vmdk"
    return None


def collect_orphan_disk_candidates(content, vms, collected_at: datetime, datastore_filter: str | None = None):
    used = collect_used_vmdk_paths(vms)
    log(f"VMDKs em uso coletados via vCenter: {len(used)}")

    ds_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datastore], True)
    try:
        search_spec = vim.HostDatastoreBrowserSearchSpec()
        search_spec.matchPattern = ["*.vmdk"]
        details = vim.HostDatastoreBrowser.FileInfo.Details()
        details.fileType = True
        details.fileSize = True
        details.modification = True
        search_spec.details = details
        search_spec.searchCaseInsensitive = True

        candidates = []
        for ds in ds_view.view:
            ds_name = ds.name
            if datastore_filter and datastore_filter.lower() not in ds_name.lower():
                continue

            try:
                if hasattr(ds.summary, "accessible") and not ds.summary.accessible:
                    log(f"- {ds_name}: inacessível, pulando.")
                    continue

                ds_root = f"[{ds_name}] /"
                log(f"- Varrendo datastore {ds_name}")
                task = ds.browser.SearchDatastoreSubFolders_Task(datastorePath=ds_root, searchSpec=search_spec)
                results = wait_for_task(task, timeout=1800, poll=0.5)

                if not results:
                    log(f"- {ds_name}: nenhum VMDK encontrado.")
                    continue

                local_count = 0
                for folder_result in results:
                    folder_path = getattr(folder_result, "folderPath", "") or ""
                    for f in getattr(folder_result, "file", []) or []:
                        fpath = getattr(f, "path", "") or ""
                        if not fpath.lower().endswith(".vmdk"):
                            continue

                        full_path = (folder_path + fpath).replace("//", "/")
                        full_norm = norm_path(full_path)

                        if full_norm in used:
                            continue

                        descriptor = derived_descriptor_from_extent(full_path)
                        descriptor_norm = norm_path(descriptor) if descriptor else None

                        if descriptor_norm and descriptor_norm in used:
                            # Extent/flat/delta de disco ligado a descriptor em uso; não marca como órfão.
                            continue

                        size_gb = None
                        try:
                            size_gb = round(float(getattr(f, "fileSize", 0) or 0) / (1024 ** 3), 2)
                        except Exception:
                            size_gb = None

                        mod = to_naive_dt(getattr(f, "modification", None))
                        idade = round((collected_at - mod).total_seconds() / 86400, 2) if mod else None

                        low = full_path.lower()
                        if low.endswith("-delta.vmdk") or low.endswith("-sesparse.vmdk"):
                            observacao = "Candidato associado a cadeia de snapshot/delta. Validar com prioridade; não remover automaticamente."
                            confianca = 0.35
                        elif low.endswith("-flat.vmdk"):
                            observacao = "Arquivo extent/flat sem descriptor em uso identificado. Validar vínculo antes de qualquer remoção."
                            confianca = 0.50
                        else:
                            observacao = "Descriptor VMDK não associado a VM ativa pelo inventário do vCenter. Validar antes de qualquer remoção."
                            confianca = 0.80

                        candidates.append({
                            "datastore": ds_name,
                            "vmdk_path": full_path,
                            "arquivo": fpath,
                            "tamanho_gb": size_gb,
                            "data_modificacao": mod,
                            "idade_dias": idade,
                            "vm_associada_encontrada": "NAO_ENCONTRADA_NO_INVENTARIO_VCENTER",
                            "cluster": "VALIDAR",
                            "status_validacao": "CANDIDATO_A_ORFAO",
                            "confianca": confianca,
                            "observacao": observacao,
                            "raw_json": json.dumps({
                                "fileType": str(getattr(f, "fileType", "") or ""),
                                "descriptor_inferred": descriptor,
                                "source": "vcenter_datastore_browser"
                            }, ensure_ascii=False, default=str),
                        })
                        local_count += 1

                log(f"- {ds_name}: candidatos acumulados = {len(candidates)} (+{local_count})")

            except vim.fault.NoPermission as exc:
                log(f"Permissão negada em {ds_name}: {getattr(exc, 'msg', exc)}")
            except TimeoutError:
                log(f"Timeout ao varrer {ds_name}")
            except vmodl.MethodFault as exc:
                log(f"Falha ao varrer {ds_name}: {getattr(exc, 'msg', exc)}")
            except Exception as exc:
                log(f"Erro inesperado em {ds_name}: {exc}")

        return candidates
    finally:
        try:
            ds_view.Destroy()
        except Exception:
            pass


def ensure_schema(con):
    con.execute(SCHEMA_SQL)


def insert_many(con, table: str, columns: list[str], rows: list[dict]):
    if not rows:
        return
    placeholders = ",".join(["?"] * len(columns))
    sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
    data = [[row.get(c) for c in columns] for row in rows]
    con.executemany(sql, data)


def severity_for_poweroff(days):
    if days is None:
        return "VALIDAR"
    if days >= 90:
        return "CRITICO"
    if days >= 60:
        return "RISCO"
    if days >= 30:
        return "ATENCAO"
    return "OBSERVAR"


def build_recommendations(run_id, collected_at, power_rows, snap_rows, orphan_rows):
    recs = []
    for r in power_rows:
        if not r["is_powered_off"]:
            continue
        sev = severity_for_poweroff(r.get("dias_desligada"))
        if sev in ("OBSERVAR",):
            continue
        recs.append({
            "run_id": run_id,
            "created_at": collected_at,
            "item_type": "POWERED_OFF_VM",
            "severity": sev,
            "entity_name": r["vm_name"],
            "cluster": r.get("cluster"),
            "metric": f"dias_desligada={r.get('dias_desligada')}",
            "finding": "VM desligada encontrada com recursos ainda alocados.",
            "recommendation": "Validar com o responsável se a VM ainda é necessária. A IA apenas recomenda; não desligar/remover automaticamente.",
            "action_allowed": False,
        })
    for r in snap_rows:
        if (r.get("snapshot_age_days") or 0) <= 20:
            continue
        recs.append({
            "run_id": run_id,
            "created_at": collected_at,
            "item_type": "OLD_SNAPSHOT",
            "severity": r.get("status_risco") or "ATENCAO",
            "entity_name": r["vm_name"],
            "cluster": r.get("cluster"),
            "metric": f"snapshot_age_days={r.get('snapshot_age_days')}",
            "finding": "Snapshot antigo encontrado.",
            "recommendation": "Validar com responsável e planejar consolidação/remoção controlada. A IA apenas recomenda; não remove snapshot.",
            "action_allowed": False,
        })
    for r in orphan_rows:
        recs.append({
            "run_id": run_id,
            "created_at": collected_at,
            "item_type": "ORPHAN_DISK_CANDIDATE",
            "severity": "VALIDAR",
            "entity_name": r.get("vmdk_path"),
            "cluster": r.get("cluster"),
            "metric": f"tamanho_gb={r.get('tamanho_gb')}",
            "finding": "VMDK candidato a órfão encontrado por varredura de datastore.",
            "recommendation": "Validar vínculo com VM, template, backup, clone ou snapshot antes de qualquer remoção. A IA apenas recomenda.",
            "action_allowed": False,
        })
    return recs


def connect_vcenter(host: str, username: str, password: str):
    context = ssl._create_unverified_context()
    return SmartConnect(host=host, user=username, pwd=password, sslContext=context)


def get_password(service_name: str, username: str):
    env_pass = os.getenv("VC_PASS") or os.getenv("VCENTER_PASSWORD")
    if env_pass:
        return env_pass
    if keyring:
        try:
            saved = keyring.get_password(service_name, username)
            if saved:
                log(f"Credencial encontrada no keyring para {username}")
                return saved
        except Exception:
            pass
    return getpass.getpass("Senha vCenter: ")


def main():
    ap = argparse.ArgumentParser(description="Etapa 16A.2 - coleta direta vCenter/pyVmomi para Otimização")
    ap.add_argument("--db", default="data/database/rmc_copilot.duckdb")
    ap.add_argument("--vcenter-host", default=os.getenv("VCENTER_HOST") or "srv-vcsprd01")
    ap.add_argument("--user", default=os.getenv("VC_USER") or os.getenv("VCENTER_USER") or "")
    ap.add_argument("--cluster", default="")
    ap.add_argument("--max-vms", type=int, default=0)
    ap.add_argument("--days-back-poweroff", type=int, default=365)
    ap.add_argument("--snapshot-warning-days", type=int, default=20)
    ap.add_argument("--include-orphan-scan", action="store_true", help="Varre datastores. Pode demorar.")
    ap.add_argument("--datastore-filter", default="")
    args = ap.parse_args()

    username = args.user.strip() or input("Usuário vCenter: ").strip()
    password = get_password("vCenter_Access", username)

    run_id = "OPT16A2_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    collected_at = datetime.now()

    log(f"[INICIO] Coleta Otimização 16A.2 direta vCenter | host={args.vcenter_host} | cluster={args.cluster or 'ALL'} | max_vms={args.max_vms or 'ALL'}")
    log("[REGRA] IA/coleta não executa ação operacional; apenas registra dados para relatório e recomendação.")

    si = None
    try:
        si = connect_vcenter(args.vcenter_host, username, password)
        content = si.RetrieveContent()
        about = content.about
        log(f"[OK] Conectado ao vCenter: {about.fullName} | versão={about.version}")

        view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
        all_vms = list(view.view)
        try:
            view.Destroy()
        except Exception:
            pass

        if args.cluster:
            all_vms = [vm for vm in all_vms if args.cluster.lower() in get_cluster(vm).lower()]

        total_found = len(all_vms)
        if args.max_vms and args.max_vms > 0:
            all_vms = all_vms[:args.max_vms]

        log(f"VMs encontradas no escopo: {total_found}; processando: {len(all_vms)}")

        power_rows = []
        snap_rows = []

        for idx, vm in enumerate(all_vms, 1):
            if idx == 1 or idx % 100 == 0:
                log(f"Processando VM {idx}/{len(all_vms)}: {getattr(vm, 'name', 'N/A')}")
            try:
                vm_name = vm.name
                cluster = get_cluster(vm)
                host = get_host(vm)
                power_state = str(getattr(vm.runtime, "powerState", "") or "")
                is_off = power_state.lower().endswith("poweredoff") or "poweredoff" in power_state.lower()

                off_dt = find_last_poweroff_event(content, vm, args.days_back_poweroff) if is_off else None
                dias_desligada = round((collected_at - off_dt).total_seconds() / 86400, 2) if off_dt else None

                cpu_count = None
                mem_gb = None
                guest = None
                try:
                    if getattr(vm, "config", None):
                        cpu_count = safe_float(vm.config.hardware.numCPU)
                        mem_gb = round(float(vm.config.hardware.memoryMB or 0) / 1024, 2)
                        guest = getattr(vm.config, "guestFullName", None)
                except Exception:
                    pass

                raw = {
                    "guest": guest,
                    "instanceUuid": getattr(getattr(vm, "config", None), "instanceUuid", None),
                    "power_off_event": off_dt,
                    "source": "vcenter_pyvmomi",
                }

                power_rows.append({
                    "run_id": run_id,
                    "collected_at": collected_at,
                    "vm_name": vm_name,
                    "vm_resource_id": getattr(getattr(vm, "config", None), "instanceUuid", None),
                    "cluster": cluster,
                    "host": host,
                    "power_state": power_state,
                    "is_powered_off": is_off,
                    "dias_desligada": dias_desligada,
                    "cpu_count": cpu_count,
                    "memory_gb": mem_gb,
                    "disk_provisioned_gb": get_disk_total_gb(vm),
                    "datastore_names": get_datastores(vm),
                    "ambiente": "VALIDAR",
                    "raw_json": json.dumps(raw, ensure_ascii=False, default=str),
                })

                for snap in collect_snapshot_tree(vm.snapshot.rootSnapshotList if getattr(vm, "snapshot", None) else [], vm_name, vm, collected_at, args.snapshot_warning_days):
                    snap_rows.append({
                        "run_id": run_id,
                        "collected_at": collected_at,
                        "vm_name": vm_name,
                        "vm_resource_id": getattr(getattr(vm, "config", None), "instanceUuid", None),
                        "cluster": cluster,
                        "host": host,
                        "snapshot_name": snap["snapshot_name"],
                        "snapshot_created_at": snap["snapshot_created_at"],
                        "snapshot_age_days": snap["snapshot_age_days"],
                        "snapshot_size_gb": snap["snapshot_size_gb"],
                        "snapshot_count": snap["snapshot_count"],
                        "datastore": get_datastores(vm),
                        "status_risco": snap["status_risco"],
                        "raw_json": snap["raw_json"],
                    })

            except Exception as exc:
                log(f"[WARN] Falha ao processar VM {getattr(vm, 'name', 'N/A')}: {exc}")

        orphan_rows = []
        if args.include_orphan_scan:
            log("[ORPHAN] Varredura de datastores habilitada. Pode demorar.")
            orphan_rows = collect_orphan_disk_candidates(content, all_vms, collected_at, args.datastore_filter or None)
        else:
            log("[ORPHAN] Varredura de datastores não executada. Use -IncludeOrphanScan no .ps1 ou --include-orphan-scan no .py.")

        db_path = Path(args.db)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(str(db_path))
        try:
            ensure_schema(con)

            insert_many(con, "vm_power_state_snapshots", [
                "run_id","collected_at","vm_name","vm_resource_id","cluster","host","power_state","is_powered_off",
                "dias_desligada","cpu_count","memory_gb","disk_provisioned_gb","datastore_names","ambiente","raw_json"
            ], power_rows)

            insert_many(con, "vm_snapshot_inventory", [
                "run_id","collected_at","vm_name","vm_resource_id","cluster","host","snapshot_name","snapshot_created_at",
                "snapshot_age_days","snapshot_size_gb","snapshot_count","datastore","status_risco","raw_json"
            ], snap_rows)

            insert_many(con, "orphan_disk_candidates", [
                "run_id","collected_at","datastore","vmdk_path","arquivo","tamanho_gb","data_modificacao","idade_dias",
                "vm_associada_encontrada","cluster","status_validacao","confianca","observacao","raw_json"
            ], [
                {
                    "run_id": run_id,
                    "collected_at": collected_at,
                    **r
                } for r in orphan_rows
            ])

            recs = build_recommendations(run_id, collected_at, power_rows, snap_rows, [
                {"run_id": run_id, "collected_at": collected_at, **r} for r in orphan_rows
            ])
            insert_many(con, "optimization_recommendations", [
                "run_id","created_at","item_type","severity","entity_name","cluster","metric","finding","recommendation","action_allowed"
            ], recs)

            con.execute("""
                INSERT INTO optimization_collection_runs (
                    run_id, collected_at, source, vrops_host, auth_source, cluster_filter, status, message,
                    total_vms, total_powered_off_vms, total_snapshots, total_snapshots_over_20d, total_orphan_disk_candidates
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                run_id, collected_at, "VCENTER_PYVMOMI", args.vcenter_host, "vCenter",
                args.cluster or "ALL", "OK",
                "Coleta direta via vCenter/pyVmomi. Nenhuma ação operacional executada.",
                len(power_rows),
                sum(1 for r in power_rows if r["is_powered_off"]),
                len(snap_rows),
                sum(1 for r in snap_rows if (r.get("snapshot_age_days") or 0) > args.snapshot_warning_days),
                len(orphan_rows),
            ])
        finally:
            con.close()

        log(f"[OK] run_id={run_id}")
        log(f"[OK] VMs={len(power_rows)} | powered_off={sum(1 for r in power_rows if r['is_powered_off'])} | snapshots={len(snap_rows)} | snapshots>{args.snapshot_warning_days}d={sum(1 for r in snap_rows if (r.get('snapshot_age_days') or 0) > args.snapshot_warning_days)} | discos_candidatos={len(orphan_rows)}")
        log("[IMPORTANTE] Nenhuma ação operacional foi executada. A coleta só registra dados para análise e recomendação.")

    finally:
        if si:
            try:
                Disconnect(si)
                log("[OK] Desconectado do vCenter.")
            except Exception:
                pass


if __name__ == "__main__":
    main()
