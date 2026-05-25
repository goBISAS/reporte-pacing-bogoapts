import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import urllib.parse
import re

# CONFIGURACIÓN DE PÁGINA PREMIUM
st.set_page_config(
    page_title="BogoApts - Paid Media Dashboard",
    page_icon="🏢",
    layout="wide"
)

# ESTILOS PREMIUM GO BIG
st.markdown("""
    <style>
    .main { background-color: #0d0d0d; }
    [data-testid="stMetricValue"] { font-size: 32px; color: #d6b58e !important; font-weight: 700; }
    [data-testid="stMetricLabel"] { color: #f5f5f5 !important; }
    h1, h2, h3 { color: #ffffff; font-family: 'Georgia', serif; }
    .stSidebar { background-color: #1a1a1a; border-right: 1px solid #333; }
    .stPlotlyChart { border: 1px solid #333; border-radius: 8px; background-color: #1a1a1a; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA HISTÓRICA DE MESES ---
def obtener_meses_disponibles():
    meses_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    start_year, start_month = 2026, 5
    now = datetime.now()
    lista = []
    ano, mes = start_year, start_month
    while (ano < now.year) or (ano == now.year and mes <= now.month):
        lista.append(f"{meses_es[mes-1]} {ano}")
        if mes == 12:
            mes = 1
            ano += 1
        else:
            mes += 1
    return list(reversed(lista))

def get_csv_url_by_sheet(url, sheet_name):
    try:
        id_publicacion = url.split("/d/")[1].split("/")[0]
        sheet_enc = urllib.parse.quote(sheet_name)
        return f"https://docs.google.com/spreadsheets/d/{id_publicacion}/gviz/tq?tqx=out:csv&sheet={sheet_enc}"
    except:
        return url

# --- SIDEBAR CONTROL ---
meses_disponibles = obtener_meses_disponibles()
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=150", use_container_width=True)
    st.markdown("## 📊 Control de Paid Media")
    st.write("Propiedad: **BogoApts**")
    st.markdown("---")
    mes_seleccionado = st.selectbox("📅 Seleccione el Mes de Reporte:", options=meses_disponibles)

# --- CONEXIÓN DINÁMICA CON LA URL TEXTUAL VERIFICADA ---
url_base = "https://docs.google.com/spreadsheets/d/1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0/"
url_pacing = get_csv_url_by_sheet(url_base, mes_seleccionado)

try:
    df_raw = pd.read_csv(url_pacing, header=None, dtype=str).fillna('')
    
    # 1. RADAR: Buscar la fila de encabezados
    idx_header = None
    for i, row in df_raw.iterrows():
        valores_fila = [str(x).lower() for x in row.tolist()]
        if any(k in val for val in valores_fila for k in ['campaign', 'campaña', 'canal']):
            idx_header = i
            break
    
    if idx_header is None:
        st.error(f"⚠️ Estructura de campaña no localizada en la pestaña '{mes_seleccionado}'.")
        st.stop()

    # 2. LECTURA DEL PRESUPUESTO APROBADO
    presupuesto_mensual = "$0"
    for i in range(idx_header):
        fila = df_raw.iloc[i].astype(str).tolist()
        for j, celda in enumerate(fila):
            celda_limpia = celda.lower().strip()
            if 'approved' in celda_limpia or 'aprobado' in celda_limpia:
                if j + 1 < len(fila) and fila[j+1].strip() not in ['', 'nan', '<na>']:
                    presupuesto_mensual = fila[j+1].strip()
                break
        if presupuesto_mensual != "$0":
            break

    # 3. CONSTRUCCIÓN DE MATRIZ DE DATOS (Estructura fija posicional)
    df_datos = df_raw.iloc[idx_header + 1:].copy()
    
    col_idx_medio = 0  # Columna A: Canal
    col_idx_camp = 1   # Columna B: Campaign
    col_idx_spend = 7  # Columna H: Spend (COP)
    col_idx_tipo = 15  # Columna P: Official Conversions
    col_idx_res = 14   # Columna O: Platform Conversions
    col_idx_cpa = 17   # Columna R: CPA
    col_idx_fecha = 18 # Columna S: Actualizacion Pacing

    # 4. EXTRACCIÓN INVERSA DE FECHA DE ACTUALIZACIÓN
    fecha_update = "N/D"
    if len(df_datos) > 0 and len(df_raw.columns) > col_idx_fecha:
        for row_pos in range(len(df_raw) - 1, idx_header,
