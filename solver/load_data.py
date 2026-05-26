from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = {"id", "cidade", "pais", "latitude", "longitude", "procura"}


def load_clientes_csv(filepath: str | Path) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df.columns = [c.strip().lower() for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Faltam colunas obrigatórias: {sorted(missing)}")

    df["id"] = pd.to_numeric(df["id"], errors="raise").astype(int)
    df["cidade"] = df["cidade"].astype(str)
    df["pais"] = df["pais"].astype(str)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="raise")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="raise")
    df["procura"] = pd.to_numeric(df["procura"], errors="raise")

    return df