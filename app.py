import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import urllib.parse
import re

# CONFIGURACIÓN DE PÁGINA
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

# --- SISTEMA DE CONTROL DE PERIODOS ---
def obtener_meses():
    m_list = [
        "enero", "febrero", "marzo", "abril", 
        "mayo", "junio", "julio", "agosto", 
        "septiembre", "octubre", "noviembre", 
        "diciembre"
    ]
    ano, mes = 2026, 5
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

def format_url(doc_id, sheet_name):
    sheet_enc = urllib.parse.quote(sheet_name)
    return f"https://docs.google.com/spreadsheets/d/{doc_id}/gviz/tq?tqx=out:csv&sheet={sheet_enc}"

def parse_num(val):
    """Transforma formatos mixtos (ej: $62.610.165 o 83) a número limpio float/int"""
    txt = str(val).strip().replace('$', '')
    if '.' in txt and ',' not in txt:
        partes = txt.split('.')
        if len(partes) > 2 or (len(partes) == 2 and len(partes[1]) == 3):
            txt = txt.replace('.', '')
    txt = txt.replace(',', '')
    txt = re.sub(r'[^\d.-]', '', txt)
    try:
        return float(txt) if txt != '' else 0.0
    except:
        return 0.0

# --- CONTROLES SIDEBAR ---
meses_disponibles = obtener_meses()
with st.sidebar:
    try:
        st.image("Logo_bogoapts_dashboard.PNG", use_container_width=True)
    except:
        st.caption("🏢 *Dashboard BogoApts*")
    mes_sel = st.selectbox("📅 Mes Control Pauta:", options=meses_disponibles)

# ==========================================
# BACKEND - LECTURA PARALELA DE FUENTES
# ==========================================

# 1. FUENTE PACING DIARIO OPERATIVO
id_pacing = "1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0"
url_pacing = format_url(id_pacing, mes_sel)

presupuesto_mensual = "$0"
gasto_total = 0
fecha_update = "N/D"
df_pacing = pd.DataFrame()
pacing_ok = False

try:
    df_r_pacing = pd.read_csv(url_pacing, header=None, dtype=str).fillna('')
    for i in range(min(5, len(df_r_pacing))):
        fila = [str(x).lower().strip() for x in df_r_pacing.iloc[i].tolist()]
        if 'approved' in fila or 'aprobado' in fila:
            idx = fila.index('approved') if 'approved' in fila else fila.index('aprobado')
            if idx + 1 < len(fila):
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
        
        lista_p.append({
            'Medio_Raw': c_medio, 'Campaña': c_camp,
            'Estado': str(row[4]).strip() if len(row) > 4 else 'N/D',
            'Gasto_Raw': str(row[7]).strip() if len(row) > 7 else '0',
            'Objetivo': str(row[15]).strip() if len(row) > 15 else 'General',
            'Resultados': str(row[14]).strip() if len(row) > 14 else 'N/D',
            'CPA': str(row[17]).strip() if len(row) > 17 else 'N/D'
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

# 2. FUENTE ROAS HISTÓRICO COMERCIAL (PROCESAMIENTO GLOBAL REESTRUCTURADO)
id_roas = "190FjfTc6ZsAsRsj3swki1Ch6BME6j2CbfgyxcUt1pY"
url_roas = format_url(id_roas, "Roas")

tot_inversion, tot_ventas = 0.0, 0.0
tot_leads, tot_cotiz, tot_cierres = 0, 0, 0
df_historico = pd.DataFrame()
roas_ok = False

try:
    df_r_roas = pd.read_csv(url_roas, header=None, dtype=str).fillna('')
    registros = []
    
    # Mapear matriz de control financiero histórico (Filas 4 a 31)
    for r in range(3, min(31, len(df_r_roas))):
        linea = df_r_roas.iloc[r].astype(str).tolist()
        m_id = str(linea[1]).strip()
        
        if m_id != '' and 'total' not in m_id.lower() and 'meta' not in m_id.lower():
            inv_v = parse_num(linea[2])
            ven_v = parse_num(linea[3])
            roas_v = parse_num(linea[4])
            
            # Buscar su respectiva fila en el bloque de embudo comercial inferior (Filas 33+)
            l_ld, l_ct, l_ci = 0, 0, 0
            for ri in range(32, len(df_r_roas)):
                linea_i = df_r_roas.iloc[ri].astype(str).tolist()
                if str(linea_i[1]).lower().strip() == m_id.lower().strip():
                    l_ld = int(parse_num(linea_i[8]))
                    l_ct = int(parse_num(linea_i[9]))
                    l_ci = int(parse_num(linea_i[10]))
                    break
                    
            registros.append({
                'Mes Comercial': m_id.title(), 'Inversion': inv_v, 'Ventas': ven_v,
                'ROAS': roas_v, 'Leads': l_ld, 'Cotizaciones': l_ct, 'Cierres': l_ci
            })
            
    df_historico = pd.DataFrame(registros)
    if not df_historico.empty:
        tot_inversion = df_historico['Inversion'].sum()
        tot_ventas = df_historico['Ventas'].sum()
        tot_leads = df_historico['Leads'].sum()
        tot_cotiz = df_historico['Cotizaciones'].sum()
        tot_cierres = df_historico['Cierres'].sum()
        roas_ok = True
except Exception as e:
    pass

# ==========================================
# FRONTEND - ARQUITECTURA DE PESTAÑAS
# ==========================================
st.title("🏢 Panel Analytics Comercial — BogoApts")

t_pacing, t_atribucion = st.tabs(
