import pandas as pd

from rmc_copilot.rules import (
#from rmc_copilot.capacity_rules import (
    classificar_vm_cpu,
    classificar_vm_memoria,
    classificar_vm_disco,
)


def analisar_vms(df_resumo: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica regras de capacity planning sobre o resumo estatístico das VMs.
    """
    df = df_resumo.copy()

    df["status_cpu"] = df.apply(
        lambda row: classificar_vm_cpu(row["cpu_avg"], row["cpu_p95"]),
        axis=1
    )

    df["status_memoria"] = df.apply(
        lambda row: classificar_vm_memoria(row["mem_avg"], row["mem_p95"]),
        axis=1
    )

    df["status_disco"] = df.apply(
        lambda row: classificar_vm_disco(row["disk_p95"]),
        axis=1
    )

    return df

# Criar saída explicável
# A LLM vai explicar, mas antes vamos criar texto determinístico.

def gerar_recomendacao_vm(row) -> str:
    recomendacoes = []

    if row["status_cpu"] == "SUPERDIMENSIONADA_CPU":
        recomendacoes.append(
            f"CPU com baixa utilização: média {row['cpu_avg']:.1f}% e p95 {row['cpu_p95']:.1f}%. Avaliar redução de vCPU."
        )

    if row["status_cpu"] == "SUBDIMENSIONADA_CPU":
        recomendacoes.append(
            f"CPU com alta utilização: p95 {row['cpu_p95']:.1f}%. Avaliar aumento de vCPU ou redistribuição da carga."
        )

    if row["status_memoria"] == "SUPERDIMENSIONADA_MEMORIA":
        recomendacoes.append(
            f"Memória com baixa utilização: média {row['mem_avg']:.1f}% e p95 {row['mem_p95']:.1f}%. Avaliar redução de RAM."
        )

    if row["status_memoria"] == "SUBDIMENSIONADA_MEMORIA":
        recomendacoes.append(
            f"Memória com alta utilização: p95 {row['mem_p95']:.1f}%. Avaliar aumento de RAM."
        )

    if row["status_disco"] == "RISCO_DISCO":
        recomendacoes.append(
            f"Disco em risco: p95 {row['disk_p95']:.1f}%. Avaliar expansão ou limpeza."
        )

    if not recomendacoes:
        return "VM sem indícios relevantes de superdimensionamento ou subdimensionamento."

    return " ".join(recomendacoes)

# df_analise["recomendacao"] = df_analise.apply(gerar_recomendacao_vm, axis=1)
# df["recomendacao"] = df_analise.apply(gerar_recomendacao_vm, axis=1)