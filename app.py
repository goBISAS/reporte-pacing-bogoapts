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
            .str.replace('$', '', regex=False)\
            .str.replace(',', '', regex=False)\
            .str.strip()
        
        df_filtered[col_spend] = pd.to_numeric(df_filtered[col_spend], errors='coerce').fillna(0.0)
        
        # Renombrar columnas clave de manera unificada para uso interno del script
        df_filtered = df_filtered.rename(columns={
            col_campaign: 'Campaña',
            col_spend: 'Spend (COP)',
            platform_col: 'Plataforma',
            objective_col: 'Objetivo',
            results_col: 'Resultados',
            cpa_col: 'CPA'
        })
        
        return df_filtered, budget_val
    except Exception as e:
        # Fallback elegante con datos simulados estructurados si hay un error de conexión de red o estructura
        st.sidebar.error(f"Error al conectar con la fuente en vivo: {e}. Desplegando estructura estándar con datos de bitácora.")
        df_mock = pd.DataFrame({
            'Plataforma': ['Meta Network', 'Meta Network', 'Google Network', 'Google Network'],
            'Campaña': ['Conversión_Colombia_Mensajeria', 'Consideración_Colombia_Tráfico', 'Conversión_Google_Search', 'Awareness_YouTube_Display'],
            'Objetivo': ['Official Conversions', 'Official Conversions', 'Official Conversions', 'Official Conversions'],
            'Spend (COP)': [2500000.0, 1250000.0, 650000.0, 187927.0],
            'Resultados': [32, 117, 14, 0],
            'CPA': [78125, 10683, 46428, 0]
        })
        return df_mock, 5000000.0

# Carga de datos
df, presupuesto_mensual = load_and_process_data(CSV_URL)

# Cálculo Automático requerido (Suma estricta calculada en Python de las campañas individuales filtradas)
gasto_total = float(df['Spend (COP)'].sum())

# BRANDING EN SIDEBAR (Logo del cliente e información general)
with st.sidebar:
    # Intento de cargar el archivo local especificado. Si no se encuentra en el repositorio se usa un placeholder alternativo de texto elegante.
    try:
        st.image("Logo_bogoapts_dashboard.PNG", use_container_width=True)
    except Exception:
        st.markdown(
            "<div style='padding:20px; text-align:center; border:2px solid #808080; font-weight:bold; font-size:16pt; color:#FFFFFF;'>BOGOAPTS</div>", 
            unsafe_allow_html=True
        )
    
    st.markdown("### **Control de Paid Media**")
    st.markdown(f"**Cliente:** Bogoapts")
    st.markdown(f"**Agencia:** goBIG Consulting")
    st.markdown("---")
    st.markdown("**Configuración del Dashboard:**")
    st.markdown("- Arquitectura estándar Versión 1.0")
    st.markdown("- Paleta de color optimizada para alto contraste móvil.")

# SECCIÓN PRINCIPAL DEL DASHBOARD
st.markdown("<h1 style='text-align: center; color: #FFFFFF;'>Dashboard de Rendimiento Paid Media</h1>", unsafe_allow_html=True)
st.write("")

# MÉTRICAS SUPERIORES (st.metric)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        label="Presupuesto Mensual", 
        value=f"$ {presupuesto_mensual:,.0f} COP"
    )
with col2:
    st.metric(
        label="Inversión Ejecutada (Cálculo Automático)", 
        value=f"$ {gasto_total:,.0f} COP"
    )
with col3:
    dia_actual = datetime.now().day
    st.metric(
        label="Día del Mes Actual", 
        value=f"Día {dia_actual}"
    )

st.write("")

# GRÁFICA PRINCIPAL (Plotly Treemap optimizado para UX Móvil)
st.markdown("### Distribución de Inversión Acumulada")

# Procesamiento para agregar el monto total gastado en el nombre de la plataforma (Nivel 1)
df_grouped = df.groupby(['Plataforma', 'Objetivo'], as_index=False)['Spend (COP)'].sum()

# Calcular totales por plataforma para inyectar en el string de Nivel 1 de manera clara
plataforma_totales = df_grouped.groupby('Plataforma')['Spend (COP)'].transform('sum')
df_grouped['Plataforma_Label'] = df_grouped['Plataforma'] + "<br>$ " + plataforma_totales.map('{:,.0f}'.format) + " COP"

# Generación del Treemap con Plotly Object Graphic
fig = go.Figure(go.Treemap(
    labels=df_grouped['Objetivo'],
    parents=df_grouped['Plataforma_Label'],
    values=df_grouped['Spend (COP)'],
    branchvalues="total",
    # UX Móvil Requerida: texttemplate para mostrar siempre nombre y valor monetario sin necesidad de hover
    texttemplate="<b>%{label}</b><br>Gasto: $ %{value:,.0f} COP<br>%{percentParent:.1%} del medio",
    textfont=dict(size=14, color="#FFFFFF"),
    marker=dict(
        colors=['#808080', '#A0A0A0', '#606060', '#D0D0D0'], # Variaciones de la paleta gris principal
        line=dict(width=2, color='#000000')
    ),
    hovertemplate="Plataforma/Objetivo: %{currentPath}%{label}<br>Inversión: $ %{value:,.0f} COP<extra></extra>"
))

fig.update_layout(
    margin=dict(t=10, l=10, r=10, b=10),
    paper_bgcolor='#000000',
    plot_bgcolor='#000000',
    height=450
)

st.plotly_chart(fig, use_container_width=True)

st.write("")

# TABLA DE DETALLES (Dentro de un st.expander limpio al final)
with st.expander("Ver Tabla Detallada de Campañas (Data Clean)"):
    # Selección limpia de las columnas requeridas por el estándar
    columns_to_show = ['Plataforma', 'Campaña', 'Objetivo', 'Resultados', 'CPA', 'Spend (COP)']
    
    # Asegurar orden y visualización impecable
    df_clean_display = df[columns_to_show].copy()
    
    # Formatear columnas numéricas para presentación limpia como DataFrame de Streamlit
    df_clean_display['Spend (COP)'] = df_clean_display['Spend (COP)'].map('$ {:,.0f}'.format)
    df_clean_display['CPA'] = pd.to_numeric(df_clean_display['CPA'], errors='coerce').fillna(0).map('$ {:,.0f}'.format)
    df_clean_display['Resultados'] = pd.to_numeric(df_clean_display['Resultados'], errors='coerce').fillna(0).map('{:,.0f}'.format)
    
    # Renombrar 'Plataforma' a 'Medio' según el requerimiento de la tabla de detalles
    df_clean_display = df_clean_display.rename(columns={'Plataforma': 'Medio'})
    
    st.dataframe(df_clean_display, use_container_width=True)
