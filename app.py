import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import re

# 1. Configuración de la interfaz visual de Streamlit
st.set_page_config(
    page_title="Dashboard de Rendimiento - Bogoapts",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyección de estilos CSS optimizados para el modo oscuro corporativo
st.markdown("""
    <style>
        .stApp {
            background-color: #000000;
            color: #FFFFFF;
        }
        h1, h2, h3, p, span, label {
            color: #FFFFFF !important;
        }
        div[data-testid="stMetric"] {
            background-color: #1A1A1A;
            border-left: 4px solid #808080;
            padding: 15px;
            border-radius: 5px;
        }
        section[data-testid="stSidebar"] {
            background-color: #111111;
            border-right: 1px solid #333333;
        }
        .streamlit-expanderHeader {
            background-color: #1A1A1A !important;
            color: #FFFFFF !important;
            border: 1px solid #333333 !important;
        }
    </style>
""", unsafe_allow_html=True)

# 2. Pipeline robusto de extracción y limpieza de datos
@st.cache_data(ttl=600)
def load_and_process_data(sheet_url, gid_id="388077940"):
    try:
        # Generar URL de descarga de la pestaña específica en formato CSV
        base_url = sheet_url.split('/edit')[0]
        csv_url = f"{base_url}/export?format=csv&gid={gid_id}"
        
        # Leer el documento completo de forma cruda sin asumir cabeceras fijas
        df_raw = pd.read_csv(csv_url, header=None).fillna("")
        
        if df_raw.empty:
            return pd.DataFrame(), 5000000.0, 2123295.0

        # --- BLOQUE 1: Extracción Inteligente de Métricas del Encabezado ---
        presupuesto_mensual = 5000000.0  # Valores base por defecto
        gasto_total_sheet = 2123295.0
        
        # Escaneo de las primeras 10 filas para encontrar los KPI globales de la marca
        for idx, row in df_raw.head(10).iterrows():
            row_str = " ".join([str(cell).lower() for cell in row])
            
            # Buscar coincidencia para presupuesto aprobado
            if "approved budget" in row_str or "presupuesto" in row_str:
                for cell in row:
                    val_clean = re.sub(r'[^\d]', '', str(cell))
                    if val_clean.isdigit() and float(val_clean) > 100000:
                        presupuesto_mensual = float(val_clean)
                        
            # Buscar coincidencia para gasto ejecutado acumulado
            if "monthly spend" in row_str or "spend" in row_str or "gasto" in row_str:
                for cell in row:
                    val_clean = re.sub(r'[^\d]', '', str(cell))
                    if val_clean.isdigit() and float(val_clean) > 0 and float(val_clean) != presupuesto_mensual:
                        gasto_total_sheet = float(val_clean)

        # --- BLOQUE 2: Localización Dinámica de la Tabla de Campañas ---
        header_row_idx = None
        
        # Buscar en qué fila se encuentra la cabecera de la tabla de datos
        for idx, row in df_raw.iterrows():
            row_str_cells = [str(cell).strip().lower() for cell in row]
            # Validamos palabras clave comunes de tus reportes
            if any(k in row_str_cells for k in ['medio', 'plataforma', 'media', 'campaña', 'campaign', 'objective', 'objetivo']):
                header_row_idx = idx
                break
        
        # Failsafe: Si no encuentra cabeceras por texto
