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

# --- MESES DISPONIBLES ---
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
        "📅 Seleccione Mes:", 
        options=meses_disponibles
    )

partes = mes_sel.split(" ")
mes_nom = partes[0].lower().strip()
ano_num = partes[1].strip()

# ==========================================
# BACKEND - PROCESAMIENTO LINEAL
# ==========================================

url_pacing_base = "https://docs.google.com/spreadsheets/d/1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0/"
url_pacing = get_csv_url(url_pacing_base, mes_sel)

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
    
    # Búsqueda directa de presupuesto
    for i in range(min(5, len(df_r_pacing))):
        f_list = df_r_pacing.iloc[i].astype(str).tolist()
        for pos in range(len(f_list)):
            celda_txt = str(f_list[pos]).lower().strip()
            es_target = 'approved' in celda_txt or 'aprobado' in celda_txt
            if es_target and (pos + 1 < len(f_list)):
                presupuesto_mensual = str(f_list[pos + 1]).strip()
                break

    df_d_pacing = df_r_pacing.iloc[3:].copy()
    
    # Fecha de actualización
    if len(df_r_pacing.columns) > 18:
        for r in range(len(df_r_pacing)-1, 2, -1):
            val_celda = str(df_r_pacing.iloc[r, 18]).strip()
            if val_celda != '' and 'total' not in val_celda.lower():
                fecha_update = val_celda
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
        if 'campaña' in c_camp.lower(): 
            continue
        if 'total' in c_camp.lower(): 
            continue
            
        v_st = str(row[4]).strip() if len(row) > 4 else 'N/D'
        if v_st == '':
            v_st = 'N/D'
            
        v_sp = str(row[7]).strip() if len(row) > 7 else '0'
        v_tp = str(row[15]).strip() if len(row) > 15 else 'General'
        if v_tp == '':
            v_tp = 'Sin Objetivo'
            
        v_re = str(row[14]).strip() if len(row) > 14 else 'N/D'
        v_cp = str(row[17]).strip() if len(row) > 17 else 'N/D'

        lista_p.append({
            'Medio_Raw': c_medio, 
            'Campaña': c_camp, 
            'Estado': v_st,
            'Gasto_Raw': v_sp, 
            'Objetivo': v_tp, 
            'Resultados': v_re, 
            'CPA': v_cp
        })

    df_pacing = pd.DataFrame(lista_p)
    if not df_pacing.empty:
        df_pacing['Medio_Raw'] = df_pacing['Medio_Raw'].replace(
            ['', 'nan'], pd.NA
        )
        df_pacing['Medio'] = df_pacing['Medio_Raw'].ffill().fillna(
            'Sin Medio'
        )
        df_pacing['Gasto'] = df_pacing['Gasto_Raw'].str.replace(
            r'[^\d.-]', '', regex=True
        )
        df_pacing['Gasto'] = pd.to_numeric(
            df_pacing['Gasto'], errors='coerce'
        ).fillna(0)

        resumen = df_pacing.groupby('Medio')['Gasto'].sum()
        mapa = {
            m: f"{m} (${t:,.0f})" 
            for m, t in resumen.items()
        }
        df_pacing['Medio_Labels'] = df_pacing['Medio'].map(mapa)
        gasto_total = df_pacing['Gasto'].sum()
        pacing_ok = True
except Exception as e:
    st.error(f"Error Módulo Pacing: {e}")

# --- BITÁCORA COMERCIAL ROAS ---
url_roas = "https://docs.google.com/spreadsheets/d/190FjfTc6ZsAsRsj3swki1Ch6BME6j2CbfgyxcUt1pY/gviz/tq?tqx=out:csv&gid=0"

inv_com = "$0"
ventas_com = "$0"
r_real = "0.0"
r_esp = "0.0"
cumpli = "0.0%"
leads = "0"
cotiz = "0"
cierres = "0"
roas_ok = False

