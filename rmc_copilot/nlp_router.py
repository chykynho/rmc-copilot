def detectar_intencao(pergunta: str) -> str:
    pergunta = pergunta.lower()

    if "superdimension" in pergunta or "sobrando" in pergunta or "reduzir" in pergunta:
        return "vms_superdimensionadas"

    if "subdimension" in pergunta or "satur" in pergunta or "risco" in pergunta:
        return "vms_subdimensionadas"

    if "cluster" in pergunta:
        return "analise_clusters"

    if "host" in pergunta:
        return "analise_hosts"

    if "disco" in pergunta or "storage" in pergunta or "datastore" in pergunta:
        return "analise_disco"

    return "resumo_geral"