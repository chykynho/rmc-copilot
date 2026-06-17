import pandas as pd
from pathlib import Path


def listar_abas(arquivo_excel: str) -> list[str]:
    """
    Lista as abas disponíveis em um arquivo Excel.
    """
    xls = pd.ExcelFile(arquivo_excel)
    return xls.sheet_names


def carregar_aba(arquivo_excel: str, aba: str) -> pd.DataFrame:
    """
    Carrega uma aba específica do arquivo Excel.
    """
    df = pd.read_excel(arquivo_excel, sheet_name=aba)
    df.columns = [str(col).strip() for col in df.columns]
    return df


def salvar_parquet(df: pd.DataFrame, caminho_saida: str) -> None:
    """
    Salva um DataFrame em formato parquet.
    """
    Path(caminho_saida).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(caminho_saida, index=False)