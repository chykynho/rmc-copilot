import pandas as pd


def preparar_historico_percentual(
    df: pd.DataFrame,
    nome_recurso: str
) -> pd.DataFrame:
    """
    Prepara histórico percentual de CPU ou memória.

    Espera colunas:
    - cluster
    - vm
    - vm_resource_id
    - date
    - used_pct
    """

    df = df.copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["used_pct"] = pd.to_numeric(df["used_pct"], errors="coerce")

    df = df.dropna(subset=["vm", "vm_resource_id", "date", "used_pct"])

    resumo = (
        df.groupby(["cluster", "vm", "vm_resource_id"])
        .agg(
            **{
                f"{nome_recurso}_media_pct": ("used_pct", "mean"),
                f"{nome_recurso}_max_pct": ("used_pct", "max"),
                f"{nome_recurso}_p95_pct": ("used_pct", lambda x: x.quantile(0.95)),
                f"{nome_recurso}_min_pct": ("used_pct", "min"),
                f"{nome_recurso}_amostras": ("used_pct", "count"),
                f"{nome_recurso}_primeira_data": ("date", "min"),
                f"{nome_recurso}_ultima_data": ("date", "max"),
            }
        )
        .reset_index()
    )

    return resumo


def preparar_historico_disco(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara histórico de disco por VM.

    Como HIST_DISK pode ter várias partições por VM,
    primeiro considera o pior caso por VM/data:
    - maior used_pct
    - maior used_gb
    - soma de capacity_gb
    - soma de free_gb
    """

    df = df.copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    colunas_numericas = [
        "used_gb",
        "capacity_gb",
        "free_gb",
        "used_pct",
        "free_pct",
        "threshold_pct",
        "threshold_gb",
        "crash_100_gb",
    ]

    for col in colunas_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["cluster", "vm", "vm_resource_id", "date", "used_pct"])

    # Consolida por VM e data, considerando múltiplas partições
    diario_vm = (
        df.groupby(["cluster", "vm", "vm_resource_id", "date"])
        .agg(
            disk_used_pct_max=("used_pct", "max"),
            disk_used_gb_total=("used_gb", "sum"),
            disk_capacity_gb_total=("capacity_gb", "sum"),
            disk_free_gb_total=("free_gb", "sum"),
            particoes=("partition", "nunique"),
        )
        .reset_index()
    )

    resumo = (
        diario_vm.groupby(["cluster", "vm", "vm_resource_id"])
        .agg(
            disk_media_pct=("disk_used_pct_max", "mean"),
            disk_max_pct=("disk_used_pct_max", "max"),
            disk_p95_pct=("disk_used_pct_max", lambda x: x.quantile(0.95)),
            disk_min_pct=("disk_used_pct_max", "min"),
            disk_used_gb_medio=("disk_used_gb_total", "mean"),
            disk_capacity_gb_medio=("disk_capacity_gb_total", "mean"),
            disk_free_gb_medio=("disk_free_gb_total", "mean"),
            disk_particoes_max=("particoes", "max"),
            disk_amostras=("disk_used_pct_max", "count"),
            disk_primeira_data=("date", "min"),
            disk_ultima_data=("date", "max"),
        )
        .reset_index()
    )

    return resumo


def consolidar_metricas_vm(
    df_vms: pd.DataFrame,
    df_cpu: pd.DataFrame,
    df_mem: pd.DataFrame,
    df_disk: pd.DataFrame
) -> pd.DataFrame:
    """
    Consolida inventário de VMs com métricas de CPU, memória e disco.
    """

    vms = df_vms.copy()

    cpu = preparar_historico_percentual(df_cpu, "cpu")
    mem = preparar_historico_percentual(df_mem, "mem")
    disk = preparar_historico_disco(df_disk)

    df = vms.merge(
        cpu,
        on=["cluster", "vm", "vm_resource_id"],
        how="left"
    )

    df = df.merge(
        mem,
        on=["cluster", "vm", "vm_resource_id"],
        how="left"
    )

    df = df.merge(
        disk,
        on=["cluster", "vm", "vm_resource_id"],
        how="left"
    )

    return df