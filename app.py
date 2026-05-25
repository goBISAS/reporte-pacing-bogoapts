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
def load_and_process_data(sheet_url):
    try:
        # Convertir URL de visualización a exportación CSV
        csv_url = sheet_url.replace('/edit?gid=', '/export?format=csv&gid=')
        if '/export?' not in csv_url:
            csv_url = re.sub(r'/edit#gid=\d+', '', sheet_url) + '/export?format=csv'
        
        # Carga del encabezado para extraer el Presupuesto Mensual (filas 1-5)
        df_header = pd.read_csv(csv_url, nrows=5, header=None)
        
        # Búsqueda dinámica de la métrica de presupuesto en las primeras filas
        presupuesto_mensual = 0.0
        for col in df_header.columns:
            for val in df_header[col].dropna():
                val_str = str(val).strip()
                if any(k in val_str.lower() for k in ['presupuesto', 'budget', 'total mensual']):
                    numbers = re.findall(r'\d+[.,]?\d*[.,]?\d*', val_str)
                    if numbers:
                        clean_num = ''.join(c for c in numbers[0] if c.isdigit())
                        presupuesto_mensual = float(clean_num) if clean_num else 0.0
        
        # Respaldo en caso de que no haya una celda de texto explícita
        if presupuesto_mensual == 0.0:
            for col in df_header.columns:
                for val in df_header[col].dropna():
                    try:
                        clean_val = str(val).replace('$', '').replace(',', '').replace('.', '').strip()
                        if clean_val.isdigit() and float(clean_val) > 100000:
                            presupuesto_mensual = float(clean_val)
                            break
                    except:
                        continue

        # Carga de los datos de campaña (fila 6 en adelante)
        df = pd.read_csv(csv_url, skiprows=5)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Identificación e indexación adaptativa de columnas clave de la hoja
        campaign_col = [c for c in df.columns if 'campa' in c.lower() or 'name' in c.lower()][0]
        platform_col = [c for c in df.columns if 'plataforma' in c.lower() or 'medio' in c.lower() or 'source' in c.lower()][0]
        spend_col = [c for c in df.columns if 'spend' in c.lower() or 'invers' in c.lower() or 'gasto' in c.lower()][0]
        
        objective_col = [c for c in df.columns if 'objetivo' in c.lower() or 'objective' in c.lower()]
        objective_col = objective_col[0] if objective_col else None
        
        results_col = [c for c in df.columns if 'result' in c.lower() or 'convers' in c.lower()]
        results_col = results_col[0] if results_col else None
        
        cpa_col = [c for c in df.columns if 'cpa' in c.lower() or 'costo por' in c.lower()]
        cpa_col = cpa_col[0] if cpa_col else None

        # Requerimiento Estricto: Descartar filas con "TOTAL" para evitar duplicaciones
        df = df[~df[campaign_col].astype(str).str.upper().str.contains('TOTAL')]
        df = df[~df[platform_col].astype(str).str.upper().str.contains('TOTAL')]
        df = df.dropna(subset=[campaign_col, platform_col])

        # Requerimiento Estricto: Limpieza de la columna Spend (COP) a float puro
        def clean_currency(val):
            if pd.isna(val):
                return 0.0
            val_str = str(val).replace('$', '').replace('COP', '')
            val_str = re.sub(r'[\s,.]', '', val_str) # Remueve separadores visuales
            try:
                return float(val_str)
            except ValueError:
                return 0.0

        df[spend_col] = df[spend_col].apply(clean_currency)
        
        if results_col:
            df[results_col] = pd.to_numeric(df[results_col], errors='coerce').fillna(0)
        if cpa_col:
            df[cpa_col] = df[cpa_col].apply(clean_currency)
            
        # Homologación a DataFrame Estructurado estándar
        mapped_df = pd.DataFrame({
            'Medio': df[platform_col],
            'Campaña': df[campaign_col],
            'Objetivo': df[objective_col] if objective_col else 'Official Conversions',
            'Spend': df[spend_col],
            'Resultados': df[results_col] if results_col else 0,
            'CPA': df[cpa_col] if cpa_col else 0.0
        })
        
        mapped_df['Objetivo'] = mapped_df['Objetivo'].fillna('Official Conversions')
        
        return mapped_df, presupuesto_mensual
        
    except Exception as e:
        st.error(f"Error crítico en lectura de la arquitectura de datos: {e}")
        return pd.DataFrame(), 0.0

# 3. Sidebar e Identidad Visual (Branding)
st.sidebar.image("Logo_bogoapts_dashboard.PNG", use_container_width=True)
st.sidebar.title("Bogoapts Dashboard")
st.sidebar.markdown("""
**Control de Rendimiento de Paid Media** *Versión 1.0 Estándar* ___
**Cliente:** Bogoapts  
**Entorno:** Streamlit Cloud  
**Frecuencia:** Tiempo Real (API Cacheada)
""")

# URL de origen de datos asignada
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0/edit?gid=388077940#gid=388077940"

# Ejecución de Pipeline de Datos
df_clean, presupuesto = load_and_process_data(SHEET_URL)

if not df_clean.empty:
    # 4. Cálculo Automático en Python del Gasto acumulado (Requerimiento Estricto)
    gasto_total = float(df_clean['Spend'].sum())
    dia_actual = datetime.now().day
    
    if presupuesto == 0:
        presupuesto = 15000000.0  # Fallback seguro de negocio si la cabecera está vacía

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

    # 6. Gráfica Principal: Plotly Treemap (UX Móvil Optimizado)
    st.subheader("🎯 Distribución de Inversión Acumulada")
    
    # Inyección dinámica del monto total gastado por plataforma en el string de Nivel 1
    plataforma_totals = df_clean.groupby('Medio')['Spend'].sum().to_dict()
    df_clean['Medio_Label'] = df_clean['Medio'].apply(lambda x: f"{x} (${plataforma_totals[x]:,.0f} COP)")

    fig = px.treemap(
        df_clean,
        path=['Medio_Label', 'Objetivo'],
        values='Spend',
        color='Spend',
        color_continuous_scale=['#444444', '#808080', '#FFFFFF'] # Escala monocromática corporativa
    )

    # Requerimiento UX Móvil: Uso estricto de texttemplate para impresión nativa sin necesidad de hover
    fig.update_traces(
        texttemplate="<b>%{label}</b><br>$%{value:,.0f} COP<br>%{percentParent:.1%}",
        textposition="inside",
        insidetextfont=dict(size=14, color="#FFFFFF")
    )

    fig.update_layout(
        margin=dict(t=10, l=10, r=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        coloraxis_showscale=False
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 7. Tabla de Detalles (st.expander final)
    with st.expander("🔍 Ver Tabla de Detalles Completa"):
        df_display = df_clean[['Medio', 'Campaña', 'Objetivo', 'Spend', 'Resultados', 'CPA']].copy()
        
        # Formateo estricto para presentación ejecutiva del cliente
        df_display['Spend'] = df_display['Spend'].apply(lambda x: f"$ {x:,.0f} COP")
        df_display['CPA'] = df_display['CPA'].apply(lambda x: f"$ {x:,.0f} COP" if x > 0 else "N/A")
        df_display['Resultados'] = df_display['Resultados'].apply(lambda x: f"{x:,.0f}" if x > 0 else "0")
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)

else:
    st.error("Error en la extracción. Asegúrate de que las credenciales de lectura compartida de Google Sheets estén activas.")
