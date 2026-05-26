import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    try:
        st.image("Logo_bogoapts_dashboard.PNG", use_container_width=True)
    except:
        st.caption("🏢 *Subir 'Logo_bogoapts_dashboard.PNG' a GitHub para activar el logo personalizado*")
        
    st.markdown("## 📊 Control de Paid Media")
    st.write("Propiedad: **BogoApts**")
    st.markdown("---")
    mes_seleccionado = st.selectbox("📅 Seleccione el Mes de Reporte:", options=meses_disponibles)

# Fragmentación del periodo seleccionado para las bitácoras de negocio internas
partes_mes = mes_seleccionado.split(" ")
mes_nombre_inf = partes_mes[0].lower().strip()
ano_numero_inf = partes_mes[1].strip()

# ==========================================================
# SECCIÓN 1: PROCESAMIENTO EXCLUSIVO DE DATOS (BACKEND)
# ==========================================================

# --- BLOQUE PACING DIARIO ---
url_base_pacing = "https://docs.google.com/spreadsheets/d/1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0/"
url_pacing = get_csv_url_by_sheet(url_base_pacing, mes_seleccionado)

presupuesto_mensual = "$0"
gasto_total_calculado = 0
fecha_update = "N/D"
df_limpio_pacing = pd.DataFrame()
pacing_exitoso = False

try:
    df_raw_pacing = pd.read_csv(url_pacing, header=None, dtype=str).fillna('')
    idx_header = 2 
    
    for i in range(idx_header + 1):
        if i >= len(df_raw_pacing): break
        fila = df_raw_pacing.iloc[i].astype(str).tolist()
        for j, celda in enumerate(fila):
            celda_limpia = celda.lower().strip()
            if 'approved' in celda_limpia or 'aprobado' in celda_limpia:
                if j + 1 < len(fila) and fila[j+1].strip() not in ['', 'nan', '<na>']:
                    presupuesto_mensual = fila[j+1].strip()
                break
        if presupuesto_mensual != "$0":
            break

    df_datos_pacing = df_raw_pacing.iloc[idx_header + 1:].copy()
    col_idx_medio = 0; col_idx_camp = 1; col_idx_status = 4
    col_idx_spend = 7; col_idx_res
