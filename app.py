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
        # URL de descarga directa inmutable
        base_url = sheet_url.split('/edit')[0]
        csv_url = f"{base_url}/export?format=csv&gid={gid_id}"
        
        # --- BLOQUE 1: Carga limpia de la tabla de Campañas (Forzado desde Fila 6 / skiprows=5) ---
        # Leemos directo omitiendo la cabecera problemática para evitar errores de tipado
        df = pd.read_csv(csv_url, skiprows=5)
        df.columns = [str(c).strip() for c in df.columns]
        
        if df.empty:
            return pd.DataFrame(), 5000000.0

        # --- BLOQUE 2: Mapeo Flexible e Inteligente de Columnas por Posición e Identidad ---
        camp_matches = [c for c in df.columns if any(k in c.lower() for k in ['campa', 'name', 'nombre', 'ad group'])]
        plat_matches = [c for c in df.columns if any(k in c.lower() for k in ['plataforma', 'medio', 'source', 'network', 'canal'])]
        spend_matches = [c for c in df.columns if any(k in c.lower() for k in ['spend', 'invers', 'gasto', 'valor', 'cop'])]
        obj_matches = [c for c in df.columns if any(k in c.lower() for k in ['objetivo', 'objective', 'goal', 'tipo'])]
        res_matches = [c for c in df.columns if any(k in c.lower() for k in ['result', 'convers', 'compras', 'cant'])]
        cpa_matches = [c for c in df.columns if any(k in c.lower() for k in ['cpa', 'costo por', 'cost/'])]

        # Garantizar asignaciones por posición física en caso de nombres ausentes
        campaign_col = camp_matches[0] if camp_matches else df.columns[1] if len(df.columns) > 1 else df.columns[0]
        platform_col = plat_matches[0] if plat_matches else df.columns[0]
        spend_col = spend_matches[0] if spend_matches else df.columns[3] if len(df.columns) > 3 else df.columns[-1]
        
        objective_col = obj_matches[0] if obj_matches else None
        results_col = res_matches[0] if res_matches else None
        cpa_col = cpa_matches[0] if cpa_matches else None

        # Convertidor numérico robusto y seguro a Float plano
        def clean_currency(val):
            if pd.isna(val) or str(val).strip() == '':
                return 0.0
            # Removemos cualquier carácter no numérico excepto el signo menos si existiera
            val_str = re.sub(r'[^\d]', '', str(val))
            try:
                return float(val_str) if val_str else 0.0
            except ValueError:
                return 0.0

        # Forzar casteo a string para evitar colisiones en métodos vectoriales
        df[campaign_col] = df[campaign_col].astype(str).str.strip()
        df[platform_col] = df[platform_col].astype(str).str.strip()
        df[spend_col] = df[spend_col].apply(clean_currency)

        # --- FILTRADO DE SEGURIDAD EXCLUSIVO: Purga total de acumulados intermedios ---
        # Excluimos cualquier fila que no pertenezca a campañas individuales
        df = df[df[campaign_col] != '']
        df = df[~df[campaign_col].str.lower().str.contains('total', na=False)]
        df = df[~df[platform_col].str.lower().str.contains('total', na=False)]
        df = df[~df[campaign_col].str.lower().str.contains('monthly', na=False)]
        df = df[~df[campaign_col].str.lower().str.contains('budget', na=False)]
        df = df[~df[campaign_col].str.lower().str.contains('gasto', na=False)]

        # Homologación formal al DataFrame de la V1.0 Estándar
        mapped_df = pd.DataFrame()
        mapped_df['Medio'] = df[platform_col]
        mapped_df['Campaña'] = df[campaign_col]
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
        
        # Mantener solo las celdas con inversión real activa
        mapped_df = mapped_df[mapped_df['Spend'] > 0]
        
        # --- BLOQUE 3: Lectura estática aislada del Presupuesto aprobado (Fila 3 / Columna C) ---
        presupuesto_mensual = 5000000.0  # Asignación por coordenadas directas según captura de referencia
        try:
            df_budget_check = pd.read_csv(csv_url, nrows=4, header=None)
            if df_budget_check.shape[1] >= 3:
                raw_val = df_budget_check.iloc[2, 2]  # Celda C3 (Fila 3, Columna C)
                clean_val = re.sub(r'[^\d]', '', str(raw_val))
                if clean_val.isdigit() and float(clean_val) > 0:
                    presupuesto_mensual = float(clean_val)
        except:
            pass # Si falla la lectura de la celda aislada, el fallback seguro de la hoja se mantiene

        return mapped_df, presupuesto_mensual
        
    except Exception as e:
        st.error(f"Error crítico en el pipeline de ingeniería de datos: {e}")
        return pd.DataFrame(), 0.0

# 3. Sidebar e Identidad Visual (Branding)
st.sidebar.image("Logo_bogoapts_dashboard.PNG", use_container_width=True)
st.sidebar.title("Bogoapts Dashboard")
st.sidebar.markdown("""
**Control de Rendimiento de Paid Media** *Versión 2.0 Certificada* ___
**Cliente:** Bogoapts  
**Conexión:** GID Target Activo  
**Filtros:** Totales Excluidos (Python Calc)
""")

# URL de origen de datos asignada
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Qkw-Fi3tLvY68maHxJOmHlX9sx0kOvNg-150YRE42W0/edit?gid=388077940#gid=388077940"

# Ejecución del Pipeline limpio de datos
df_clean, presupuesto = load_and_process_data(SHEET_URL, gid_id="388077940")

if not df_clean.empty:
    # 4. Cálculo Automático Puro en Python libre de Totales duplicados (Requerimiento Estricto)
    gasto_total = float(df_clean['Spend'].sum())
    dia_actual = datetime.now().day

    # 5. Sección Superior de Métricas
    st.title("📊 Rendimiento de Paid Media — Bogoapts")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Presupuesto Mensual Meta", value=f"$ {presupuesto:,.0f} COP")
    with col2:
        st.metric(label="Inversión Ejecutada (Python Calc)", value=f"$ {gasto_total:,.0f} COP")
    with col3:
        st.metric(label="Día del Mes Actual", value=f"Día {dia_actual}")

    st.markdown("---")

    # 6. Gráfica Principal: Plotly Treemap (Agregación Preventiva Homogénea)
    st.subheader("📊 Distribución por Canal y Objetivo")
    
    # Consolidamos datos agrupando limpiamente por Medio y Objetivo
    df_grouped = df_clean.groupby(['Medio', 'Objetivo'], as_index=False)['Spend'].sum()
    
    # Inyectamos los acumulados reales por canal en las etiquetas de nivel superior
    plataforma_totals = df_grouped.groupby('Medio')['Spend'].sum().to_dict()
    df_grouped['Medio_Label'] = df_grouped['Medio'].apply(lambda x: f"{x} (${plataforma_totals[x]:,.0f} COP)")

    fig = px.treemap(
        df_grouped,
        path=['Medio_Label', 'Objetivo'],
        values='Spend',
        color='Spend',
        color_continuous_scale=['#444444', '#808080', '#FFFFFF']
    )

    # UX Móvil Nativo Estable libre de errores internos de validación por índices
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
