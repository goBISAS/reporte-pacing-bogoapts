import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import re

# 1. Configuración de la página de Streamlit
st.set_page_config(
    page_title="Dashboard de Rendimiento - Bogoapts",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS personalizado para cumplir con la paleta de colores del cliente
# Principal: #808080, Secundario: #FFFFFF, Fondo: #000000
st.markdown("""
    <style>
        /* Fondo de la aplicación */
        .stApp {
            background-color: #000000;
            color: #FFFFFF;
        }
        /* Títulos y textos generales */
        h1, h2, h3, p, span, label {
            color: #FFFFFF !important;
        }
        /* Contenedores de métricas superiores */
        div[data-testid="stMetric"] {
            background-color: #1A1A1A;
            border-left: 4px solid #808080;
            padding: 15px;
            border-radius: 5px;
        }
        /* Sidebar personalizado */
        section[data-testid="stSidebar"] {
            background-color: #111111;
            border-right: 1px solid #333333;
        }
        /* Estilo para los expanders */
        .streamlit-expanderHeader {
            background-color: #1A1A1A !important;
            color: #FFFFFF !important;
            border: 1px solid #333333 !important;
        }
    </style>
""", unsafe_allow_html=True)

# 2. Funciones de Carga y Procesamiento de Datos (Cacheado a 10 min)
@st.cache_data(ttl=600)
def load_and_process_data(sheet_url, gid_id="388077940"):
    try:
        # Extracción directa por GID único (Inmutable ante cambios de nombre de pestaña)
        base_url = sheet_url.split('/edit')[0]
        csv_url = f"{base_url}/export?format=csv&gid={gid_id}"
        
        # Carga del encabezado para extraer el Presupuesto Mensual (filas 1-5)
        df_header = pd.read_csv(csv_url, nrows=5, header=None)
        
        # Búsqueda dinámica del presupuesto mensual en las celdas del header
        presupuesto_mensual = 0.0
        for col in df_header.columns:
            for val in df_header[col].dropna():
                val_str = str(val).strip()
                if any(k in val_str.lower() for k in ['presupuesto', 'budget', 'total mensual', 'meta']):
                    numbers = re.findall(r'\d+[.,]?\d*[.,]?\d*', val_str)
                    if numbers:
                        clean_num = ''.join(c for c in numbers[0] if c.isdigit())
                        presupuesto_mensual = float(clean_num) if clean_num else 0.0
        
        # Carga de los datos de campaña (fila 6 en adelante)
        df = pd.read_csv(csv_url, skiprows=5)
        df.columns = [str(c).strip() for c in df.columns]
        
        if df.empty or len(df.columns) < 2:
            return pd.DataFrame(), presupuesto_mensual

        # --- SISTEMA FAILSAFE: Mapeo Flexible de Columnas ---
        camp_matches = [c for c in df.columns if any(k in c.lower() for k in ['campa', 'name', 'nombre', 'ad group'])]
        plat_matches = [c for c in df.columns if any(k in c.lower() for k in ['plataforma', 'medio', 'source', 'network', 'canal'])]
        spend_matches = [c for c in df.columns if any(k in c.lower() for k in ['spend', 'invers', 'gasto', 'valor', 'cop'])]
        obj_matches = [c for c in df.columns if any(k in c.lower() for k in ['objetivo', 'objective', 'goal', 'tipo'])]
        res_matches = [c for c in df.columns if any(k in c.lower() for k in ['result', 'convers', 'compras', 'cant'])]
        cpa_matches = [c for c in df.columns if any(k in c.lower() for k in ['cpa', 'costo por', 'cost/'])]

        # Mapeos por posición física de respaldo
        campaign_col = camp_matches[0] if camp_matches else df.columns[1] if len(df.columns) > 1 else df.columns[0]
        platform_col = plat_matches[0] if plat_matches else df.columns[0]
        spend_col = spend_matches[0] if spend_matches else df.columns[3] if len(df.columns) > 3 else df.columns[-1]
        
        objective_col = obj_matches[0] if obj_matches else None
        results_col = res_matches[0] if res_matches else None
        cpa_col = cpa_matches[0] if cpa_matches else None

        # Requerimiento Estricto: Filtrar filas "TOTAL"
        df = df[~df[campaign_col].astype(str).str.upper().str.contains('TOTAL', na=False)]
        df = df[~df[platform_col].astype(str).str.upper().str.contains('TOTAL', na=False)]
        df = df.dropna(subset=[campaign_col, platform_col])

        # Limpieza de formatos de moneda
        def clean_currency(val):
            if pd.isna(val):
                return 0.0
            val_str = str(val).upper().replace('$', '').replace('COP', '').replace('USD', '')
            val_str = re.sub(r'[\s,.]', '', val_str)
            try:
                return float(val_str)
            except ValueError:
                try:
                    return float(str(val).replace('$', '').replace(',', '').strip())
                except:
                    return 0.0

        df[spend_col] = df[spend_col].apply(clean_currency)
        
        # Construcción del DataFrame Estructurado de Negocio
        mapped_df = pd.DataFrame()
        mapped_df['Medio'] = df[platform_col]
        mapped_df['Campaña'] = df[campaign_col]
        mapped_df['Objetivo'] = df[objective_col] if objective_col else 'Official Conversions'
        mapped_df['Spend'] = df[spend_col]
        
        if results_col:
            mapped_df['Resultados'] = pd.to_numeric(df[results_col], errors='coerce').fillna(0)
        else:
            mapped_df['Resultados'] = 0
            
        if cpa_col:
            mapped_df['CPA'] = df[cpa_col].apply(clean_currency)
        else:
            mapped_df['CPA'] = 0.0
        
        # Unificación del nombre de objetivos nulos
        mapped_df['Objetivo'] = mapped_df['Objetivo'].fillna('Official Conversions')
        
        # Filtrado para Plotly Treemap
        mapped_df = mapped_df[mapped_df['Spend'] > 0]
        
        return mapped_df, presupuesto_mensual
        
    except Exception as e:
        st.error(f"Error crítico en lectura de la arquitectura de datos: {e}")
        return pd.DataFrame(), 0.0

# 3. Sidebar e Identidad Visual (Branding)
st.sidebar.image("Logo_bogoapts_dashboard.PNG", use_container_width=True)
st.sidebar.title("Bogoapts Dashboard")
st.sidebar.markdown("""
**Control de Rendimiento de Paid Media** *Versión 1.4 Corrección* ___
**Cliente:** Bogoapts  
**Conexión:** Pacing Target Activo  
**Entorno:** Streamlit Cloud  
""")

# URL base asignada
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0/edit?gid=388077940#gid=388077940"

# Ejecución del pipeline por GID
df_clean, presupuesto = load_and_process_data(SHEET_URL, gid_id="388077940")

if not df_clean.empty:
    # 4. Cálculo Automático en Python del Gasto acumulado
    gasto_total = float(df_clean['Spend'].sum())
    dia_actual = datetime.now().day
    
    if presupuesto == 0:
        presupuesto = 15000000.0  # Fallback seguro corporativo

    # 5. Métricas Superiores (st.metric)
    st.title("📊 Rendimiento de Paid Media — Bogoapts")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Presupuesto Mensual Meta", value=f"$ {presupuesto:,.0f} COP")
    with col2:
        st.metric(label="Inversión Ejecutada (Python Calc)", value=f"$ {gasto_total:,.0f} COP")
    with col3:
        st.metric(label="Día del Mes Actual", value=f"Día {dia_actual}")

    st.markdown("---")

    # 6. Gráfica Principal: Plotly Treemap Ajustado (Corrección de Título y Bug)
    st.subheader("📊 Distribución por Canal y Objetivo")
    
    # Agrupación dinámica para etiquetas de Nivel 1
    plataforma_totals = df_clean.groupby('Medio')['Spend'].sum().to_dict()
    df_clean['Medio_Label'] = df_clean['Medio'].apply(lambda x: f"{x} (${plataforma_totals[x]:,.0f} COP)")

    fig = px.treemap(
        df_clean,
        path=['Medio_Label', 'Objetivo'],
        values='Spend',
        color='Spend',
        color_continuous_scale=['#444444', '#808080', '#FFFFFF']
    )

    # UX Móvil Sólido: Eliminamos el argumento estático insidefontcolor causante del bug
    fig.update_traces(
        texttemplate="<b>%{label}</b><br>$%{value:,.0f} COP<br>%{percentParent:.1%}",
        textposition="inside"
    )

    fig.update_layout(
        margin=dict(t=15, l=10, r=10, b=15),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        coloraxis_showscale=False
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 7. Tabla de Detalles: Rendimiento de Campañas (Desplegado al corregir el hilo)
    with st.expander("🎯 Rendimiento de Campañas (Bogoapts)"):
        # Generamos las columnas alineadas al benchmark enviado de Cantabria Labs
        df_display = pd.DataFrame()
        df_display['Campaña'] = df_clean['Campaña']
        df_display['Tipo de Resultado'] = df_clean['Objetivo']
        df_display['Resultados (Cant.)'] = df_clean['Resultados'].apply(lambda x: f"{x:,.0f}" if x > 0 else "0")
        df_display['Costo por Resultado'] = df_clean['CPA'].apply(lambda x: f"$ {x:,.0f} COP" if x > 0 else "N/A")
        df_display['Inversión Total (Spend)'] = df_clean['Spend'].apply(lambda x: f"$ {x:,.0f} COP")
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)

else:
    st.warning("⚠️ Error al procesar los datos de la hoja. Comprueba que el archivo cuente con registros en las celdas inferiores.")
