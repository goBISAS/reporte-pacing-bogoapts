import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import urllib.parse
import re

# CONFIGURACIÓN PREMIUM
st.set_page_config(
    page_title="BogoApts",
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
    </style>
    """, unsafe_allow_html=True)

# --- MESES DISPONIBLES (PARA PAUTA) ---
def obtener_meses():
    m_list = [
        "enero", "febrero", "marzo", "abril", 
        "mayo", "junio", "julio", "agosto", 
        "septiembre", "octubre", "noviembre", 
        "diciembre"
    ]
    ano = 2026
    mes = 5
    now = datetime.now()
    lista = []
    while (ano < now.year) or (
        ano == now.year and mes <= now.month
    ):
        lista.append(f"{m_list[mes-1]} {ano}")
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
        base = "https://docs.google.com/spreadsheets/d/"
        return f"{base}{id_pub}/gviz/tq?tqx=out:csv&sheet={sheet_enc}"
    except:
        return url

def limpiar_moneda(texto):
    """Limpia cadenas con formato de moneda (ej: $62.610.165 o 62,610,165) a float puro"""
    txt = str(texto).strip().replace('$', '')
    # Si contiene puntos de miles (ej: 62.610.165), los eliminamos
    if '.' in txt and ',' not in txt:
        # Validar si es punto de mil o decimal único
        partes = txt.split('.')
        if len(partes) > 2 or (len(partes) == 2 and len(partes[1]) == 3):
            txt = txt.replace('.', '')
    # En caso de formato americano con comas en miles
    txt = txt.replace(',', '')
    # Dejar solo dígitos, signos menos y el punto decimal real si quedó alguno
    txt = re.sub(r'[^\d.-]', '', txt)
    try:
        return float(txt) if txt != '' else 0.0
    except:
        return 0.0

# --- BARRA LATERAL ---
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
        "📅 Mes Control Pauta:", 
        options=meses_disponibles
    )

partes = mes_sel.split(" ")
mes_nom = partes[0].lower().strip()
ano_num = partes[1].strip()

# ==========================================
# BACKEND - PROCESAMIENTO 
# ==========================================

# 1. PROCESAMIENTO PAUTA MENSUAL
url_pacing_base = "https://docs.google.com/spreadsheets/d/1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0/"
url_pacing = get_csv_url(url_pacing_base, mes_sel)

presupuesto_mensual = "$0"
gasto_total = 0
fecha_update = "N/D"
df_pacing = pd.DataFrame()
pacing_ok = False

try:
    df_r_pacing = pd.read_csv(url_pacing, header=None, dtype=str).fillna('')
    for i in range(min(5, len(df_r_pacing))):
        f_list = df_r_pacing.iloc[i].astype(str).tolist()
        for pos in range(len(f_list)):
            celda_txt = str(f_list[pos]).lower().strip()
            if ('approved' in celda_txt or 'aprobado' in celda_txt) and (pos + 1 < len(f_list)):
                presupuesto_mensual = str(f_list[pos + 1]).strip()
                break

    df_d_pacing = df_r_pacing.iloc[3:].copy()
    if len(df_r_pacing.columns) > 18:
        for r in range(len(df_r_pacing)-1, 2, -1):
            val_celda = str(df_r_pacing.iloc[r, 18]).strip()
            if val_celda != '' and 'total' not in val_celda.lower():
                fecha_update = val_celda
                break

    lista_p = []
    for idx, row in df_d_pacing.iterrows():
        if len(row) <= 4: continue
        c_camp = str(row[1]).strip()
        c_medio = str(row[0]).strip()
        if c_camp == '' or 'campaign' in c_camp.lower() or 'total' in c_camp.lower(): continue
            
        v_st = str(row[4]).strip() if len(row) > 4 else 'N/D'
        v_sp = str(row[7]).strip() if len(row) > 7 else '0'
        v_tp = str(row[15]).strip() if len(row) > 15 else 'General'
        v_re = str(row[14]).strip() if len(row) > 14 else 'N/D'
        v_cp = str(row[17]).strip() if len(row) > 17 else 'N/D'

        lista_p.append({
            'Medio_Raw': c_medio, 'Campaña': c_camp, 'Estado': v_st,
            'Gasto_Raw': v_sp, 'Objetivo': v_tp, 'Resultados': v_re, 'CPA': v_cp
        })

    df_pacing = pd.DataFrame(lista_p)
    if not df_pacing.empty:
        df_pacing['Medio'] = df_pacing['Medio_Raw'].replace(['', 'nan'], pd.NA).ffill().fillna('Sin Medio')
        df_pacing['Gasto'] = pd.to_numeric(df_pacing['Gasto_Raw'].str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)
        resumen = df_pacing.groupby('Medio')['Gasto'].sum()
        df_pacing['Medio_Labels'] = df_pacing['Medio'].map({m: f"{m} (${t:,.0f})" for m, t in resumen.items()})
        gasto_total = df_pacing['Gasto'].sum()
        pacing_ok = True
except Exception as e:
    st.error(f"Error Módulo Pacing: {e}")

# 2. PROCESAMIENTO HISTÓRICO COMERCIAL ROAS
url_roas_base = "
