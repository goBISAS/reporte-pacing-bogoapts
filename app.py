import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import urllib.parse
import re

# CONFIGURACIÓN PREMIUM
st.set_page_config(
    page_title="BogoApts Dashboard",
    page_icon="🏢",
    layout="wide"
)

# ESTILOS GO BIG
st.markdown("""
    <style>
    .main { background-color: #0d0d0d; }
    [data-testid="stMetricValue"] { 
        font-size: 32px; 
        color: #d6b58e !important; 
        font-weight: 700; 
    }
    h1, h2, h3 { 
        color: #ffffff; 
        font-family: 'Georgia', serif; 
    }
    .stSidebar { background-color: #1a1a1a; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE MESES ---
def obtener_meses():
    meses_es = [
        "enero", "febrero", "marzo", "abril", 
        "mayo", "junio", "julio", "agosto", 
        "septiembre", "octubre", "noviembre", 
        "diciembre"
    ]
    start_y, start_m = 2026, 5
    now = datetime.now()
    lista = []
    ano, mes = start_y, start_m
    while (ano < now.year) or (
        ano == now.year and mes <= now.month
    ):
        lista.append(f"{meses_es[mes-1]} {ano}")
        if mes == 12:
            mes = 1
            ano += 1
        else:
            mes += 1
    return list(reversed(lista))

def get_csv_url(url, sheet_name):
    try:
        p1 = url.split("/d/")[1]
        id_pub = p1.split("/")[0]
        sheet_enc = urllib.parse.quote(sheet_name)
        return f"https://docs.google.com/spreadsheets/d/{id_pub}/gviz/tq?tqx=out:csv&sheet={sheet_enc}"
    except:
        return url

# --- CONTROLES SIDEBAR ---
meses_disponibles = obtener_meses()
with st.sidebar:
    try:
        st.image(
            "Logo_bogoapts_dashboard.PNG", 
            use_container_width=True
        )
    except:
        st.caption("🏢 *Dashboard BogoApts*")
        
    mes_sel = st.selectbox(
        "📅 Seleccione Mes:", 
        options=meses_disponibles
    )

partes = mes_sel.split(" ")
mes_nom = partes[0].lower().strip()
ano_num = partes[1].strip()

# ==========================================
# BACKEND - PROCESAMIENTO LINEAL PROTEGIDO
# ==========================================

# --- PACING DE PAUTA DIARIA ---
url_pacing_base = "https://docs.google.com/spreadsheets/d/1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0/"
url_pacing = get_csv_url(url_pacing_base, mes_sel)

presupuesto_mensual = "$0"
gasto_total = 0
fecha_update = "N/D"
df_pacing = pd.DataFrame()
pacing_ok = False

try:
    df_r_pacing = pd.read_csv(
        url_pacing, 
        header=None, 
        dtype=str
    ).fillna('')
    
    # Lectura segura de presupuesto aprobado
    for i in range(min(5, len(df_r_pacing))):
        fila = [
            str(x).lower().strip() 
            for x in df_r_pacing.iloc[i].tolist()
        ]
        if 'approved' in fila:
            idx = fila.index('approved')
            presupuesto_mensual = str(
                df_r_pacing.iloc[i, idx + 1]
            ).strip()
            break
        if 'aprobado' in fila:
            idx =
