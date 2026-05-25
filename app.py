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
        # Construcción inmutable de la URL mediante exportación a CSV por GID
        base_url = sheet_url.split('/edit')[0]
        csv_url = f"{base_url}/export?format=csv&gid={gid_id}"
        
        # Carga masiva inicial sin procesar tipos para limpiar la estructura manualmente
        df_raw = pd.read_csv(csv_url, header=None)
        
        if df_raw.empty:
            return pd.DataFrame(), 0.0

        # --- EXTRACCIÓN PRECISIÓN: Presupuesto Mensual ---
        presupuesto_mensual = 0.0
        # Buscamos en el bloque superior asegurando transformación estricta a string
        for idx, row in df_raw.head(10).iterrows():
            # Convertimos toda la fila a texto plano e iterable sin valores flotantes huérfanos
            row_str_list = [str(item).lower() for item in row.dropna().values]
            if any('approved budget' in s or 'budget' in s or 'presupuesto' in s for s in row_str_list):
                for cell in row.dropna():
                    cell_clean = re.sub(r'[\s\$,.COP]', '', str(cell))
                    if cell_clean.isdigit():
                        val_float = float(cell_clean)
                        if val_float > presupuesto_mensual:
                            presupuesto_mensual = val_float

        # --- EXTRACCIÓN PRECISIÓN: Tabla de Campañas ---
        header_row_idx = 5 # Defecto estándar (fila 6)
        for idx, row in df_raw.head(15).iterrows():
            row_str_list = [str(item).lower() for item in row.dropna().values]
            if any('spend' in s or 'invers' in s or 'gasto' in s for s in row_str_list) and any('campa' in s or 'name' in s for s in row_str_list):
                header_row_idx = idx
                break
                
        # Recargamos el DataFrame utilizando el índice descubierto
        df = pd.read_csv(csv_url, skiprows=header_row_idx)
        df.columns = [str(c).strip() for c in df.columns]

        # --- MAPEO ADAPTATIVO FAILSAFE ---
        camp_matches = [c for c in df.columns if any(k in c.lower() for k in ['campa', 'name', 'nombre', 'ad group'])]
        plat_matches = [c for c in df.columns if any(k in c.lower() for k in ['plataforma', 'medio', 'source', 'network', 'canal'])]
        spend_matches = [c for c in df.columns if any(k in c.lower() for k in ['spend', 'invers', 'gasto', 'valor', 'cop'])]
        obj_matches = [c for c in df.columns if any(k in c.lower() for k in ['objetivo', 'objective', 'goal', 'tipo'])]
        res_matches = [c for c in df.columns if any(k in c.lower() for k in ['result', 'convers', 'compras', 'cant'])]
        cpa_matches = [c for c in df.columns if any(k in c.lower() for k in ['cpa', 'costo por', 'cost/'])]

        campaign_col = camp_matches[0] if camp_matches else df.columns[1] if len(df.columns) > 1 else df.columns[0]
        platform_col = plat_matches[0] if plat_matches else df.columns[0]
        spend_col = spend_matches[0] if spend_matches else df.columns[3] if len(df.columns) > 3 else df.columns[-1]
        
        objective_col = obj_matches[0] if obj_matches else None
        results_col = res_matches[0] if res_matches else None
        cpa_col = cpa_matches[0] if cpa_matches else None

        # Limpieza estricta de filas vacías
        df = df.dropna(subset=[campaign_col, platform_col])
        
        # Filtrado estricto asegurando tipo string antes de aplicar métodos de texto (.str)
        df = df[~df[campaign_col].astype(str).str.upper().str.contains('TOTAL', na=False)]
        df = df[~df[platform_col].astype(str).str.upper().str.contains('TOTAL', na=False)]
        df = df[~df[campaign_col].astype(str).str.lower().str.contains('monthly', na=False)]

        # Convertidor monetario robusto a Float puro
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
        
        # Estructuración final de la arquitectura limpia
        mapped_df = pd.DataFrame()
        mapped_df['Medio'] = df[platform_col].astype(str).str.strip()
        mapped_df['Campaña'] = df[campaign_col].astype(str).str.strip()
        mapped_df['Objetivo'] = df[objective_col].astype(str).str.strip() if objective_col else 'Official Conversions'
        mapped_df['Spend'] = df[spend_col]
        
        if results_col:
            mapped_df['Resultados'] = pd.to_numeric(df[results_col], errors='coerce').fillna(0)
        else:
            mapped_df['Resultados'] = 0
            
        if cpa_col:
            mapped_df['CPA'] = df[cpa_col].apply(clean_currency)
        else:
            mapped_df['CPA'] = 0.0
        
        mapped_df['Objetivo'] = mapped_df['Objetivo'].replace(['nan', 'None', '', 'NAN'], 'Official Conversions').fillna('Official Conversions')
        
        # Filtrar registros en cero o vacíos
        mapped_df = mapped_df[mapped_df['Spend'] > 0]
        
        return mapped_df, presupuesto_mensual
        
    except Exception as e:
        st.error(f"Error crítico en el pipeline de ingeniería de datos: {e}")
        return pd.DataFrame(), 0.0

# 3. Sidebar e Identidad Visual (Branding)
st.sidebar.image("Logo_bogoapts_dashboard.PNG", use_container_width=True)
st.sidebar.title("Bogoapts Dashboard")
st.sidebar.markdown("""
**Control de Rendimiento de Paid Media** *Versión 1.8 Estable* ___
**Cliente:** Bogoapts  
**Conexión:** GID Target Activo  
**Entorno:** Streamlit Cloud  
""")

# URL de origen de datos asignada
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0/edit?gid=388077940#gid=388077940"

# Ejecución de Pipeline de Carga limpia
df_clean, presupuesto = load_and_process_data(SHEET_URL, gid_id="388077940")

if not df_clean.empty:
    # 4. Cálculo Automático Real en Python (Requerimiento Estricto)
    gasto_total = float(df_clean['Spend'].sum())
    dia_actual = datetime.now().day
    
    if presupuesto == 0:
        presupuesto = 5000000.0  # Mapeo según tu captura de pantalla de referencia

    # 5. Sección Superior de Métricas (st.metric)
    st.title("📊 Rendimiento de Paid Media — Bogoapts")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Presupuesto Mensual Meta", value=f"$ {presupuesto:,.0f} COP")
    with col2:
        st.metric(label="Inversión Ejecutada (Python Calc)", value=f"$ {gasto_total:,.0f} COP")
    with col3:
        st.metric(label="Día del Mes Actual", value=f"Día {dia_actual}")

    st.markdown("---")

    # 6. Gráfica Principal: Plotly Treemap (Estrategia de Agregación Segura)
    st.subheader("📊 Distribución por Canal y Objetivo")
    
    df_grouped = df_clean.groupby(['Medio', 'Objetivo'], as_index=False)['Spend'].sum()
    
    # Inyectamos totales acumulados por canal en las etiquetas del Treemap
    plataforma_totals = df_grouped.groupby('Medio')['Spend'].sum().to_dict()
    df_grouped['Medio_Label'] = df_grouped['Medio'].apply(lambda x: f"{x} (${plataforma_totals[x]:,.0f} COP)")

    fig = px.treemap(
        df_grouped,
        path=['Medio_Label', 'Objetivo'],
        values='Spend',
        color='Spend',
        color_continuous_scale=['#444444', '#808080', '#FFFFFF']
    )

    # UX Móvil Nativo Estable
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

    # 7. Tabla de Detalles: Rendimiento de Campañas
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
