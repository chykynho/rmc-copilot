import pandas as pd

from rmc_copilot.rules import (
    classificar_cpu,
    classificar_memoria,
    classificar_disco,
    classificar_status_geral,
)


def valor_ou_none(row, coluna):
    """
    Retorna None se a coluna não existir ou se o valor for nulo.
    """
    if coluna not in row:
        return None

    valor = row[coluna]

    if pd.isna(valor):
        return None

    return valor


def categorizar_vm_por_nome(nome_vm: str) -> str:
    """
    Classifica a VM por padrão de nome.

    Isso evita recomendações agressivas para appliances,
    rede, segurança, banco e backup.
    """
    if not isinstance(nome_vm, str):
        return "DESCONHECIDA"

    nome = nome_vm.upper()

    regras = {
        "SEGURANCA_REDE": [
            "FW", "FIREWALL", "PROXY", "SWG", "WAF", "VPN", "WLC", "DNA",
            "AUTH", "CAAUTH", "IDM", "COLLECTOR"
        ],
        "BACKUP": [
            "BKP", "BACKUP", "VEEAM", "COMMVAULT", "TSM"
        ],
        "BANCO_DADOS": [
            "SQL", "DB", "ORA", "ORACLE", "MYSQL", "POSTGRE", "MONGO"
        ],
        "WEB_APP": [
            "WEB", "APP", "API", "JBOSS", "TOMCAT", "IIS", "NGINX"
        ],
        "VDI_XENAPP": [
            "VDI", "XENAPP", "CTX", "CITRIX"
        ],
        "MONITORAMENTO": [
            "ZABBIX", "PRTG", "MONITOR", "OBS", "GRAFANA", "PROMETHEUS"
        ],
    }

    for categoria, termos in regras.items():
        if any(termo in nome for termo in termos):
            return categoria

    return "SERVIDOR_GERAL"


def nivel_recomendacao_por_categoria(categoria_vm: str) -> str:
    """
    Define o nível de agressividade da recomendação.
    """

    categorias_conservadoras = {
        "SEGURANCA_REDE",
        "BACKUP",
        "BANCO_DADOS",
        "VDI_XENAPP",
        "MONITORAMENTO",
    }

    if categoria_vm in categorias_conservadoras:
        return "CONSERVADORA"

    return "NORMAL"


def gerar_recomendacao(row) -> str:
    """
    Gera recomendação textual priorizando risco antes de otimização.
    """

    recomendacoes_risco = []
    recomendacoes_atencao = []
    recomendacoes_otimizacao = []

    vm = row.get("vm", "VM")
    categoria_vm = row.get("categoria_vm", "DESCONHECIDA")
    nivel_recomendacao = row.get("nivel_recomendacao", "NORMAL")

    status_cpu = row.get("status_cpu", "")
    status_memoria = row.get("status_memoria", "")
    status_disco = row.get("status_disco", "")

    cpu_media = row.get("cpu_media_pct", None)
    cpu_p95 = row.get("cpu_p95_pct", None)
    cpu_max = row.get("cpu_max_pct", None)

    mem_media = row.get("mem_media_pct", None)
    mem_p95 = row.get("mem_p95_pct", None)
    mem_max = row.get("mem_max_pct", None)

    disk_p95 = row.get("disk_p95_pct", None)
    disk_max = row.get("disk_max_pct", None)
    disk_free = row.get("disk_free_gb_medio", None)

    prefixo_conservador = ""
    if nivel_recomendacao == "CONSERVADORA":
        prefixo_conservador = (
            f"VM classificada como {categoria_vm}; recomendação deve ser validada "
            f"com o time responsável antes de qualquer alteração. "
        )

    # RISCOS
    if status_disco == "RISCO_DISCO_CRITICO":
        recomendacoes_risco.append(
            f"Disco crítico: p95 {disk_p95:.1f}% e máximo {disk_max:.1f}%. "
            f"Ação recomendada: expansão, limpeza ou revisão imediata de crescimento."
        )

    if status_disco == "RISCO_DISCO":
        recomendacoes_risco.append(
            f"Disco em risco: p95 {disk_p95:.1f}%. "
            f"Avaliar expansão, limpeza, logs, snapshots ou crescimento da aplicação."
        )

    if status_memoria == "SUBDIMENSIONADA_MEMORIA":
        recomendacoes_risco.append(
            f"Memória em risco: p95 {mem_p95:.1f}% e máximo {mem_max:.1f}%. "
            f"Avaliar aumento de RAM ou investigação de consumo anormal."
        )

    if status_cpu == "SUBDIMENSIONADA_CPU":
        recomendacoes_risco.append(
            f"CPU em risco: p95 {cpu_p95:.1f}% e máximo {cpu_max:.1f}%. "
            f"Avaliar aumento de vCPU, CPU Ready, contenção no host ou redistribuição da carga."
        )

    # ATENÇÃO
    if status_disco == "ATENCAO_DISCO":
        recomendacoes_atencao.append(
            f"Disco em atenção: p95 {disk_p95:.1f}%. Monitorar crescimento."
        )

    if status_memoria == "ATENCAO_MEMORIA":
        recomendacoes_atencao.append(
            f"Memória em atenção: p95 {mem_p95:.1f}%. Monitorar tendência antes de alterar recurso."
        )

    if status_cpu == "ATENCAO_CPU":
        recomendacoes_atencao.append(
            f"CPU em atenção: p95 {cpu_p95:.1f}%. Verificar se os picos são recorrentes."
        )

    # OTIMIZAÇÃO
    if status_cpu == "SUPERDIMENSIONADA_CPU":
        if nivel_recomendacao == "CONSERVADORA":
            recomendacoes_otimizacao.append(
                f"CPU com baixa utilização: média {cpu_media:.1f}% e p95 {cpu_p95:.1f}%. "
                f"Por ser {categoria_vm}, não reduzir automaticamente; apenas avaliar com o responsável."
            )
        else:
            recomendacoes_otimizacao.append(
                f"CPU possivelmente superdimensionada: média {cpu_media:.1f}% e p95 {cpu_p95:.1f}%. "
                f"Avaliar redução gradual de vCPU."
            )

    if status_memoria == "SUPERDIMENSIONADA_MEMORIA":
        if nivel_recomendacao == "CONSERVADORA":
            recomendacoes_otimizacao.append(
                f"Memória com baixa utilização: média {mem_media:.1f}% e p95 {mem_p95:.1f}%. "
                f"Por ser {categoria_vm}, não reduzir automaticamente; validar dependência da aplicação."
            )
        else:
            recomendacoes_otimizacao.append(
                f"Memória possivelmente superdimensionada: média {mem_media:.1f}% e p95 {mem_p95:.1f}%. "
                f"Avaliar redução gradual de RAM."
            )

    if status_disco == "POSSIVEL_EXCESSO_DISCO":
        recomendacoes_otimizacao.append(
            f"Disco com baixa utilização: p95 {disk_p95:.1f}%. "
            f"Avaliar provisionamento excessivo ou oportunidade de reclaim."
        )

    partes = []

    if prefixo_conservador:
        partes.append(prefixo_conservador)

    if recomendacoes_risco:
        partes.append("Risco: " + " ".join(recomendacoes_risco))

    if recomendacoes_atencao:
        partes.append("Atenção: " + " ".join(recomendacoes_atencao))

    if recomendacoes_otimizacao:
        partes.append("Otimização: " + " ".join(recomendacoes_otimizacao))

    if not partes:
        return f"{vm}: sem indícios relevantes de risco, superdimensionamento ou subdimensionamento."

    return f"{vm}: " + " ".join(partes)


