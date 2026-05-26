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
        st.caption("🏢 *Subir 'Logo_bogoapts_dashboard.PNG'*")
        
    st.markdown("## 📊 Control de Paid Media")
    st.write("Propiedad: **BogoApts**")
    st.markdown("---")
    mes_seleccionado = st.selectbox("📅 Seleccione el Mes de Reporte:", options=meses_disponibles)

# Fragmentación para consultas comerciales internas
partes_mes = mes_seleccionado.split(" ")
mes_nombre_inf = partes_mes[0].lower().strip()
ano_numero_inf = partes_mes[1].strip()


# ==========================================================
# SECCIÓN 1: BACKEND - EXTRACCIÓN Y PROCESAMIENTO
# ==========================================================

# --- PACING DIARIO DE PAUTA ---
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
    
    # Búsqueda ultra corta y segura de presupuesto
    for i in range(min(5, len(df_raw_pacing))):
        fila = [str(x).lower().strip() for x in df_raw_pacing.iloc[i].tolist()]
        if 'approved' in fila or 'aprobado' in fila:
            idx_target = fila.index('approved') if 'approved' in fila else fila.index('aprobado')
            if idx_target + 1 < len(fila):
                presupuesto_mensual = str(df_raw_pacing.iloc[i, idx_target + 1]).strip()
            break

    df_datos_pacing = df_raw_pacing.iloc[idx_header + 1:].copy()
    
    col_idx_medio = 0
    col_idx_camp = 1
    col_idx_status = 4
    col_idx_spend = 7
    col_idx_res = 14
    col_idx_tipo = 15
    col_idx_cpa = 17
    col_idx_fecha = 18

    if len(df_datos_pacing) > 0 and len(df_raw_pacing.columns) > col_idx_fecha:
        for row_pos in range(len(df_raw_pacing) - 1, idx_header, -1):
            val_celda = str(df_raw_pacing.iloc[row_pos, col_idx_fecha]).strip()
            val_lower =
