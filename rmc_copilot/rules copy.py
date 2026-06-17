def classificar_vm_cpu(cpu_avg: float, cpu_p95: float) -> str:
    """
    Classifica uma VM quanto ao uso de CPU.
    """
    if cpu_avg < 20 and cpu_p95 < 40:
        return "SUPERDIMENSIONADA_CPU"
    elif cpu_p95 > 85:
        return "SUBDIMENSIONADA_CPU"
    else:
        return "OK_CPU"


def classificar_vm_memoria(mem_avg: float, mem_p95: float) -> str:
    """
    Classifica uma VM quanto ao uso de memória.
    """
    if mem_avg < 40 and mem_p95 < 60:
        return "SUPERDIMENSIONADA_MEMORIA"
    elif mem_p95 > 85:
        return "SUBDIMENSIONADA_MEMORIA"
    else:
        return "OK_MEMORIA"


def classificar_vm_disco(disk_usage_pct: float) -> str:
    """
    Classifica uma VM quanto ao uso de disco.
    """
    if disk_usage_pct > 85:
        return "RISCO_DISCO"
    elif disk_usage_pct < 40:
        return "POSSIVEL_EXCESSO_DISCO"
    else:
        return "OK_DISCO"