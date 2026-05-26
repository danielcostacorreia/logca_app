"""
Alínea 1.2 — Modelo MILP de definição da rede de distribuição.

Usa as distâncias reais do Google Maps (sem portagens) extraídas do Excel das colegas.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import milp, LinearConstraint, Bounds

CUSTO_KM = 13  # €/km/unidade × 100 (unidades em ×100 ton)

FABRICAS = [
    {"id": 0, "nome": "Felgueiras", "lat": 41.367740, "lon": -8.198110, "cap": 500},
    {"id": 1, "nome": "Mangualde",  "lat": 40.607028, "lon": -7.763532, "cap": 1200},
]

CDS_CANDIDATOS = [
    {"id": 0, "nome": "Munique XL",          "lat": 48.915190, "lon": 11.756490, "cap": 600,  "custo_fixo": 2500},
    {"id": 1, "nome": "Madrid XL",           "lat": 40.637128, "lon": -3.134727, "cap": 500,  "custo_fixo": 2000},
    {"id": 2, "nome": "Portugal - Coimbra",  "lat": 40.179190, "lon": -8.466150, "cap": 200,  "custo_fixo": 1000},
    {"id": 3, "nome": "Espanha - Saragoça",  "lat": 41.330000, "lon": -1.220000, "cap": 300,  "custo_fixo": 1200},
    {"id": 4, "nome": "França - Blois",      "lat": 47.624100, "lon":  1.327500, "cap": 270,  "custo_fixo": 1000},
    {"id": 5, "nome": "Itália - Milão",      "lat": 45.490000, "lon":  9.290000, "cap": 200,  "custo_fixo": 1000},
    {"id": 6, "nome": "Alemanha - Nuremberga","lat": 49.410000, "lon": 11.050000, "cap": 220,  "custo_fixo": 1500},
]

# Listas para opções A e B (mantidas para compatibilidade)
CDS_OPCAO_A = CDS_CANDIDATOS[2:]   # só os 5 normais
CDS_OPCAO_B = CDS_CANDIDATOS[:2]   # só os 2 XL

# ── Distâncias reais Google Maps (km) extraídas do Excel ─────────────────────
# Ordem: MuniqueXL, MadridXL, Coimbra, Saragoça, Blois, Milão, Nuremberga
DIST_FAB_CD = {
    "Felgueiras": [2293.0, 593.0, 169.0, 716.0, 1359.0, 2070.0, 2217.0],
    "Mangualde":  [2247.0, 480.0,  96.3, 670.0, 1312.0, 2024.0, 2170.0],
}
DIST_CLI_CD = {
    "Évora":             [2379.0,  564.0,  162.0,  789.0, 1450.0, 2127.0, 1918.0],
    "Faro":              [2571.0,  687.0,  412.0,  912.0, 1642.0, 2217.0, 2498.0],
    "Coimbra":           [2340.0,  572.0,   10.8,  764.0, 1410.0, 2102.0, 2264.0],
    "Santa Maria da Feira": [2358.0, 590.0, 96.6, 783.0, 1429.0, 2120.0, 2282.0],
    "Chaves":            [2205.0,  518.0,  244.0,  645.0, 1276.0, 1999.0, 2130.0],
    "Bragança":          [2120.0,  418.0,  289.0,  545.0, 1191.0, 1883.0, 2045.0],
    "Oviedo":            [2025.0,  536.0,  610.0,  576.0, 1096.0, 1703.0, 1950.0],
    "Toledo":            [2110.0,  131.0,  493.0,  356.0, 1181.0, 1694.0, 2034.0],
    "Valência":          [1959.0,  336.0,  880.0,  263.0, 1149.0, 1368.0, 1883.0],
    "Saragoça":          [1765.0,  257.0,  828.0,   54.3,  836.0, 1315.0, 1689.0],
    "Barcelona":         [1618.0,  563.0, 1134.0,  359.0,  899.0, 1027.0, 1542.0],
    "Toulouse":          [1369.0,  643.0, 1101.0,  442.0,  525.0,  916.0, 1294.0],
    "Limoges":           [1123.0,  860.0, 1244.0,  718.0,  227.0,  891.0, 1046.0],
    "Ródano":            [ 829.0, 1213.0, 1557.0, 1012.0,  333.0,  589.0,  754.0],
    "Le Mans":           [1076.0, 1039.0, 1420.0,  895.0,  108.0, 1022.0, 1003.0],
    "Milão":             [ 568.0, 1569.0, 2106.0, 1365.0,  904.0,   11.4,  621.0],
    "Verona":            [ 537.0, 1729.0, 2268.0, 1524.0, 1065.0,  146.0,  591.0],
    "Florença":          [ 785.0, 1767.0, 2304.0, 1676.0, 1216.0,  335.0,  839.0],
    "Munique":           [ 114.0, 1979.0, 2310.0, 1778.0,  953.0,  452.0,  168.0],
    "Frankfurt":         [ 323.0, 1743.0, 2124.0, 1599.0,  738.0,  731.0,  231.0],
    "Berlim":            [ 525.0, 2300.0, 2681.0, 2143.0, 1222.0, 1042.0,  457.0],
}

# Procuras do enunciado (×100 ton/ano)
PROCURAS_ENUNCIADO = {
    "Évora": 30, "Faro": 40, "Coimbra": 50, "Santa Maria da Feira": 20,
    "Chaves": 30, "Bragança": 10, "Oviedo": 25, "Toledo": 25,
    "Valência": 75, "Saragoça": 75, "Barcelona": 100, "Toulouse": 100,
    "Limoges": 100, "Ródano": 30, "Le Mans": 40, "Milão": 100,
    "Verona": 50, "Florença": 50, "Munique": 75, "Frankfurt": 50, "Berlim": 75,
}


def _dist_fab_cd(fab_nome: str, cd_id: int) -> float:
    """Distância Google Maps fábrica → CD."""
    row = DIST_FAB_CD.get(fab_nome)
    if row is None:
        # fallback haversine
        import math
        f = next(f for f in FABRICAS if f["nome"] == fab_nome)
        cd = CDS_CANDIDATOS[cd_id]
        R = 6371.0
        dlat = math.radians(cd["lat"] - f["lat"])
        dlon = math.radians(cd["lon"] - f["lon"])
        a = math.sin(dlat/2)**2 + math.cos(math.radians(f["lat"])) * math.cos(math.radians(cd["lat"])) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))
    return row[cd_id]


def _dist_cli_cd(cli_nome: str, cd_id: int, cli_lat: float = None, cli_lon: float = None) -> float:
    """Distância Google Maps cliente → CD."""
    nome_norm = cli_nome.strip()
    row = DIST_CLI_CD.get(nome_norm)
    if row is None:
        # Try case-insensitive exact match
        for k in DIST_CLI_CD:
            if k.lower() == nome_norm.lower():
                row = DIST_CLI_CD[k]
                break
    if row is None:
        # Try partial match (remove accents for comparison)
        import unicodedata
        def norm(s):
            return ''.join(c for c in unicodedata.normalize('NFD', s.lower())
                           if unicodedata.category(c) != 'Mn')
        nome_sem_acento = norm(nome_norm)
        for k in DIST_CLI_CD:
            if norm(k) == nome_sem_acento or norm(k) in nome_sem_acento or nome_sem_acento in norm(k):
                row = DIST_CLI_CD[k]
                break
    if row is None and cli_lat is not None:
        import math
        cd = CDS_CANDIDATOS[cd_id]
        R = 6371.0
        dlat = math.radians(cd["lat"] - cli_lat)
        dlon = math.radians(cd["lon"] - cli_lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(cli_lat)) * math.cos(math.radians(cd["lat"])) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))
    if row is None:
        return 1000.0  # fallback
    return row[cd_id]


def resolver_milp(
    df_clientes: pd.DataFrame,
    fabricas: list[dict] | None = None,
    cds_candidatos: list[dict] | None = None,
    custo_km: float = CUSTO_KM,
    cds_forcados: list[int] | None = None,
) -> dict:
    """
    Resolve o MILP de localização de CDs.
    Usa distâncias reais do Google Maps quando disponíveis.
    """
    if fabricas is None:
        fabricas = FABRICAS
    if cds_candidatos is None:
        cds_candidatos = CDS_CANDIDATOS

    I = len(fabricas)
    J = len(cds_candidatos)
    K = len(df_clientes)
    clientes = df_clientes.reset_index(drop=True).to_dict("records")

    # Custos de transporte usando distâncias reais
    c_fab_cd = np.zeros((I, J))
    for i, fab in enumerate(fabricas):
        for j, cd in enumerate(cds_candidatos):
            dist = _dist_fab_cd(fab["nome"], cd["id"] if "id" in cd else j)
            c_fab_cd[i, j] = dist * custo_km

    c_cd_cli = np.zeros((J, K))
    for j, cd in enumerate(cds_candidatos):
        for k, cli in enumerate(clientes):
            dist = _dist_cli_cd(
                cli["cidade"],
                cd["id"] if "id" in cd else j,
                cli.get("latitude"), cli.get("longitude")
            )
            c_cd_cli[j, k] = dist * custo_km

    c_fixo = np.array([cd["custo_fixo"] * 1000 for cd in cds_candidatos], dtype=float)

    # Índices
    n_x = I * J; n_z = J * K; n_y = J
    n_vars = n_x + n_z + n_y

    def idx_x(i, j): return i * J + j
    def idx_z(j, k): return n_x + j * K + k
    def idx_y(j):    return n_x + n_z + j

    # Função objectivo
    c_obj = np.zeros(n_vars)
    for i in range(I):
        for j in range(J):
            c_obj[idx_x(i, j)] = c_fab_cd[i, j]
    for j in range(J):
        for k in range(K):
            c_obj[idx_z(j, k)] = c_cd_cli[j, k]
    for j in range(J):
        c_obj[idx_y(j)] = c_fixo[j]

    lb = np.zeros(n_vars)
    ub = np.full(n_vars, np.inf)
    for j in range(J):
        ub[idx_y(j)] = 1.0
    for i in range(I):
        for j in range(J):
            ub[idx_x(i, j)] = fabricas[i]["cap"]

    if cds_forcados is not None:
        for j in range(J):
            if j in cds_forcados:
                lb[idx_y(j)] = 1.0; ub[idx_y(j)] = 1.0
            else:
                lb[idx_y(j)] = 0.0; ub[idx_y(j)] = 0.0

    bounds = Bounds(lb=lb, ub=ub)

    # Restrições
    A_rows, b_lo, b_hi = [], [], []

    # Cap fábricas
    for i in range(I):
        row = np.zeros(n_vars)
        for j in range(J):
            row[idx_x(i, j)] = 1.0
        A_rows.append(row); b_lo.append(-np.inf); b_hi.append(fabricas[i]["cap"])

    # Equilíbrio CDs
    for j in range(J):
        row = np.zeros(n_vars)
        for i in range(I): row[idx_x(i, j)] = 1.0
        for k in range(K): row[idx_z(j, k)] = -1.0
        A_rows.append(row); b_lo.append(0.0); b_hi.append(0.0)

    # Cap CDs (linearizada)
    for j in range(J):
        row = np.zeros(n_vars)
        for k in range(K): row[idx_z(j, k)] = 1.0
        row[idx_y(j)] = -cds_candidatos[j]["cap"]
        A_rows.append(row); b_lo.append(-np.inf); b_hi.append(0.0)

    # Satisfação da procura
    for k in range(K):
        row = np.zeros(n_vars)
        for j in range(J): row[idx_z(j, k)] = 1.0
        A_rows.append(row)
        b_lo.append(clientes[k]["procura"]); b_hi.append(np.inf)

    A = np.vstack(A_rows)
    constraints = LinearConstraint(A, b_lo, b_hi)

    # Resolver MILP real (igual ao Excel)
    integrality = np.zeros(n_vars)

    # x = integer
    for i in range(I):
        for j in range(J):
            integrality[idx_x(i, j)] = 1

    # z = integer
    for j in range(J):
        for k in range(K):
            integrality[idx_z(j, k)] = 1

    # y = binary
    for j in range(J):
        integrality[idx_y(j)] = 1

    res = milp(
        c=c_obj,
        integrality=integrality,
        bounds=bounds,
        constraints=constraints,
        options={
            "time_limit": 120,
            "presolve": True,
        }
    )

    if res.x is None:
        return {
            "status": "falhou",
            "message": str(res.message)
        }

    x_sol = res.x

    y_sol = np.array([
        round(x_sol[idx_y(j)])
        for j in range(J)
    ])

    cds_abertos = [
        cds_candidatos[j]
        for j in range(J)
        if y_sol[j] == 1
    ]

    fab_cd_rows = []
    for i in range(I):
        for j in range(J):
            v = round(x_sol[idx_x(i, j)])

            if v > 0:
                dist = _dist_fab_cd(
                    fabricas[i]["nome"],
                    cds_candidatos[j].get("id", j)
                )
                fab_cd_rows.append({
                    "Fábrica": fabricas[i]["nome"],
                    "CD": cds_candidatos[j]["nome"],
                    "Fluxo": v,
                    "Distância (km)": dist,
                    "Custo transp. (k€)": round(dist * v * custo_km / 1000, 2),
                })

    cd_cli_rows = []
    for j in range(J):
        for k in range(K):
            v = round(x_sol[idx_z(j, k)])
            if v > 0:
                dist = _dist_cli_cd(clientes[k]["cidade"], cds_candidatos[j].get("id", j),
                                    clientes[k].get("latitude"), clientes[k].get("longitude"))
                cd_cli_rows.append({
                    "CD": cds_candidatos[j]["nome"], "Cliente": clientes[k]["cidade"],
                    "País": clientes[k]["pais"], "Fluxo": v,
                    "Distância (km)": dist,
                    "Custo transp. (k€)": round(dist * v * custo_km / 1000, 2),
                })

    # Recalcular custos com y já arredondados (não usar res.fun da LP relaxada)
    custo_fixo_total = sum(cds_candidatos[j]["custo_fixo"] * 1000 * int(y_sol[j]) for j in range(J))
    
    # Custo de transporte = soma directa dos fluxos × distâncias × custo_km
    custo_transp_fab = sum(r["Custo transp. (k€)"] * 1000 for r in fab_cd_rows)
    custo_transp_cli = sum(r["Custo transp. (k€)"] * 1000 for r in cd_cli_rows)
    custo_transp_total = custo_transp_fab + custo_transp_cli
    custo_total = custo_transp_total + custo_fixo_total

    return {
        "status": "ok", "message": str(res.message),
        "cds_abertos": cds_abertos, "y": y_sol,
        "fab_cd": pd.DataFrame(fab_cd_rows),
        "cd_cli": pd.DataFrame(cd_cli_rows),
        "custo_transporte": round(custo_transp_total, 0),
        "custo_fixo": round(custo_fixo_total, 0),
        "custo_total": round(custo_total, 0),
    }


def gerar_instancia(
    df_base: pd.DataFrame,
    caps_cd: dict[str, float],
    ratio: float,
    variacao: float,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Gera instância respeitando caps por CD (como o VBA)."""
    df = df_base.copy()

    def cd_mais_proximo(cidade, lat, lon):
        import math
        dists = DIST_CLI_CD.get(cidade.strip())
        if dists:
            j = int(np.argmin(dists))
            return CDS_CANDIDATOS[j]["nome"]
        # fallback haversine
        best = min(CDS_CANDIDATOS, key=lambda cd: (
            (cd["lat"] - lat)**2 + (cd["lon"] - lon)**2
        ))
        return best["nome"]

    df["_cd"] = df.apply(lambda r: cd_mais_proximo(r["cidade"], r["latitude"], r["longitude"]), axis=1)

    novos = []
    for cd_nome, grupo in df.groupby("_cd"):
        cap = caps_cd.get(cd_nome, float("inf"))
        noise = rng.uniform(1 - variacao, 1 + variacao, size=len(grupo))
        procuras_raw = (grupo["procura"].values * ratio * noise).clip(min=1.0)
        soma = procuras_raw.sum()
        if soma > cap:
            procuras_raw = procuras_raw * (cap / soma)
        grupo = grupo.copy()
        grupo["procura"] = procuras_raw.round(1)
        novos.append(grupo)

    df_result = pd.concat(novos).sort_values("id").reset_index(drop=True)
    return df_result.drop(columns=["_cd"])