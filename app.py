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
    ano, mes = 2026, 5
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

def format_url(doc_id, name):
    enc = urllib.parse.quote(name)
    b = "https://docs.google.com/spreadsheets/d/"
    return f"{b}{doc_id}/gviz/tq?tqx=out:csv&sheet={enc}"

def parse_num(val):
    txt = str(val).strip().replace('$', '')
    if '.' in txt and ',' not in txt:
        pt = txt.split('.')
        if len(pt) > 2 or (
            len(pt) == 2 and len(pt[1]) == 3
        ):
            txt = txt.replace('.', '')
    txt = txt.replace(',', '')
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
        st.caption("🏢 *BogoApts*")
    mes_sel = st.selectbox(
        "📅 Mes Control Pauta:", 
        options=meses_disponibles
    )

# ==========================================
# BACKEND - LECTURA DE GOOGLE SHEETS
# ==========================================

# 1. RENDIMIENTO DE PAUTA MENSUAL OPERATIVO
id_pacing = "1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0"
url_pacing = format_url(id_pacing, mes_sel)

presupuesto_mensual = "$0"
gasto_total = 0
fecha_update = "N/D"
df_pacing = pd.DataFrame()
pacing_ok = False

try:
    df_r_pacing = pd.read_csv(
        url_pacing, 
        header=None, 
        dtype=str
    ).fillna('')
    for i in range(min(5, len(df_r_pacing))):
        f = [
            str(x).lower().strip() 
            for x in df_r_pacing.iloc[i].tolist()
        ]
        if 'approved' in f or 'aprobado' in f:
            idx = f.index('approved') if 'approved' in f else f.index('aprobado')
            if idx + 1 < len(f):
                presupuesto_mensual = str(
                    df_r_pacing.iloc[i, idx + 1]
                ).strip()
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
        if len(row) <= 4: 
            continue
        c_camp = str(row[1]).strip()
        c_medio = str(row[0]).strip()
        if c_camp == '': 
            continue
        if 'campaign' in c_camp.lower(): 
            continue
        if 'total' in c_camp.lower(): 
            continue
        
        lista_p.append({
            'Medio_Raw': c_medio, 
            'Campaña': c_camp,
            'Estado': str(row[4]).strip() if len(row) > 4 else 'N/D',
            'Gasto_Raw': str(row[7]).strip() if len(row) > 7 else '0',
            'Objetivo': str(row[15]).strip() if len(row) > 15 else 'General',
            'Resultados': str(row[14]).strip() if len(row) > 14 else 'N/D',
            'CPA': str(row[17]).strip() if len(row) > 17 else 'N/D'
        })

    df_pacing = pd.DataFrame(lista_p)
    if not df_pacing.empty:
        df_pacing['Medio'] = df_pacing['Medio_Raw'].replace(
            ['', 'nan'], pd.NA
        ).ffill().fillna('Sin Medio')
        df_pacing['Gasto'] = pd.to_numeric(
            df_pacing['Gasto_Raw'].str.replace(
                r'[^\d.-]', '', regex=True
            ), errors='coerce'
        ).fillna(0)
        resumen = df_pacing.groupby('Medio')['Gasto'].sum()
        df_pacing['Medio_Labels'] = df_pacing['Medio'].map(
            {m: f"{m} (${t:,.0f})" for m, t in resumen.items()}
        )
        gasto_total = df_pacing['Gasto'].sum()
        pacing_ok = True
except Exception as e:
    st.error(f"Error Módulo Pacing: {e}")

# 2. ATRIBUCIÓN E HISTÓRICO COMERCIAL (HOJA ROAS)
id_roas = "190FjfTc6ZsAsRsj3swki1Ch6BME6j2CbfgyxcUt1pY"
url_roas = format_url(id_roas, "Roas")

tot_inversion, tot_ventas = 0.0, 0.0
tot_leads, tot_cotiz, tot_cierres = 0, 0, 0
df_historico = pd.DataFrame()
roas_ok = False

