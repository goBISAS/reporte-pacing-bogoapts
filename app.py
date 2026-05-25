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

# Inyección de estilos CSS para el modo oscuro corporativo
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

# 2. Pipeline de carga y limpieza de datos (Sintaxis Corregida)
@st.cache_data(ttl=600)
def load_and_process_data(sheet_url, gid_id="388077940"):
    # Valores base por defecto en caso de cualquier anomalía de conexión
    presupuesto_mensual = 5000000.0
    gasto_total_sheet = 2123295.0
    
    try:
        # Generar URL de descarga inmutable en formato CSV por GID
        base_url = sheet_url.split('/edit')[0]
        csv_url = f"{base_url}/export?format=csv&gid={gid_id}"
        
        # --- BLOQUE 1: Extracción Quirúrgica de Métricas de Cabecera ---
        try:
            df_header = pd.read_csv(csv_url, nrows=6, header=None).fillna("")
            df_header = df_header.astype(str)
            
            for idx, row in df_header.iterrows():
                row_str = " ".join(row.values).lower()
                # Buscar presupuesto aprobado
                if "approved budget" in row_str or "budget" in row_str:
                    for cell in row.values:
                        val_clean = re.sub(r'[^\d]', '', str(cell))
                        if val_clean.isdigit() and float(val_clean) > 100000:
                            presupuesto_mensual = float(val_clean)
                # Buscar gasto reportado en la hoja
                if "monthly spend" in row_str or "spend" in row_str:
                    for cell in row.values:
                        val_clean = re.sub(r'[^\d]', '', str(cell))
                        if val_clean.isdigit() and float(val_clean) > 0 and float(val_clean) != presupuesto_mensual:
                            gasto_total_sheet = float(val_clean)
        except:
            pass  # Failsafe: Mantiene los valores por defecto si la cabecera cambia

        # --- BLOQUE 2: Carga de la Tabla de Campañas (Fila 6 en adelante) ---
        df = pd.read_csv(csv_url, skiprows=5)
        df.columns = [str(c).strip() for c in df.columns]
        
        if df.empty or len(df.columns) < 2:
            return pd.DataFrame(), presupuesto_mensual, gasto_total_sheet

        # Identificación e indexación adaptativa de columnas clave
        camp_col = [c for c in df.columns if any(k in c.lower() for k in ['campa', 'name', 'nombre'])][0]
        plat_col = [c for c in df.columns if any(k in c.lower() for k in ['plataforma', 'medio', 'source', 'canal'])][0]
        spend_col = [c for c in df.columns if any(k in c.lower() for k in ['spend', 'invers', 'gasto'])][0]
        
        obj_cols = [c for c in df.columns if any(k in c.lower() for k in ['objetivo', 'objective', 'tipo'])]
        obj_col = obj_cols[0] if obj_cols else None
        
        res_cols = [c for c in df.columns if any(k in c.lower() for k in ['result', 'convers', 'cant'])]
        res_col = res_cols[0] if res_cols else None
        
        cpa_cols = [c for c in df.columns if any(k in c.lower() for k in ['cpa', 'costo por'])]
        cpa_col = cpa_cols[0] if cpa_cols else None

        # Función de limpieza monetaria
        def clean_currency_to_float(val):
            if pd.isna(val) or str(val).strip() == '':
                return 0.0
            val_clean = re.sub(r'[^\d]', '', str(val))
            return float(val_clean) if val_clean else 0.0

        # Procesamiento y limpieza de registros individuales
        processed_rows = []
        for _, row in df.iterrows():
            c_name = str(row[camp_col]).strip()
            p_name = str(row[plat_col]).strip()
            spend_val = clean_currency_to_float(row[spend_col])
            
            # Filtros de exclusión estrictos contra totales o residuos
            if spend_val <= 0 or c_name == "" or p_name == "" or "nan" in c_name.lower() or "nan" in p_name.lower():
                continue
            if any(k in c_name.lower() or k in p_name.lower() for k in ['total', 'summary', 'monthly', 'budget', 'gasto', 'approved']):
                continue
                
            obj_val = str(row[obj_col]).strip() if obj_col else 'Official Conversions'
            if obj_val in ["", "nan", "None"]:
                obj_val = 'Official Conversions'
                
            res_val = pd.to_numeric(row[res_col], errors='coerce') if res_col else 0
            res_val = int(res_val) if not pd.isna(res_val) else 0
            
            cpa_val = clean_currency_to_float(row[cpa_col]) if cpa_col else 0.0

            processed_rows.append({
                'Medio': p_name,
                'Campaña': c_name,
                'Objetivo': obj_val,
                'Spend': spend_val,
                'Resultados': res_val,
                'CPA': cpa_val
            })

        df_clean = pd.DataFrame(processed_rows)
        return df_clean, presupuesto_mensual, gasto
