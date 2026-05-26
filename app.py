import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import urllib.parse
import re

# ==========================================================
# 1. CONFIGURACIÓN GENERAL
# ==========================================================
st.set_page_config(
    page_title="BogoApts Dashboard",
    page_icon="🏢",
    layout="wide"
)

st.markdown("""
    <style>
    .main { background-color: #0d0d0d; }
    [data-testid="stMetricValue"] { font-size: 32px; color: #d6b58e !important; font-weight: 700; }
    [data-testid="stMetricLabel"] { color: #f5f5f5 !important; }
    h1, h2, h3 { color: #ffffff; font-family: 'Georgia', serif; }
    .stSidebar { background-color: #1a1a1a; border-right: 1px solid #333; }
    .stPlotlyChart { border: 1px solid #333; border-radius: 8px; background-color: #1a1a1a; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES GLOBALES ---
def obtener_meses_disponibles():
    meses_es = [
        "enero", "febrero", "marzo", "abril", 
        "mayo", "junio", "julio", "agosto", 
        "septiembre", "octubre", "noviembre", "diciembre"
    ]
    start_year, start_month = 2026, 5
    now = datetime.now()
    lista = []
    ano, mes = start_year, start_month
    while (ano < now.year) or (ano == now.year and mes <= now.month):
        lista.append(f"{meses_es[mes-1]} {ano}")
        if mes == 12:
            mes = 1
            ano += 1
        else:
            mes += 1
    return list(reversed(lista))

def get_csv_url_by_sheet(url, sheet_name):
    try:
        id_publicacion = url.split("/d/")[1].split("/")[0]
        sheet_enc = urllib.parse.quote(sheet_name)
        base = "https://docs.google.com/spreadsheets/d/"
        return f"{base}{id_publicacion}/gviz/tq?tqx=out:csv&sheet={sheet_enc}"
    except:
        return url

def parse_num(val):
    txt = str(val).strip().replace('$', '')
    if txt == '-' or txt == '': return 0.0
    if '.' in txt and ',' not in txt:
        pt = txt.split('.')
        if len(pt) > 2 or (len(pt) == 2 and len(pt[1]) == 3):
            txt = txt.replace('.', '')
    txt = txt.replace(',', '')
    txt = re.sub(r'[^\d.-]', '', txt)
    try: return float(txt) if txt != '' else 0.0
    except: return 0.0

def format_label(val):
    if val >= 1_000_000: return f"${val/1_000_000:.1f}M"
    elif val >= 1_000: return f"${val/1_000:.0f}k"
    elif val == 0: return ""
    else: return f"${val:.0f}"

# =
