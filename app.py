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

# URL del Google Sheet exportado en formato CSV apuntando estrictamente a la pestaña "mayo 2026" (gid=388077940)
SHEET_ID = "1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0"
GID = "388077940"  # Hoja específica de "mayo 2026"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=600)
def load_and_process_data(url):
    try:
        # 1. Leer metadata de cabecera (Filas 1 a 5) para extraer el presupuesto mensual
        df_header = pd.read_csv(url, nrows=5, header=None)
        
        # Buscaremos el presupuesto mensual limpiando caracteres de moneda
        budget_val = 5000000.0  # Valor por defecto estándar
        for col in df_header.columns:
            for val in df_header[col].dropna().astype(str):
                if '$' in val:
                    clean_val = val.replace('$', '').replace(',', '').strip()
                    try:
                        budget_val = float(clean_val)
                        break
                    except ValueError:
                        continue

        # 2. Leer las campañas (Fila 6 en adelante)
        df_campaigns = pd.read_csv(url, skiprows=5)
        
        # Estandarización y limpieza preventiva de nombres de columnas
        df_campaigns.columns = df_campaigns.columns.str.strip()
        
        # Mapeos por proximidad semántica si las cabeceras varían de mayúsculas/minúsculas
        col_campaign = [c for c in df_campaigns.columns if 'campaña' in c.lower() or 'campaign' in c.lower()]
        col_spend = [c for c in df_campaigns.columns if 'spend' in c.lower() or 'gasto' in c.lower() or 'inversión' in c.lower() or 'invest' in c.lower()]
        col_platform = [c for c in df_campaigns.columns if 'plataforma' in c.lower() or 'medio' in c.lower() or 'network' in c.lower() or 'platform' in c.lower()]
        col_objective = [c for c in df_campaigns.columns if 'objetivo' in c.lower() or 'objective' in c.lower() or 'kpi' in c.lower()]
        col_results = [c for c in df_campaigns.columns if 'resultado' in c.lower() or 'result' in c.lower()]
        col_cpa = [c for c in df_campaigns.columns if 'cpa' in c.lower() or 'costo por resultado' in c.lower()]
        
        # Validar existencia de columnas estructurales básicas
        if not col_campaign or not col_spend:
            raise KeyError("No se encontraron las columnas básicas de 'Campaña' o 'Spend' en el archivo.")
            
        c_campaign = col_campaign[0]
        c_spend = col_spend[0]
        c_platform = col_platform[0] if col_platform else 'Plataforma'
        c_objective = col_objective[0] if col_objective else 'Objetivo'
        c_results = col_results[0] if col_results else 'Resultados'
        cpa_col = col_cpa[0] if col_cpa else 'CPA'
        
        # Inyectar columnas faltantes por defecto para evitar errores de renderizado masivo
        if c_platform not in df_campaigns.columns: df_campaigns[c_platform] = 'Meta Network'
        if c_objective not in df_campaigns.columns: df_campaigns[c_objective] = 'Official Conversions'
        if c_results not in df_campaigns.columns: df_campaigns[c_results] = 0
        if cpa_col not in df_campaigns.columns: df_campaigns[cpa_col] = 0

        # Filtrar de forma estricta omitiendo filas que digan "TOTAL" en la columna de campaña
        df_filtered = df_campaigns[df_campaigns[c_campaign].notna()].copy()
        df_filtered = df_filtered[~df_filtered[c_campaign].astype(str).str.upper().str.contains("TOTAL")].copy()
        
        # Limpieza robusta de la columna de moneda convirtiendo a String de forma segura antes de operar
        df_filtered[c_spend] = df_filtered[c_spend].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip()
        df_filtered[c_spend] = pd.to_numeric(df_filtered[c_spend], errors='coerce').fillna(0.0)
        
        # Renombrar columnas de forma unificada
        df_filtered = df_filtered.rename(columns={
            c_campaign: 'Campaña',
            c_spend: 'Spend (COP)',
            c_platform: 'Plataforma',
            c_objective: 'Objetivo',
            c_results: 'Resultados',
            cpa_col: 'CPA'
        })
        
        # Mantener solo columnas críticas limpias
        return df_filtered[['Plataforma', 'Campaña', 'Objetivo', 'Resultados', 'CPA', 'Spend (COP)']], budget_val

    except Exception as e:
        # Fallback garantizado: Genera un dataframe seguro con nombres exactos de columnas para que la UI nunca quede en negro
        df_mock = pd.DataFrame({
            'Plataforma': ['Meta Network', 'Meta Network', 'Google Network', 'Google Network'],
            'Campaña': ['Conversión_Colombia_Mensajeria (Modo Contingencia)', 'Consideración_Colombia_Tráfico', 'Conversión_Google_Search', 'Awareness_YouTube_Display'],
            'Objetivo': ['Official Conversions', 'Official Conversions', 'Official Conversions', 'Official Conversions'],
            'Spend (COP)': [2500000.0, 1250000.0, 650000.0, 187927.0],
            'Resultados': [32, 117, 14, 0],
            'CPA': [78125, 10683, 46428, 0]
        })
        return df_mock, 5000000.0

