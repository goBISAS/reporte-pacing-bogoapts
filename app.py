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
        /* Contenedores de métricas */
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

# 2. Funciones de Carga y Procesamiento de Datos (Cacheado)
@st.cache_data(ttl=600)
def load_and_process_data(sheet_url):
    try:
        # Convertir URL de visualización a exportación CSV
        csv_url = sheet_url.replace('/edit?gid=', '/export?format=csv&gid=')
        if '/export?' not in csv_url:
            csv_url = re.sub(r'/edit#gid=\d+', '', sheet_url) + '/export?format=csv'
        
        # Carga del encabezado para extraer el Presupuesto Mensual (filas 1-5)
        df_header = pd.read_csv(csv_url, nrows=5, header=None)
        
        # Intento dinámico de buscar un valor numérico que represente el presupuesto mensual
        presupuesto_mensual = 0.0
        for col in df_header.columns:
            for val in df_header[col].dropna():
                val_str = str(val).strip()
                if any(k in val_str.lower() for k in ['presupuesto', 'budget', 'total mensual']):
                    # Buscar número en la misma fila o filas adyacentes
                    numbers = re.findall(r'\d+[.,]?\d*[.,]?\d*', val_str)
                    if numbers:
                        clean_num = ''.join(c for c in numbers[0] if c.isdigit())
                        presupuesto_mensual = float(clean_num) if clean_num else 0.0
        
        # Si no se encuentra con texto, buscar el valor más alto en el header
        if presupuesto_mensual == 0.0:
            for col in df_header.columns:
                for val in df_header[col].dropna():
                    try:
                        clean_val = str(val).replace('$', '').replace(',', '').replace('.', '').strip()
                        if clean_val.isdigit() and float(clean_val) > 100
