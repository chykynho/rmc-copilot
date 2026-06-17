from pathlib import Path


# ============================================================
# Diretórios base do projeto
# ============================================================

# rmc_copilot/config.py fica dentro da pasta rmc_copilot/
# parent.parent leva para a raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DATABASE_DIR = DATA_DIR / "database"
UPLOADS_DIR = RAW_DIR / "uploads"
RMC_OUTPUTS_DIR = RAW_DIR / "rmc_outputs"

ASSETS_DIR = BASE_DIR / "app" / "assets"
LOGS_DIR = BASE_DIR / "logs"


# ============================================================
# Arquivos padrão
# ============================================================

DATABASE_PATH = DATABASE_DIR / "rmc_copilot.duckdb"

# Coloque aqui o nome do Excel bruto padrão, se quiser usar opção "arquivo padrão"
DEFAULT_EXCEL_PATH = RMC_OUTPUTS_DIR / "RMC_Recursos_VM_v5_10_2_20260610_094958.xlsx"

BV_LOGO_PATH = ASSETS_DIR / "bv_logo.png"


# ============================================================
# Criação automática de pastas
# ============================================================

for pasta in [
    DATA_DIR,
    RAW_DIR,
    PROCESSED_DIR,
    DATABASE_DIR,
    UPLOADS_DIR,
    RMC_OUTPUTS_DIR,
    ASSETS_DIR,
    LOGS_DIR,
]:
    pasta.mkdir(parents=True, exist_ok=True)


# ============================================================
# Colunas genéricas antigas
# Mantidas para compatibilidade com versões anteriores
# ============================================================

COLUNAS_PADRAO = {
    "vm": ["VM", "Vm", "Nome VM", "Name", "VM Name"],
    "cluster": ["Cluster", "Cluster Name", "Nome Cluster"],
    "host": ["Host", "ESXi", "Host Name"],
    "cpu_alloc": ["vCPU", "CPU", "CPU Allocated", "CPUs"],
    "mem_alloc_gb": ["Memory GB", "Memória GB", "Memoria GB", "RAM GB"],
    "disk_alloc_gb": ["Disk GB", "Disco GB", "Storage GB"],
    "cpu_usage_pct": ["CPU Usage %", "CPU %", "Uso CPU %"],
    "mem_usage_pct": ["Memory Usage %", "Memória %", "Uso Memória %"],
    "disk_usage_pct": ["Disk Usage %", "Disco %", "Uso Disco %"],
}


# ============================================================
# Abas obrigatórias do Excel bruto RMC/vROps
# ============================================================

ABAS_OBRIGATORIAS_EXCEL = {
    "VMS_SELECIONADAS",
    "HIST_CPU",
    "HIST_MEM",
    "HIST_DISK",
}


# ============================================================
# Configurações do dashboard
# ============================================================

APP_TITLE = "RMC Copilot"
APP_SUBTITLE = "Radar Mensal de Capacidade VMware"

STREAMLIT_PORT = 8501