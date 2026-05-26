import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import urllib.parse
import re

# CONFIGURACIÓN GENERAL
st.set_page_config(
    page_title="BogoApts",
    page_icon="🏢",
    layout="wide"
)

# ESTILOS PREMIUM GO BIG
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
    </style>
    """, unsafe_allow_html=True)

# --- MANEJO DE PERIODOS ---
def obtener_meses():
    m_list = [
        "enero", "febrero", "marzo", "abril", 
        "mayo", "junio", "julio", "agosto", 
        "septiembre", "octubre", "noviembre", 
        "diciembre"
    ]
    ano, mes = 2024, 12
    now = datetime.now()
    lista = []
    while (ano < now.year) or (ano == now.year and mes <= now.month):
        lista.append(f"{m_list[mes-1]} {ano}")
        if mes == 12:
            mes = 1
            ano += 1
        else:
            mes += 1
    return list(reversed(lista))

def format_url_pacing(doc_id, name):
    enc = urllib.parse.quote(name)
    b = "https://docs.google.com/spreadsheets/d/"
    return f"{b}{doc_id}/gviz/tq?tqx=out:csv&sheet={enc}"

def parse_num(val):
    txt = str(val).strip().replace('$', '')
    if '.' in txt and ',' not in txt:
        pt = txt.split('.')
        if len(pt) > 2 or (len(pt) == 2 and len(pt[1]) == 3):
            txt = txt.replace('.', '')
    txt = txt.replace(',', '')
    txt = re.sub(r'[^\d.-]', '', txt)
    try:
        return float(txt) if txt != '' else 0.0
    except:
        return 0.0

def normalizar_mes_abrev(txt_mes):
    t = str(txt_mes).lower().strip()
    mapeo = {
        'ene': 'enero', 'feb': 'febrero', 'mar': 'marzo',
        'abr': 'abril', 'may': 'mayo', 'jun': 'junio',
        'jul': 'julio', 'ago': 'agosto', 'sep': 'septiembre',
        'oct': 'octubre', 'nov': 'noviembre', 'dic': 'diciembre'
    }
    return mapeo.get(t, t)

# --- BARRA LATERAL ---
meses_disponibles = obtener_meses()
with st.sidebar:
    try:
        st.image("Logo_bogoapts_dashboard.PNG", use_container_width=True)
    except:
        st.caption("🏢 *BogoApts*")
    mes_sel = st.selectbox("📅 Mes Control Pauta:", options=meses_disponibles)

# ==========================================
# BACKEND - PROCESAMIENTO DE FUENTES
# ==========================================

# 1. RENDIMIENTO DE PAUTA MENSUAL OPERATIVO
id_pacing = "1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0"
url_pacing = format_url_pacing(id_pacing, mes_sel)

presupuesto_mensual = "$0"
gasto_total = 0
fecha_update = "N/D"
df_pacing = pd.DataFrame()
pacing_ok = False

try:
    df_r_pacing = pd.read_csv(url_pacing, header=None, dtype=str).fillna('')
    for i in range(min(5, len(df_r_pacing))):
        f = [str(x).lower().strip() for x in df_r_pacing.iloc[i].tolist()]
        if 'approved' in f or 'aprobado' in f:
            idx = f.index('approved') if 'approved' in f else f.index('aprobado')
            if idx + 1 < len(f):
                presupuesto_mensual = str(df_r_pacing.iloc[i, idx + 1]).strip()
            break

    df_d_pacing = df_r_pacing.iloc[3:].copy()
    if len(df_r_pacing.columns) > 18:
        for r in range(len(df_r_pacing)-1, 2, -1):
            val = str(df_r_pacing.iloc[r, 18]).strip()
            if val != '' and 'total' not in val.lower():
                fecha_update = val
                break

    lista_p = []
    for idx, row in df_d_pacing.iterrows():
        if len(row) <= 4: continue
        c_camp = str(row[1]).strip()
        c_medio = str(row[0]).strip()
        if c_camp == '' or 'campaign' in c_camp.lower() or 'total' in c_camp.lower(): continue
        
        lista_