def definir_acao_recomendada(row) -> str:
    """
    Cria uma ação curta para facilitar filtro no Excel.
    """

    status_geral = row.get("status_geral", "")
    status_cpu = row.get("status_cpu", "")
    status_memoria = row.get("status_memoria", "")
    status_disco = row.get("status_disco", "")
    nivel = row.get("nivel_recomendacao", "")

    if status_geral == "CRITICO":
        return "AÇÃO_IMEDIATA_DISCO"

    if status_disco == "RISCO_DISCO":
        return "AVALIAR_DISCO"

    if status_memoria == "SUBDIMENSIONADA_MEMORIA":
        return "AVALIAR_AUMENTO_MEMORIA"

    if status_cpu == "SUBDIMENSIONADA_CPU":
        return "AVALIAR_AUMENTO_CPU"

    if status_geral == "ATENCAO":
        return "MONITORAR"

    if status_geral == "OTIMIZACAO" and nivel == "CONSERVADORA":
        return "AVALIAR_COM_RESPONSAVEL"

    if status_cpu == "SUPERDIMENSIONADA_CPU" or status_memoria == "SUPERDIMENSIONADA_MEMORIA":
        return "AVALIAR_RIGHTSIZING"

    if status_disco == "POSSIVEL_EXCESSO_DISCO":
        return "AVALIAR_RECLAIM_DISCO"

    if status_geral == "SEM_DADOS":
        return "CORRIGIR_COLETA_METRICAS"

    return "MANTER"


def analisar_capacity_vms(df_consolidado: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica regras de capacity planning ao consolidado de VMs.
    """

    df = df_consolidado.copy()

    df["categoria_vm"] = df["vm"].apply(categorizar_vm_por_nome)
    df["nivel_recomendacao"] = df["categoria_vm"].apply(nivel_recomendacao_por_categoria)

    df["status_cpu"] = df.apply(
        lambda row: classificar_cpu(
            valor_ou_none(row, "cpu_media_pct"),
            valor_ou_none(row, "cpu_p95_pct"),
            valor_ou_none(row, "cpu_max_pct"),
        ),
        axis=1,
    )

    df["status_memoria"] = df.apply(
        lambda row: classificar_memoria(
            valor_ou_none(row, "mem_media_pct"),
            valor_ou_none(row, "mem_p95_pct"),
            valor_ou_none(row, "mem_max_pct"),
        ),
        axis=1,
    )

    df["status_disco"] = df.apply(
        lambda row: classificar_disco(
            valor_ou_none(row, "disk_media_pct"),
            valor_ou_none(row, "disk_p95_pct"),
            valor_ou_none(row, "disk_max_pct"),
        ),
        axis=1,
    )

    df["status_geral"] = df.apply(
        lambda row: classificar_status_geral(
            row["status_cpu"],
            row["status_memoria"],
            row["status_disco"],
        ),
        axis=1,
    )

    df["acao_recomendada"] = df.apply(definir_acao_recomendada, axis=1)
    df["recomendacao"] = df.apply(gerar_recomendacao, axis=1)

    return df