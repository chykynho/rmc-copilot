import pandas as pd


def resumo_estatistico_vm(
    df: pd.DataFrame,
    coluna_vm: str,
    coluna_cpu: str,
    coluna_memoria: str,
    coluna_disco: str
) -> pd.DataFrame:
    """
    Gera resumo estatístico por VM.
    """
    resumo = (
        df.groupby(coluna_vm)
        .agg(
            cpu_avg=(coluna_cpu, "mean"),
            cpu_max=(coluna_cpu, "max"),
            cpu_p95=(coluna_cpu, lambda x: x.quantile(0.95)),
            mem_avg=(coluna_memoria, "mean"),
            mem_max=(coluna_memoria, "max"),
            mem_p95=(coluna_memoria, lambda x: x.quantile(0.95)),
            disk_avg=(coluna_disco, "mean"),
            disk_max=(coluna_disco, "max"),
            disk_p95=(coluna_disco, lambda x: x.quantile(0.95)),
        )
        .reset_index()
    )

    return resumo