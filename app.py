import math
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

from solver.load_data import load_clientes_csv
from solver.alinea_11 import (
    validar_clientes,
    calcular_solver_por_pais,
    cidade_mais_proxima
)
from solver.alinea_12_alternativas import (
    CRITERIOS,
    alternativas_iniciais,
    obter_tabela_criterios,
    calcular_scores,
    calcular_scores_multiplicativo,
    obter_scores_por_criterio,
    colunas_importacao_esperadas,
    importar_alternativas_de_df,
)
from solver.alinea_12_milp import (
    resolver_milp,
    gerar_instancia,
    CDS_CANDIDATOS,
    CDS_OPCAO_A as MILP_CDS_A,
    CDS_OPCAO_B as MILP_CDS_B,
    FABRICAS as FABRICAS_MILP,
    CUSTO_KM as CUSTO_KM_MILP,
)

st.set_page_config(
    page_title="LOGCA — Rede de Distribuição",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* ── Hide default streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0f1117;
    border-right: 1px solid #1e2130;
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stRadio label {
    font-size: 0.9rem;
    padding: 0.35rem 0;
    transition: color 0.15s;
}
[data-testid="stSidebar"] .stRadio label:hover { color: #60a5fa !important; }

/* ── Page header ── */
.logca-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #0f172a 100%);
    border-radius: 12px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    border: 1px solid #1e3a5f;
    position: relative;
    overflow: hidden;
}
.logca-header::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, #1d4ed840 0%, transparent 70%);
    border-radius: 50%;
}
.logca-header::after {
    content: '';
    position: absolute;
    bottom: -30px; left: 30%;
    width: 300px; height: 150px;
    background: radial-gradient(ellipse, #0ea5e920 0%, transparent 70%);
}
.logca-header h1 {
    font-size: 1.7rem;
    font-weight: 600;
    color: #f1f5f9;
    margin: 0 0 0.3rem 0;
    letter-spacing: -0.02em;
    position: relative;
    z-index: 1;
}
.logca-header .subtitle {
    color: #64748b;
    font-size: 0.85rem;
    font-family: 'DM Mono', monospace;
    position: relative;
    z-index: 1;
}
.logca-header .badges {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
    flex-wrap: wrap;
    position: relative;
    z-index: 1;
}
.badge {
    background: #1e3a5f;
    color: #93c5fd;
    font-size: 0.72rem;
    font-family: 'DM Mono', monospace;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    border: 1px solid #2563eb30;
    letter-spacing: 0.03em;
}
.badge.green { background: #14532d; color: #86efac; border-color: #16a34a30; }
.badge.amber { background: #451a03; color: #fcd34d; border-color: #d9770630; }

/* ── Section title ── */
.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 0.5rem 0 1rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #1e2130;
    letter-spacing: -0.01em;
}

/* ── Cards ── */
.stat-card {
    background: #0f1117;
    border: 1px solid #1e2130;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    transition: border-color 0.2s;
}
.stat-card:hover { border-color: #2563eb50; }
.stat-card .label {
    font-size: 0.75rem;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
    font-family: 'DM Mono', monospace;
}
.stat-card .value {
    font-size: 1.4rem;
    font-weight: 600;
    color: #f1f5f9;
    font-family: 'DM Mono', monospace;
}
.stat-card .value.blue { color: #60a5fa; }
.stat-card .value.green { color: #4ade80; }
.stat-card .value.amber { color: #fbbf24; }

/* ── Metric overrides ── */
[data-testid="metric-container"] {
    background: #0f1117;
    border: 1px solid #1e2130;
    border-radius: 10px;
    padding: 1rem 1.25rem;
}
[data-testid="metric-container"] label {
    font-size: 0.75rem !important;
    color: #475569 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-family: 'DM Mono', monospace;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.3rem !important;
    font-family: 'DM Mono', monospace;
    color: #f1f5f9 !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 8px;
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    font-size: 0.875rem;
    transition: all 0.15s ease;
}
.stButton > button[kind="primary"] {
    background: #2563eb;
    border: none;
}
.stButton > button[kind="primary"]:hover {
    background: #1d4ed8;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px #2563eb40;
}

/* ── Tabs ── */
[data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 1px solid #1e2130;
    gap: 0;
}
[data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.85rem;
    font-weight: 500;
    color: #475569;
    padding: 0.6rem 1.2rem;
    border-radius: 6px 6px 0 0;
    border: none !important;
    background: transparent !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #60a5fa !important;
    border-bottom: 2px solid #2563eb !important;
    background: #0f111720 !important;
}

/* ── Dataframes ── */
[data-testid="stDataFrame"] {
    border: 1px solid #1e2130 !important;
    border-radius: 8px;
    overflow: hidden;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    border: 1px solid #1e2130 !important;
    border-radius: 8px !important;
    background: #0f1117 !important;
}

/* ── Info / warning boxes ── */
[data-testid="stAlert"] {
    border-radius: 8px;
    font-size: 0.875rem;
}

/* ── Divider ── */
hr { border-color: #1e2130 !important; }

/* ── Progress bar ── */
[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #2563eb, #0ea5e9) !important;
    border-radius: 999px;
}

/* Separador Armazem no radio (6o item) */
[data-testid="stSidebar"] .stRadio label:nth-of-type(6) {
    margin-top: 1.4rem !important;
    padding-top: 1.2rem !important;
    border-top: 1px solid #1e2a3a !important;
    position: relative;
}
[data-testid="stSidebar"] .stRadio label:nth-of-type(6)::before {
    content: 'Armazem';
    display: block;
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #2563eb;
    font-family: 'DM Mono', monospace;
    margin-bottom: 0.5rem;
    margin-top: -0.8rem;
}
/* Separador Roteamento (7o item) */
[data-testid="stSidebar"] .stRadio label:nth-of-type(7) {
    margin-top: 1.4rem !important;
    padding-top: 1.2rem !important;
    border-top: 1px solid #1e2a3a !important;
    position: relative;
}
[data-testid="stSidebar"] .stRadio label:nth-of-type(7)::before {
    content: 'Roteamento';
    display: block;
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #2563eb;
    font-family: 'DM Mono', monospace;
    margin-bottom: 0.5rem;
    margin-top: -0.8rem;
}

/* ── Sidebar redesign ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #0f1a2e 100%) !important;
    border-right: 1px solid #1e2a3a !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding: 1.5rem 1rem 1rem 1rem !important;
}
/* Fix collapse button so it's always visible */
[data-testid="collapsedControl"] {
    color: #60a5fa !important;
    background: #0f1a2e !important;
    border: 1px solid #1e2a3a !important;
    border-radius: 0 8px 8px 0 !important;
}
.nav-brand {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 1.8rem;
    padding-bottom: 1.2rem;
    border-bottom: 1px solid #1e2a3a;
}
.nav-brand-icon {
    width: 34px; height: 34px;
    background: linear-gradient(135deg, #2563eb, #0ea5e9);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; font-weight: 700; color: white;
    flex-shrink: 0;
}
.nav-brand-text {
    line-height: 1.2;
}
.nav-brand-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: -0.01em;
}
.nav-brand-sub {
    font-size: 0.68rem;
    color: #475569;
    font-family: 'DM Mono', monospace;
}
.nav-section {
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #2563eb;
    font-family: 'DM Mono', monospace;
    margin: 1.2rem 0 0.5rem 0;
    padding-left: 0.1rem;
}
.nav-footer {
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid #1e2a3a;
    font-size: 0.68rem;
    color: #334155;
    font-family: 'DM Mono', monospace;
    line-height: 1.8;
}
</style>
""", unsafe_allow_html=True)

# ── Page header ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="logca-header">
    <h1>LOGCA — Rede de Distribuição</h1>
    <div class="subtitle">ISEP · Logística e Gestão da Cadeia de Abastecimento · 2025/26</div>
    <div class="badges">
        <span class="badge"> Localização</span>
        <span class="badge">Modelo MILP</span>
        <span class="badge">Scipy · Plotly · Streamlit</span>
    </div>
</div>
""", unsafe_allow_html=True)


def preparar_df_base(df_inicial: pd.DataFrame) -> pd.DataFrame:
    df = df_inicial.copy()

    df["id"] = pd.to_numeric(df["id"], errors="raise").astype(int)
    df["cidade"] = df["cidade"].astype(str)
    df["pais"] = df["pais"].astype(str)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="raise")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="raise")
    df["procura"] = pd.to_numeric(df["procura"], errors="raise")

    return df


def inicializar_dados_localizacao(df_inicial: pd.DataFrame) -> None:
    if "df_localizacao_original" not in st.session_state:
        st.session_state["df_localizacao_original"] = preparar_df_base(df_inicial)

    if "df_localizacao_editado" not in st.session_state:
        st.session_state["df_localizacao_editado"] = preparar_df_base(df_inicial)


def reset_dados_localizacao() -> None:
    st.session_state["df_localizacao_editado"] = st.session_state["df_localizacao_original"].copy()

    if "resultado_solver_localizacao" in st.session_state:
        del st.session_state["resultado_solver_localizacao"]

    if "resultado_final_localizacao" in st.session_state:
        del st.session_state["resultado_final_localizacao"]


# ── Sidebar brand ────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<div class="nav-brand">'
    '<div class="nav-brand-icon">L</div>'
    '<div class="nav-brand-text">'
    '<div class="nav-brand-title">LOGCA 25/26</div>'
    '<div class="nav-brand-sub">ISEP · MEGI</div>'
    '</div></div>',
    unsafe_allow_html=True
)

# ── Navegação -- radio unico ─────────────────────────────────────────────────
MODULOS = [
    "Visão Geral",
    "Localização dos Armazéns",
    "Avaliação de Alternativas",
    "Desenho da Rede de Distribuição",
    "Geração de Instâncias",
    "Dimensionamento do Armazém",
    "Roteamento Ibérico",
]

st.sidebar.markdown('<div class="nav-section">Rede de Distribuição</div>', unsafe_allow_html=True)
secao = st.sidebar.radio(
    "",
    MODULOS,
    label_visibility="collapsed",
    key="nav_main"
)

# ── Footer ────────────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<div class="nav-footer">'
    'Elaborado por<br>'
    'Ana Ressurreição · 1211276<br>'
    'Bebiana Santos · 1201130<br>'
    'Daniel Correia · 1250363<br>'
    'Nuno Mesquita · 1190311'
    '</div>',
    unsafe_allow_html=True
)

if secao == "Visão Geral":
    st.markdown('<div class="section-title">Visão Geral da Plataforma</div>', unsafe_allow_html=True)

    col_intro, col_estado = st.columns([3, 2])

    with col_intro:
        st.markdown(
            "Plataforma de suporte à **definição e optimização da cadeia de abastecimento** "
            "de uma empresa com unidades produtivas em **Felgueiras** e **Mangualde**, "
            "que distribui nos mercados de Portugal, Espanha, França, Itália e Alemanha."
        )
        st.markdown("")
        st.markdown(
            "A plataforma integra modelos de **localização de armazéns** (centro de gravidade), "
            "**avaliação multicritério** de zonas industriais, **optimização MILP** da rede de "
            "distribuição com 7 CDs candidatos, **geração de instâncias** para análise de "
            "cenários e **dimensionamento do armazém** com previsão de procura (Holt-Winters)."
        )

    with col_estado:
        st.markdown('<div class="section-title">Módulos disponíveis</div>', unsafe_allow_html=True)
        modulos = [
            ("Localização dos Armazéns",      "Centro de gravidade + Nelder-Mead"),
            ("Avaliação de Alternativas",      "Modelo multicritério ponderado"),
            ("Desenho da Rede de Distribuição","MILP — 7 CDs candidatos"),
            ("Geração de Instâncias",          "Variação de procura e capacidades"),
            ("Dimensionamento do Armazém",     "Holt-Winters + análise de custos"),
        ]
        for nome, desc in modulos:
            st.markdown(
                f'<div class="stat-card" style="margin-bottom:0.4rem;padding:0.55rem 0.85rem">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<div>'
                f'<div style="font-size:0.85rem;color:#e2e8f0;font-weight:500">{nome}</div>'
                f'<div style="font-size:0.72rem;color:#475569;margin-top:0.1rem">{desc}</div>'
                f'</div>'
                f'<span style="font-size:0.7rem;color:#22c55e;margin-left:0.5rem;white-space:nowrap">✅</span>'
                f'</div></div>',
                unsafe_allow_html=True
            )

    st.markdown("---")
    st.markdown('<div class="section-title">Dados do problema</div>', unsafe_allow_html=True)
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    dados = [
        ("Fábricas", "2", "Felgueiras + Mangualde", "blue"),
        ("Clientes", "21", "5 mercados europeus", "blue"),
        ("CDs candidatos", "7", "Livres — solver decide", "blue"),
        ("Cap. produção", "1 700", "×100 ton/ano total", "amber"),
    ]
    for col, (label, value, sub, cor) in zip([col_d1, col_d2, col_d3, col_d4], dados):
        col.markdown(
            f'<div class="stat-card">'
            f'<div class="label">{label}</div>'
            f'<div class="value {cor}">{value}</div>'
            f'<div style="font-size:0.75rem;color:#475569;margin-top:0.25rem">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

elif secao == "Localização dos Armazéns":
    st.markdown('<div class="section-title">Localização dos Armazéns — Alínea 1.1</div>', unsafe_allow_html=True)

    col_desc, col_info = st.columns([2, 1])
    with col_desc:
        st.markdown(
            "Determina a **localização óptima** de um armazém por mercado usando o "
            "**método do centro de gravidade** ponderado pela procura, seguido de "
            "optimização Nelder-Mead. O resultado é o ponto contínuo óptimo e a "
            "cidade mais próxima desse ponto."
        )
    with col_info:
        st.markdown(
            '<div class="stat-card"><div class="label">Método</div>'
            '<div style="font-size:0.85rem;color:#e2e8f0">Centro de gravidade<br>'
            'Nelder-Mead (scipy)</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    col_fonte_1, col_fonte_2 = st.columns([1, 2])
    with col_fonte_1:
        usar_upload = st.checkbox("Carregar ficheiro manualmente", value=False)

    default_path = "data/clientes_logca.csv"
    df = None

    try:
        if usar_upload:
            uploaded_file = st.file_uploader(
                "Selecionar ficheiro CSV",
                type=["csv"],
                key="upload_localizacao"
            )
            if uploaded_file is not None:
                df = pd.read_csv(uploaded_file)
                df.columns = [c.strip().lower() for c in df.columns]
        else:
            df = load_clientes_csv(default_path)

        if df is not None:
            df = preparar_df_base(df)
            validar_clientes(df)

    except Exception as e:
        st.error(f"Erro ao carregar ou validar os dados: {e}")
        st.stop()

    if df is None:
        st.info("Seleciona ou carrega um ficheiro CSV para continuar.")
        st.stop()
    ambito_localizacao = st.radio(
        "Âmbito da análise",
        ["Todos os mercados", "Mercado Ibérico"],
        horizontal=True,
        key="ambito_localizacao"
    )                                       
    inicializar_dados_localizacao(df)

    col_ctrl_1, col_ctrl_2, col_ctrl_3 = st.columns([1, 1, 4])

    with col_ctrl_1:
        if st.button("Repor dados originais"):
            reset_dados_localizacao()
            st.success("Os dados foram repostos para o estado original.")

    with col_ctrl_2:
        mostrar_resumo_base = st.checkbox("Mostrar resumo", value=True)

    st.markdown("### Adicionar novo cliente")

    with st.expander("Inserir novo cliente"):
        col1, col2, col3 = st.columns(3)

        with col1:
            novo_id = st.number_input("ID", min_value=1, step=1, value=100, key="novo_id")
            nova_cidade = st.text_input("Cidade", key="nova_cidade")

        with col2:
            novo_pais = st.selectbox(
                "País",
                ["Portugal", "Espanha", "Franca", "Italia", "Alemanha"],
                key="novo_pais"
            )
            nova_latitude = st.number_input("Latitude", format="%.6f", key="nova_latitude")

        with col3:
            nova_longitude = st.number_input("Longitude", format="%.6f", key="nova_longitude")
            nova_procura = st.number_input("Procura", min_value=0.0, step=1.0, value=0.0, key="nova_procura")

        if st.button("Adicionar cliente"):
            df_atual = st.session_state["df_localizacao_editado"].copy()

            novo_cliente = pd.DataFrame(
                [
                    {
                        "id": int(novo_id),
                        "cidade": nova_cidade.strip(),
                        "pais": novo_pais,
                        "latitude": float(nova_latitude),
                        "longitude": float(nova_longitude),
                        "procura": float(nova_procura),
                    }
                ]
            )

            if nova_cidade.strip() == "":
                st.error("A cidade é obrigatória.")
            elif int(novo_id) in df_atual["id"].values:
                st.error("Já existe um cliente com esse ID.")
            else:
                df_atual = pd.concat([df_atual, novo_cliente], ignore_index=True)
                st.session_state["df_localizacao_editado"] = preparar_df_base(df_atual)
                st.success("Cliente adicionado com sucesso.")

    st.markdown("### Dados de entrada")
    st.write(
        "As localizações base dos clientes são mantidas fixas. "
        "Apenas a procura pode ser alterada diretamente."
    )

    df_editor = st.session_state["df_localizacao_editado"].copy()

    df_editado = st.data_editor(
        df_editor,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=["id", "cidade", "pais", "latitude", "longitude"],
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "cidade": st.column_config.TextColumn("Cidade", disabled=True),
            "pais": st.column_config.TextColumn("País", disabled=True),
            "latitude": st.column_config.NumberColumn("Latitude", format="%.6f", disabled=True),
            "longitude": st.column_config.NumberColumn("Longitude", format="%.6f", disabled=True),
            "procura": st.column_config.NumberColumn("Procura", min_value=0.0, step=1.0),
        },
        key="editor_localizacao"
    )

    st.session_state["df_localizacao_editado"] = preparar_df_base(df_editado)
    df_modelo_localizacao = st.session_state["df_localizacao_editado"].copy()
    
    if ambito_localizacao == "Mercado Ibérico":
        df_modelo_localizacao = df_modelo_localizacao[
            df_modelo_localizacao["pais"].isin(["Portugal", "Espanha"])
        ].copy()

    try:
        validar_clientes(st.session_state["df_localizacao_editado"])
        dados_validos = True
    except Exception as e:
        st.error(f"Erro de validação: {e}")
        dados_validos = False

    if mostrar_resumo_base:
        resumo = (
            df_modelo_localizacao
            .groupby("pais", as_index=False)
            .agg(n_clientes=("id","count"), procura_total=("procura","sum"))
            .sort_values("pais")
        )
        # Mini cards por país em vez de tabela
        cols_resumo = st.columns(len(resumo))
        pais_emoji = {"Portugal":"🇵🇹","Espanha":"🇪🇸","Franca":"🇫🇷","Italia":"🇮🇹","Alemanha":"🇩🇪"}
        for col, (_, r) in zip(cols_resumo, resumo.iterrows()):
            col.markdown(
                f'<div class="stat-card" style="text-align:center;padding:0.6rem">' +
                f'<div style="font-size:1.1rem">{pais_emoji.get(r["pais"],"🌍")}</div>' +
                f'<div style="font-size:0.75rem;color:#e2e8f0;font-weight:500">{r["pais"]}</div>' +
                f'<div style="font-size:0.7rem;color:#475569">{int(r["n_clientes"])} clientes</div>' +
                f'<div style="font-size:0.85rem;color:#60a5fa;font-family:DM Mono,monospace">{r["procura_total"]:.0f}</div>' +
                f'</div>',
                unsafe_allow_html=True
            )

    executar = st.button("▶ Calcular localização óptima", type="primary", disabled=not dados_validos)

    if executar:
        df_modelo = df_modelo_localizacao.copy()
        resultado_solver = calcular_solver_por_pais(df_modelo)
        resultado_final = cidade_mais_proxima(df_modelo, resultado_solver)

        st.session_state["resultado_solver_localizacao"] = resultado_solver.copy()
        st.session_state["resultado_final_localizacao"] = resultado_final.copy()

    if "resultado_final_localizacao" in st.session_state:
        df_res = st.session_state["resultado_final_localizacao"]
        df_sol = st.session_state.get("resultado_solver_localizacao")

        st.markdown("---")
        st.markdown("### Resultado — Localização óptima por mercado")

        # Cards por país
        paises_ordem = ["Portugal","Espanha","Franca","Italia","Alemanha"]
        pais_emoji   = {"Portugal":"🇵🇹","Espanha":"🇪🇸","Franca":"🇫🇷","Italia":"🇮🇹","Alemanha":"🇩🇪"}
        cores_pais   = {"Portugal":"#2563eb","Espanha":"#dc2626","Franca":"#0ea5e9","Italia":"#10b981","Alemanha":"#f59e0b"}

        cols_res = st.columns(len(df_res))
        for col, (_, row) in zip(cols_res, df_res.iterrows()):
            pais    = row.get("pais", "")
            cidade  = row.get("cidade_escolhida", "—")
            lat     = row.get("latitude_otima", "")
            lon     = row.get("longitude_otima", "")
            lat_c   = row.get("latitude_cidade", lat)
            lon_c   = row.get("longitude_cidade", lon)
            cor     = cores_pais.get(pais, "#2563eb")
            emoji   = pais_emoji.get(pais, "🌍")
            gmaps   = f"https://www.google.com/maps?q={lat_c},{lon_c}"
            try:
                coord_str = f"{float(lat):.4f}° N  {float(lon):.4f}° W"
            except (ValueError, TypeError):
                coord_str = ""
            col.markdown(
                f'<div style="border:1px solid {cor}40;border-radius:10px;padding:0.9rem 0.8rem;'
                f'background:linear-gradient(135deg,{cor}15,transparent);margin-bottom:0.3rem">'
                f'<div style="font-size:0.7rem;color:{cor};font-family:DM Mono,monospace;'
                f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.3rem">'
                f'{emoji} {pais}</div>'
                f'<div style="font-size:1.1rem;font-weight:600;color:#f1f5f9;line-height:1.2;margin-bottom:0.3rem">'
                f'{cidade}</div>'
                f'<div style="font-size:0.68rem;color:#475569;font-family:DM Mono,monospace;margin-bottom:0.4rem">'
                f'{coord_str}</div>'
                f'<a href="{gmaps}" target="_blank" style="font-size:0.68rem;color:{cor};'
                f'text-decoration:none;border:1px solid {cor}50;border-radius:4px;'
                f'padding:0.15rem 0.5rem">📍 Google Maps</a>'
                f'</div>',
                unsafe_allow_html=True
            )

        # Mapa com os resultados
        if df_sol is not None:
            st.markdown("**Mapa — pontos óptimos e cidades seleccionadas**")
            fig_loc = go.Figure()
            # Clientes por país
            df_cli = df_modelo_localizacao
            for pais in paises_ordem:
                grupo = df_cli[df_cli["pais"] == pais]
                if grupo.empty: continue
                cor = cores_pais.get(pais, "#94a3b8")
                fig_loc.add_trace(go.Scattergeo(
                    lat=grupo["latitude"], lon=grupo["longitude"],
                    text=grupo["cidade"], mode="markers",
                    marker=dict(size=6, color=cor, opacity=0.5),
                    name=f"Clientes {pais}", showlegend=True
                ))
            # Pontos óptimos
            for _, row in df_sol.iterrows():
                pais = row.get("pais","")
                cor = cores_pais.get(pais, "#ffffff")
                fig_loc.add_trace(go.Scattergeo(
                    lat=[row.get("latitude_otima", "")],
                    lon=[row.get("longitude_otima", "")],
                    text=[f"Ótimo {pais}"], mode="markers",
                    marker=dict(size=12, color=cor, symbol="star", line=dict(color="white", width=1)),
                    showlegend=False
                ))
            # Cidades discretizadas
            for _, row in df_res.iterrows():
                pais = row.get("pais","")
                cor = cores_pais.get(pais, "#ffffff")
                cidade = row.get("cidade_escolhida", "")
                lat = row.get("latitude_otima", "")
                lon = row.get("longitude_otima", "")
                fig_loc.add_trace(go.Scattergeo(
                    lat=[lat], lon=[lon], text=[cidade],
                    mode="markers+text", textposition="top center",
                    marker=dict(size=14, color=cor, symbol="diamond",
                                line=dict(color="white", width=1.5)),
                    showlegend=False
                ))
            fig_loc.update_layout(
                geo=dict(scope="europe", projection_type="mercator",
                         showland=True, landcolor="rgb(240,240,230)",
                         showocean=True, oceancolor="rgb(210,230,245)",
                         showcountries=True, countrycolor="rgb(200,200,200)",
                         lonaxis=dict(range=[-12, 22]), lataxis=dict(range=[35, 57])),
                height=420, margin=dict(l=0,r=0,t=10,b=0),
                legend=dict(orientation="h", y=-0.05, font=dict(size=10)),
                plot_bgcolor="#0f1117", paper_bgcolor="#0f1117",
            )
            st.plotly_chart(fig_loc, use_container_width=True)

        # Resumo compacto por país (tabela pequena)
        with st.expander("Ver detalhes completos", expanded=False):
            st.markdown("**Modelo contínuo (solver)**")
            if df_sol is not None:
                st.dataframe(df_sol, use_container_width=True, hide_index=True)
            st.markdown("**Resultado discretizado**")
            st.dataframe(df_res, use_container_width=True, hide_index=True)
            st.markdown("**Clientes considerados**")
            st.dataframe(
                st.session_state["df_localizacao_editado"].sort_values(["pais","cidade"]),
                use_container_width=True, hide_index=True
            )

elif secao == "Avaliação de Alternativas":
    st.markdown('<div class="section-title">Avaliação de Alternativas — Alínea 1.1</div>', unsafe_allow_html=True)

    st.markdown(
        "Modelo multicritério para comparar zonas industriais candidatas. "
        "Cada critério tem um peso e um sentido (quanto maior melhor, ou quanto menor melhor). "
        "O score final é calculado por **proporcionalidade** — a melhor alternativa recebe 9 pontos."
    )

    if "alternativas" not in st.session_state:
        st.session_state["alternativas"] = alternativas_iniciais()

    # Critérios em cards visuais agrupados
    st.markdown("---")
    st.markdown("**Critérios de avaliação**")
    grupos = {"Acessibilidade": "#2563eb", "Custos": "#f59e0b", "Recursos": "#10b981"}
    criterios_df = obter_tabela_criterios()

    for grupo, cor in grupos.items():
        grupo_criterios = criterios_df[criterios_df["Grupo"] == grupo]
        st.markdown(
            f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:{cor};margin:0.8rem 0 0.3rem 0;font-family:DM Mono,monospace">{grupo}</div>',
            unsafe_allow_html=True
        )
        cols = st.columns(len(grupo_criterios))
        for col, (_, row) in zip(cols, grupo_criterios.iterrows()):
            seta = "↓ menor melhor" if row["Sentido"] == "inversa" else "↑ maior melhor"
            col.markdown(
                f'<div class="stat-card" style="padding:0.6rem 0.8rem">'
                f'<div class="label" style="font-size:0.65rem">{seta}</div>'
                f'<div style="font-size:0.78rem;color:#e2e8f0;margin:0.2rem 0">{row["Critério"]}</div>'
                f'<div style="font-family:DM Mono,monospace;font-size:1rem;color:{cor}">{row["Peso"]}</div>'
                f'<div style="font-size:0.65rem;color:#475569">{row["Unidade"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
    st.markdown("### Importar alternativas por Excel")

    with st.expander("Importar ficheiro Excel"):
        st.write(
            "O ficheiro deve conter uma linha por alternativa e uma coluna por critério."
        )

        st.markdown("**Colunas esperadas:**")
        st.write(colunas_importacao_esperadas())

        ficheiro_excel = st.file_uploader(
            "Selecionar ficheiro Excel",
            type=["xlsx"],
            key="upload_alternativas_excel"
        )

        substituir_existentes = st.checkbox(
            "Substituir alternativas existentes",
            value=False,
            key="substituir_alternativas"
        )

        if st.button("Importar alternativas do Excel"):
            if ficheiro_excel is None:
                st.error("Seleciona primeiro um ficheiro Excel.")
            else:
                try:
                    df_importado = pd.read_excel(ficheiro_excel)

                    alternativas_importadas = importar_alternativas_de_df(df_importado)

                    if substituir_existentes:
                        st.session_state["alternativas"] = alternativas_importadas
                    else:
                        nomes_existentes = {a["nome"] for a in st.session_state["alternativas"]}
                        novas = [
                            a for a in alternativas_importadas
                            if a["nome"] not in nomes_existentes
                        ]
                        st.session_state["alternativas"].extend(novas)

                    st.success("Alternativas importadas com sucesso.")

                except Exception as e:
                    st.error(f"Erro na importação: {e}")

    st.markdown("### Adicionar alternativa")

    with st.expander("Nova zona industrial candidata", expanded=True):
        with st.form("form_nova_alternativa"):

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                novo_nome = st.text_input(
                    "Nome da alternativa",
                    placeholder="ex: Zona Industrial da Maia"
                )
            with col_b:
                nova_localizacao = st.text_input(
                    "Localização",
                    placeholder="ex: Maia, Porto"
                )
            with col_c:
                nova_nota = st.text_input(
                    "Notas (opcional)",
                    placeholder="ex: próxima da A3"
                )

            valores_criterios = {}

            for grupo in ["Acessibilidade", "Custos", "Recursos"]:
                st.markdown(
                    f"<p style='margin:10px 0 4px;font-size:0.8rem;font-weight:600;"
                    f"text-transform:uppercase;letter-spacing:.06em;color:gray'>{grupo}</p>",
                    unsafe_allow_html=True
                )
                criterios_grupo = [c for c in CRITERIOS if c["grupo"] == grupo]
                cols = st.columns(3)
                for i, crit in enumerate(criterios_grupo):
                    label = f"{crit['nome']} ({crit['unidade']})" if crit["unidade"] else crit["nome"]
                    with cols[i % 3]:
                        valores_criterios[crit["nome"]] = st.number_input(
                            label,
                            min_value=0.0,
                            value=0.0,
                            step=1.0,
                            key=f"novo_{crit['nome']}"
                        )

            st.markdown("")
            submeter = st.form_submit_button("💾 Guardar alternativa", use_container_width=True)

            if submeter:
                nome = novo_nome.strip()
                loc = nova_localizacao.strip()

                if not nome:
                    st.error("O nome da alternativa é obrigatório.")
                elif any(a["nome"] == nome for a in st.session_state["alternativas"]):
                    st.error("Já existe uma alternativa com esse nome.")
                elif not loc:
                    st.error("A localização é obrigatória.")
                else:
                    nova_alt = {
                        "nome": nome,
                        "localizacao": loc,
                        "nota": nova_nota.strip(),
                        "valores": valores_criterios,
                    }

                    st.session_state["alternativas"].append(nova_alt)
                    st.success(f"Alternativa «{nome}» adicionada com sucesso.")

    if st.session_state["alternativas"]:
        with st.expander("Remover alternativa"):
            nomes_existentes = [a["nome"] for a in st.session_state["alternativas"]]
            nome_remover = st.selectbox(
                "Selecionar alternativa a remover",
                nomes_existentes,
                key="alt_remover_form"
            )

            if st.button("Remover alternativa"):
                st.session_state["alternativas"] = [
                    a for a in st.session_state["alternativas"]
                    if a["nome"] != nome_remover
                ]
                st.success(f"Alternativa «{nome_remover}» removida.")

    if st.session_state["alternativas"]:
        st.markdown("### Alternativas registadas")

        df_lista = pd.DataFrame([
            {
                "Nome": a["nome"],
                "Localização": a["localizacao"],
                "Notas": a["nota"]
            }
            for a in st.session_state["alternativas"]
        ])

        st.dataframe(df_lista, use_container_width=True, hide_index=True)
    else:
        st.info("Ainda não existem alternativas.")

    st.markdown("### Ranking das alternativas")

    if len(st.session_state["alternativas"]) < 2:
        st.warning("É necessário pelo menos 2 alternativas para calcular o ranking.")
        st.stop()

    df_scores_adit = calcular_scores(st.session_state["alternativas"])
    df_scores_mult = calcular_scores_multiplicativo(st.session_state["alternativas"])

    metodo_tab = st.radio("Método de avaliação", ["Aditivo", "Multiplicativo", "Comparação"],
                          horizontal=True, key="metodo_rank")

    if metodo_tab == "Comparação":
        st.markdown("#### Aditivo vs Multiplicativo")
        comp = []
        for i, ra in df_scores_adit.iterrows():
            rm = df_scores_mult[df_scores_mult["Nome"] == ra["Nome"]]
            sm = rm["Score Final (Mult.)"].values[0] if not rm.empty else 0
            ridx = df_scores_mult[df_scores_mult["Nome"]==ra["Nome"]].index
            comp.append({"Alternativa": ra["Nome"], "Localização": ra["Localização"],
                         "Score Aditivo": ra["Score Final"], "Rank Aditivo": i+1,
                         "Score Multiplicativo": round(float(sm),4),
                         "Rank Mult.": int(ridx[0])+1 if len(ridx) else 0})
        st.dataframe(pd.DataFrame(comp), use_container_width=True, hide_index=True)
        st.caption("Aditivo: soma ponderada. Multiplicativo: produto ponderado (score^peso). "
                   "Divergências indicam pontos fracos graves numa alternativa.")
        df_scores = df_scores_adit
    elif metodo_tab == "Multiplicativo":
        df_scores = df_scores_mult.rename(columns={"Score Final (Mult.)": "Score Final"})
    else:
        df_scores = df_scores_adit


    melhor = df_scores.iloc[0]

    # ── Destaque da melhor alternativa ───────────────────────────────────
    st.markdown(
        f'''<div style="background:linear-gradient(135deg,#1e3a5f,#0f172a);
            border:1px solid #2563eb;border-radius:12px;padding:1.25rem 1.75rem;
            margin-bottom:1rem;display:flex;align-items:center;justify-content:space-between">
          <div>
            <div style="font-size:0.7rem;color:#60a5fa;text-transform:uppercase;
                letter-spacing:.08em;font-family:DM Mono,monospace;margin-bottom:.4rem">
              ✅ Melhor alternativa</div>
            <div style="font-size:1.5rem;font-weight:600;color:#f1f5f9;line-height:1.2">
              {melhor["Localização"]}</div>
            <div style="font-size:0.82rem;color:#475569;margin-top:.4rem;
                font-family:DM Mono,monospace">
              {melhor["Nome"]}</div>
          </div>
          <div style="text-align:right;flex-shrink:0;margin-left:2rem">
            <div style="font-size:0.7rem;color:#475569;text-transform:uppercase;
                letter-spacing:.08em;font-family:DM Mono,monospace;margin-bottom:.3rem">
              Score Final</div>
            <div style="font-size:2.4rem;font-weight:700;color:#60a5fa;
                font-family:DM Mono,monospace;line-height:1">{melhor["Score Final"]:.4f}</div>
            <div style="font-size:0.72rem;color:#334155;margin-top:.2rem">máx. teórico: 9.0</div>
          </div>
        </div>''',
        unsafe_allow_html=True
    )

    # ── Ranking horizontal ────────────────────────────────────────────────
    st.markdown("**Ranking das alternativas**")
    cores_rank = ["#2563eb","#0ea5e9","#38bdf8","#7dd3fc","#bae6fd"]
    fig_rank = go.Figure()
    for i, (_, row) in enumerate(df_scores.iterrows()):
        fig_rank.add_trace(go.Bar(
            y=[row["Localização"]],
            x=[row["Score Final"]],
            orientation="h",
            marker=dict(color=cores_rank[i % len(cores_rank)],
                        line=dict(color="rgba(0,0,0,0)", width=0)),
            text=f'{row["Nome"]}  {row["Score Final"]:.4f}',
            textposition="inside",
            textfont=dict(color="#f1f5f9", size=11, family="DM Mono"),
            showlegend=False,
        ))
    fig_rank.update_layout(
        xaxis=dict(range=[0, 9.5], showgrid=True, gridcolor="#1e2130",
                   zeroline=False, tickfont=dict(color="#475569", family="DM Mono"),
                   title=dict(text="Score (máx. 9)", font=dict(color="#475569", size=11))),
        yaxis=dict(showgrid=False, tickfont=dict(color="#e2e8f0", size=11),
                   automargin=True),
        plot_bgcolor="#0f1117", paper_bgcolor="#0f1117",
        height=max(160, len(df_scores) * 65 + 40),
        margin=dict(l=10, r=40, t=10, b=30),
        bargap=0.4,
    )
    fig_rank.add_vline(x=9, line_dash="dot", line_color="#1e2130")
    st.plotly_chart(fig_rank, use_container_width=True)

    st.markdown("### Radar chart dos critérios")

    df_radar = obter_scores_por_criterio(st.session_state["alternativas"])

    if not df_radar.empty:

        criterios_radar = [c["nome"] for c in CRITERIOS]

        fig = go.Figure()

        for _, row in df_radar.iterrows():
            valores = [row[c] for c in criterios_radar]
            valores += [valores[0]]  # fechar o polígono
            theta = criterios_radar + [criterios_radar[0]]

            fig.add_trace(
                go.Scatterpolar(
                    r=valores,
                    theta=theta,
                    fill="toself",
                    name=row["Nome"]
                )
            )

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 9]
                )
            ),
            showlegend=True,
            height=700
        )

        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Ver detalhe completo dos scores"):
        st.dataframe(df_scores, use_container_width=True, hide_index=True)

