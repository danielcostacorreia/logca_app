from __future__ import annotations
import pandas as pd


CRITERIOS = [
    {"grupo": "Acessibilidade", "nome": "Distância euclidiana ao centroide (ponto ideal)", "tipo": "numerico", "sentido": "inversa", "peso": 0.14, "unidade": "km"},
    {"grupo": "Acessibilidade", "nome": "Distância à zona industrial", "tipo": "numerico", "sentido": "inversa", "peso": 0.06, "unidade": "escala 1-9"},
    {"grupo": "Acessibilidade", "nome": "Tempo de acesso ao porto marítimo mais próximo (min)", "tipo": "numerico", "sentido": "inversa", "peso": 0.05, "unidade": "min"},
    {"grupo": "Acessibilidade", "nome": "Tempo de acesso ao aeroporto mais próximo (min)", "tipo": "numerico", "sentido": "inversa", "peso": 0.04, "unidade": "min"},
    {"grupo": "Acessibilidade", "nome": "Tempo de acesso à estação ferroviária mais próxima (min)", "tipo": "numerico", "sentido": "inversa", "peso": 0.05, "unidade": "min"},
    {"grupo": "Acessibilidade", "nome": "Proximidade centro urbano mais próximo", "tipo": "numerico", "sentido": "direta", "peso": 0.04, "unidade": "escala 1-9"},
    {"grupo": "Acessibilidade", "nome": "Qualidade da rede de transportes públicos", "tipo": "numerico", "sentido": "direta", "peso": 0.04, "unidade": "escala 1-9"},

    {"grupo": "Custos", "nome": "Custo de instalação (€M)", "tipo": "numerico", "sentido": "inversa", "peso": 0.12, "unidade": "M€"},
    {"grupo": "Custos", "nome": "Custo terreno (€/m2)", "tipo": "numerico", "sentido": "inversa", "peso": 0.10, "unidade": "€/m²"},
    {"grupo": "Custos", "nome": "Salário médios na área (€/mês)", "tipo": "numerico", "sentido": "inversa", "peso": 0.07, "unidade": "€/mês"},
    {"grupo": "Custos", "nome": "Incentivos camarários (%)", "tipo": "numerico", "sentido": "direta", "peso": 0.07, "unidade": "%"},

    {"grupo": "Recursos", "nome": "Mão de obra qualificada", "tipo": "numerico", "sentido": "direta", "peso": 0.10, "unidade": "escala 1-9"},
    {"grupo": "Recursos", "nome": "Existência de serviços de apoio", "tipo": "numerico", "sentido": "direta", "peso": 0.06, "unidade": "escala 1-9"},
    {"grupo": "Recursos", "nome": "Área disponível (m2)", "tipo": "numerico", "sentido": "direta", "peso": 0.06, "unidade": "m²"},
]


def alternativas_iniciais() -> list[dict]:
    return []


def valor_padrao(criterio: dict):
    return 0.0


def construir_df_alternativas(alternativas: list[dict]) -> pd.DataFrame:
    rows = []

    for alt in alternativas:
        row = {
            "Nome": alt["nome"],
            "Localização": alt["localizacao"],
            "Notas": alt["nota"],
        }

        for crit in CRITERIOS:
            row[crit["nome"]] = alt["valores"].get(crit["nome"], valor_padrao(crit))

        rows.append(row)

    return pd.DataFrame(rows)


def obter_tabela_criterios() -> pd.DataFrame:
    df = pd.DataFrame(CRITERIOS)
    df["peso_percentual"] = (df["peso"] * 100).round(0).astype(int).astype(str) + "%"

    return df[["grupo", "nome", "sentido", "peso_percentual", "unidade"]].rename(
        columns={
            "grupo": "Grupo",
            "nome": "Critério",
            "sentido": "Sentido",
            "peso_percentual": "Peso",
            "unidade": "Unidade",
        }
    )


def colunas_importacao_esperadas() -> list[str]:
    return ["Nome", "Localização", "Notas"] + [c["nome"] for c in CRITERIOS]


