"""
utils.py — El Cimiento y Motor del Sistema
Fase 1: Sanitización de Datos y Matemáticas Temporales
"""
import re
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from itertools import product

# ==========================================
# 1. EL PURIFICADOR DE DATOS
# ==========================================

def _parse_hora(s: str) -> str:
    """Convierte horas con 'a.m./p.m.' a formato militar 24h ('HH:MM:SS')"""
    s = str(s).strip()
    # Si ya es formato 24h puro (Ej: 14:00:00 o 9:00:00)
    if re.match(r'^\d{1,2}:\d{2}:\d{2}$', s):
        return s
        
    # Si tiene a.m. o p.m.
    match = re.match(r'(\d{1,2}):(\d{2})(?::\d{2})?\s*(a\.?\s*m\.?|p\.?\s*m\.?)?', s, re.IGNORECASE)
    if not match:
        return s 

    h = int(match.group(1))
    m = int(match.group(2))
    periodo = (match.group(3) or '').lower().replace(' ', '').replace('.', '')
    
    if periodo == 'pm' and h != 12:
        h += 12
    elif periodo == 'am' and h == 12:
        h = 0
        
    return f"{h:02d}:{m:02d}:00"

def cargar_materias(ruta: str) -> pd.DataFrame:
    """Lee el CSV y repara columnas rotas (como 'SalÃ³n') y horas en distintos formatos."""
    # Leemos el archivo crudo
    df = pd.read_csv(ruta, encoding='latin1')

    # Limpiamos espacios extraños al inicio/final de las columnas
    df.columns = df.columns.str.strip()

    # MAGIA 1: Reparamos el Mojibake (Transforma 'SalÃ³n' -> 'Salón')
    columnas_limpias = []
    for c in df.columns:
        if any(ord(ch) > 127 for ch in c):
            try:
                c_limpia = c.encode('latin1').decode('utf-8', errors='replace')
                columnas_limpias.append(c_limpia)
            except:
                columnas_limpias.append(c)
        else:
            columnas_limpias.append(c)
    df.columns = columnas_limpias

    # MAGIA 2: Planchamos las horas al mismo formato universal
    for col in ['Hora_ini', 'Hora_fin']:
        if col in df.columns:
            df[col] = df[col].apply(_parse_hora)

    # Tiramos filas que tengan basura o estén vacías en el Excel
    df = df.dropna(subset=['Hora_ini', 'Hora_fin', 'Dias'])

    return df.reset_index(drop=True)

# ==========================================
# 2. UTILIDADES DE TIEMPO
# ==========================================

def hms_a_decimal(hms_str: str) -> float:
    """Convierte '09:30:00' a 9.5 para poder graficarlo"""
    h, m, s = map(int, str(hms_str).split(":"))
    decimal = h + (m / 60.0) + (s / 3600.0)
    # Redondeo fino para evitar "huecos" visuales en las gráficas (ej. 8.98 -> 9.0)
    if abs(decimal - round(decimal)) < 0.05:
        return round(decimal)
    return decimal

def agregar_columnas_temporales(df: pd.DataFrame) -> pd.DataFrame:
    """Le inyecta las matemáticas al dataframe antes de revisar empalmes."""
    df = df.copy()
    map_dias = {"L": 1, "A": 2, "M": 3, "J": 4, "V": 5, "S": 6} # Por si alguna vez hay sábados
    df["Dia_Num"] = df["Dias"].map(map_dias)
    
    df["start_dec"] = df["Hora_ini"].astype(str).apply(hms_a_decimal)
    df["end_dec"] = df["Hora_fin"].astype(str).apply(hms_a_decimal)
    df["duration_dec"] = df["end_dec"] - df["start_dec"]
    return df
