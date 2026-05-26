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

# 1. PROCESAMIENTO PAUTA MENSUAL (Mantiene filtro por mes operativo)
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

# 2. PROCESAMIENTO HISTÓRICO COMERCIAL ROAS (LÓGICA AGREGADA DINÁMICA)
url_roas_base = "https://docs.google.com/spreadsheets/d/190FjfTc6ZsAsRsj3swki1Ch6BME6j2CbfgyxcUt1pY/"
url_roas = get_csv_url(url_roas_base, "Roas")

tot_inversion = 0
tot_ventas = 0
tot_leads = 0
tot_cotiz = 0
tot_cierres = 0
df_historico_visual = pd.DataFrame()
roas_ok = False

try:
    df_r_roas = pd.read_csv(url_roas, header=None, dtype=str).fillna('')
    
    # Mapeo limpio de registros reales excluyendo filas vacías o de control financiero
    registros_limpios = []
    
    # Procesar bloque superior (Métricas financieras básicas por fila válida)
    l_sup = min(31, len(df_r_roas))
    for r in range(3, l_sup):
        linea = df_r_roas.iloc[r].astype(str).tolist()
        m_identificado = str(linea[1]).strip()
        if m_identificado != '' and 'total' not in m_identificado.lower() and 'meta' not in m_identificado.lower():
            # Extraer numéricos limpios para consolidación general
            inv_val = float(re.sub(r'[^\d.]', '', str(linea[2]))) if re.sub(r'[^\d.]', '', str(linea[2])) else 0.0
            ven_val = float(re.sub(r'[^\d.]', '', str(linea[3]))) if re.sub(r'[^\d.]', '', str(linea[3])) else 0.0
            r_real_val = float(re.sub(r'[^\d.]', '', str(linea[4]))) if re.sub(r'[^\d.]', '', str(linea[4])) else 0.0
            
            # Buscar correspondencia de embudo en bloque inferior (Filas 33+)
            l_leads, l_cotiz, l_cierres = 0, 0, 0
            for ri in range(32, len(df_r_roas)):
                linea_i = df_r_roas.iloc[ri].astype(str).tolist()
                if str(linea_i[1]).lower().strip() == m_identificado.lower().strip():
                    l_leads = int(re.sub(r'[^\d]', '', str(linea_i[8]))) if re.sub(r'[^\d]', '', str(linea_i[8])) else 0
                    l_cotiz = int(re.sub(r'[^\d]', '', str(linea_i[9]))) if re.sub(r'[^\d]', '', str(linea_i[9])) else 0
                    l_cierres = int(re.sub(r'[^\d]', '', str(linea_i[10]))) if re.sub(r'[^\d]', '', str(linea_i[10])) else 0
                    break
            
            registros_limpios.append({
                'Periodo': m_identificado.title(),
                'Inversion': inv_val,
                'Ventas': ven_val,
                'ROAS': r_real_val,
                'Leads': l_leads,
                'Cotizaciones': l_cotiz,
                'Cierres': l_cierres
            })
            
    df_historico_visual = pd.DataFrame(registros_limpios)
    if not df_historico_visual.empty:
        tot_inversion = df_historico_visual['Inversion'].sum()
        tot_ventas = df_historico_visual['Ventas'].sum()
        tot_leads = df_historico_visual['Leads'].sum()
        tot_cotiz = df_historico_visual['Cotizaciones'].sum()
        tot_cierres = df_historico_visual['Cierres'].sum()
        roas_ok = True
except Exception as e:
    pass

# ==========================================
# FRONTEND - ARQUITECTURA VISUAL MÁSTER
# ==========================================
st.title("🏢 Panel Analytics Comercial — BogoApts")

t_pacing, t_atribucion = st.tabs([
    "📊 Rendimiento de Pauta (Operativo)", 
    "📈 Atribución, Retorno e Histórico"
])

