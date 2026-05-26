import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import urllib.parse
import re

# ==========================================================
# 1. CONFIGURACIÓN GENERAL
# ==========================================================
st.set_page_config(
    page_title="BogoApts Dashboard",
    page_icon="🏢",
    layout="wide"
)

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

# --- FUNCIONES GLOBALES ---
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

# ==========================================================
# 2. MENÚ LATERAL PRINCIPAL
# ==========================================================
with st.sidebar:
    try:
        st.image("Logo_bogoapts_dashboard.PNG", use_container_width=True)
    except:
        st.caption("🏢 *BogoApts*")
        
    st.markdown("## Menú de Navegación")
    vista_activa = st.radio(
        "Seleccione el módulo:",
        ["📊 Control de Pauta (Pacing)", "📈 Histórico y ROAS"]
    )
    st.markdown("---")

# ==========================================================
# 3. MÓDULO 1: CONTROL DE PAUTA (PACING)
# ==========================================================
if vista_activa == "📊 Control de Pauta (Pacing)":
    
    # Declaramos la variable de meses ANTES de usarla
    meses_disponibles = obtener_meses_disponibles()
    
    with st.sidebar:
        mes_seleccionado = st.selectbox("📅 Seleccione el Mes de Reporte:", options=meses_disponibles)

    st.title(f"🏢 Sistema Inteligente BogoApts: {mes_seleccionado.title()}")

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
        
        col_idx_medio, col_idx_camp, col_idx_status, col_idx_spend = 0, 1, 4, 7
        col_idx_res, col_idx_tipo, col_idx_cpa, col_idx_fecha = 14, 15, 17, 18

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
                
            lista_campanas.append({
                'Medio_Raw': celda_medio, 'Campaña': celda_camp,
                'Estado': str(row[col_idx_status]).strip() if len(row) > col_idx_status else 'N/D',
                'Gasto_Raw': str(row[col_idx_spend]).strip() if len(row) > col_idx_spend else '0',
                'Objetivo': str(row[col_idx_tipo]).strip() if len(row) > col_idx_tipo else 'General',
                'Resultados': str(row[col_idx_res]).strip() if len(row) > col_idx_res else 'N/D',
                'CPA': str(row[col_idx_cpa]).strip() if len(row) > col_idx_cpa else 'N/D'
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

    # FRONTEND PAUTA
    if pacing_exitoso:
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Presupuesto Mensual", f"{presupuesto_mensual}")
        with c2: st.metric("Inversión Ejecutada", f"${gasto_total_calculado:,.0f}")
        with c3:
            # Aquí es donde fallaba, ahora `meses_disponibles` sí existe
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
        st.error("No se pudieron cargar los datos de rendimiento de pauta.")

# ==========================================================
# 4. MÓDULO 2: HISTÓRICO Y ROAS (NUEVO & AISLADO)
# ==========================================================
elif vista_activa == "📈 Histórico y ROAS":
    st.title("📈 Desempeño Histórico y ROAS Comercial")
    
    url_roas = "https://docs.google.com/spreadsheets/d/190FjfTc6ZsAsRsj3swki1Ch6BME6j2CbfgyxcUt1pMY/gviz/tq?tqx=out:csv&gid=212931455"
    df_hist = pd.DataFrame()
    roas_ok = False
    
    try:
        df_roas_raw = pd.read_csv(url_roas, header=None, dtype=str).fillna('')
        registros = []
        for r in range(1, len(df_roas_raw)):
            row = df_roas_raw.iloc[r].astype(str).tolist()
            if len(row) < 10: continue
            
            ano, mes = str(row[0]).strip(), str(row[1]).strip()
            if mes == '' or mes == '-' or 'total' in mes.lower(): continue
            
            inv_total = parse_num(row[5])
            leads = int(parse_num(row[6]))
            cotiz = int(parse_num(row[7]))
            cierres = int(parse_num(row[8]))
            ventas = parse_num(row[9])
            roas_calc = (ventas / inv_total) if inv_total > 0 else 0.0
            
            registros.append({
                'Periodo': f"{mes.title()} {ano}", 'Inversión Total': inv_total,
                'Ventas Atribuidas': ventas, 'ROAS': roas_calc,
                'Leads': leads, 'Cotizaciones': cotiz, 'Cierres': cierres
            })
            
        df_hist = pd.DataFrame(registros)
        roas_ok = True
    except Exception as e:
        st.error(f"Error de conexión con la hoja ROAS: {e}")

    if roas_ok and not df_hist.empty:
        total_ventas = df_hist['Ventas Atribuidas'].sum()
        total_inv = df_hist['Inversión Total'].sum()
        roas_global = (total_ventas / total_inv) if total_inv > 0 else 0.0
        
        df_ventas_activas = df_hist[df_hist['Ventas Atribuidas'] > 0]
        if not df_ventas_activas.empty:
            idx_max_roas = df_ventas_activas['ROAS'].idxmax()
            mes_top = df_ventas_activas.loc[idx_max_roas, 'Periodo']
            roas_top = df_ventas_activas.loc[idx_max_roas, 'ROAS']
            texto_mes_top = f"{mes_top} ({roas_top:.2f}x)"
        else:
            texto_mes_top = "N/D"

        st.markdown("### 🏆 Hitos de Negocio Acumulados")
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.metric("Ventas Históricas", f"${total_ventas:,.0f}")
        with k2: st.metric("ROAS Global", f"{roas_global:.2f}x")
        with k3: st.metric("Inversión Total", f"${total_inv:,.0f}")
        with k4: st.metric("Mes Más Rentable", texto_mes_top)
        st.divider()
        
        col1, col2 = st.columns([1.5, 1])
        with col1:
            st.markdown("### 📊 Evolución Mensual: Ventas vs Inversión")
            fig_evolucion = go.Figure()
            fig_evolucion.add_trace(go.Bar(x=df_hist['Periodo'], y=df_hist['Ventas Atribuidas'], name='Ventas Atribuidas', marker_color='#d6b58e'))
            fig_evolucion.add_trace(go.Bar(x=df_hist['Periodo'], y=df_hist['Inversión Total'], name='Inversión (Spend)', marker_color='#5b3f8e'))
            fig_evolucion.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", margin=dict(t=20, b=20, l=10, r=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_evolucion, use_container_width=True)
            
        with col2:
            st.markdown("### 🎯 Embudo Histórico")
            total_l, total_c, total_ci = df_hist['Leads'].sum(), df_hist['Cotizaciones'].sum(), df_hist['Cierres'].sum()
            if total_l > 0:
                fig_funnel = go.Figure(go.Funnel(y=["Leads Atribuidos", "Cotizaciones", "Cierres Efectivos"], x=[total_l, total_c, total_ci], textinfo="value+percent initial", marker={"color": ["#d6b58e", "#aa8b66", "#5b3f8e"]}))
                fig_funnel.update_layout(margin=dict(t=20, b=20, l=20, r=20), paper_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig_funnel, use_container_width=True)
            else:
                st.info("No hay suficientes registros para el embudo.")
                
        st.markdown("### 📋 Matriz de Control Mensual")
        df_mostrar = df_hist.copy()
        df_mostrar['Inversión Total'] = df_mostrar['Inversión Total'].map(lambda x: f"${x:,.0f}")
        df_mostrar['Ventas Atribuidas'] = df_mostrar['Ventas Atribuidas'].map(lambda x: f"${x:,.0f}")
        df_mostrar['ROAS'] = df_mostrar['ROAS'].map(lambda x: f"{x:.2f}x")
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

    else:
        st.info("No se detectaron datos históricos válidos en la hoja. Verifica que haya celdas con números cargados.")

# PIE DE PÁGINA COMÚN
st.caption("BogoApts Analytics | Strategic Analytics by goBIG")
