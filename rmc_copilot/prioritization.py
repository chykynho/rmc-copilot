import pandas as pd


def classificar_criticidade_futura(risco_futuro: str) -> str:
    """
    Converte risco futuro em criticidade temporal.
    """

    if not isinstance(risco_futuro, str):
        return "SEM_RISCO_FUTURO"

    if risco_futuro.startswith("RISCO_30D"):
        return "RISCO_FUTURO_30D"

    if risco_futuro.startswith("RISCO_60D"):
        return "RISCO_FUTURO_60D"

    if risco_futuro.startswith("RISCO_90D"):
        return "RISCO_FUTURO_90D"

    return "SEM_RISCO_FUTURO"


def calcular_score_prioridade(row) -> int:
    """
    Calcula score operacional da VM.

    Quanto maior o score, maior a prioridade.
    """

    score = 0

    status_geral = row.get("status_geral", "")
    risco_futuro = row.get("risco_futuro_90d", "")
    categoria_vm = row.get("categoria_vm", "")

    # Risco atual
    if status_geral == "CRITICO":
        score += 100
    elif status_geral == "RISCO":
        score += 80
    elif status_geral == "ATENCAO":
        score += 50
    elif status_geral == "OTIMIZACAO":
        score += 25
    elif status_geral == "OK":
        score += 0
    elif status_geral == "SEM_DADOS":
        score += 40

    # Risco futuro
    if isinstance(risco_futuro, str):
        if risco_futuro.startswith("RISCO_30D"):
            score += 40
        elif risco_futuro.startswith("RISCO_60D"):
            score += 25
        elif risco_futuro.startswith("RISCO_90D"):
            score += 15

    # Peso por recurso
    if "DISCO" in str(risco_futuro):
        score += 10

    if "MEMORIA" in str(risco_futuro):
        score += 8

    if "CPU" in str(risco_futuro):
        score += 4

    # Categorias sensíveis
    if categoria_vm in ["BANCO_DADOS", "SEGURANCA_REDE", "BACKUP"]:
        score += 10

    if categoria_vm in ["VDI_XENAPP"]:
        score += 5

    return score


def classificar_prioridade_final(score: int) -> str:
    """
    Classifica prioridade final com base no score.
    """

    if score >= 120:
        return "P0_ACAO_IMEDIATA"

    if score >= 90:
        return "P1_ALTA"

    if score >= 60:
        return "P2_MEDIA"

    if score >= 30:
        return "P3_BAIXA"

    return "P4_MONITORAR"


def definir_acao_final(row) -> str:
    """
    Define ação final combinando risco atual, futuro e categoria.
    """

    status_geral = row.get("status_geral", "")
    risco_futuro = row.get("risco_futuro_90d", "")
    acao_recomendada = row.get("acao_recomendada", "")
    categoria_vm = row.get("categoria_vm", "")
    prioridade_final = row.get("prioridade_final", "")

    if status_geral == "CRITICO":
        return "TRATAR_IMEDIATAMENTE"

    if status_geral == "RISCO":
        return "ANALISAR_EM_CURTO_PRAZO"

    if isinstance(risco_futuro, str) and risco_futuro.startswith("RISCO_30D"):
        return "ANTECIPAR_ACAO_30D"

    if isinstance(risco_futuro, str) and risco_futuro.startswith("RISCO_60D"):
        return "PLANEJAR_ACAO_60D"

    if isinstance(risco_futuro, str) and risco_futuro.startswith("RISCO_90D"):
        return "MONITORAR_PLANEJAR_90D"

    if status_geral == "ATENCAO":
        return "MONITORAR_RADAR_MENSAL"

    if status_geral == "OTIMIZACAO":
        if categoria_vm in ["BANCO_DADOS", "SEGURANCA_REDE", "BACKUP", "VDI_XENAPP"]:
            return "VALIDAR_RIGHTSIZING_COM_RESPONSAVEL"
        return "AVALIAR_RIGHTSIZING"

    if status_geral == "SEM_DADOS":
        return "CORRIGIR_COLETA"

    if prioridade_final == "P4_MONITORAR":
        return "MANTER_MONITORAMENTO"

    return acao_recomendada or "MANTER"


def gerar_recomendacao_final(row) -> str:
    """
    Gera recomendação executiva final.
    """

    vm = row.get("vm", "VM")
    cluster = row.get("cluster", "cluster")
    status_geral = row.get("status_geral", "")
    prioridade_final = row.get("prioridade_final", "")
    acao_final = row.get("acao_final", "")
    risco_futuro = row.get("risco_futuro_90d", "")
    categoria_vm = row.get("categoria_vm", "")
    recomendacao_base = row.get("recomendacao", "")

    disk_p95 = row.get("disk_p95_pct")
    mem_p95 = row.get("mem_p95_pct")
    cpu_p95 = row.get("cpu_p95_pct")

    partes = []

    partes.append(
        f"{vm} no cluster {cluster}: prioridade {prioridade_final}, "
        f"status atual {status_geral}, ação final {acao_final}."
    )

    if categoria_vm:
        partes.append(f"Categoria identificada: {categoria_vm}.")

    if pd.notna(cpu_p95):
        partes.append(f"CPU p95 atual: {cpu_p95:.1f}%.")

    if pd.notna(mem_p95):
        partes.append(f"Memória p95 atual: {mem_p95:.1f}%.")

    if pd.notna(disk_p95):
        partes.append(f"Disco p95 atual: {disk_p95:.1f}%.")

    if risco_futuro and risco_futuro != "SEM_RISCO_90D":
        partes.append(f"Risco projetado: {risco_futuro}.")

    if recomendacao_base:
        partes.append(f"Detalhe técnico: {recomendacao_base}")

    return " ".join(partes)


def aplicar_priorizacao_v04(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica priorização operacional v0.4.
    """

    df = df.copy()

    df["criticidade_futura"] = df["risco_futuro_90d"].apply(
        classificar_criticidade_futura
    )

    df["score_prioridade"] = df.apply(calcular_score_prioridade, axis=1)

    df["prioridade_final"] = df["score_prioridade"].apply(
        classificar_prioridade_final
    )

    df["acao_final"] = df.apply(definir_acao_final, axis=1)

    df["recomendacao_final"] = df.apply(gerar_recomendacao_final, axis=1)

    df = df.sort_values(
        ["score_prioridade", "status_geral", "risco_futuro_90d"],
        ascending=[False, True, True]
    )

    return df