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

# --- CONEXIÓN DINÁMICA CON LA URL TEXTUAL CORREGIDA ---
url_base = "https://docs.google.com/spreadsheets/d/1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0/"
url_pacing = get_csv_url_by_sheet(url_base, mes_seleccionado)

try:
    # Carga cruda del documento sin asumir nombres de columnas
    df_raw = pd.read_csv(url_pacing, header=None, dtype=str).fillna('')
    
    # Definición de fila base de inicio (Los datos duros de campañas empiezan después de la fila 3)
    idx_header = 2 
    
    # 1. LECTURA DEL PRESUPUESTO APROBADO (Buscado dinámicamente en las celdas superiores)
    presupuesto_mensual = "$0"
    for i in range(idx_header + 1):
        fila = df_raw.iloc[i].astype(str).tolist()
        for j, celda in enumerate(fila):
            celda_limpia = celda.lower().strip()
            if 'approved' in celda_limpia or 'aprobado' in celda_limpia:
                if j + 1 < len(fila) and fila[j+1].strip() not in ['', 'nan', '<na>']:
                    presupuesto_mensual = fila[j+1].strip()
                break
        if presupuesto_mensual != "$0":
            break

    # 2. CAPTURA DE MATRIZ DE DATOS REALES DE BOGOAPTS
    df_datos = df_raw.iloc[idx_header + 1:].copy()
    
    # Asignación de índices fijos según la estructura visual de BogoApts
    col_idx_medio = 0  # Columna A: Medio
    col_idx_camp = 1   # Columna B: Nombre de la campaña
    col_idx_spend = 7  # Columna H: Inversión (COP)
    col_idx_res = 14   # Columna O: Platform Conversions
    col_idx_tipo = 15  # Columna P: Official Conversions
    col_idx_cpa = 17   # Columna R: CPA
    col_idx_fecha = 18 # Columna S: Actualizacion Pacing

    # 3. EXTRACCIÓN INVERSA DE FECHA DE ACTUALIZACIÓN (Columna S)
    fecha_update = "N/D"
    if len(df_datos) > 0 and len(df_raw.columns) > col_idx_fecha:
        for row_pos in range(len(df_raw) - 1, idx_header, -1):
            val_celda = str(df_raw.iloc[row_pos, col_idx_fecha]).strip()
            val_lower = val_celda.lower()
            
            if val_celda != '' and val_lower not in ['nan', 'none', '<na>', '-', 'null', 'total']:
                if not any(k in val_lower for k in ['actualiz', 'pacing', 'fecha', 'campaign', 'nombre']):
                    fecha_update = val_celda
                    break

    # 4. CONSTRUCCIÓN ASIGNADA DEL DATAFRAME PROCESADO
    df_limpio = pd.DataFrame()
    df_limpio['Campaña'] = df_datos.iloc[:, col_idx_camp].astype(str).str.strip()
    df_limpio['Medio'] = df_datos.iloc[:, col_idx_medio].astype(str).str.strip()
    df_limpio['Gasto_Raw'] = df_datos.iloc[:, col_idx_spend].astype(str).str.strip()
    
    if len(df_datos.columns) > col_idx_tipo:
        df_limpio['Objetivo'] = df_datos.iloc[:, col_idx_tipo].astype(str).str.strip().replace('', 'Sin Objetivo')
    else:
        df_limpio['Objetivo'] = 'General'
        
    df_limpio['Resultados'] = df_datos.iloc[:, col_idx_res].astype(str).str.strip() if len(df_datos.columns) > col_idx_res else 'N/D'
    df_limpio['CPA'] = df_datos.iloc[:, col_idx_cpa].astype(str).str.strip() if len(df_datos.columns) > col_idx_cpa else 'N/D'

    # 5. LIMPIEZA DE FILAS EN BLANCO Y TOTALES DE CONTROL
    df_limpio = df_limpio[df_limpio['Campaña'] != '']
    df_limpio = df_limpio[~df_limpio['Campaña'].str.upper().str.contains('TOTAL')]
    df_limpio = df_limpio[~df_limpio['Campaña'].str.lower().str.contains('campaign|campaña|nombre de la')]

    # Agrupación y formateo numérico del gasto
    df_limpio['Medio'] = df_limpio['Medio'].replace(['', 'nan', 'NaN'], pd.NA).ffill().fillna('Sin Medio')
    df_limpio['Gasto'] = df_limpio['Gasto_Raw'].str.replace(r'[^\d.-]', '', regex=True)
    df_limpio['Gasto'] = pd.to_numeric(df_limpio['Gasto'], errors='coerce').fillna(0)

    # Cálculo para las etiquetas de los gráficos
    resumen_medios = df_limpio.groupby('Medio')['Gasto'].sum()
    mapa_medios = {med: f"{med} (${tot:,.0f})" for med, tot in resumen_medios.items()}
    df_limpio['Medio_Labels'] = df_limpio['Medio'].map(mapa_medios).astype(str)
    gasto_total_calculado = df_limpio['Gasto'].sum()

    # --- INTERFAZ VISUAL ---
    st.title(f"🏢 Dashboard Gerencial BogoApts: {mes_seleccionado.title()}")
    
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Presupuesto Mensual", f"{presupuesto_mensual}")
    with c2: st.metric("Inversión Ejecutada", f"${gasto_total_calculado:,.0f}")
    with c3:
        if mes_seleccionado == meses_disponibles[0]:
            st.metric("Día de Medición", f"Día {datetime.now().day}")
        else:
            st.metric("Estado del Mes", "Cerrado")

    st.success(f"✅ Sincronización exitosa con la pestaña [{mes_seleccionado}] | Último registro: {fecha_update}")
    st.divider()

    # --- VISUALIZACIÓN TREEMAP ---
    st.header("📊 Distribución por Canal y Objetivo")
    df_plot = df_limpio[df_limpio['Gasto'] > 0]
    if not df_plot.empty:
        fig = px.treemap(df_plot, path=['Medio_Labels', 'Objetivo'], values='Gasto', color='Gasto', color_continuous_scale=['#d6b58e', '#5b3f8e'])
        fig.update_traces(texttemplate="<b>%{label}</b><br>$%{value:,.0f}", hovertemplate="<b>%{label}</b><br>Inversión: $%{value:,.0f}<extra></extra>", textposition="middle center")
        fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No se detectan datos de gasto mayores a $0 para graficar en este periodo.")

    # --- TABLA CONTROL ---
    with st.expander("📝 Detalle General de Campañas"):
        st.dataframe(df_limpio[['Medio', 'Campaña', 'Objetivo', 'Resultados', 'CPA']].sort_values(by='Medio'), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error detectado en el procesamiento de datos: {e}")

st.caption(f"BogoApts Real Estate Analytics | Strategic Analytics by goBIG")
