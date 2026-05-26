import math
import pandas as pd


def validate_clientes(df: pd.DataFrame) -> None:
    """
    Valida campos essenciais dos clientes.
    """
    if df.empty:
        raise ValueError("O dataframe de clientes está vazio.")

    if df["procura"].isna().any():
        raise ValueError("Existem valores de procura em falta.")

    if (df["procura"] < 0).any():
        raise ValueError("Existem valores de procura negativos.")

    if df["latitude"].isna().any() or df["longitude"].isna().any():
        raise ValueError("Existem coordenadas em falta.")

    if df["pais"].isna().any():
        raise ValueError("Existem países em falta.")


def euclidean_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Distância euclidiana simples entre dois pontos.
    Para a fase inicial é suficiente.
    """
    return math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2)