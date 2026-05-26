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

# ESTILOS PREMIUM
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
    if txt == '-' or txt == '': return 0.0
    if '.' in txt and ',' not in txt:
        pt = txt.split('.')
        if len(pt) > 2 or (len(pt) == 2 and len(pt[1]) == 3):
            txt = txt.replace('.', '')
    txt = txt.replace(',', '')
    txt = re.sub(r'[^\d.-]', '', txt)
    try: return float(txt) if txt != '' else 0.0
    except: return 0.0

# --- BARRA LATERAL ---
meses_disponibles = obtener_meses()
with st.sidebar:
    try:
        st.image("Logo_bogoapts_dashboard.PNG", use_container_width=True)
    except:
        st.caption("🏢 *BogoApts*")
    mes_sel = st.selectbox("📅 Mes Control Pauta:", options=meses_disponibles)

# ==========================================
# BACKEND - LECTURA DE GOOGLE SHEETS
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
    
    # Búsqueda flexible de presupuesto (Corregido)
    for i in range(min(5, len(df_r_pacing))):
        f_list = df_r_pacing.iloc[i].astype(str).tolist()
        for pos in range(len(f_list)):
            celda_txt = str(f_list[pos]).lower().strip()
            if ('approved' in celda_txt or 'aprobado' in celda_txt) and (pos + 1 < len(f_list)):
                presupuesto_mensual = str(f_list[pos + 1]).strip()
                break
        if presupuesto_mensual != "$0":
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

# 2. ATRIBUCIÓN E HISTÓRICO COMERCIAL (URL CORREGIDA CON "M" Y MAPEO DE COLUMNAS NUEVO)
url_roas_final = "https://docs.google.com/spreadsheets/d/190FjfTc6ZsAsRsj3swki1Ch6BME6j2CbfgyxcUt1pMY/gviz/tq?tqx=out:csv&gid=212931455"

tot_inversion, tot_ventas = 0.0, 0.0
tot_leads, tot_cotiz, tot_cierres = 0, 0, 0
df_historico = pd.DataFrame()
roas_ok = False

try:
    df_r_roas = pd.read_csv(url_roas_final, header=None, dtype=str).fillna('')
    registros = []
    
    ano_actual = "2024"
    # Iniciamos la lectura desde la fila 2 saltando cabeceras
    for r in range(2, len(df_r_roas)):
        linea = df_r_roas.iloc[r].astype(str).tolist()
        if len(linea) < 10: continue
        
        # Mapeo de celdas combinadas de Año
        val_ano = str(linea[0]).strip()
        if val_ano != '' and val_ano.isdigit():
            ano_actual = val_ano
            
        val_mes = str(linea[1]).strip()
        if val_mes == '' or 'total' in val_mes.lower() or 'roas' in val_mes.lower() or 'spend' in val_mes.lower():
            continue
            
        # Extracción según las columnas de la nueva tabla "ROAS Final"
        inv_v = parse_num(linea[5])  # Columna F: Total spend
        l_ld = int(parse_num(linea[6]))  # Columna G: Leads Atribuidos
        l_ct = int(parse_num(linea[7]))  # Columna H: Cotizaciones
        l_ci = int(parse_num(linea[8]))  # Columna I: Cierres
        ven_v = parse_num(linea[9])  # Columna J: Ventas atribuidas a marketing
        
        # Cálculo de ROAS automático
        roas_v = (ven_v / inv_v) if inv_v > 0 else 0.0
        
        registros.append({
            'Mes Comercial': f"{val_mes.title()} {ano_actual}", 
            'Inversion': inv_v, 
            'Ventas': ven_v,
            'ROAS': roas_v, 
            'Leads': l_ld, 
            'Cotizaciones': l_ct, 
            'Cierres': l_ci
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
    st.error(f"Error Técnico en lectura de ROAS Final: {e}")

# ==========================================
# FRONTEND - INTERFAZ DE NAVEGACIÓN
# ==========================================
st.title("🏢 Panel Analytics Comercial — BogoApts")

t1, t2 = st.tabs([
    "📊 Rendimiento Pauta", 
    "📈 Atribución e Histórico"
])

with t1:
    st.subheader(f"Vista Mensual Operativa: {mes_sel.title()}")
    if pacing_ok:
        mx1, mx2, mx3 = st.columns(3)
        with mx1:
