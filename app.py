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

# Fragmentación del periodo seleccionado para las bitácoras internas
partes_mes = mes_seleccionado.split(" ")
mes_nombre_inf = partes_mes[0].lower().strip()
ano_numero_inf = partes_mes[1].strip()

# ==========================================================
# FUENTE 1: CONTROL DIARIO DE PAUTA (EL NÚCLEO INMUNE CERRADO)
# ==========================================================
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
    col_idx_spend = 7; col_idx_res = 14; col_idx_tipo = 15; col_idx_cpa = 17; col_idx_fecha = 18

    if len(df_datos_pacing) > 0 and len(df_raw_pacing.columns) > col_idx_fecha:
        for row_pos in range(len(df_raw_pacing) - 1, idx_header, -1):
            val_celda = str(df_raw_pacing.iloc[row_pos, col_idx_fecha]).strip()
            val_lower = val_celda.lower()
            if val_celda != '' and val_lower not in ['nan', 'none', '<na>', '-', 'null', 'total']:
                if not any(k in val_lower for k in ['actualiz', 'pacing', 'fecha', 'campaign', 'nombre']):
                    fecha_update = val_celda
                    break

    lista_campanas = []
    for idx, row in df_datos_pacing.iterrows():
        if len(row) <= max(col_idx_camp, col_idx_medio): continue
        celda_camp = str(row[col_idx_camp]).strip()
        celda_medio = str(row[col_idx_medio]).strip()
        if celda_camp == '' or any(k in celda_camp.lower() for k in ['campaign', 'campaña', 'nombre de la', 'total']):
            continue
        celda_status = str(row[col_idx_status]).strip() if len(row) > col_idx_status else 'N/D'
        if celda_status == '': celda_status = 'N/D'
        celda_spend = str(row[col_idx_spend]).strip() if len(row) > col_idx_spend else '0'
        celda_tipo = str(row[col_idx_tipo]).strip() if len(row) > col_idx_tipo else 'General'
        if celda_tipo == '': celda_tipo = 'Sin Objetivo'
        celda_res = str(row[col_idx_res]).strip() if len(row) > col_idx_res else 'N/D'
        celda_cpa = str(row[col_idx_cpa]).strip() if len(row) > col_idx_cpa else 'N/D'

        lista_campanas.append({
            'Medio_Raw': celda_medio, 'Campaña': celda_camp, 'Estado': celda_status,
            'Gasto_Raw': celda_spend, 'Objetivo': celda_tipo, 'Resultados': celda_res, 'CPA': celda_cpa
        })

    df_limpio_pacing = pd.DataFrame(lista_campanas)
    df_limpio_pacing['Medio_Raw'] = df_limpio_pacing['Medio_Raw'].replace(['', 'nan', 'NaN'], pd.NA)
    df_limpio_pacing['Medio'] = df_limpio_pacing['Medio_Raw'].ffill().fillna('Sin Medio')
    df_limpio_pacing['Gasto'] = df_limpio_pacing['Gasto_Raw'].str.replace(r'[^\d.-]', '', regex=True)
    df_limpio_pacing['Gasto'] = pd.to_numeric(df_limpio_pacing['Gasto'], errors='coerce').fillna(0)

    resumen_medios = df_limpio_pacing.groupby('Medio')['Gasto'].sum()
    mapa_medios = {med: f"{med} (${tot:,.0f})" for med, tot in resumen_medios.items()}
    df_limpio_pacing['Medio_Labels'] = df_limpio_pacing['Medio'].map(mapa_medios).astype(str)
    gasto_total_calculado = df_limpio_pacing['Gasto'].sum()
    pacing_exitoso = True
except Exception as e:
    st.error(f"Error detectado en el Módulo de Pacing: {e}")

# ==========================================================
# FUENTE 2: BITÁCORA DEL ROAS (BLOQUES PERFECTAMENTE CERRADOS)
# ==========================================================
url_roas_csv = "https://docs.google.com/spreadsheets/d/190FjfTc6ZsAsRsj3swki1Ch6BME6j2CbfgyxcUt1pY/gviz/tq?tqx=out:csv&gid=0"

inv_roas_mes = "$0"; ventas_roas_mes = "$0"; roas_real = "0.0"; roas_esperado = "0.0"
cumplimiento_roas = "0.0%"; leads_mes = "0"; cotizaciones_mes = "0"; cierres_mes = "0"
roas_exitoso = False

try:
    df_raw_roas = pd.read_csv(url_roas_csv, header=None, dtype=str).fillna('')
    
    # 1. Bloque Superior
    filas_superior = []
    for r_idx in range(3, min(31, len(df_raw_roas))):
        filas_superior.append(df_raw_roas.iloc[r_idx].astype(str).tolist())
    
    df_sup = pd.DataFrame(filas_superior)
    if not df_sup.empty:
        df_sup[0] = df_sup[0].str.strip().replace(['', 'nan'], pd.NA).ffill() 
        df_sup[1] = df_sup[1].str.lower().str.strip()
        
        fila_mes_sup = df_sup[(df_sup[0] == ano_numero_inf) & (df_sup[1] == mes_nombre_inf)]
        if not fila_mes_sup.empty:
            inv_roas_mes = fila_mes_sup.iloc[0, 2].strip()          
            ventas_roas_mes = fila_mes_sup.iloc[0, 3].strip()       
            roas_real = fila_mes_sup.iloc[0, 4].strip()             
            roas_esperado = fila_mes_sup.iloc[0, 6].strip()         
            cumplimiento_roas = fila_mes_sup.iloc[0, 7].strip()     

    # 2. Bloque Inferior
    filas_inferior = []
    for r_idx in range(32, len(df_raw_roas)):
        filas_inferior.append(df_raw_roas.iloc[r_idx].astype(str).tolist())
        
    df_inf = pd.DataFrame(filas_inferior)
    if not df_inf.empty:
        df_inf[0] = df_inf[0].str.strip().replace(['', 'nan'], pd.NA).ffill() 
        df_inf[1] = df_inf[1].str.lower().str.strip()
        
        fila_mes_inf = df_inf[(df_inf[0] == ano_numero_inf) & (df_inf[1] == mes_nombre_inf)]
        if not fila_mes_inf.empty:
            leads_mes = fila_mes_inf.iloc[0, 8].strip()             
            cotizaciones_mes = fila_mes_inf.iloc[0, 9].strip()       
            cierres_mes = fila_mes_inf.iloc[0, 10].strip()           
            
    roas_exitoso = True
except Exception as e:
    pass


# ==========================================================
# RENDERIZADO