try:
    df_r_roas = pd.read_csv(
        url_roas, 
        header=None, 
        dtype=str
    ).fillna('')
    
    # Bloque Superior Flexibilizado
    f_sup = []
    l_sup = min(31, len(df_r_roas))
    for r in range(3, l_sup):
        f_sup.append(df_r_roas.iloc[r].astype(str).tolist())
    df_s = pd.DataFrame(f_sup)
    if not df_s.empty:
        # Formateo Ultra-Seguro de texto contra mayúsculas y puntos decimales
        df_s[0] = df_s[0].str.strip().replace(['', 'nan'], pd.NA).ffill()
        df_s[0] = df_s[0].astype(str).str.replace(r'[^\d]', '', regex=True)
        df_s[1] = df_s[1].astype(str).str.lower().str.strip()
        
        # Filtro inteligente tolerante
        f_mes = df_s[(df_s[0] == ano_num) & (df_s[1] == mes_nom)]
        if not f_mes.empty:
            inv_com = str(f_mes.iloc[0, 2]).strip()
            ventas_com = str(f_mes.iloc[0, 3]).strip()
            r_real = str(f_mes.iloc[0, 4]).strip()
            r_esp = str(f_mes.iloc[0, 6]).strip()
            cumpli = str(f_mes.iloc[0, 7]).strip()

    # Bloque Inferior Flexibilizado
    f_inf = []
    for r in range(32, len(df_r_roas)):
        f_inf.append(df_r_roas.iloc[r].astype(str).tolist())
    df_i = pd.DataFrame(f_inf)
    if not df_i.empty:
        df_i[0] = df_i[0].str.strip().replace(['', 'nan'], pd.NA).ffill()
        df_i[0] = df_i[0].astype(str).str.replace(r'[^\d]', '', regex=True)
        df_i[1] = df_i[1].astype(str).str.lower().str.strip()
        
        f_mes_i = df_i[(df_i[0] == ano_num) & (df_i[1] == mes_nom)]
        if not f_mes_i.empty:
            leads = str(f_mes_i.iloc[0, 8]).strip()
            cotiz = str(f_mes_i.iloc[0, 9]).strip()
            cierres = str(f_mes_i.iloc[0, 10]).strip()
    roas_ok = True
except:
    pass

# ==========================================
# FRONTEND - ARQUITECTURA VISUAL
# ==========================================
st.title(f"🏢 Panel BogoApts: {mes_sel.title()}")

t_pacing, t_atribucion = st.tabs(
    ["📊 Rendimiento Pauta", "📈 Atribución y Retorno"]
)

with t_pacing:
    if pacing_ok:
        mx1, mx2, mx3 = st.columns(3)
        with mx1: 
            st.metric("Presupuesto Mensual", presupuesto_mensual)
        with mx2: 
            st.metric("Inversión Ejecutada", f"${gasto_total:,.0f}")
        with mx3: 
            d_lbl = "Cerrado"
            if mes_sel == meses_disponibles[0]:
                d_lbl = f"Día {datetime.now().day}"
            st.metric("Estado de Medición", d_lbl)
            
        st.success(f"✅ Sincronización exitosa | Registro: {fecha_update}")
        st.divider()
        
        st.header("📊 Distribución por Canal")
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
            
        with st.expander("📝 Detalle General de Campañas"):
            st.dataframe(
                df_pacing[[
                    'Medio', 'Campaña', 'Estado', 
                    'Objetivo', 'Resultados', 'CPA'
                ]].sort_values(by='Medio'),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.error("Error al desplegar la interfaz gráfica de pauta.")

with t_atribucion:
    # Verificación de datos de negocio activos
    if roas_ok and ventas_com != "$0" and ventas_com != "" and ventas_com != "0":
        ka, kb, kc, kd = st.columns(4)
        with ka: st.metric("Ventas Atribuidas", ventas_com)
        with kb: st.metric("ROAS Real", f"{r_real}x", help=f"Meta: {r_esp}x")
        with kc: st.metric("Cumplimiento", cumpli)
        with kd: st.metric("Cierres de Venta", f"{cierres} Unds")
        st.divider()
        
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("🎯 Embudo de Conversión Comercial")
            try:
                l_c = int(re.sub(r'[^\d]', '', str(leads))) if re.sub(r'[^\d]', '', str(leads)) else 0
                co_c = int(re.sub(r'[^\d]', '', str(cotiz))) if re.sub(r'[^\d]', '', str(cotiz)) else 0
                ci_c = int(re.sub(r'[^\d]', '', str(cierres))) if re.sub(r'[^\d]', '', str(cierres)) else 0
                
                f_fig = go.Figure(go.Funnel(
                    y=["Leads Atribuidos", "Cotizaciones", "Cierres Efectivos"],
                    x=[l_c, co_c, ci_c],
                    textinfo="value+percent initial",
                    marker={"color": ["#d6b58e", "#aa8b66", "#5b3f8e"]}
                ))
                f_fig.update_layout(
                    margin=dict(t=20, b=20, l=20, r=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color="white"
                )
                st.plotly_chart(f_fig, use_container_width=True)
            except:
                st.info("Formateando estructura de embudo.")
        with g2:
            st.subheader("📋 Resumen Financiero de Negocio")
            st.markdown(f"""
            * **Mes Comercial:** `{mes_sel.upper()}`
            * **Inversión Bitácora:** `{inv_com}`
            * **Retorno Esperado:** `{r_esp}x`
            * **Eficiencia Comercial:** El cumplimiento estratégico se sitúa en un **`{cumpli}`**.
            """)
            st.metric("Prospectos Totales", f"{leads} Leads")
            st.metric("Cotizaciones Generadas", f"{cotiz} Cotizaciones")
    else:
        st.info("💡 Módulo de Atribución listo. Los datos comerciales se desplegarán automáticamente cuando la Bitácora registre métricas de venta e inversión para el periodo seleccionado.")

st.caption("BogoApts Analytics | Strategic Analytics by goBIG")
