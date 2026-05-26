import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import urllib.parse

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

# ==========================================================
# BACKEND: CONTROL DIARIO DE PAUTA (NÚCLEO INMUNE)
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
    
    # Búsqueda de presupuesto
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
    
    # Índices de columnas clave
    col_idx_medio = 0
    col_idx_camp = 1
    col_idx_status = 4    # AQUÍ ESTÁ EL ESTADO DE LA CAMPAÑA
    col_idx_spend = 7
    col_idx_res = 14
    col_idx_tipo = 15
    col_idx_cpa = 17
    col_idx_fecha = 18

    # Búsqueda de fecha de actualización
    if len(df_datos_pacing) > 0 and len(df_raw_pacing.columns) > col_idx_fecha:
        for row_pos in range(len(df_raw_pacing) - 1, idx_header, -1):
            val_celda = str(df_raw_pacing.iloc[row_pos, col_idx_fecha]).strip()
            val_lower = val_celda.lower()
            if val_celda != '' and val_lower not in ['nan', 'none', '<na>', '-', 'null', 'total']:
                if not any(k in val_lower for k in ['actualiz', 'pacing', 'fecha', 'campaign', 'nombre']):
                    fecha_update = val_celda
                    break

    # Procesamiento de filas
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
    
    if not df_limpio_pacing.empty:
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
    st.error(f"Error procesando datos de Pauta: {e}")


# ==========================================================
# RENDERIZADO VISUAL UNIFICADO
# ==========================================================
st.title(f"🏢 Sistema Inteligente BogoApts: {mes_seleccionado.title()}")

if pacing_exitoso:
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

    st.header("📊 Distribución por Canal y Objetivo")
    df_plot = df_limpio_pacing[df_limpio_pacing['Gasto'] > 0]
    if not df_plot.empty:
        fig = px.treemap(df_plot, path=['Medio_Labels', 'Objetivo'], values='Gasto', color='Gasto', color_continuous_scale=['#d6b58e', '#5b3f8e'])
        fig.update_traces(texttemplate="<b>%{label}</b><br>$%{value:,.0f}", hovertemplate="<b>%{label}</b><br>Inversión: $%{value:,.0f}<extra></extra>", textposition="middle center")
        fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No se detectan datos de gasto mayores a $0 para graficar.")

    with st.expander("📝 Detalle General de Campañas"):
        st.dataframe(df_limpio_pacing[['Medio', 'Campaña', 'Estado', 'Objetivo', 'Resultados', 'CPA']].sort_values(by='Medio'), use_container_width=True, hide_index=True)
else:
    st.error("No se pudieron cargar los datos de rendimiento de pauta. Revisa la URL y los permisos.")

st.caption(f"BogoApts Real Estate Analytics | Strategic Analytics by goBIG")
