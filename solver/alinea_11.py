import math
import pandas as pd
from scipy.optimize import minimize


def validar_clientes(df: pd.DataFrame) -> None:
    required = {"id", "cidade", "pais", "latitude", "longitude", "procura"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltam colunas obrigatórias: {sorted(missing)}")

    if df.empty:
        raise ValueError("O ficheiro de clientes está vazio.")

    if df["id"].duplicated().any():
        raise ValueError("Existem IDs de cliente duplicados.")

    if df["cidade"].astype(str).str.strip().eq("").any():
        raise ValueError("Existem cidades vazias.")

    if df["pais"].astype(str).str.strip().eq("").any():
        raise ValueError("Existem países vazios.")

    if df["procura"].isna().any():
        raise ValueError("Existem valores de procura em falta.")

    if (df["procura"] < 0).any():
        raise ValueError("Existem procuras negativas.")

    if df["latitude"].isna().any() or df["longitude"].isna().any():
        raise ValueError("Existem coordenadas em falta.")


def objective(point, df):
    x, y = point
    total = 0.0

    for _, row in df.iterrows():
        dx = x - row["latitude"]
        dy = y - row["longitude"]
        dist = math.sqrt(dx**2 + dy**2)
        total += row["procura"] * dist

    return total


def centro_gravidade_inicial(df):
    total_procura = df["procura"].sum()

    x0 = (df["latitude"] * df["procura"]).sum() / total_procura
    y0 = (df["longitude"] * df["procura"]).sum() / total_procura

    return x0, y0


def resolver_pais(grupo):
    x0, y0 = centro_gravidade_inicial(grupo)

    result = minimize(
        objective,
        x0=[x0, y0],
        args=(grupo,),
        method="Nelder-Mead"
    )

    return {
        "latitude_otima": result.x[0],
        "longitude_otima": result.x[1],
        "func_obj": result.fun
    }


def criar_link_google_maps(latitude, longitude):
    return f"https://www.google.com/maps?q={latitude},{longitude}"


def calcular_solver_por_pais(df):
    resultados = []

    for pais, grupo in df.groupby("pais"):
        sol = resolver_pais(grupo)

        lat = round(sol["latitude_otima"], 6)
        lon = round(sol["longitude_otima"], 6)

        resultados.append({
            "pais": pais,
            "latitude_otima": lat,
            "longitude_otima": lon,
            "func_obj": round(sol["func_obj"], 6),
            "google_maps_otimo": criar_link_google_maps(lat, lon)
        })

    return pd.DataFrame(resultados).sort_values("pais").reset_index(drop=True)


def cidade_mais_proxima(df, resultados_solver):
    resultados = []

    for _, row in resultados_solver.iterrows():
        pais = row["pais"]
        lat_opt = row["latitude_otima"]
        lon_opt = row["longitude_otima"]

        grupo = df[df["pais"] == pais].copy()

        melhor_dist = float("inf")
        melhor_cidade = None
        melhor_lat = None
        melhor_lon = None

        for _, cli in grupo.iterrows():
            dx = lat_opt - cli["latitude"]
            dy = lon_opt - cli["longitude"]
            dist = math.sqrt(dx**2 + dy**2)

            if dist < melhor_dist:
                melhor_dist = dist
                melhor_cidade = cli["cidade"]
                melhor_lat = cli["latitude"]
                melhor_lon = cli["longitude"]

        resultados.append({
            "pais": pais,
            "cidade_escolhida": melhor_cidade,
            "latitude_cidade": round(melhor_lat, 6),
            "longitude_cidade": round(melhor_lon, 6),
            "latitude_otima": round(lat_opt, 6),
            "longitude_otima": round(lon_opt, 6),
            "distancia_ao_otimo": round(melhor_dist, 6)
        })

    return pd.DataFrame(resultados).sort_values("pais").reset_index(drop=True)