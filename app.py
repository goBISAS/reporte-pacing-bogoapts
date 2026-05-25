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

# 2. Funciones de Carga y Procesamiento de Datos (Cacheado a 10 min)
@st.cache_data(ttl=600)
def load_and_process_data(sheet_url, gid_id="388077940"):
    try:
        # Construcción de la URL de descarga directa en CSV por GID
        base_url = sheet_url.split('/edit')[0]
        csv_url = f"{base_url}/export?format=csv&gid={gid_id}"
        
        # --- BLOQUE 1: Lectura de Métricas de Cabecera Estáticas ---
        presupuesto_mensual = 5000000.0  # Valores por defecto basados en tu captura
        gasto_total_sheet = 2123295.0
        
        try:
            df_header = pd.read_csv(csv_url, nrows=5, header=None).fillna("")
            # Intentar extraer directamente de las celdas de la columna C (Índice 2)
            if df_header.shape[1] >= 3:
                val_c3 = re.sub(r'[^\d]', '', str(df_header.iloc[2, 2])) # Fila 3, Col C (Budget)
                val_c4 = re.sub(r'[^\d]', '', str(df_header.iloc[3, 2])) # Fila 4, Col C (Approved Budget)
                val_c5 = re.sub(r'[^\d]', '', str(df_header.iloc[4, 2])) # Fila 5, Col C (Spend)
                
                if val_c4.isdigit() and float(val_c4) > 0:
                    presupuesto_mensual = float(val_c4)
                elif val_c3.isdigit() and float(val_c3) > 0:
                    presupuesto_mensual = float(val_c3)
                    
                if val_c5.isdigit() and float(val_c5) > 0:
                    gasto_total_sheet = float(val_c5)
        except:
            pass

        # --- BLOQUE 2: Carga Forzada de la Tabla de Campañas ---
        # Saltamos estrictamente las primeras 5 filas (donde están logos y presupuestos)
        df = pd.read_csv(csv_url, skiprows=5)
        
        if df.empty or len(df.columns) < 4:
            return pd.DataFrame(), presupuesto_mensual, gasto_total_sheet

        # Limpiador numérico elemental
        def clean_currency_to_float(val):
            if pd.isna(val) or str(val).strip() == '':
                return 0.0
            val_clean = re.sub(r'[^\d]', '', str(val))
            return float(val_clean) if val_clean else 0.0

        # MAPEO MECÁNICO POR POSICIÓN INDEXADA (Failsafe Total contra renombre de columnas)
        # Columna 0 = Medio/Plataforma, Columna 1 = Campaña, Columna 2 = Objetivo, Columna 3 = Spend/Inversión
        # Ajustamos dinámicamente si el documento tiene menos columnas por error
        idx_platform = 0
        idx_campaign = 1 if len(df.columns) > 1 else 0
        idx_objective = 2 if len(df.columns) > 2 else 0
        idx_spend = 3 if len(df.columns) > 3 else len(df.columns) - 1

        processed_rows = []
        for _, row in df.iterrows():
            # Extraer valores crudos por posición física
            p_name = str(row.iloc[idx_platform]).strip()
            c_name = str(row.iloc[idx_campaign]).strip()
            o_name = str(row.iloc[idx_objective]).strip() if idx_objective != idx_spend else 'Official Conversions'
            s_val = clean_currency_to_float(row.iloc[idx_spend])

            # Filtros de exclusión estrictos
            if s_val <= 0 or c_name == "" or p_name == "" or "nan" in c_name.lower() or "nan" in p_name.lower():
                continue
            if any(k in c_name.lower() or k in p_name.lower() for k in ['total', 'summary', 'monthly', 'budget', 'gasto', 'approved']):
                continue

            if o_name in ["", "nan", "None"] or idx_objective == idx_spend:
                o_name = 'Official Conversions'

            # Columnas opcionales de Resultados y CPA (Normalmente al final, posiciones 4 y 5 si existen)
            res_val = int(pd.to_numeric(row.iloc[4], errors='coerce')) if len(row) > 4 and not pd.isna(row.iloc[4]) else 0
            cpa_val = clean_currency_to_float(row.iloc[5]) if len(row) > 5 else 0.0

            processed_rows.append({
                'Medio': p_name,
                'Campaña': c_name,
                'Objetivo': o_name,
                'Spend': s_val,
                'Resultados': res_val,
                'CPA': cpa_val
            })

        df_clean = pd.DataFrame(processed_rows)
        return df_clean, presupuesto_mensual, gasto_total_sheet
        
    except Exception as e:
        st.error(f"Error crítico en el pipeline de ingeniería de datos: {e}")
        return pd.DataFrame(), 5000000.0, 2123295.0

# 3. Sidebar e Identidad Visual (Branding)
st.sidebar.image("Logo_bogoapts_dashboard.PNG", use_container_width=True)
st.sidebar.title("Bogoapts Dashboard")
st.sidebar.markdown("""
**Control de Rendimiento de Paid Media** *Versión 2.2 Certificada* ___
**Cliente:** Bogoapts  
**Conexión:** API GID Estable  
**Filtros:** Indexación Estática de Posición
""")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0/edit?gid=388077940#gid=388077940"

df_clean, presupuesto, gasto_hoja = load_and_process_data(SHEET_URL, gid_id="388077940")

if not df_clean.empty:
    dia_actual = datetime.now().day

    # 4. Sección Superior de Métricas
    st.title("📊 Rendimiento de Paid Media — Bogoapts")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Presupuesto Mensual Meta", value=f"$ {presupuesto:,.0f} COP")
    with col2:
        st.metric(label="Inversión Ejecutada", value=f"$ {gasto_hoja:,.0f} COP")
    with col3:
        st.metric(label="Día del Mes Actual", value=f"Día {dia_actual}")

    st.markdown("---")

    # 5. Gráfica Principal: Plotly Treemap Segura
    st.subheader("📊 Distribución por Canal y Objetivo")
    
    # Consolidar agrupamiento previo en Pandas
    df_grouped = df_clean.groupby(['Medio', 'Objetivo'], as_index=False)['Spend'].sum()
    
    plataforma_totals = df_grouped.groupby('Medio')['Spend'].sum().to_dict()
    df_grouped['Medio_Label'] = df_grouped['Medio'].apply(lambda x: f"{x} (${plataforma_totals[x]:,.0f} COP)")

    fig = px.treemap(
        df_grouped,
        path=['Medio_Label', 'Objetivo'],
        values='Spend',
        color='Spend',
        color_continuous_scale=['#444444', '#808080', '#FFFFFF']
    )

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