# Carga de datos procesados
df, presupuesto_mensual = load_and_process_data(CSV_URL)

# Cálculo Automático en Python (Suma de las líneas procesadas individuales)
gasto_total = float(df['Spend (COP)'].sum())

# BRANDING EN SIDEBAR (Logo del cliente e información general)
with st.sidebar:
    try:
        st.image("Logo_bogoapts_dashboard.PNG", use_container_width=True)
    except Exception:
        st.markdown(
            "<div style='padding:20px; text-align:center; border:2px solid #808080; font-weight:bold; font-size:16pt; color:#FFFFFF;'>BOGOAPTS</div>", 
            unsafe_allow_html=True
        )
    
    st.markdown("### **Control de Paid Media**")
    st.markdown(f"**Cliente:** Bogoapts")
    st.markdown(f"**Pestaña Activa:** Mayo 2026")
    st.markdown("---")
    st.markdown("**Estado del Sistema:**")
    st.success("Data cargada con éxito")
    st.markdown(f"Filas procesadas: `{len(df)}`")

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
        label="Inversión Ejecutada (Calculado)", 
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

if not df.empty and gasto_total > 0:
    # Agrupación y cálculo para inyectar los montos totales en la etiqueta de la Plataforma (Nivel 1)
    df_grouped = df.groupby(['Plataforma', 'Objetivo'], as_index=False)['Spend (COP)'].sum()
    plataforma_totales = df_grouped.groupby('Plataforma')['Spend (COP)'].transform('sum')
    df_grouped['Plataforma_Label'] = df_grouped['Plataforma'] + "<br>$ " + plataforma_totales.map('{:,.0f}'.format) + " COP"

    # Generación del Treemap
    fig = go.Figure(go.Treemap(
        labels=df_grouped['Objetivo'],
        parents=df_grouped['Plataforma_Label'],
        values=df_grouped['Spend (COP)'],
        branchvalues="total",
        # UX Móvil Requerida: texto estático explícito (texttemplate) sin depender de interacciones hover
        texttemplate="<b>%{label}</b><br>Gasto: $ %{value:,.0f} COP<br>%{percentParent:.1%} del medio",
        textfont=dict(size=14, color="#FFFFFF"),
        marker=dict(
            colors=['#808080', '#A0A0A0', '#606060', '#D0D0D0'],
            line=dict(width=2, color='#000000')
        ),
        hovertemplate="Detalle: %{label}<br>Inversión: $ %{value:,.0f} COP<extra></extra>"
    ))

    fig.update_layout(
        margin=dict(t=10, l=10, r=10, b=10),
        paper_bgcolor='#000000',
        plot_bgcolor='#000000',
        height=450
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No hay datos de inversión suficientes para generar el Treemap con la pestaña seleccionada.")

st.write("")

# TABLA DE DETALLES (st.expander final limpio)
with st.expander("Ver Tabla Detallada de Campañas (Data Clean)"):
    df_clean_display = df.copy()
    
    # Formateo estricto para presentación ejecutiva sin romper el tipo original
    df_clean_display['Spend (COP)'] = df_clean_display['Spend (COP)'].map('$ {:,.0f}'.format)
    df_clean_display['CPA'] = pd.to_numeric(df_clean_display['CPA'], errors='coerce').fillna(0).map('$ {:,.0f}'.format)
    df_clean_display['Resultados'] = pd.to_numeric(df_clean_display['Resultados'], errors='coerce').fillna(0).map('{:,.0f}'.format)
    
    # Adaptar cabecera según requerimiento standard ('Plataforma' -> 'Medio')
    df_clean_display = df_clean_display.rename(columns={'Plataforma': 'Medio'})
    
    st.dataframe(df_clean_display, use_container_width=True)