try:
    df_r_roas = pd.read_csv(
        url_roas, 
        header=None, 
        dtype=str
    ).fillna('')
    registros = []
    
    # Procesamiento de registros mensuales históricos (Filas 4 a 31)
    for r in range(3, min(31, len(df_r_roas))):
        linea = df_r_roas.iloc[r].astype(str).tolist()
        m_id = str(linea[1]).strip()
        
        if m_id != '' and 'total' not in m_id.lower() and 'meta' not in m_id.lower():
            inv_v = parse_num(linea[2])
            ven_v = parse_num(linea[3])
            roas_v = parse_num(linea[4])
            
            # Buscar correspondencia de embudo inferior (Filas 33+)
            l_ld, l_ct, l_ci = 0, 0, 0
            for ri in range(32, len(df_r_roas)):
                linea_i = df_r_roas.iloc[ri].astype(str).tolist()
                if str(linea_i[1]).lower().strip() == m_id.lower().strip():
                    l_ld = int(parse_num(linea_i[8]))
                    l_ct = int(parse_num(linea_i[9]))
                    l_ci = int(parse_num(linea_i[10]))
                    break
                    
            registros.append({
                'Mes Comercial': m_id.title(), 
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
    pass

# ==========================================
# FRONTEND - INTERFAZ DE NAVEGACIÓN
# ==========================================
st.title("🏢 Panel Analytics Comercial — BogoApts")

# Líneas súper cortas anti-recortes para renderizar pestañas
t1, t2 = st.tabs([
    "📊 Rendimiento Pauta", 
    "📈 Atribución e Histórico"
])

# --- PESTAÑA 1: PACING OPERATIVO ---
with t1:
    st.subheader(f"Vista Mensual Operativa: {mes_sel.title()}")
    if pacing_ok:
        mx1, mx2, mx3 = st.columns(3)
        with mx1: st.metric("Presupuesto Aprobado", presupuesto_mensual)
        with mx2: st.metric("Inversión Ejecutada", f"${gasto_total:,.0f}")
        with mx3: 
            d_lbl = "Cerrado" if mes_sel != meses_disponibles[0] else f"Día {datetime.now().day} Activo"
            st.metric("Estado del Periodo", d_lbl)
            
        st.success(f"✅ Sincronizado | Datos: {fecha_update}")
        st.divider()
        
        df_p = df_pacing[df_pacing['Gasto'] > 0]
        if not df_p.empty:
            fig = px.treemap(
                df_p, 
                path=['Medio_Labels', 'Objetivo'], 
                values='Gasto', 
                color='Gasto',
                color_continuous_scale=['#d6b58e', '#5b3f8e']
            )
            fig.update_layout(
                margin=dict(t=10, l=10, r=10, b=10), 
                paper_bgcolor='rgba(0,0,0,0)', 
                font_color="white"
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with st.expander("📝 Ver Detalle de Campañas del Mes"):
            st.dataframe(
                df_pacing[[
                    'Medio', 'Campaña', 'Estado', 
                    'Objetivo', 'Resultados', 'CPA'
                ]].sort_values(by='Medio'),
                use_container_width=True, 
                hide_index=True
            )
    else:
        st.error("Error al desplegar la interfaz operativa de pauta.")

# --- PESTAÑA 2: CONSOLIDADO COMERCIAL ---
with t2:
    st.subheader("📈 Resultados Consolidados del Proyecto")
    if roas_ok and not df_historico.empty:
        ka, kb, kc, kd = st.columns(4)
        with ka: st.metric("Ventas Atribuidas Totales", f"${tot_ventas:,.0f}")
        with kb:
            roas_g = (tot_ventas / tot_inversion) if tot_inversion > 0 else 0.0
            st.metric("ROAS Histórico Consolidado", f"{roas_g:.2f}x")
        with kc: st.metric("Inversión en Bitácora", f"${tot_inversion:,.0f}")
        with kd: st.metric("Cierres Efectivos Totales", f"{tot_cierres} Unds")
        st.divider()
        
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("🎯 Conversión de Embudo Comercial")
            f_fig = go.Figure(go.Funnel(
                y=["Leads Atribuidos", "Cotizaciones", "Cierres Efectivos"],
                x=[tot_leads, tot_cotiz, tot_cierres],
                textinfo="value+percent initial",
                marker={"color": ["#d6b58e", "#aa8b66", "#5b3f8e"]}
            ))
            f_fig.update_layout(
                margin=dict(t=20, b=20, l=20, r=20), 
                paper_bgcolor='rgba(0,0,0,0)', 
                font_color="white"
            )
            st.plotly_chart(f_fig, use_container_width=True)
            
        with g2:
            st.subheader("📈 Evolución Histórica de Ventas")
            df_g = df_historico[df_historico['Ventas'] > 0]
            if not df_g.empty:
                fig_barras = px.bar(
                    df_g, 
                    x='Mes Comercial', 
                    y='Ventas', 
                    text_auto='.2s',
                    color_discrete_sequence=['#d6b58e']
                )
                fig_barras.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    font_color="white"
                )
                st.plotly_chart(fig_barras, use_container_width=True)
            else:
                st.info("Registrando métricas comerciales para graficar.")
                
        st.subheader("📋 Matriz de Control Comercial")
        df_m = df_historico.copy()
        df_m['Inversion'] = df_m['Inversion'].map(lambda x: f"${x:,.0f}")
        df_m['Ventas'] = df_m['Ventas'].map(lambda x: f"${x:,.0f}")
        df_m['ROAS'] = df_m['ROAS'].map(lambda x: f"{x:.2f}x")
        st.dataframe(
            df_m.rename(columns={
                'Inversion': 'Inversión', 
                'Ventas': 'Ventas Atribuidas',
                'Leads': 'Leads Totales'
            }),
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("💡 Conectando con los datos históricos de la pestaña 'Roas'.")

st.caption("BogoApts Analytics | Strategic Analytics by goBIG")
