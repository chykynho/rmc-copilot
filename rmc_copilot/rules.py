def classificar_cpu(cpu_media, cpu_p95, cpu_max):
    """
    Classifica CPU com régua calibrada para ambiente VMware.

    Como a distribuição real mostrou CPU naturalmente baixa:
    - média geral ~11,7%
    - p95 geral ~17,2%
    - p95 de 95% das VMs até ~42,5%

    A regra ficou mais conservadora.
    """

    if cpu_media is None or cpu_p95 is None:
        return "SEM_DADOS_CPU"

    if cpu_media < 5 and cpu_p95 < 10:
        return "SUPERDIMENSIONADA_CPU"

    if cpu_p95 >= 75:
        return "SUBDIMENSIONADA_CPU"

    if cpu_p95 >= 50:
        return "ATENCAO_CPU"

    return "OK_CPU"


def classificar_memoria(mem_media, mem_p95, mem_max):
    """
    Classifica memória com régua calibrada.

    Memória é mais sensível que CPU.
    Só recomenda otimização quando média e p95 são realmente baixos.
    """

    if mem_media is None or mem_p95 is None:
        return "SEM_DADOS_MEMORIA"

    if mem_media < 25 and mem_p95 < 40:
        return "SUPERDIMENSIONADA_MEMORIA"

    if mem_p95 >= 95:
        return "SUBDIMENSIONADA_MEMORIA"

    if mem_p95 >= 85:
        return "ATENCAO_MEMORIA"

    return "OK_MEMORIA"


def classificar_disco(disk_media, disk_p95, disk_max):
    """
    Classifica disco.

    Disco acima de 90% é risco.
    Disco acima de 95% é crítico.
    Disco abaixo de 30% pode indicar provisionamento excessivo.
    """

    if disk_media is None or disk_p95 is None:
        return "SEM_DADOS_DISCO"

    if disk_p95 >= 95:
        return "RISCO_DISCO_CRITICO"

    if disk_p95 >= 90:
        return "RISCO_DISCO"

    if disk_p95 >= 85:
        return "ATENCAO_DISCO"

    if disk_p95 < 30:
        return "POSSIVEL_EXCESSO_DISCO"

    return "OK_DISCO"


def classificar_status_geral(status_cpu, status_memoria, status_disco):
    """
    Consolida o status geral da VM.

    Prioridade:
    1. CRITICO
    2. RISCO
    3. ATENCAO
    4. OTIMIZACAO
    5. OK
    6. SEM_DADOS
    """

    status = [status_cpu, status_memoria, status_disco]

    if "RISCO_DISCO_CRITICO" in status:
        return "CRITICO"

    if (
        "SUBDIMENSIONADA_CPU" in status
        or "SUBDIMENSIONADA_MEMORIA" in status
        or "RISCO_DISCO" in status
    ):
        return "RISCO"

    if (
        "ATENCAO_CPU" in status
        or "ATENCAO_MEMORIA" in status
        or "ATENCAO_DISCO" in status
    ):
        return "ATENCAO"

    if (
        "SUPERDIMENSIONADA_CPU" in status
        or "SUPERDIMENSIONADA_MEMORIA" in status
        or "POSSIVEL_EXCESSO_DISCO" in status
    ):
        return "OTIMIZACAO"

    if (
        status_cpu == "SEM_DADOS_CPU"
        and status_memoria == "SEM_DADOS_MEMORIA"
        and status_disco == "SEM_DADOS_DISCO"
    ):
        return "SEM_DADOS"

    return "OK"