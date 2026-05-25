# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Configuración de la página (Debe ser el primer comando de Streamlit)
st.set_page_config(
    page_title="Dashboard de Rendimiento Paid Media - Bogoapts",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para cumplir estrictamente con la paleta de colores
# Principal: #808080 (Gris), Secundario: #FFFFFF (Blanco), Fondo: #000000 (Negro)
st.markdown(
    """
    <style>
    /* Fondo de la aplicación y color de texto base */
    .stApp {
        background-color: #000000;
        color: #FFFFFF;
    }
    /* Estilos para el Sidebar */
    [data-testid="stSidebar"] {
        background-color: #111111; /* Negro sutilmente contrastado */
        border-right: 1px solid #808080;
    }
    /* Títulos y textos del Sidebar */
    [data-testid="stSidebar"] .stMarkdown h1, 
    [data-testid="stSidebar"] .stMarkdown h2, 
    [data-testid="stSidebar"] .stMarkdown h3,
    [data-testid="stSidebar"] p {
        color: #FFFFFF !important;
    }
    /* Estilos para las tarjetas de métricas (st.metric) */
    [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-weight: bold !important;
        font-size: 24pt !important;
    }
    [data-testid="stMetricLabel"] {
        color: #808080 !important;
        font-weight: 500 !important;
    }
    /* Estilo para los Expanders */
    .stExpander {
        background-color: #111111 !important;
        border: 1px solid #808080 !important;
        border-radius: 5px;
    }
    /* Color de los encabezados generales */
    h1, h2, h3 {
        color: #FFFFFF !important;
        border-bottom: 2px solid #808080;
        padding-bottom: 5px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# URL del Google Sheet exportado en formato CSV para lectura directa con pandas
SHEET_ID = "1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0"
GID = "388077940"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=600)
def load_and_process_data(url):
    # Intentar leer el Google Sheet usando la estructura indicada: 
    # Filas 1-5 cabecera con presupuesto mensual, fila 6 en adelante campañas.
    try:
        # 1. Leer metadata de cabecera (Filas 1 a 5) para extraer el presupuesto mensual
        df_header = pd.read_csv(url, nrows=5, header=None)
        
        # Basado en la bitácora goBIG, se asume que el 'Monthly Approved Budget' o 'Monthly Budget' está en la fila 2 o columna indexada.
        # Buscaremos dinámicamente un valor numérico formateado como moneda en estas primeras filas.
        budget_val = 5000000 # Valor por defecto seguro según bitácora en caso de fallo string parsing
        for col in df_header.columns:
            for val in df_header[col].dropna().astype(str):
                if '$' in val and ('Budget' in str(df_header.values) or 'Approved' in str(df_header.values)):
                    clean_val = val.replace('$', '').replace(',', '').strip()
                    try:
                        budget_val = float(clean_val)
                        break
                    except ValueError:
                        continue

        # 2. Leer las campañas (Fila 6 en adelante)
        df_campaigns = pd.read_csv(url, skiprows=5)
        
        # Estandarización y limpieza de nombres de columnas
        df_campaigns.columns = df_campaigns.columns.str.strip()
        
        # Mapeo dinámico de nombres si difieren ligeramente (e.g., 'Spend (COP)' o 'Inversión')
        col_campaign = [c for c in df_campaigns.columns if 'campaña' in c.lower() or 'campaign' in c.lower()][0]
        col_spend = [c for c in df_campaigns.columns if 'spend' in c.lower() or 'gasto' in c.lower() or 'inversión' in c.lower()][0]
        col_platform = [c for c in df_campaigns.columns if 'plataforma' in c.lower() or 'medio' in c.lower() or 'network' in c.lower() or 'platform' in c.lower()]
        col_objective = [c for c in df_campaigns.columns if 'objetivo' in c.lower() or 'objective' in c.lower() or 'kpi' in c.lower()]
        col_results = [c for c in df_campaigns.columns if 'resultado' in c.lower() or 'result' in c.lower()]
        col_cpa = [c for c in df_campaigns.columns if 'cpa' in c.lower() or 'costo por resultado' in c.lower()]
        
        # Asignar nombres limpios o usar los existentes si coinciden exactamente
        platform_col = col_platform[0] if col_platform else 'Plataforma'
        objective_col = col_objective[0] if col_objective else 'Objetivo'
        results_col = col_results[0] if col_results else 'Resultados'
        cpa_col = col_cpa[0] if col_cpa else 'CPA'
        
        if platform_col not in df_campaigns.columns: df_campaigns[platform_col] = 'Meta Network'
        if objective_col not in df_campaigns.columns: df_campaigns[objective_col] = 'Official Conversions'
        if results_col not in df_campaigns.columns: df_campaigns[results_col] = 0
        if cpa_col not in df_campaigns.columns: df_campaigns[cpa_col] = 0

        # Filtrar de forma estricta omitiendo filas que digan "TOTAL" en la columna de campaña
        df_filtered = df_campaigns[~df_campaigns[col_campaign].astype(str).str.upper().str.contains("TOTAL")].copy()
        
        # Limpieza estricta de la columna de gasto/spend eliminando '$', ',' y espacios, convirtiendo a float
        df_filtered[col_spend] = df_filtered[col_spend].astype(str)\
            .str.replace
