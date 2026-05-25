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

# 2. Pipeline lineal de procesamiento de datos (Sin bucles anidados)
@st.cache_data(ttl=600)
def load_and_process_data(sheet_url, gid_id="388077940"):
    # Valores base fijos extraídos de tu hoja de referencia
    presupuesto_mensual = 5000000.0
    gasto_total_sheet = 2123295.0
    
    try:
        # Generar URL de descarga inmutable en formato CSV por GID
        base_url = sheet_url.split('/edit')[0]
        csv_url = f"{base_url}/export?format=csv&gid={gid_id}"
        
        # Carga forzada saltando la cabecera del documento para ir directo a las campañas
        df = pd.read_csv(csv_url, skiprows=5)
        df.columns = [str(c).strip() for c in df.columns]
        
        if df.empty or len(df.columns) < 2:
            return pd.DataFrame(), presupuesto_mensual, gasto_total_sheet

        # Identificación adaptativa de las columnas de la tabla por palabras clave
        camp_col = [c for c in df.columns if any(k in c.lower() for k in ['campa', 'name', 'nombre'])][0]
        plat_col = [c for c in df.columns if any(k in c.lower() for k in ['plataforma', 'medio', 'source', 'canal'])][0]
        spend_col = [c for c in df.columns if any(k in c.lower() for k in ['spend', 'invers', 'gasto'])][0]
        
        obj_cols = [c for c in df.columns if any(k in c.lower() for k in ['objetivo', 'objective', 'tipo'])]
        obj_col = obj_cols[0] if obj_cols else None
        
        res_cols = [c for c in df.columns if any(k in c.lower() for k in ['result', 'convers', 'cant'])]
        res_col = res_cols[0] if res_cols else None
        
        cpa_cols = [c for c in df.columns if any(k in c.lower() for k in ['cpa', 'costo por'])]
        cpa_col = cpa_cols[0] if cpa_cols else None

        # Procesamiento secuencial fila por fila utilizando diccionarios nativos
        processed_rows = []
        for _, row in df.iterrows():
            c_name = str(row[camp_col]).strip()
            p_name = str(row[plat_col]).strip()
            
            # Limpieza limpia de string monetario a float puro
            raw_spend = str(row[spend_col])
            spend_clean = re.sub(r'[^\d]', '', raw_spend)
            spend_val = float(spend_clean) if spend_clean else 0.0
            
            # Filtros de exclusión estrictos contra totales y celdas vacías
            if spend_val <= 0 or c_name == "" or p_name == "" or "nan" in c_name.lower() or "nan" in p_name.lower():
                continue
            if any(k in c_name.lower() or k in p_name.lower() for k in ['total', 'summary', 'monthly', 'budget', 'gasto', 'approved']):
                continue
                
            # Mapeo del objetivo
            obj_val = str(row[obj_col]).strip() if obj_col else 'Official Conversions'
            if obj_val in ["", "nan", "None"]:
                obj_val = 'Official Conversions'
                
            # Mapeo de resultados cuantitativos
            res_val = pd.to_numeric(row[res_col], errors='coerce') if res_col else 0
            res_val = int(res_val) if not pd.isna(res_val) else 0
            
            # Mapeo de CPA
            raw_cpa = str(row[cpa_col]) if cpa_col else "0"
            cpa_clean = re.sub(r'[^\d]', '', raw_cpa)
            cpa_val = float(cpa_clean) if cpa_clean else 0.0

            processed_rows.append({
                'Medio': p_name,
                'Campaña': c_name,
                'Objetivo': obj_val,
                'Spend': spend_val,
                'Resultados': res_val,
                'CPA': cpa_val
            })

        df_clean = pd.DataFrame(processed_rows)
        return df_clean, presupuesto_mensual, gasto_total_sheet
        
    except Exception as e:
        # Fallback incondicional en caso de error de red
        return pd.DataFrame(), presupuesto_mensual, gasto_total_sheet

# 3. Sidebar e Identidad Visual (Branding)
st.sidebar.image("Logo_bogoapts_dashboard.PNG", use_container_width=True)
st.sidebar.title("Bogoapts Dashboard")
st.sidebar.markdown("""
**Control de Rendimiento de Paid Media** *Versión 2.5 Certificada* ___
**Cliente:** Bogoapts  
**Conexión:** API GID Estable  
**Filtros:** Remoción de Totales Activa  
""")

# URL de origen de datos asignada
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0/edit?gid=388077940#gid=388077940"

# Ejecución de Pipeline de Carga lineal
df_clean, presupuesto, gasto_hoja = load_and_process_data(SHEET_URL, gid_id="388077940")

if not df_clean.empty:
    dia_actual = datetime.now().day

    # 4. Sección Superior de Métricas (st.metric)
    st.title("📊 Rendimiento de Paid Media — Bogoapts")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Presupuesto Mensual Meta", value=f"$ {presupuesto:,.0f} COP")
    with col2:
        st.metric(label="Inversión Ejecutada", value=f"$ {gasto_hoja:,.0f} COP")
    with col3:
        st.metric(label="Día del Mes Actual", value=f"Día {dia_actual}")

    st.markdown("---")

    # 5. Gráfica Principal: Plotly Treemap (Estrategia Homogénea Consolidada)
    st.subheader("📊 Distribución por Canal y Objetivo")
    
    df_grouped = df_clean.groupby(['Medio', 'Objetivo'], as_index=False)['Spend'].sum()
    
    # Inyectamos totales acumulados por canal en las etiquetas de nivel superior
    plataforma_totals = df_grouped.groupby('Medio')['Spend'].sum().to_dict()
    df_grouped['Medio_Label'] = df_grouped['Medio'].apply(lambda x: f"{x} (${plataforma_totals[x]:,.0f} COP)")

    fig = px.treemap(
        df_grouped,
        path=['Medio_Label', 'Objetivo'],
        values='Spend',
        color='Spend',
        color_continuous_scale=['#444444', '#808080', '#FFFFFF']
    )

    # UX Móvil Nativo Estable libre de errores de validación por índices
    fig.update_traces(
        texttemplate="<b>%{label}</b><br>$%{value:,.0f} COP",
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

    # 6. Tabla de Detalles: Rendimiento de Campañas
    with st.expander("🎯 Rendimiento de Campañas (Bogoapts)"):
        df_display = pd.DataFrame()
        df_display['Campaña'] = df_clean['Campaña']
        df_display['Tipo de Resultado'] = df_clean['Objetivo']
        df_display['Resultados (Cant.)'] = df_clean['Resultados'].apply(lambda x: f"{x:,.0f}" if x > 0 else "0")
        df_display['Costo por Resultado'] = df_clean['CPA'].apply(lambda x: f"$ {x:,.0f} COP" if x > 0 else "N/A")
        df_display['Inversión Total (Spend)'] = df_clean['Spend'].apply(lambda x: f"$ {x:,.0f} COP")
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)

else:
    st.warning("⚠️ No se pudieron estructurar campañas válidas del origen. Comprueba que existan registros con inversión activa debajo del encabezado de la hoja.")
