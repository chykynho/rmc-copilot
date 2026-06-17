import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def preparar_historico_recurso(
    df: pd.DataFrame,
    coluna_valor: str = "used_pct"
) -> pd.DataFrame:
    """
    Prepara histórico temporal com data e valor numérico.
    """

    df = df.copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df[coluna_valor] = pd.to_numeric(df[coluna_valor], errors="coerce")

    df = df.dropna(subset=["cluster", "vm", "vm_resource_id", "date", coluna_valor])

    return df


def calcular_forecast_por_vm(
    df_hist: pd.DataFrame,
    prefixo: str,
    coluna_valor: str = "used_pct",
    min_amostras: int = 10
) -> pd.DataFrame:
    """
    Calcula tendência e forecast 30/60/90 dias por VM usando regressão linear simples.

    Retorna:
    - tendencia_pct_dia
    - valor_atual_estimado
    - forecast_30d
    - forecast_60d
    - forecast_90d
    """

    df = preparar_historico_recurso(df_hist, coluna_valor=coluna_valor)

    resultados = []

    for (cluster, vm, vm_resource_id), grupo in df.groupby(["cluster", "vm", "vm_resource_id"]):
        grupo = grupo.sort_values("date")

        if len(grupo) < min_amostras:
            resultados.append({
                "cluster": cluster,
                "vm": vm,
                "vm_resource_id": vm_resource_id,
                f"{prefixo}_tendencia_pct_dia": np.nan,
                f"{prefixo}_valor_atual_estimado": np.nan,
                f"{prefixo}_forecast_30d": np.nan,
                f"{prefixo}_forecast_60d": np.nan,
                f"{prefixo}_forecast_90d": np.nan,
                f"{prefixo}_forecast_status": "AMOSTRAS_INSUFICIENTES",
            })
            continue

        primeira_data = grupo["date"].min()

        grupo["dias"] = (grupo["date"] - primeira_data).dt.days

        X = grupo[["dias"]].values
        y = grupo[coluna_valor].values

        try:
            modelo = LinearRegression()
            modelo.fit(X, y)

            tendencia = float(modelo.coef_[0])
            ultimo_dia = int(grupo["dias"].max())

            valor_atual = float(modelo.predict([[ultimo_dia]])[0])
            forecast_30 = float(modelo.predict([[ultimo_dia + 30]])[0])
            forecast_60 = float(modelo.predict([[ultimo_dia + 60]])[0])
            forecast_90 = float(modelo.predict([[ultimo_dia + 90]])[0])

            forecast_30 = max(0, min(100, forecast_30))
            forecast_60 = max(0, min(100, forecast_60))
            forecast_90 = max(0, min(100, forecast_90))
            valor_atual = max(0, min(100, valor_atual))

            status = "OK_FORECAST"

        except Exception:
            tendencia = np.nan
            valor_atual = np.nan
            forecast_30 = np.nan
            forecast_60 = np.nan
            forecast_90 = np.nan
            status = "ERRO_FORECAST"

        resultados.append({
            "cluster": cluster,
            "vm": vm,
            "vm_resource_id": vm_resource_id,
            f"{prefixo}_tendencia_pct_dia": tendencia,
            f"{prefixo}_valor_atual_estimado": valor_atual,
            f"{prefixo}_forecast_30d": forecast_30,
            f"{prefixo}_forecast_60d": forecast_60,
            f"{prefixo}_forecast_90d": forecast_90,
            f"{prefixo}_forecast_status": status,
        })

    return pd.DataFrame(resultados)


def preparar_historico_disco_para_forecast(df_disk: pd.DataFrame) -> pd.DataFrame:
    """
    Consolida HIST_DISK por VM/data usando o pior used_pct entre partições.
    """

    df = df_disk.copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["used_pct"] = pd.to_numeric(df["used_pct"], errors="coerce")

    df = df.dropna(subset=["cluster", "vm", "vm_resource_id", "date", "used_pct"])

    diario_vm = (
        df.groupby(["cluster", "vm", "vm_resource_id", "date"])
        .agg(
            used_pct=("used_pct", "max")
        )
        .reset_index()
    )

    return diario_vm


def consolidar_forecasts(
    df_base: pd.DataFrame,
    df_cpu: pd.DataFrame,
    df_mem: pd.DataFrame,
    df_disk: pd.DataFrame
) -> pd.DataFrame:
    """
    Adiciona forecast de CPU, memória e disco ao DataFrame base.
    """

    forecast_cpu = calcular_forecast_por_vm(df_cpu, prefixo="cpu")
    forecast_mem = calcular_forecast_por_vm(df_mem, prefixo="mem")

    disk_diario = preparar_historico_disco_para_forecast(df_disk)
    forecast_disk = calcular_forecast_por_vm(disk_diario, prefixo="disk")

    df = df_base.copy()

    df = df.merge(
        forecast_cpu,
        on=["cluster", "vm", "vm_resource_id"],
        how="left"
    )

    df = df.merge(
        forecast_mem,
        on=["cluster", "vm", "vm_resource_id"],
        how="left"
    )

    df = df.merge(
        forecast_disk,
        on=["cluster", "vm", "vm_resource_id"],
        how="left"
    )

    return df


def classificar_risco_futuro(row) -> str:
    """
    Classifica risco futuro considerando forecasts 30/60/90 dias.
    """

    disk_30 = row.get("disk_forecast_30d")
    disk_60 = row.get("disk_forecast_60d")
    disk_90 = row.get("disk_forecast_90d")

    mem_30 = row.get("mem_forecast_30d")
    mem_60 = row.get("mem_forecast_60d")
    mem_90 = row.get("mem_forecast_90d")

    cpu_30 = row.get("cpu_forecast_30d")
    cpu_60 = row.get("cpu_forecast_60d")
    cpu_90 = row.get("cpu_forecast_90d")

    # Disco tem prioridade operacional
    if pd.notna(disk_30) and disk_30 >= 95:
        return "RISCO_30D_DISCO"

    if pd.notna(disk_60) and disk_60 >= 95:
        return "RISCO_60D_DISCO"

    if pd.notna(disk_90) and disk_90 >= 95:
        return "RISCO_90D_DISCO"

    # Memória
    if pd.notna(mem_30) and mem_30 >= 95:
        return "RISCO_30D_MEMORIA"

    if pd.notna(mem_60) and mem_60 >= 95:
        return "RISCO_60D_MEMORIA"

    if pd.notna(mem_90) and mem_90 >= 95:
        return "RISCO_90D_MEMORIA"

    # CPU
    if pd.notna(cpu_30) and cpu_30 >= 85:
        return "RISCO_30D_CPU"

    if pd.notna(cpu_60) and cpu_60 >= 85:
        return "RISCO_60D_CPU"

    if pd.notna(cpu_90) and cpu_90 >= 85:
        return "RISCO_90D_CPU"

    return "SEM_RISCO_90D"


def adicionar_risco_futuro(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona coluna risco_futuro_90d.
    """

    df = df.copy()
    df["risco_futuro_90d"] = df.apply(classificar_risco_futuro, axis=1)
    return df