# PESTAÑA 1: CONTROL MENSUAL OPERATIVO DE PAUTA
with t_pacing:
    st.subheader(f"Vista Mensual Operativa: {mes_sel.title()}")
    if pacing_ok:
        mx1, mx2, mx3 = st.columns(3)
        with mx1: st.metric("Presupuesto Mensual Aprobado", presupuesto_mensual)
        with mx2: st.metric("Inversión Ejecutada en Pauta", f"${gasto_total:,.0f}")
        with mx3: 
            d_lbl = "Cerrado" if mes_sel != meses_disponibles[0] else f"Día {datetime.now().day} Activo"
            st.metric("Estado del Periodo", d_lbl)
            
        st.success(f"✅ Sincronizado | Registro de datos: {fecha_update}")
        st.divider()
        
        df_p = df_pacing[df_pacing['Gasto'] > 0]
        if not df_p.empty:
            fig = px.treemap(
                df_p, path=['Medio_Labels', 'Objetivo'], values='Gasto', color='Gasto',
                color_continuous_scale=['#d6b58e', '#5b3f8e']
            )
            fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), paper_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig, use_container_width=True)
            
        with st.expander("📝 Ver Detalle de Campañas del Mes"):
            st.dataframe(
                df_pacing[['Medio', 'Campaña', 'Estado', 'Objetivo', 'Resultados', 'CPA']].sort_values(by='Medio'),
                use_container_width=True, hide_index=True
            )
    else:
        st.error("Error al desplegar la interfaz de pauta.")

# PESTAÑA 2: ATRIBUCIÓN E HISTÓRICO CONSOLIDADO (NUEVA LÓGICA INTEGRADORA)
with t_atribucion:
    st.subheader("📈 Rendimiento Comercial Acumulado de Estrategia (Histórico)")
    if roas_ok and not df_historico_visual.empty:
        # 1. Métricas Clave Consolidadas Globales
        ka, kb, kc, kd = st.columns(4)
        with ka: 
            st.metric("Ventas Atribuidas Totales", f"${tot_ventas:,.0f}")
        with kb: 
            roas_global_calc = (tot_ventas / tot_inversion) if tot_inversion > 0 else 0.0
            # Si en mayo la inversión es 0 en esta hoja pero hay ventas, el ROAS se estabiliza con el histórico real
            st.metric("ROAS Histórico Consolidado", f"{roas_global_calc:.2f}x")
        with kc: 
            st.metric("Inversión Registrada", f"${tot_inversion:,.0f}")
        with kd: 
            st.metric("Cierres de Venta Totales", f"{tot_cierres} Unidades")
        st.divider()
        
        # 2. Bloque Gráfico de dos Columnas
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("🎯 Embudo de Conversión Acumulado")
            f_fig = go.Figure(go.Funnel(
                y=["Leads Atribuidos", "Cotizaciones", "Cierres Efectivos"],
                x=[tot_leads, tot_cotiz, tot_cierres],
                textinfo="value+percent initial",
                marker={"color": ["#d6b58e", "#aa8b66", "#5b3f8e"]}
            ))
            f_fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), paper_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(f_fig, use_container_width=True)
            
        with g2:
            st.subheader("📈 Evolución Temporal de Ventas e Impacto")
            # Gráfico de líneas temporal para ver el comportamiento mes a mes
            fig_lineas = px.bar(
                df_historico_visual, x='Periodo', y='Ventas',
                text_auto='.2s', title="Volumen de Venta por Mes Comercial",
                color_discrete_sequence=['#d6b58e']
            )
            fig_lineas.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_lineas, use_container_width=True)
            
        # 3. Historial en Formato Tabla de Datos Abierta
        st.subheader("📋 Matriz de Control Comercial Histórico")
        st.dataframe(
            df_historico_visual.rename(columns={
                'Periodo': 'Mes Comercial', 'Inversion': 'Inversión ($)', 
                'Ventas': 'Ventas ($)', 'Leads': 'Leads Totales', 
                'Cotizaciones': 'Cotizaciones'
            }),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("💡 Esperando lectura de datos desde la hoja 'Roas'.")

st.caption("BogoApts Analytics | Strategic Analytics by goBIG")