def validar_df_importacao(df: pd.DataFrame) -> None:
    colunas_esperadas = colunas_importacao_esperadas()
    em_falta = [c for c in colunas_esperadas if c not in df.columns]

    if em_falta:
        raise ValueError(f"Faltam colunas no ficheiro importado: {em_falta}")

    if df["Nome"].astype(str).str.strip().eq("").any():
        raise ValueError("Existem alternativas sem Nome.")

    if df["Localização"].astype(str).str.strip().eq("").any():
        raise ValueError("Existem alternativas sem Localização.")

    for crit in CRITERIOS:
        nome = crit["nome"]
        serie = pd.to_numeric(df[nome], errors="coerce")

        if serie.isna().any():
            raise ValueError(f"O critério numérico '{nome}' tem valores não numéricos ou vazios.")

        if (serie < 0).any():
            raise ValueError(f"O critério numérico '{nome}' contém valores negativos.")


def importar_alternativas_de_df(df: pd.DataFrame) -> list[dict]:
    validar_df_importacao(df)

    alternativas = []

    for _, row in df.iterrows():
        alt = {
            "nome": str(row["Nome"]).strip(),
            "localizacao": str(row["Localização"]).strip(),
            "nota": "" if pd.isna(row["Notas"]) else str(row["Notas"]).strip(),
            "valores": {},
        }

        for crit in CRITERIOS:
            nome_crit = crit["nome"]
            alt["valores"][nome_crit] = float(row[nome_crit])

        alternativas.append(alt)

    return alternativas


def calcular_score_criterio(col: pd.Series, sentido: str, nome: str) -> pd.Series:
    col = pd.to_numeric(col, errors="coerce").astype(float)

    if sentido == "direta":
        melhor = col.max()
        if melhor == 0:
            return pd.Series(0.0, index=col.index)
        score = 9 * (col / melhor)

    else:  # inversa
        if (col == 0).any():
            raise ValueError(
                f"O critério '{nome}' contém zero e não pode ser usado com proporcionalidade inversa."
            )
        melhor = col.min()
        score = 9 * (melhor / col)

    return score.clip(0, 9)


def calcular_scores(alternativas: list[dict]) -> pd.DataFrame:
    if not alternativas:
        return pd.DataFrame()

    df = construir_df_alternativas(alternativas).copy()

    df_scores = df[["Nome", "Localização"]].copy()
    total = pd.Series(0.0, index=df.index)

    for crit in CRITERIOS:
        nome = crit["nome"]
        peso = crit["peso"]
        sentido = crit["sentido"]

        score = calcular_score_criterio(df[nome], sentido, nome)

        total += score * peso
        df_scores[f"Score - {nome}"] = score.round(2)

    df_scores["Score Final"] = total.round(4)

    return df_scores.sort_values("Score Final", ascending=False).reset_index(drop=True)


def calcular_scores_multiplicativo(alternativas: list[dict]) -> pd.DataFrame:
    """Método multiplicativo — produto ponderado dos scores normalizados."""
    if not alternativas:
        return pd.DataFrame()

    df = construir_df_alternativas(alternativas).copy()
    df_scores = df[["Nome", "Localização"]].copy()
    # Score multiplicativo: produto de (score_i ^ peso_i)
    total = pd.Series(1.0, index=df.index)

    for crit in CRITERIOS:
        nome    = crit["nome"]
        peso    = crit["peso"]
        sentido = crit["sentido"]
        score   = calcular_score_criterio(df[nome], sentido, nome)
        # Evitar zero (score mínimo = 0.001)
        score_clipped = score.clip(lower=0.001)
        total *= (score_clipped ** peso)
        df_scores[f"Score - {nome}"] = score.round(2)

    df_scores["Score Final (Mult.)"] = total.round(4)
    return df_scores.sort_values("Score Final (Mult.)", ascending=False).reset_index(drop=True)


def obter_scores_por_criterio(alternativas: list[dict]) -> pd.DataFrame:
    if not alternativas:
        return pd.DataFrame()

    df = construir_df_alternativas(alternativas).copy()
    df_scores = df[["Nome", "Localização"]].copy()

    for crit in CRITERIOS:
        nome = crit["nome"]
        sentido = crit["sentido"]

        score = calcular_score_criterio(df[nome], sentido, nome)
        df_scores[nome] = score.round(2)

    return df_scores