elif secao == "Desenho da Rede de Distribuição":
    import math

    st.markdown('<div class="section-title">Desenho da Rede de Distribuição — Alínea 1.2</div>', unsafe_allow_html=True)
    st.write(
        "Visualização da rede de distribuição e resultado da optimização MILP com os 7 CDs candidatos. "
        "Corre o modelo na tab **Optimização MILP** para obter a solução óptima."
    )

    # ── Dados fixos do problema ──────────────────────────────────────────────
    CUSTO_KM = 0.13  # €/km/unidade

    # Fábricas — fixas (dados do enunciado)
    FABRICAS = [
        {"nome": "Felgueiras", "lat": 41.367740, "lon": -8.198110, "cap": 500},
        {"nome": "Mangualde",  "lat": 40.607028, "lon": -7.763532, "cap": 1200},
    ]

    # Custos fixos dos CDs por país (dados do enunciado, em k€)
    # Chaves normalizadas (sem acentos) para resistir a variações do CSV
    CUSTOS_FIXOS_PAIS_NORM = {
        "portugal": 1000, "espanha": 1200, "franca": 1000, "franca": 1000,
        "frança": 1000, "italia": 1000, "itália": 1000, "alemanha": 1500,
    }

    def _custo_fixo(pais: str) -> int:
        return CUSTOS_FIXOS_PAIS_NORM.get(pais.lower().strip(), 1000)

    # ── Clientes: vêm do df editado na sessão (com procuras actualizadas) ───
    df_rede = st.session_state.get("df_localizacao_editado")

    if df_rede is None or df_rede.empty:
        st.warning(
            "⚠️ Ainda não há dados de clientes carregados. "
            "Vai ao módulo **Localização dos Armazéns**, carrega o ficheiro CSV e volta aqui."
        )
        st.stop()

    CLIENTES = [
        {
            "nome": row["cidade"],
            "pais": row["pais"],
            "lat": row["latitude"],
            "lon": row["longitude"],
            "procura": row["procura"],
        }
        for _, row in df_rede.iterrows()
    ]

    # ── CDs Opção A: resultado do solver (cidade mais próxima por país) ──────
    # Fallback para valores do enunciado se o solver ainda não tiver corrido.
    FALLBACK_CDS_A = [
        {"nome": "CD Portugal (Coimbra)",    "pais": "Portugal", "lat": 40.179190, "lon": -8.466150},
        {"nome": "CD Espanha (Saragoca)",    "pais": "Espanha",  "lat": 41.330000, "lon": -1.220000},
        {"nome": "CD Franca (Blois)",        "pais": "Franca",   "lat": 47.624100, "lon":  1.327500},
        {"nome": "CD Italia (Milao Este)",   "pais": "Italia",   "lat": 45.490000, "lon":  9.290000},
        {"nome": "CD Alemanha (Nuremberga)", "pais": "Alemanha", "lat": 49.410000, "lon": 11.050000},
    ]

    resultado_solver = st.session_state.get("resultado_final_localizacao")

    if resultado_solver is not None and not resultado_solver.empty:
        CDS_OPCAO_A = []
        for _, row in resultado_solver.iterrows():
            pais = row["pais"]
            custo_fixo = _custo_fixo(pais)
            procura_pais = sum(c["procura"] for c in CLIENTES if c["pais"] == pais)
            CDS_OPCAO_A.append({
                "nome": f"CD {pais} ({row['cidade_escolhida']})",
                "pais": pais,
                "lat": row["latitude_cidade"],
                "lon": row["longitude_cidade"],
                "custo_fixo": custo_fixo,
                "cap": procura_pais,
            })
        fonte_cds = "solver"
    else:
        CDS_OPCAO_A = [
            {**cd, "custo_fixo": _custo_fixo(cd["pais"]),
             "cap": sum(c["procura"] for c in CLIENTES if c["pais"] == cd["pais"])}
            for cd in FALLBACK_CDS_A
        ]
        fonte_cds = "fallback"

    # ── CDs Opção B — dois XL (fixos do enunciado) ────────────────────────────
    CDS_OPCAO_B = [
        {"nome": "CD Munique XL", "pais": "todos", "lat": 48.915190, "lon": 11.756490, "custo_fixo": 2500, "cap": 600},
        {"nome": "CD Madrid XL",  "pais": "todos", "lat": 40.637128, "lon": -3.134727, "custo_fixo": 2000, "cap": 500},
    ]

    # ── Aviso sobre a fonte dos dados ──────────────────────────────────────
    milp_rede_check = st.session_state.get("milp_rede")
    if milp_rede_check and milp_rede_check.get("status") == "ok":
        cds_nomes = ", ".join(cd["nome"] for cd in milp_rede_check["cds_abertos"])
        st.success(
            f"✅ A rede usa os **resultados do solver MILP** — {len(milp_rede_check['cds_abertos'])} CDs abertos: {cds_nomes}."
        )
    else:
        st.info(
            "ℹ️ Ainda não existe solução MILP. Vai à tab **Optimização MILP** e clica em Resolver para actualizar o mapa."
        )

    def graus_para_km(lat1, lon1, lat2, lon2):
        """Distância haversine em km entre dois pontos geográficos."""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return R * 2 * math.asin(math.sqrt(a))

    def cd_mais_proximo(cliente, cds):
        return min(cds, key=lambda cd: graus_para_km(cliente["lat"], cliente["lon"], cd["lat"], cd["lon"]))

    def calcular_custo_distribuicao(clientes, cds):
        """Custo CD → clientes (€/ano). Cada cliente vai ao CD mais próximo."""
        total = 0.0
        linhas = []
        for c in clientes:
            cd = cd_mais_proximo(c, cds)
            dist = graus_para_km(c["lat"], c["lon"], cd["lat"], cd["lon"])
            custo = dist * c["procura"] * CUSTO_KM
            total += custo
            linhas.append({
                "Cliente": c["nome"],
                "País": c["pais"],
                "CD Abastecedor": cd["nome"],
                "Procura (×100 ton)": c["procura"],
                "Distância CD→Cliente (km)": round(dist, 1),
                "Custo Transp. (k€/ano)": round(custo / 1000, 2),
            })
        return total, linhas

    def calcular_custo_fabrica_cd(fabricas, cds):
        """Custo fábricas → CDs. Distribui capacidade de forma proporcional."""
        total = 0.0
        linhas = []
        procura_total_cd = {cd["nome"]: sum(
            c["procura"] for c in CLIENTES
            if cd_mais_proximo(c, cds)["nome"] == cd["nome"]
        ) for cd in cds}

        for fab in fabricas:
            for cd in cds:
                dist = graus_para_km(fab["lat"], fab["lon"], cd["lat"], cd["lon"])
                vol = procura_total_cd.get(cd["nome"], 0) * (fab["cap"] / sum(f["cap"] for f in fabricas))
                custo = dist * vol * CUSTO_KM
                total += custo
                linhas.append({
                    "Fábrica": fab["nome"],
                    "CD": cd["nome"],
                    "Distância (km)": round(dist, 1),
                    "Volume estimado (×100 ton)": round(vol, 1),
                    "Custo Transp. (k€/ano)": round(custo / 1000, 2),
                })
        return total, linhas

    def custo_fixo_total(cds):
        return sum(cd["custo_fixo"] for cd in cds)

    # Cálculos heurísticos removidos — usar MILP na tab Optimização

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_mapa, tab_custos, tab_detalhe = st.tabs(["🗺️ Mapa da Rede", "🔢 Optimização MILP", "📋 Detalhe"])

    with tab_mapa:
        # CDs para o mapa: se MILP já correu, usa resultado; senão usa fallback
        milp_rede = st.session_state.get("milp_rede")
        if milp_rede and milp_rede.get("status") == "ok" and milp_rede.get("cds_abertos"):
            cds_sel = [
                {"nome": cd["nome"], "lat": cd["lat"], "lon": cd["lon"]}
                for cd in milp_rede["cds_abertos"]
            ]
            st.success(f"✅ Mapa actualizado com o resultado do MILP — "
                       f"{len(cds_sel)} CD(s) aberto(s): "
                       f"{', '.join(cd['nome'] for cd in cds_sel)}")
        else:
            cds_sel = CDS_OPCAO_A
            st.info("ℹ️ Corre o MILP na tab **Optimização MILP** para actualizar o mapa com a solução óptima.")

        fig_map = go.Figure()

        # Fábricas
        fig_map.add_trace(go.Scattergeo(
            lat=[f["lat"] for f in FABRICAS],
            lon=[f["lon"] for f in FABRICAS],
            text=[f["nome"] for f in FABRICAS],
            mode="markers+text",
            textposition="top center",
            marker=dict(size=14, color="#e74c3c", symbol="square"),
            name="Fábricas",
        ))

        # CDs
        fig_map.add_trace(go.Scattergeo(
            lat=[cd["lat"] for cd in cds_sel],
            lon=[cd["lon"] for cd in cds_sel],
            text=[cd["nome"] for cd in cds_sel],
            mode="markers+text",
            textposition="top center",
            marker=dict(size=16, color="#2980b9", symbol="diamond"),
            name="Centros de Distribuição",
        ))

        # Clientes
        _paleta = ["#27ae60", "#f39c12", "#8e44ad", "#16a085", "#c0392b", "#2980b9", "#c0392b"]
        _paises_unicos = sorted(set(c["pais"] for c in CLIENTES))
        cores_pais = {p: _paleta[i % len(_paleta)] for i, p in enumerate(_paises_unicos)}
        for pais in cores_pais:
            grupo = [c for c in CLIENTES if c["pais"] == pais]
            fig_map.add_trace(go.Scattergeo(
                lat=[c["lat"] for c in grupo],
                lon=[c["lon"] for c in grupo],
                text=[c["nome"] for c in grupo],
                mode="markers+text",
                textposition="bottom center",
                marker=dict(size=9, color=cores_pais[pais]),
                name=f"Clientes {pais}",
            ))

        # Linhas Fábrica → CD
        for fab in FABRICAS:
            for cd in cds_sel:
                fig_map.add_trace(go.Scattergeo(
                    lat=[fab["lat"], cd["lat"], None],
                    lon=[fab["lon"], cd["lon"], None],
                    mode="lines",
                    line=dict(width=1, color="#e74c3c", dash="dot"),
                    showlegend=False,
                ))

        # Linhas CD → Cliente
        for c in CLIENTES:
            cd = cd_mais_proximo(c, cds_sel)
            fig_map.add_trace(go.Scattergeo(
                lat=[cd["lat"], c["lat"], None],
                lon=[cd["lon"], c["lon"], None],
                mode="lines",
                line=dict(width=1.5, color="#2980b9"),
                showlegend=False,
            ))

        fig_map.update_layout(
            geo=dict(
                scope="europe",
                projection_type="mercator",
                showland=True,
                landcolor="rgb(240,240,230)",
                showocean=True,
                oceancolor="rgb(210,230,245)",
                showcountries=True,
                countrycolor="rgb(200,200,200)",
                showcoastlines=True,
                lonaxis=dict(range=[-12, 22]),
                lataxis=dict(range=[35, 57]),
            ),
            height=520,
            width=1100,
            margin=dict(l=0, r=0, t=40, b=0),
            legend=dict(
                orientation="h",
                yanchor="top", y=-0.02,
                xanchor="left", x=0,
                font=dict(size=11),
            ),
        )
        st.plotly_chart(fig_map, use_container_width=False)

    with tab_custos:
        st.markdown("### Optimização MILP — Alínea 1.2")
        st.write(
            "O modelo decide livremente quais dos **7 CDs candidatos** abrir, "
            "minimizando o custo total de transporte + custos fixos de instalação, "
            "respeitando as capacidades das fábricas e satisfazendo toda a procura."
        )

        with st.expander("CDs candidatos e capacidades", expanded=False):
            df_cds_cand = pd.DataFrame(CDS_CANDIDATOS)[["nome", "cap", "custo_fixo"]].rename(
                columns={"nome": "CD", "cap": "Cap. (unid.)", "custo_fixo": "Custo fixo (k€)"}
            )
            st.dataframe(df_cds_cand, use_container_width=True, hide_index=True)

        if st.button("▶ Resolver MILP (livre)", type="primary", key="btn_milp_rede"):
            with st.spinner("A resolver... (pode demorar alguns segundos)"):
                try:
                    res = resolver_milp(df_rede, cds_candidatos=CDS_CANDIDATOS)
                    st.session_state["milp_rede"] = res
                except Exception as e:
                    st.error(f"Erro: {e}")

        milp_res = st.session_state.get("milp_rede")

        if milp_res is None:
            st.info("Clica **Resolver MILP** para executar o modelo.")
        elif milp_res["status"] != "ok":
            st.error(f"Sem solução: {milp_res['message']}")
        else:
            def _fmt_eur(v):
                if v >= 1_000_000: return f"{v/1_000_000:,.2f} M€"
                elif v >= 1_000:   return f"{v/1_000:,.1f} k€"
                return f"{v:,.0f} €"

            # Métricas
            c1, c2, c3 = st.columns(3)
            c1.metric("Custo Transporte", _fmt_eur(milp_res["custo_transporte"]))
            c2.metric("Custo Fixo CDs", _fmt_eur(milp_res["custo_fixo"]))
            c3.metric("Custo Total", _fmt_eur(milp_res["custo_total"]))

            # CDs abertos
            st.markdown("#### CDs seleccionados pelo modelo")
            n_abertos = len(milp_res["cds_abertos"])
            st.success(f"✅ O solver abriu **{n_abertos} CD(s)** de entre os 7 candidatos.")
            df_ab = pd.DataFrame(milp_res["cds_abertos"])[["nome", "cap", "custo_fixo"]].rename(
                columns={"nome": "CD", "cap": "Cap. (unid.)", "custo_fixo": "Custo fixo (k€)"}
            )
            st.dataframe(df_ab, use_container_width=True, hide_index=True)

            st.caption("💡 O mapa da Rede é actualizado automaticamente com estes CDs — vai à tab **Mapa da Rede**.")

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.markdown("**Fluxos Fábricas → CDs**")
                if not milp_res["fab_cd"].empty:
                    st.dataframe(milp_res["fab_cd"], use_container_width=True, hide_index=True)
            with col_f2:
                st.markdown("**Fluxos CDs → Clientes**")
                if not milp_res["cd_cli"].empty:
                    st.dataframe(milp_res["cd_cli"], use_container_width=True, hide_index=True)

    with tab_detalhe:
        milp_det = st.session_state.get("milp_rede")
        if milp_det is None or milp_det.get("status") != "ok":
            st.info("Corre o modelo em **Optimização MILP** para ver o detalhe dos fluxos.")
        else:
            st.markdown("### Detalhe: Fluxos CDs → Clientes")
            st.dataframe(milp_det["cd_cli"], use_container_width=True, hide_index=True)

            st.markdown("### Detalhe: Fluxos Fábricas → CDs")
            st.dataframe(milp_det["fab_cd"], use_container_width=True, hide_index=True)

elif secao == "Geração de Instâncias":
    import numpy as np

    st.subheader("Geração de Instâncias — Alínea 1.3")
    st.write(
        "Replica os 4 botões do Excel VBA: varia procuras, capacidades das fábricas "
        "ou capacidades dos CDs, e corre o MILP em cada cenário gerado."
    )

    # ── Verificar dados base ─────────────────────────────────────────────────
    df_base = st.session_state.get("df_localizacao_editado")
    if df_base is None or df_base.empty:
        st.warning("⚠️ Sem dados de clientes. Vai ao módulo **Localização dos Armazéns**, carrega o CSV e volta aqui.")
        st.stop()

    # ── Valores iniciais do enunciado (ReporInstanciaInicial) ────────────────
    PROCURAS_INICIAIS = [30, 40, 50, 20, 30, 10, 25, 25, 75, 75, 100, 100, 100, 30, 40, 100, 50, 50, 75, 50, 75]
    FABRICAS_INICIAIS = {"Felgueiras": 500, "Mangualde": 1200}
    CDS_BASE = [
        {"nome": "Munique XL",  "lat": 48.915190, "lon": 11.756490, "cap_base": 600,  "custo_fixo": 2500},
        {"nome": "Madrid XL",   "lat": 40.637128, "lon": -3.134727, "cap_base": 500,  "custo_fixo": 2000},
        {"nome": "Coimbra",     "lat": 40.179190, "lon": -8.466150, "cap_base": 200,  "custo_fixo": 1000},
        {"nome": "Saragoça",    "lat": 41.330000, "lon": -1.220000, "cap_base": 300,  "custo_fixo": 1200},
        {"nome": "Blois",       "lat": 47.624100, "lon":  1.327500, "cap_base": 270,  "custo_fixo": 1000},
        {"nome": "Milão",       "lat": 45.490000, "lon":  9.290000, "cap_base": 200,  "custo_fixo": 1000},
        {"nome": "Nuremberga",  "lat": 49.410000, "lon": 11.050000, "cap_base": 220,  "custo_fixo": 1500},
    ]
    FABRICAS_BASE = [
        {"id": 0, "nome": "Felgueiras", "lat": 41.367740, "lon": -8.198110, "cap": 500},
        {"id": 1, "nome": "Mangualde",  "lat": 40.607028, "lon": -7.763532, "cap": 1200},
    ]

    # Estado da sessão para os parâmetros actuais
    if "inst_procuras" not in st.session_state:
        st.session_state["inst_procuras"] = PROCURAS_INICIAIS.copy()
    if "inst_fab_caps" not in st.session_state:
        st.session_state["inst_fab_caps"] = FABRICAS_INICIAIS.copy()
    if "inst_cd_caps" not in st.session_state:
        st.session_state["inst_cd_caps"] = {cd["nome"]: cd["cap_base"] for cd in CDS_BASE}

    PAISES = sorted(df_base["pais"].unique().tolist())

    # ── Painel de controlo ───────────────────────────────────────────────────
    st.markdown("### Painel de controlo")
    st.info(
        "Usa os botões abaixo para gerar variações (como o VBA fazia no Excel), "
        "depois clica **Resolver MILP** para optimizar a rede com esses dados."
    )

    col_b1, col_b2, col_b3, col_b4 = st.columns(4)

    with col_b1:
        if st.button("🎲 Variar Procuras", use_container_width=True,
                     help="Gera procuras aleatórias (5-50) por grupo de CD, respeitando a capacidade de cada CD"):
            st.session_state["_last_variacao"] = "Variar Procura"
            rng = np.random.default_rng()
            # Grupos por CD (igual ao VBA): Coimbra→PT, Madrid→ES(parcial), Blois→FR, Milão→IT
            # Usar grupos do Excel: linhas 20-26=PT(Coimbra), 27-31=ES(Madrid×0.7), 34-36=FR, 38-40=IT
            grupos = [
                (list(range(0, 6)),   200),         # Portugal → Coimbra (cap 200)
                (list(range(6, 11)),  500 * 0.7),   # Espanha → Madrid ×0.7
                (list(range(11, 15)), 270),          # França → Blois (cap 270)
                (list(range(15, 18)), 200),          # Itália → Milão (cap 200)
                (list(range(18, 21)), 220),          # Alemanha → Nuremberga (cap 220)
            ]
            novas = list(st.session_state["inst_procuras"])
            for indices, cap_max in grupos:
                vals = [int(rng.integers(5, 51)) for _ in indices]
                soma = sum(vals)
                if soma > cap_max:
                    vals = [max(1, int(v * cap_max / soma)) for v in vals]
                for idx, v in zip(indices, vals):
                    novas[idx] = v
            st.session_state["inst_procuras"] = novas
            st.session_state.pop("inst_resultado", None)
            st.rerun()

    with col_b2:
        if st.button("🏭 Variar Fábricas", use_container_width=True,
                     help="Felgueiras: 100-500; Mangualde: 400-1200"):
            st.session_state["_last_variacao"] = "Variar Capacidade das Fábricas"
            rng = np.random.default_rng()
            st.session_state["inst_fab_caps"] = {
                "Felgueiras": int(rng.integers(100, 501)),
                "Mangualde":  int(rng.integers(400, 1201)),
            }
            st.session_state.pop("inst_resultado", None)
            st.rerun()

    with col_b3:
        if st.button("🏗️ Variar CDs (±20%)", use_container_width=True,
                     help="Varia a capacidade de cada CD entre ±20% do valor base"):
            st.session_state["_last_variacao"] = "Variar Capacidade CD's"
            rng = np.random.default_rng()
            novas_caps = {}
            for cd in CDS_BASE:
                base = cd["cap_base"]
                novas_caps[cd["nome"]] = max(1, int(base * (0.8 + rng.random() * 0.4)))
            st.session_state["inst_cd_caps"] = novas_caps
            st.session_state.pop("inst_resultado", None)
            st.rerun()

    with col_b4:
        if st.button("↩️ Repor Inicial", use_container_width=True,
                     help="Repõe todos os valores originais do enunciado"):
            st.session_state["inst_procuras"] = PROCURAS_INICIAIS.copy()
            st.session_state["inst_fab_caps"] = FABRICAS_INICIAIS.copy()
            st.session_state["inst_cd_caps"] = {cd["nome"]: cd["cap_base"] for cd in CDS_BASE}
            st.session_state.pop("inst_resultado", None)
            st.rerun()

    # ── Estado actual ────────────────────────────────────────────────────────
    st.markdown("### Estado actual da instância")

    procuras_actuais = st.session_state["inst_procuras"]
    fab_caps = st.session_state["inst_fab_caps"]
    cd_caps = st.session_state["inst_cd_caps"]

    col_est1, col_est2, col_est3 = st.columns(3)

    with col_est1:
        st.markdown("**Procura dos clientes**")
        cidades = df_base["cidade"].tolist()
        df_proc = pd.DataFrame({
            "Cidade": cidades[:len(procuras_actuais)],
            "País": df_base["pais"].tolist()[:len(procuras_actuais)],
            "Procura": procuras_actuais[:len(cidades)],
            "Original": PROCURAS_INICIAIS[:len(cidades)],
        })
        df_proc["Δ"] = df_proc["Procura"] - df_proc["Original"]
        st.dataframe(df_proc, use_container_width=True, hide_index=True, height=300)
        st.caption(f"Total: **{sum(procuras_actuais):.0f}** (original: {sum(PROCURAS_INICIAIS)})")

    with col_est2:
        st.markdown("**Capacidade das fábricas**")
        df_fab = pd.DataFrame([
            {"Fábrica": nome, "Cap. actual": cap, "Cap. original": FABRICAS_INICIAIS[nome],
             "Δ": cap - FABRICAS_INICIAIS[nome]}
            for nome, cap in fab_caps.items()
        ])
        st.dataframe(df_fab, use_container_width=True, hide_index=True)
        st.caption(f"Total: **{sum(fab_caps.values())}** (original: {sum(FABRICAS_INICIAIS.values())})")

    with col_est3:
        st.markdown("**Capacidade dos CDs**")
        df_cd = pd.DataFrame([
            {"CD": nome, "Cap. actual": cap, "Cap. base": next(c["cap_base"] for c in CDS_BASE if c["nome"] == nome),
             "Δ": cap - next(c["cap_base"] for c in CDS_BASE if c["nome"] == nome)}
            for nome, cap in cd_caps.items()
        ])
        st.dataframe(df_cd, use_container_width=True, hide_index=True)

    # ── Resolver MILP ────────────────────────────────────────────────────────
    st.markdown("---")
    st.info(
        "O modelo decide livremente quais dos **7 CDs candidatos** abrir "
        "(LP relaxado + arredondamento, igual à Alínea 1.2), com as capacidades "
        "e procuras da instância actual."
    )
    if st.button("▶ Resolver MILP com estes dados", type="primary", key="btn_inst_milp"):
        df_inst = df_base.copy()
        df_inst["procura"] = procuras_actuais[:len(df_inst)]

        fabricas_inst = [
            {**f, "cap": fab_caps.get(f["nome"], f["cap"])}
            for f in FABRICAS_BASE
        ]

        # CDs com capacidades variadas — todos os 7 candidatos, livre
        cds_inst = [
            {**cd, "cap": cd_caps.get(cd["nome"], cd["cap_base"]), "id": i}
            for i, cd in enumerate(CDS_BASE)
        ]

        with st.spinner("A resolver MILP..."):
            try:
                res = resolver_milp(df_inst, fabricas=fabricas_inst,
                                    cds_candidatos=cds_inst)
                # Determine tipo_inst from session state
                _tipo = st.session_state.get("_last_variacao", "")
                st.session_state["inst_resultado"] = {
                    "res": res, "df_inst": df_inst,
                    "fab_caps": fab_caps.copy(), "cd_caps": cd_caps.copy(),
                    "opcao": "Livre (7 CDs candidatos)",
                    "tipo_inst": _tipo,
                }
            except Exception as e:
                st.error(f"Erro: {e}")

    # ── Resultado ────────────────────────────────────────────────────────────
    inst_res = st.session_state.get("inst_resultado")
    if inst_res:
        res = inst_res["res"]
        st.markdown("### Resultado do MILP")

        if res.get("status") != "ok":
            st.error(f"Sem solução: {res['message']}")
        else:
            def _fe(v):
                if v >= 1_000_000: return f"{v/1_000_000:,.2f} M€"
                elif v >= 1_000: return f"{v/1_000:,.1f} k€"
                return f"{v:,.0f} €"

            c1, c2, c3 = st.columns(3)
            c1.metric("Custo Transporte", _fe(res["custo_transporte"]))
            c2.metric("Custo Fixo CDs", _fe(res["custo_fixo"]))
            c3.metric("Custo Total", _fe(res["custo_total"]))

            st.markdown(f"**Opção:** {inst_res['opcao']}")
            st.markdown("**CDs abertos:**  " + "  ·  ".join(cd["nome"] for cd in res["cds_abertos"]))

            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.markdown("**Fluxos Fábricas → CDs**")
                if not res["fab_cd"].empty:
                    st.dataframe(res["fab_cd"], use_container_width=True, hide_index=True)
            with col_r2:
                st.markdown("**Fluxos CDs → Clientes**")
                if not res["cd_cli"].empty:
                    st.dataframe(res["cd_cli"], use_container_width=True, hide_index=True)

            # Export
            st.markdown("**Exportar resultado**")
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                if not res["fab_cd"].empty:
                    st.download_button("⬇️ Fluxos Fab→CD", data=res["fab_cd"].to_csv(index=False).encode(),
                                       file_name="inst_fab_cd.csv", mime="text/csv", key="dl_inst_fab")
            with col_e2:
                if not res["cd_cli"].empty:
                    st.download_button("⬇️ Fluxos CD→Cli", data=res["cd_cli"].to_csv(index=False).encode(),
                                       file_name="inst_cd_cli.csv", mime="text/csv", key="dl_inst_cli")

            # ── Mapa da solução ──────────────────────────────────────────
            st.markdown("---")
            st.markdown("**🗺️ Mapa da solução desta instância**")


            fig_inst = go.Figure()

            # Fábricas
            fig_inst.add_trace(go.Scattergeo(
                lat=[f["lat"] for f in FABRICAS_BASE],
                lon=[f["lon"] for f in FABRICAS_BASE],
                text=[f["nome"] for f in FABRICAS_BASE],
                mode="markers+text", textposition="top center",
                marker=dict(size=14, color="#e74c3c", symbol="square"),
                name="Fábricas",
            ))

            # CDs abertos nesta instância
            fig_inst.add_trace(go.Scattergeo(
                lat=[cd["lat"] for cd in res["cds_abertos"]],
                lon=[cd["lon"] for cd in res["cds_abertos"]],
                text=[cd["nome"] for cd in res["cds_abertos"]],
                mode="markers+text", textposition="top center",
                marker=dict(size=16, color="#2563eb", symbol="diamond"),
                name="CDs abertos",
            ))

            # Clientes
            _paleta_inst = ["#27ae60","#f39c12","#8e44ad","#16a085","#c0392b"]
            _paises_inst = sorted(set(row["pais"] for _, row in inst_res["df_inst"].iterrows()))
            _cores_inst = {p: _paleta_inst[i % len(_paleta_inst)] for i, p in enumerate(_paises_inst)}
            for pais in _paises_inst:
                grupo = inst_res["df_inst"][inst_res["df_inst"]["pais"] == pais]
                fig_inst.add_trace(go.Scattergeo(
                    lat=grupo["latitude"].tolist(),
                    lon=grupo["longitude"].tolist(),
                    text=grupo["cidade"].tolist(),
                    mode="markers+text", textposition="bottom center",
                    marker=dict(size=8, color=_cores_inst[pais]),
                    name=f"Clientes {pais}",
                ))

            # Linhas Fábrica → CD
            if not res["fab_cd"].empty:
                for _, row in res["fab_cd"].iterrows():
                    fab = next((f for f in FABRICAS_BASE if f["nome"] == row["Fábrica"]), None)
                    cd  = next((c for c in res["cds_abertos"] if c["nome"] == row["CD"]), None)
                    if fab and cd:
                        fig_inst.add_trace(go.Scattergeo(
                            lat=[fab["lat"], cd["lat"], None],
                            lon=[fab["lon"], cd["lon"], None],
                            mode="lines", line=dict(width=2, color="#e74c3c", dash="dot"),
                            showlegend=False,
                        ))

            # Linhas CD → Cliente
            if not res["cd_cli"].empty:
                for _, row in res["cd_cli"].iterrows():
                    cd = next((c for c in res["cds_abertos"] if c["nome"] == row["CD"]), None)
                    cli = inst_res["df_inst"][inst_res["df_inst"]["cidade"] == row["Cliente"]]
                    if cd is not None and not cli.empty:
                        fig_inst.add_trace(go.Scattergeo(
                            lat=[cd["lat"], cli.iloc[0]["latitude"], None],
                            lon=[cd["lon"], cli.iloc[0]["longitude"], None],
                            mode="lines", line=dict(width=1, color="#2563eb"),
                            showlegend=False,
                        ))

            fig_inst.update_layout(
                geo=dict(scope="europe", projection_type="mercator",
                         showland=True, landcolor="rgb(240,240,230)",
                         showocean=True, oceancolor="rgb(210,230,245)",
                         showcountries=True, countrycolor="rgb(200,200,200)",
                         lonaxis=dict(range=[-12, 22]), lataxis=dict(range=[35, 57])),
                height=480, margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="left", x=0),
            )
            st.plotly_chart(fig_inst, use_container_width=True)

elif secao == "Dimensionamento do Armazém":
    import numpy as np
    from plotly.subplots import make_subplots

    st.markdown('<div class="section-title">Parte 2 — Dimensionamento do Armazém (Espanha)</div>', unsafe_allow_html=True)

    # ── Dados do enunciado ───────────────────────────────────────────────────
    PRODUTOS = {
        "A": {"comp": 400, "larg": 200, "alt": 200, "peso": 20},
        "B": {"comp": 335, "larg": 220, "alt": 190, "peso": 14},
    }
    PALETES = {
        "EUR 1": {"w": 800,  "d": 1200, "h": 144, "max_kg": 1200, "peso": 25},
        "EUR 2": {"w": 1200, "d": 1000, "h": 144, "max_kg": 1500, "peso": 35},
        "EUR 6": {"w": 800,  "d": 600,  "h": 144, "max_kg": 600,  "peso": 9.5},
    }
    CUSTO_CONSTR   = 1200   # €/m²
    VIDA_UTIL      = 40     # anos
    CUSTO_FIXO_ANO = 150    # €/m²/ano
    CUSTO_OP       = 0.25   # €/palete movimentada
    CUSTO_ARR      = 16     # €/palete/mês arrendamento
    CUSTO_ARR_OP   = 8      # €/palete operação arrendamento
    TURNOVER       = 4      # rotações/mês
    ALT_MAX_RACK   = 6000   # mm
    ALT_CARGA      = 1000   # mm (altura caixas empilhadas)
    ALT_PALETE     = 144    # mm
    FOLGA          = 75     # mm (níveis 1-3)
    FOLGA_TOPO     = 100    # mm (níveis 4-5)
    ALT_VIGA       = 100    # mm

    # Dados históricos
    HIST_A = [178007,174362,161894,152960,155774,160070,183801,195331,199595,198885,193502,175414,
              183347,179593,166750,157549,160447,164872,189315,201191,205583,204851,199307,180676,
              189948,186058,172753,163221,166223,170808,196130,208434,212984,212226,206483,187181,
              294420,288390,267768,252993,257646,264753,304002,323073,330126,328951,320048,290130,
              373913,366256,340066,321301,327211,336236,386083,410303,419260,417767,406461,368466]
    HIST_B = [40303,37449,44021,39615,48562,50859,48329,43536,61748,55134,58170,50970,
              41513,38572,45341,40804,50019,52384,49779,44842,63600,56788,59915,52500,
              43007,39961,46973,42273,51820,54270,51571,46456,65890,58833,62072,54390,
              66661,61939,72809,65523,80321,84119,79936,72008,102130,91191,96212,84304,
              84660,78663,92468,83214,102008,106831,101519,91450,129705,115812,122190,107066]

    # Previsões Holt-Winters (resultado das colegas)
    MEDIA_PREV_A = 453222   # caixas/mês (procura média mensal produto A)
    MAX_PREV_A   = 563277   # caixas/mês (procura máxima mensal produto A)
    MEDIA_PREV_B = 119127   # caixas/mês (procura média mensal produto B)
    MAX_PREV_B   = 165209   # caixas/mês (procura máxima mensal produto B)

    tab_prev, tab_paletes, tab_dim, tab_layout = st.tabs([
        "📈 2.1 Previsão de Procura",
        "📦 2.1 Análise de Paletes",
        "📐 2.2 Dimensionamento",
        "🏭 2.3 Layout"
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — PREVISÃO
    # ════════════════════════════════════════════════════════════════════════
    with tab_prev:
        st.markdown('<div class="section-title">Previsão de Procura — Holt-Winters Multiplicativo</div>', unsafe_allow_html=True)
        st.write("Série temporal de 60 meses (Jan 2021 – Dez 2025) com previsão para os próximos 36 meses.")

        import pandas as pd
        from datetime import datetime

        datas = pd.date_range("2021-01-01", periods=60, freq="MS")
        datas_prev = pd.date_range("2026-01-01", periods=36, freq="MS")

        # Holt-Winters multiplicativo simples para visualização
        def holt_winters_mult(data, alpha, beta, gamma, m=12, n_ahead=36):
            data = list(data)
            n = len(data)
            L = [None]*n; T = [None]*n; S = [1.0]*(n+n_ahead)
            # Init
            L[m-1] = sum(data[:m])/m
            T[m-1] = (sum(data[m:2*m]) - sum(data[:m])) / (m*m)
            for i in range(m):
                S[i] = data[i] / L[m-1]
            for t in range(m, n):
                L[t] = alpha*(data[t]/S[t-m]) + (1-alpha)*(L[t-1]+T[t-1])
                T[t] = beta*(L[t]-L[t-1]) + (1-beta)*T[t-1]
                S[t] = gamma*(data[t]/L[t]) + (1-gamma)*S[t-m]
            preds = []
            for h in range(1, n_ahead+1):
                pred = (L[n-1] + h*T[n-1]) * S[n-m + ((h-1)%m)]
                preds.append(max(0, pred))
            return preds

        prev_a = holt_winters_mult(HIST_A, 0.73, 0.038, 1.0)
        prev_b = holt_winters_mult(HIST_B, 0.74, 0.024, 1.0)

        prod_sel = st.radio("Produto", ["A", "B", "A + B"], horizontal=True, key="prev_prod")

        fig = go.Figure()
        if "A" in prod_sel:
            fig.add_trace(go.Scatter(x=datas, y=HIST_A, name="Produto A — Histórico",
                                     line=dict(color="#2563eb", width=2)))
            fig.add_trace(go.Scatter(x=datas_prev, y=prev_a, name="Produto A — Previsão",
                                     line=dict(color="#2563eb", width=2, dash="dash")))
        if "B" in prod_sel:
            fig.add_trace(go.Scatter(x=datas, y=HIST_B, name="Produto B — Histórico",
                                     line=dict(color="#f59e0b", width=2)))
            fig.add_trace(go.Scatter(x=datas_prev, y=prev_b, name="Produto B — Previsão",
                                     line=dict(color="#f59e0b", width=2, dash="dash")))

        fig.add_vline(x=pd.Timestamp("2026-01-01").timestamp() * 1000, line_dash="dot", line_color="#475569",
                      annotation_text="Início previsão", annotation_position="top left")
        fig.update_layout(height=380, margin=dict(t=20, b=20),
                          xaxis_title="Mês", yaxis_title="Caixas/mês",
                          legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown('<div class="stat-card"><div class="label">Média prev. A</div><div class="value blue">{:,.0f}</div><div style="font-size:.75rem;color:#475569">caixas/mês</div></div>'.format(MEDIA_PREV_A), unsafe_allow_html=True)
        c2.markdown('<div class="stat-card"><div class="label">Máx prev. A</div><div class="value blue">{:,.0f}</div><div style="font-size:.75rem;color:#475569">caixas/mês</div></div>'.format(MAX_PREV_A), unsafe_allow_html=True)
        c3.markdown('<div class="stat-card"><div class="label">Média prev. B</div><div class="value amber">{:,.0f}</div><div style="font-size:.75rem;color:#475569">caixas/mês</div></div>'.format(MEDIA_PREV_B), unsafe_allow_html=True)
        c4.markdown('<div class="stat-card"><div class="label">Máx prev. B</div><div class="value amber">{:,.0f}</div><div style="font-size:.75rem;color:#475569">caixas/mês</div></div>'.format(MAX_PREV_B), unsafe_allow_html=True)

        st.markdown("**Conclusão:** O modelo multiplicativo apresenta melhor desempenho (MSE menor). "
                    "A procura tem tendência crescente e sazonalidade clara — queda em Abril, pico em Setembro/Outubro. "
                    "Usa-se a **média prevista** para o dimensionamento base e o **máximo** para análise de pico.")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — PALETES
    # ════════════════════════════════════════════════════════════════════════
    with tab_paletes:
        st.markdown('<div class="section-title">Análise de Paletes — EUR 1 e EUR 2</div>', unsafe_allow_html=True)
        st.caption("A EUR 6 (meia-palete) foi excluída da análise por se destinar exclusivamente a operações de last mile / palete de loja.")

        col_pa, col_pb = st.columns(2)
        with col_pa:
            procura_a = st.number_input("Procura mensal Produto A (caixas)", value=int(MEDIA_PREV_A),
                                         min_value=1000, step=1000, key="pal_qa")
        with col_pb:
            procura_b = st.number_input("Procura mensal Produto B (caixas)", value=int(MEDIA_PREV_B),
                                         min_value=1000, step=1000, key="pal_qb")

        n_niveis = 4  # fixo -- Mecalux: 5 nivel excede 6m maximo
        st.info("**Níveis de rack: 4** (fixo) — Com base no catálogo Mecalux, o 5.º nível atingiria 6 750 mm, excedendo o máximo de 6 000 mm. O 4.º nível fica em 5 400 mm ✅")

        n_armazenagem = st.radio("Sistema de armazenagem", [2, 3],
            format_func=lambda x: "Duplo (n=2)" if x == 2 else "Triplo (n=3)",
            horizontal=True, key="pal_narma")

        AREA_MODULO = {"EUR 1": {2: 2.43, 3: 3.48}, "EUR 2": {2: 2.91, 3: 4.20}}
        PALETES_ANALISE = {"EUR 1": PALETES["EUR 1"], "EUR 2": PALETES["EUR 2"]}
        CAIXAS_PALETE_ONPALLET = {"A": {"EUR 1": 60, "EUR 2": 75}, "B": {"EUR 1": 55, "EUR 2": 70}}

        def caixas_por_palete(prod, pal):
            bh = PRODUTOS[prod]["alt"]
            n_cam = ALT_CARGA // bh
            total = CAIXAS_PALETE_ONPALLET[prod][pal]
            por_camada = total // n_cam
            peso_carga = total * PRODUTOS[prod]["peso"]
            return total, peso_carga, por_camada, 1, n_cam

        def custo_palete_mensal(procura, prod, pal, n_niv, n_arma):
            total_cx, peso, nx, ny, n_cam = caixas_por_palete(prod, pal)
            if total_cx == 0: return None
            if peso > PALETES[pal]["max_kg"]:
                total_cx = int(PALETES[pal]["max_kg"] / PRODUTOS[prod]["peso"])
            n_pal = int(np.ceil(procura / total_cx))
            area_pal = PALETES[pal]["w"] * PALETES[pal]["d"] / 1e6
            area_nec = n_pal * area_pal
            area_chao = area_nec / n_niv
            # Numero de racks (modulos) necessarios
            n_racks = int(np.ceil(n_pal / n_niv))
            area_racks = n_racks * AREA_MODULO[pal][n_arma]
            custo_constr_mes = area_chao * CUSTO_CONSTR / (VIDA_UTIL * 12)
            custo_fixo_mes   = area_nec  * CUSTO_FIXO_ANO / 12
            custo_op_mes     = area_nec  * CUSTO_OP
            custo_total = custo_constr_mes + custo_fixo_mes + custo_op_mes
            return {
                "Palete": pal, "Armazenagem": f"n={n_arma}",
                "Cx/palete": total_cx, "Nº paletes": n_pal, "Nº racks": n_racks,
                "Area modulo (m2)": AREA_MODULO[pal][n_arma],
                "Area racks (m2)": round(area_racks, 2),
                "Area chao (m2)": round(area_chao, 1),
                "Custo constr/mes (€)": round(custo_constr_mes, 2),
                "Custo fixo/mes (€)": round(custo_fixo_mes, 2),
                "Custo op/mes (€)": round(custo_op_mes, 2),
                "Custo total/mes (€)": round(custo_total, 2),
            }

        st.markdown("#### Produto A")
        rows_a_all = [custo_palete_mensal(procura_a, "A", p, n_niveis, n_armazenagem) for p in PALETES_ANALISE]
        st.dataframe(pd.DataFrame([r for r in rows_a_all if r]), use_container_width=True, hide_index=True)

        st.markdown("#### Produto B")
        rows_b_all = [custo_palete_mensal(procura_b, "B", p, n_niveis, n_armazenagem) for p in PALETES_ANALISE]
        st.dataframe(pd.DataFrame([r for r in rows_b_all if r]), use_container_width=True, hide_index=True)

        # Tabela resumo area total A+B para todos os cenarios
        st.markdown("#### Área total de armazenagem (A+B) — comparação completa")
        tabela_area = []
        for pal in PALETES_ANALISE:
            for n_arma in [2, 3]:
                ra = custo_palete_mensal(procura_a, "A", pal, n_niveis, n_arma)
                rb = custo_palete_mensal(procura_b, "B", pal, n_niveis, n_arma)
                if ra and rb:
                    tabela_area.append({
                        "Palete": pal,
                        "Armazenagem": f"n={n_arma} ({'Dupla' if n_arma==2 else 'Tripla'})",
                        "Area A (m2)": ra["Area racks (m2)"],
                        "Area B (m2)": rb["Area racks (m2)"],
                        "Area Total (m2)": round(ra["Area racks (m2)"] + rb["Area racks (m2)"], 2),
                        "Custo total/mes (€)": round(ra["Custo total/mes (€)"] + rb["Custo total/mes (€)"], 2),
                    })
        df_area = pd.DataFrame(tabela_area)
        min_area_idx = df_area["Area Total (m2)"].idxmin()
        st.dataframe(df_area, use_container_width=True, hide_index=True)

        totais_bar = {f"{r['Palete']} {r['Armazenagem']}": r["Custo total/mes (€)"] for r in tabela_area}
        fig_pal = go.Figure(data=[go.Bar(
            x=list(totais_bar.keys()), y=list(totais_bar.values()),
            marker_color=["#1e3a5f","#2563eb","#7c2d12","#dc2626"],
            text=[f"{v:,.0f} €" for v in totais_bar.values()], textposition="outside"
        )])
        fig_pal.update_layout(height=340, margin=dict(t=30, b=10),
                              yaxis_title="€/mês", showlegend=False, xaxis_tickangle=-15)
        st.plotly_chart(fig_pal, use_container_width=True)

        melhor_row = df_area.loc[min_area_idx]
        eur1_t_row = df_area[(df_area["Palete"]=="EUR 1") & (df_area["Armazenagem"].str.contains("Tripla"))]

        st.markdown("---")
        st.warning(
            f"📐 Menor área total: **{melhor_row['Palete']} {melhor_row['Armazenagem']}** — "
            f"{melhor_row['Area Total (m2)']} m²"
        )
        if not eur1_t_row.empty:
            r = eur1_t_row.iloc[0]
            st.success(
                f"✅ **Decisão final: EUR 1 (800×1200 mm) com armazenagem tripla (n=3)** — "
                f"área total {r['Area Total (m2)']} m²\n\n"
                f"Embora a {melhor_row['Palete']} {melhor_row['Armazenagem']} apresente menor área "
                f"({melhor_row['Area Total (m2)']} m² vs {r['Area Total (m2)']} m²), "
                f"a EUR 1 é o **padrão logístico dominante no mercado europeu**, assegurando "
                f"maior compatibilidade com fornecedores e clientes, menos manuseamentos e menor "
                f"risco operacional. É a solução mais adequada do ponto de vista operacional, "
                f"comercial e estratégico."
            )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 — DIMENSIONAMENTO
    # ════════════════════════════════════════════════════════════════════════
    with tab_dim:
        st.markdown('<div class="section-title">Dimensionamento do Armazém — Alínea 2.2</div>', unsafe_allow_html=True)

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            usa_max = st.radio("Procura a considerar", ["Média prevista", "Valor máximo previsto"],
                               horizontal=True, key="dim_procura")
        with col_d2:
            n_niv_dim = st.radio("Níveis de rack", [4, 5], index=1, horizontal=True, key="dim_niv")

        qa = MEDIA_PREV_A if usa_max == "Média prevista" else MAX_PREV_A
        qb = MEDIA_PREV_B if usa_max == "Média prevista" else MAX_PREV_B

        # Caixas por palete EUR1
        cx_a, _, _, _, _ = caixas_por_palete("A", "EUR 1")
        cx_b, _, _, _, _ = caixas_por_palete("B", "EUR 1")
        if cx_a > PALETES["EUR 1"]["max_kg"] // PRODUTOS["A"]["peso"]:
            cx_a = PALETES["EUR 1"]["max_kg"] // PRODUTOS["A"]["peso"]
        if cx_b > PALETES["EUR 1"]["max_kg"] // PRODUTOS["B"]["peso"]:
            cx_b = PALETES["EUR 1"]["max_kg"] // PRODUTOS["B"]["peso"]

        # Paletes — calculadas com os valores seleccionados (média ou máximo)
        n_pal_a = qa / cx_a
        n_pal_b = qb / cx_b
        n_pal_total = n_pal_a + n_pal_b
        n_pal_stock_float = n_pal_total / TURNOVER
        n_pal_stock = math.ceil(n_pal_stock_float)

        # Paletes médias (sempre usadas nos custos operacionais — independente do radio)
        n_pal_a_med = MEDIA_PREV_A / cx_a
        n_pal_b_med = MEDIA_PREV_B / cx_b
        n_pal_total_med = n_pal_a_med + n_pal_b_med  # para custo operação interno
        area_pal_eur1 = PALETES["EUR 1"]["w"] * PALETES["EUR 1"]["d"] / 1e6
        # Área de armazenamento estático (zona B) necessária
        area_b_nec = (n_pal_stock * area_pal_eur1) / n_niv_dim

        # Zona B = 17,5% da área total → área total = área_b / 0.175
        area_total_nec = area_b_nec / 0.175
        # Zona C (variável) = 7,5%
        area_c_nec = area_total_nec * 0.075

        st.markdown("#### Paletes necessárias")
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="stat-card"><div class="label">Paletes A/mês (sel.)</div><div class="value blue">{n_pal_a:,.0f}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-card"><div class="label">Paletes B/mês (sel.)</div><div class="value amber">{n_pal_b:,.0f}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-card"><div class="label">Total paletes/mês</div><div class="value">{n_pal_total:,.0f}</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="stat-card"><div class="label">Em stock (÷{TURNOVER})</div><div class="value green">{n_pal_stock:,}</div></div>', unsafe_allow_html=True)

        st.markdown(f"#### Área necessária estimada: **{area_total_nec:,.0f} m²**")

        # Comparação das 3 opções
        OPCOES = [2000, 4000, 6000]
        st.markdown("#### Comparação das 3 opções de área de armazenamento")

        rows_dim = []
        for area_arm in OPCOES:
            area_total_armaz = area_arm * 2        # D=50% do total
            area_b           = area_arm * 0.35
            area_c           = area_arm * 0.15

            # Capacidade: density scales with rack levels
            # Excel usa 4 níveis → densidade base = 3.4483 paletes/m²
            # Com 5 níveis a mesma área comporta 25% mais paletes
            DENSIDADE_BASE = 3.4482758620689657  # Excel (4 níveis)
            DENSIDADE_PAL  = DENSIDADE_BASE * (n_niv_dim / 4)
            cap_total = int(area_arm * 0.35 * DENSIDADE_PAL)

            # Fórmulas do Excel (verificadas):
            # Amortização  = área_total × custo_constr / (vida_util × 12)
            # Fixos        = área_total × custo_fixo_anual / 12
            # Op. interna  = (pal_media_total - défice) × 2 × custo_op  (entrada+saída)
            # Arrendamento = défice × custo_arr  (aluguer mensal)
            # Op. externa  = défice × custo_arr_op  (custo operacional externo)
            deficit       = max(0.0, n_pal_stock_float - cap_total)
            pal_med_total = n_pal_total_med   # sempre médias para custo operacional
            custo_amort   = area_total_armaz * CUSTO_CONSTR / (VIDA_UTIL * 12)
            custo_fixo    = area_total_armaz * CUSTO_FIXO_ANO / 12
            custo_op_int  = (pal_med_total - deficit) * 2 * CUSTO_OP
            custo_arr     = deficit * CUSTO_ARR              if deficit > 0 else 0
            custo_arr_op  = deficit * CUSTO_ARR_OP            if deficit > 0 else 0
            custo_total   = custo_amort + custo_fixo + custo_op_int + custo_arr + custo_arr_op

            rows_dim.append({
                "Área armazenamento (m²)": area_arm,
                "Área total armazém (m²)": int(area_total_armaz),
                "Cap. paletes (B+C)": cap_total,
                "Paletes em stock": n_pal_stock,
                "Défice (paletes)": deficit,
                "Amortização/mês (€)": round(custo_amort),
                "Custo fixo/mês (€)": round(custo_fixo),
                "Custo operação/mês (€)": round(custo_op_int),
                "Arrendamento/mês (€)": round(custo_arr + custo_arr_op),
                "Custo TOTAL/mês (€)": round(custo_total),
                "_adequada": True,  # todas são opções válidas (défice coberto por arrendamento)
            })

        df_dim = pd.DataFrame(rows_dim)
        adequadas = df_dim[df_dim["_adequada"]]
        melhor_area = df_dim.loc[df_dim["Custo TOTAL/mês (€)"].idxmin(), "Área armazenamento (m²)"]

        st.dataframe(df_dim.drop(columns=["_adequada"]), use_container_width=True, hide_index=True)

        # Gráfico
        fig_dim = go.Figure()
        categorias = ["Amortização/mês (€)", "Custo fixo/mês (€)", "Custo operação/mês (€)", "Arrendamento/mês (€)"]
        cores_dim  = ["#2563eb", "#0ea5e9", "#f59e0b", "#ef4444"]
        for cat, cor in zip(categorias, cores_dim):
            fig_dim.add_trace(go.Bar(name=cat.replace("/mês (€)",""),
                                     x=[f"{o} m²" for o in OPCOES],
                                     y=[r[cat] for r in rows_dim],
                                     marker_color=cor))
        fig_dim.update_layout(barmode="stack", height=360, yaxis_title="€/mês",
                              margin=dict(t=20, b=20),
                              legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_dim, use_container_width=True)

        # Dados da área recomendada para a conclusão
        row_melhor = df_dim[df_dim["Área armazenamento (m²)"] == melhor_area].iloc[0]
        deficit_melhor  = int(row_melhor["Défice (paletes)"])
        total_melhor    = int(row_melhor["Custo TOTAL/mês (€)"])
        arr_melhor      = int(row_melhor["Arrendamento/mês (€)"])
        cap_melhor      = int(row_melhor["Cap. paletes (B+C)"])

        st.markdown("### Conclusão — Área seleccionada")
        st.success(
            f"✅ **Recomenda-se o armazém de {melhor_area:,.0f} m²** "
            f"(área total: **{int(melhor_area*2):,} m²**) com um custo total de **{total_melhor:,} €/mês**."
        )

        if deficit_melhor > 0:
            st.info(
                f"ℹ️ **Estratégia híbrida — armazém próprio + arrendamento externo:**\n\n"
                f"O armazém de {melhor_area:,.0f} m² tem capacidade para **{cap_melhor:,} paletes** "
                f"em stock, mas o stock máximo previsto é de **{int(n_pal_stock):,} paletes**. "
                f"O défice de **{deficit_melhor:,} paletes** é coberto por espaço arrendado a terceiros "
                f"({CUSTO_ARR}€/palete/mês + {CUSTO_ARR_OP}€/palete operação), "
                f"representando **{arr_melhor:,} €/mês** em arrendamento.\n\n"
                f"**Porquê não construir maior?** Apesar do arrendamento, o custo total de 2.000 m² "
                f"({total_melhor:,} €/mês) é significativamente mais baixo do que 4.000 m² "
                f"({int(df_dim[df_dim['Área armazenamento (m²)']==4000]['Custo TOTAL/mês (€)'].values[0]):,} €/mês), "
                f"porque os custos fixos e de amortização de um armazém maior são muito superiores "
                f"ao custo do arrendamento externo pontual."
            )
        else:
            st.info(
                f"ℹ️ O armazém de {melhor_area:,.0f} m² cobre toda a procura máxima prevista "
                f"({cap_melhor:,} ≥ {int(n_pal_stock):,} paletes) sem necessidade de arrendamento externo."
            )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4 — LAYOUT
    # ════════════════════════════════════════════════════════════════════════
    with tab_layout:
        st.markdown('<div class="section-title">Proposta de Layout — Alínea 2.3</div>', unsafe_allow_html=True)

        # ── Parâmetros do modelo (do Excel das colegas) ───────────────────────
        import math as _math
        w   = 2.50    # largura prateleira dupla (m)
        L   = 2.90    # comprimento espaço armazenamento (m)
        h   = 4       # níveis verticais
        a   = 3.50    # largura corredor (m)
        Ch  = 0.25    # custo movimentação (€/palete)
        Cs  = 150     # custo anual por área (€/m²)
        d   = 116636  # procura anual (paletes)

        # Cp — custo anual por unidade de comprimento de parede externa
        # Cp = Cs × (h × L + w/2) / h  [fórmula do modelo]
        # Valor calculado no Excel: 316.17
        Cp = 316.17

        # Regra de escolha do layout
        CpCh   = Cp / Ch      # = 1264.7
        dCpCh2 = 2 * CpCh     # = 2529.3

        st.markdown("### Escolha do Layout")
        col_r1, col_r2 = st.columns([1, 1])
        with col_r1:
            st.markdown("**Parâmetros de configuração**")
            params = [
                ("w — Largura prateleira dupla", f"{w} m"),
                ("L — Comprimento espaço arm.", f"{L} m"),
                ("h — Níveis verticais", f"{h}"),
                ("a — Largura corredor", f"{a} m"),
                ("Ch — Custo movimentação", f"{Ch} €/palete"),
                ("Cs — Custo anual por área", f"{Cs} €/m²"),
                ("Cp — Custo parede externa", f"{Cp:.2f} €/m"),
                ("d — Procura anual", f"{d:,} paletes"),
                ("K — Cap. total armazém", "774 paletes"),
            ]
            for l, v in params:
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:0.22rem 0;'
                    f'border-bottom:1px solid #1e2130;font-size:0.8rem">'
                    f'<span style="color:#64748b;font-family:DM Mono,monospace">{l}</span>'
                    f'<span style="color:#e2e8f0;font-family:DM Mono,monospace">{v}</span></div>',
                    unsafe_allow_html=True
                )

        with col_r2:
            st.markdown("**Regra de escolha**")
            regra_rows = [
                ("Cp/Ch", f"{CpCh:,.1f}"),
                ("2×Cp/Ch", f"{dCpCh2:,.1f}"),
                ("d", f"{d:,}"),
                ("d < Cp/Ch ?", "F"),
                ("d > 2×Cp/Ch ?", "V"),
                ("Layout escolhido", "**Layout 2**"),
            ]
            for l, v in regra_rows:
                bold = l == "Layout escolhido"
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:0.22rem 0;'
                    f'border-bottom:1px solid #1e2130;font-size:0.82rem;'
                    f'{"background:#1e3a5f20;border-radius:4px;padding:0.4rem 0.5rem;" if bold else ""}">'
                    f'<span style="color:{"#60a5fa" if bold else "#64748b"}">{l}</span>'
                    f'<span style="color:{"#60a5fa" if bold else "#e2e8f0"};font-family:DM Mono,monospace">{v}</span></div>',
                    unsafe_allow_html=True
                )
            st.caption("Se d < Cp/Ch → Layout 1 | Se d > 2×Cp/Ch → Layout 2 | Se Cp/Ch ≤ d ≤ 2×Cp/Ch → inconclusivo")

        # ── Dois layouts calculados ───────────────────────────────────────────
        st.markdown("---")
        st.markdown("### Configuração dos dois layouts")

        # Layout 1: u1 = n1*(w+a), v1 = 2a + m1*L
        # m1 (espaços por prateleira), n1 (prateleiras duplas) — valores Excel
        m1, n1 = 10, 9; u1, v1 = 57, 37
        # Layout 2: u2 = 3a + m2*L, v2 = n2*(w+a)
        m2, n2 = 20, 5; u2, v2 = 69, 29

        col_l1, col_l2 = st.columns(2)
        def _layout_card(col, title, m, n, u, v, chosen=False):
            cor = "#2563eb" if chosen else "#475569"
            badge = ' <span style="background:#2563eb;color:white;font-size:0.65rem;padding:0.1rem 0.4rem;border-radius:4px;margin-left:0.5rem">✓ Escolhido</span>' if chosen else ""
            col.markdown(
                f'<div style="border:1px solid {cor};border-radius:8px;padding:1rem;margin-bottom:0.5rem">'
                f'<div style="font-size:0.95rem;font-weight:600;color:#e2e8f0;margin-bottom:0.6rem">{title}{badge}</div>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.3rem;font-size:0.8rem">'
                f'<span style="color:#64748b">m (espaços/prateleira)</span><span style="color:#e2e8f0;font-family:DM Mono,monospace">{m}</span>'
                f'<span style="color:#64748b">n (prateleiras duplas)</span><span style="color:#e2e8f0;font-family:DM Mono,monospace">{n}</span>'
                f'<span style="color:#64748b">u — Comprimento</span><span style="color:#e2e8f0;font-family:DM Mono,monospace">{u} m</span>'
                f'<span style="color:#64748b">v — Largura</span><span style="color:#e2e8f0;font-family:DM Mono,monospace">{v} m</span>'
                f'<span style="color:#64748b">Área</span><span style="color:#e2e8f0;font-family:DM Mono,monospace">{u*v} m²</span>'
                f'</div></div>',
                unsafe_allow_html=True
            )
        _layout_card(col_l1, "Layout 1", m1, n1, u1, v1, chosen=False)
        _layout_card(col_l2, "Layout 2", m2, n2, u2, v2, chosen=True)

        st.markdown("---")
        st.markdown("### Layout do armazém — Layout 2 (69m × 29m)")

        # ── Dados fixos do layout (Excel das colegas — Layout 2 escolhido) ──────
        U = 69.0
        V = 29.0
        AREA_TOTAL = U * V

        # Sub-zonas da zona D (áreas reais do Excel)
        ZONAS_D = {
            "Picking / Preparação":      {"area": 726, "comp": 36.3, "larg": 20},
            "Área de Receção e Conferência": {"area": 464, "comp": 29,   "larg": 16},
            "Área de Expedição":         {"area": 580, "comp": 29,   "larg": 20},
            "Escritórios e Áreas Sociais": {"area": 230, "comp": 11.5, "larg": 20},
        }
        TOTAL_D = sum(z["area"] for z in ZONAS_D.values())
        # Área de racks do Excel: capacidade real = 2160 paletes, área = 540 m²
        # Dimensões: comprimento = 69 - 36.3 = 32.7m, largura = 29 - 9 = 20m → 654m²
        # O Excel reporta 540m² (zona B estática)
        AREA_RACKS = 540

        # Docas
        N_DOCAS = 2

        # ── Especificações ────────────────────────────────────────────────────
        st.markdown("**Especificações do armazém (Layout 2)**")
        col_s1, col_s2 = st.columns(2)

        def _spec_row(label, val):
            return (f'<div style="display:flex;justify-content:space-between;padding:0.25rem 0;' +
                    f'border-bottom:1px solid #1e2130;font-size:0.82rem">' +
                    f'<span style="color:#64748b">{label}</span>' +
                    f'<span style="color:#e2e8f0;font-family:DM Mono,monospace">{val}</span></div>')

        with col_s1:
            for l, v in [
                ("Comprimento (u)", f"{U:.0f} m"),
                ("Largura (v)", f"{V:.0f} m"),
                ("Área total", f"{AREA_TOTAL:.0f} m²"),
                ("Zona racks", f"{AREA_RACKS:.0f} m²"),
                ("Zona D total", f"{TOTAL_D} m²"),
                ("Nº docas", f"{N_DOCAS}"),
            ]:
                st.markdown(_spec_row(l, v), unsafe_allow_html=True)

        with col_s2:
            for nome, z in ZONAS_D.items():
                st.markdown(_spec_row(nome, f"{z['area']} m²  ({z['comp']}×{z['larg']} m)"), unsafe_allow_html=True)

        st.markdown("---")

        # ── Diagrama do layout — imagem do Excel ─────────────────────────────
        st.markdown("**Diagrama do layout**")
        col_img, _ = st.columns([1, 1])
        with col_img:
            st.image("layout_armazem.png", use_container_width=True)


        # ── Tabela de zonas ───────────────────────────────────────────────────
        st.markdown("**Subdivisão das zonas**")
        df_zonas = pd.DataFrame([
            {"Zona": "Armazenamento (racks)", "Área (m²)": AREA_RACKS, "Comprimento (m)": "32,7", "Largura (m)": "9,0 (zona B)"},
            {"Zona": "Picking / Preparação",  "Área (m²)": 726,  "Comprimento (m)": "36,3", "Largura (m)": "20"},
            {"Zona": "Receção e Conferência", "Área (m²)": 464,  "Comprimento (m)": "29",   "Largura (m)": "16"},
            {"Zona": "Expedição",             "Área (m²)": 580,  "Comprimento (m)": "29",   "Largura (m)": "20"},
            {"Zona": "Escritórios e Sociais", "Área (m²)": 230,  "Comprimento (m)": "11,5", "Largura (m)": "20"},
            {"Zona": "TOTAL",                 "Área (m²)": int(AREA_TOTAL), "Comprimento (m)": f"{U:.0f}", "Largura (m)": f"{V:.0f}"},
        ])
        st.dataframe(df_zonas, use_container_width=True, hide_index=True)

        # ── Docas justificação ────────────────────────────────────────────────
        with st.expander("Nº de Docas — N = (D×H)/(C×S)", expanded=False):
            # Valores do relatório
            _D_dia   = 251   # paletes/dia (315278 / 1258 dias)
            _C55     = 20;   _H55  = 40    # camião 55m³
            _C_semi  = 33;   _H_semi = 66  # semi-reboque
            _S       = 480
            _N55   = (_D_dia * _H55)   / (_C55   * _S)
            _Nsemi = (_D_dia * _H_semi) / (_C_semi * _S)
            _Ndoc  = max(1, int(np.ceil(max(_N55, _Nsemi))))
            st.markdown(f"""
| Variável | Descrição | Valor |
|---|---|---|
| D | Cadência paletes/dia (315 278 pal ÷ 1 258 dias úteis) | **{_D_dia} pal/dia** |
| H (camião 55m³) | {_C55} pal × 2 min | **{_H55} min** |
| H (semi-reboque) | {_C_semi} pal × 2 min | **{_H_semi} min** |
| C | Capacidade camião | **{_C55} ou {_C_semi} pal** |
| S | Tempo disponível/dia | **{_S} min** |

**N (camião 55m³)** = ({_D_dia} × {_H55}) / ({_C55} × {_S}) = **{_N55:.2f} → {_Ndoc} doca(s)**

**N (semi-reboque)** = ({_D_dia} × {_H_semi}) / ({_C_semi} × {_S}) = **{_Nsemi:.2f} → {_Ndoc} doca(s)**
""")

        # ── Tecnologias ───────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Tecnologias e pressupostos**")
        tecno = [
            ("Sistema armazenamento", "Estantes porta-paletes triplas (n=3), 4 níveis — Mecalux"),
            ("Palete standard", "EUR 1 (800×1200 mm) — EPAL"),
            ("Corredor empilhador", "3,5 m (reach truck)"),
            ("Fluxo interno", "Fluxo em U — Receção → Armazenamento → Preparação → Expedição"),
            ("Movimentação", "Empilhador reach truck"),
            ("WMS", "Sistema de Gestão de Armazém — controlo de localização e turnover"),
            ("Tecnologia picking", "Pick-to-light na zona de Preparação"),
            ("Segurança", "Sprinklers, sinalização de emergência, guardas de rack"),
        ]
        for label, val in tecno:
            st.markdown(
                f'<div style="display:flex;gap:1rem;padding:0.35rem 0;border-bottom:1px solid #1e2130;font-size:0.83rem">' +
                f'<span style="color:#60a5fa;min-width:200px;font-family:DM Mono,monospace;font-size:0.78rem">{label}</span>' +
                f'<span style="color:#94a3b8">{val}</span></div>',
                unsafe_allow_html=True
            )


elif secao == "Roteamento Ibérico":
    import sys, os
    import numpy as np

    st.markdown('<div class="section-title">Parte 3 — Planeamento da Distribuição (Mercado Ibérico)</div>', unsafe_allow_html=True)
    st.write(
        "Modelo VRP com Janelas Temporais (VRP-TW) para o mercado ibérico. "
        "O CD de Espanha (Saragoça) abastece os clientes de Portugal e Espanha — "
        "22 dias/mês, entregando Produto A e B em rotas separadas."
    )

    EXCEL_DATA_PATH = Path(__file__).resolve().parent / "data" / "Tabelas_Parte_3.xlsx"

    tab_dados, tab_vrp, tab_analise = st.tabs([
        "📋 Dados do Problema",
        "🚛 Resolver VRP",
        "📊 Análise Comparativa",
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — DADOS
    # ════════════════════════════════════════════════════════════════════════
    with tab_dados:
        st.markdown("### Pressupostos do enunciado")
        pressupostos_vrp = [
            ("Tempo carga/descarga", "2 min/palete"),
            ("Tempo abastecimento veículo", "15 min"),
            ("Chegada antecipada", "Permitida — veículo espera pelo início da janela"),
            ("Preparação Produto A", "Termina às 02:00 (120 min desde meia-noite)"),
            ("Preparação Produto B", "Termina às 04:00 (240 min desde meia-noite)"),
            ("Entregas simultâneas A+B", "Não permitidas — rotas separadas por produto"),
            ("Dias de trabalho/ano", "264 dias"),
            ("Split delivery", "Permitido — procura pode ser dividida entre veículos"),
        ]
        for label, val in pressupostos_vrp:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:0.3rem 0;'
                f'border-bottom:1px solid #1e2130;font-size:0.85rem">'
                f'<span style="color:#64748b">{label}</span>'
                f'<span style="color:#e2e8f0;font-family:DM Mono,monospace">{val}</span></div>',
                unsafe_allow_html=True
            )

        st.markdown("---")

        # Verificar se Excel existe
        if not EXCEL_DATA_PATH.exists():
            st.warning(
                f"⚠️ Ficheiro de dados não encontrado: `{EXCEL_DATA_PATH}`\\n\\n"
                "Cria uma pasta `data/` na pasta do projecto e coloca lá o ficheiro `Tabelas_Parte_3.xlsx`."
            )
        else:
            st.success(f"✅ Ficheiro de dados encontrado: `{EXCEL_DATA_PATH}`")
            try:
                from solver.vrp_iberico import load_data, NODE_NAMES
                data_vrp = load_data(EXCEL_DATA_PATH)

                # Coordenadas dos nós (ordem igual ao NODE_NAMES do vrp_iberico)
                COORDS_VRP = {
                    0:  (41.330, -1.220),   # CD Saragoça
                    1:  (39.258, -7.931),   # Évora
                    2:  (37.455, -7.872),   # Faro
                    3:  (40.211, -8.410),   # Coimbra
                    4:  (40.928, -8.548),   # St Mª Feira
                    5:  (41.755, -7.473),   # Chaves
                    6:  (41.808, -6.768),   # Bragança
                    7:  (43.364, -5.849),   # Oviedo
                    8:  (39.868, -4.027),   # Toledo
                    9:  (39.477, -0.376),   # Valência
                    10: (41.652, -0.889),   # Saragoça (cliente)
                    11: (41.391,  2.172),   # Barcelona
                }

                def fmt_time(m):
                    return f"{int(m)//60:02d}:{int(m)%60:02d}"

                st.markdown("### Veículos disponíveis")
                veh_rows = []
                for vid, veh in data_vrp["vehicles"].items():
                    veh_rows.append({
                        "ID": vid, "Tipo": veh["name"],
                        "Capacidade (kg)": veh["capacity_kg"],
                        "Custo fixo/dia (€)": veh["cost_fix"],
                        "Custo variável (€/km)": veh["cost_var"],
                    })
                st.dataframe(pd.DataFrame(veh_rows), use_container_width=True, hide_index=True)

                st.markdown("### Clientes ibéricos")
                cli_rows = []
                for i in range(1, len(data_vrp["tw_early"])):
                    tw_e = data_vrp["tw_early"][i]
                    tw_l = data_vrp["tw_late"][i]
                    cli_rows.append({
                        "Cliente": NODE_NAMES[i] if i < len(NODE_NAMES) else f"Nó {i}",
                        "Procura A (kg)": data_vrp["demand_a"].get(i, 0),
                        "Procura B (kg)": data_vrp["demand_b"].get(i, 0),
                        "Janela início": fmt_time(tw_e),
                        "Janela fim": fmt_time(tw_l),
                        "Serviço A (min)": data_vrp["service_a"].get(i, 0),
                        "Serviço B (min)": data_vrp["service_b"].get(i, 0),
                    })
                st.dataframe(pd.DataFrame(cli_rows), use_container_width=True, hide_index=True)

                st.markdown("### Mapa — Clientes ibéricos e CD Saragoça")
                COORDS_VRP2rp = COORDS_VRP
                fig_map = go.Figure()
                depot = COORDS_VRP[0]
                fig_map.add_trace(go.Scattergeo(
                    lat=[depot[0]], lon=[depot[1]],
                    text=["CD — Saragoça"], mode="markers+text",
                    textposition="top center",
                    marker=dict(size=16, color="#2563eb", symbol="diamond"),
                    name="CD Saragoça",
                ))
                for i, row in enumerate(cli_rows):
                    coord = COORDS_VRP.get(i+1)
                    if coord:
                        fig_map.add_trace(go.Scattergeo(
                            lat=[coord[0]], lon=[coord[1]],
                            text=[row["Cliente"]], mode="markers+text",
                            textposition="top center",
                            marker=dict(size=9, color="#f59e0b"),
                            showlegend=(i == 0),
                            name="Clientes" if i == 0 else "",
                        ))
                if True:
                    fig_map.update_layout(
                        geo=dict(scope="europe", projection_type="mercator",
                                 showland=True, landcolor="rgb(240,240,230)",
                                 showocean=True, oceancolor="rgb(210,230,245)",
                                 showcountries=True, countrycolor="rgb(200,200,200)",
                                 lonaxis=dict(range=[-10, 5]),
                                 lataxis=dict(range=[36, 44])),
                        height=420, margin=dict(l=0, r=0, t=10, b=0),
                        legend=dict(orientation="h", y=-0.05),
                    )
                    st.plotly_chart(fig_map, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao carregar dados: {e}")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — RESOLVER VRP
    # ════════════════════════════════════════════════════════════════════════
    with tab_vrp:
        st.markdown("### Resolver VRP-TW")

        if not EXCEL_DATA_PATH.exists():
            st.warning(f"⚠️ Coloca o ficheiro `Tabelas_Parte_3.xlsx` em `data/` para activar o solver.")
        else:
            col_v, col_p = st.columns(2)
            with col_v:
                cenario = st.radio(
                    "Cenário (alínea 3.1)",
                    ["a) Só veículo id=1", "b) Só veículo id=2", "c) Frota mista (id=1 e 2)"],
                    key="vrp_cenario"
                )
            with col_p:
                produto = st.radio("Produto", ["A", "B", "A + B"], horizontal=True, key="vrp_produto")

            if st.button("▶ Resolver VRP", type="primary", key="btn_vrp"):
                try:
                    from solver.vrp_iberico import load_data, build_and_solve_vrp, compute_max_vehicles, NODE_NAMES
                    data_vrp2 = load_data(EXCEL_DATA_PATH)
                    v_ids = sorted(data_vrp2["vehicles"].keys())
                    vids_sel = ([v_ids[0]] if "a)" in cenario
                                else [v_ids[1]] if "b)" in cenario
                                else v_ids)
                    prods = ["A", "B"] if "+" in produto else [produto]

                    resultados = {}
                    for prod in prods:
                        with st.spinner(f"A resolver Produto {prod}..."):
                            n_veic = compute_max_vehicles(data_vrp2, vids_sel, prod)
                            res = build_and_solve_vrp(prod, vids_sel, n_veic, data_vrp2, verbose=False)
                            resultados[prod] = res

                    st.session_state["vrp_resultado"] = {
                        "resultados": resultados,
                        "cenario": cenario,
                        "produto": produto,
                        "vids": vids_sel,
                        "data": data_vrp2,
                    }
                except Exception as e:
                    st.error(f"Erro no solver: {e}")
                    import traceback; st.code(traceback.format_exc())

            vrp_res = st.session_state.get("vrp_resultado")
            if vrp_res:
                resultados = vrp_res["resultados"]
                data_v = vrp_res["data"]
                from solver.vrp_iberico import NODE_NAMES as _NODE_NAMES_VRP
                node_names_dict = {i: _NODE_NAMES_VRP[i] for i in range(len(_NODE_NAMES_VRP))}
                COORDS_VRP2 = {0:(41.330,-1.220),1:(39.258,-7.931),2:(37.455,-7.872),
                    3:(40.211,-8.410),4:(40.928,-8.548),5:(41.755,-7.473),6:(41.808,-6.768),
                    7:(43.364,-5.849),8:(39.868,-4.027),9:(39.477,-0.376),10:(41.652,-0.889),
                    11:(41.391,2.172)}
                _DAYS = 264

                st.markdown(f"**Cenário:** {vrp_res['cenario']}  |  **Produto:** {vrp_res['produto']}")

                # Métricas por produto
                for prod, res in resultados.items():
                    custo_d = res.get("obj", 0)
                    st.markdown(f"#### Produto {prod}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Custo diário", f"{custo_d:,.2f} €")
                    c2.metric("Custo anual", f"{custo_d * _DAYS:,.0f} €")
                    c3.metric("Nº veículos", res.get("n_vehicles_used", 0))
                    st.markdown(f"**Status:** {res.get('status','—')}")

                    # Rotas
                    if res.get("routes"):
                        for k, route in res["routes"].items():
                            with st.expander(f"Veículo {k+1} — {route['vehicle_type']} — {route['load_kg']:.0f} kg", expanded=True):
                                st.markdown(f"**Rota:** {route['route_str']}")
                                for node_idx, kg in route["client_loads"].items():
                                    st.markdown(f"&nbsp;&nbsp;↳ {node_names_dict.get(node_idx, f'Nó {node_idx}')}: {kg:.1f} kg")

                    # Mapa das rotas
                    if res.get("routes") and COORDS_VRP2:
                        fig_r = go.Figure()
                        depot = COORDS_VRP2.get(0, (41.33, -1.22))
                        fig_r.add_trace(go.Scattergeo(
                            lat=[depot[0]], lon=[depot[1]], text=["CD Saragoça"],
                            mode="markers+text", textposition="top center",
                            marker=dict(size=14, color="#2563eb", symbol="diamond"),
                            name="CD"
                        ))
                        cores_rota = ["#ef4444","#f59e0b","#10b981","#8b5cf6","#06b6d4","#f97316"]
                        for ki, (k, route) in enumerate(res["routes"].items()):
                            cor = cores_rota[ki % len(cores_rota)]
                            served = [0] + list(route["client_loads"].keys()) + [0]
                            lats = [COORDS_VRP2[n][0] for n in served if n in COORDS_VRP2]
                            lons = [COORDS_VRP2[n][1] for n in served if n in COORDS_VRP2]
                            fig_r.add_trace(go.Scattergeo(
                                lat=lats, lon=lons, mode="lines+markers",
                                line=dict(color=cor, width=2),
                                marker=dict(size=7, color=cor),
                                name=f"V{k+1} {route['vehicle_type']}"
                            ))
                            for node_idx in route["client_loads"]:
                                c = COORDS_VRP2.get(node_idx)
                                if c:
                                    fig_r.add_trace(go.Scattergeo(
                                        lat=[c[0]], lon=[c[1]],
                                        text=[node_names_dict.get(node_idx, "")],
                                        mode="markers+text", textposition="top center",
                                        marker=dict(size=8, color=cor),
                                        showlegend=False
                                    ))
                        fig_r.update_layout(
                            geo=dict(scope="europe", projection_type="mercator",
                                     showland=True, landcolor="rgb(240,240,230)",
                                     showocean=True, oceancolor="rgb(210,230,245)",
                                     showcountries=True, lonaxis=dict(range=[-10, 5]),
                                     lataxis=dict(range=[36, 44])),
                            height=420, margin=dict(l=0,r=0,t=10,b=0),
                            legend=dict(orientation="h", y=-0.05),
                        )
                        st.plotly_chart(fig_r, use_container_width=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 — ANÁLISE COMPARATIVA
    # ════════════════════════════════════════════════════════════════════════
    with tab_analise:
        st.markdown("### Análise Comparativa — Alínea 3.1")
        st.write("Compara o custo anual total (Produto A + B) para os três cenários de frota.")

        if not EXCEL_DATA_PATH.exists():
            st.warning("⚠️ Dados não disponíveis — coloca o Excel em `data/`.")
        elif "vrp_comparativo" not in st.session_state:
            st.info("Clica **Resolver todos os cenários** para gerar a comparação completa.")
            if st.button("▶ Resolver todos os cenários (a + b + c)", key="btn_vrp_all"):
                try:
                    from solver.vrp_iberico import load_data, build_and_solve_vrp, compute_max_vehicles, NODE_NAMES as _NN
                    data_all = load_data(EXCEL_DATA_PATH)
                    v_ids_all = sorted(data_all["vehicles"].keys())
                    _DAYS = 264

                    comparativo = []
                    cenarios_all = [
                        ("a) Só veículo id=1", [v_ids_all[0]]),
                        ("b) Só veículo id=2", [v_ids_all[1]]),
                        ("c) Frota mista",     v_ids_all),
                    ]
                    prog = st.progress(0)
                    total_steps = len(cenarios_all) * 2
                    step = 0
                    for label, vids in cenarios_all:
                        dia_total = 0
                        veic_a = veic_b = 0
                        for prod in ["A", "B"]:
                            n_v = compute_max_vehicles(data_all, vids, prod)
                            r = build_and_solve_vrp(prod, vids, n_v, data_all, verbose=False)
                            dia_total += r.get("obj", 0)
                            if prod == "A": veic_a = r.get("n_vehicles_used", 0)
                            else:           veic_b = r.get("n_vehicles_used", 0)
                            step += 1
                            prog.progress(step / total_steps)
                        comparativo.append({
                            "Cenário": label,
                            "Custo diário A+B (€)": round(dia_total, 2),
                            "Custo anual A+B (€)": round(dia_total * _DAYS, 0),
                            "Veículos Produto A": veic_a,
                            "Veículos Produto B": veic_b,
                        })
                    st.session_state["vrp_comparativo"] = comparativo
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")
        else:
            comparativo = st.session_state["vrp_comparativo"]
            df_comp = pd.DataFrame(comparativo)
            st.dataframe(df_comp, use_container_width=True, hide_index=True)

            # Gráfico comparativo
            fig_comp = go.Figure(data=[go.Bar(
                x=[r["Cenário"] for r in comparativo],
                y=[r["Custo anual A+B (€)"] for r in comparativo],
                marker_color=["#2563eb","#0ea5e9","#10b981"],
                text=[f"{r['Custo anual A+B (€)']:,.0f} €" for r in comparativo],
                textposition="outside",
            )])
            fig_comp.update_layout(
                height=340, yaxis_title="€/ano", showlegend=False,
                margin=dict(t=30, b=10),
                plot_bgcolor="#0f1117", paper_bgcolor="#0f1117",
            )
            st.plotly_chart(fig_comp, use_container_width=True)

            melhor_c = min(comparativo, key=lambda r: r["Custo anual A+B (€)"])
            st.success(
                f"✅ **Melhor opção: {melhor_c['Cenário']}** — "
                f"custo anual de **{melhor_c['Custo anual A+B (€)']:,.0f} €** "
                f"({melhor_c['Veículos Produto A']} veíc. Produto A + "
                f"{melhor_c['Veículos Produto B']} veíc. Produto B por dia)"
            )

            if st.button("🔄 Limpar e recalcular", key="btn_vrp_clear"):
                del st.session_state["vrp_comparativo"]
                st.rerun()