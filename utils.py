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
    
    if re.match(r'^\d{1,2}:\d{2}:\d{2}$', s):
        return s
        
    #este punto es en dado caso de que el CSV este en formato a.m y p.m
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
    """Lee el CSV y repara columnas rotas, símbolos fantasma (BOM) y horas."""
    
    df = pd.read_csv(ruta, encoding='latin1')

   
    df.columns = df.columns.str.strip()

    
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
            
    # BOM
    columnas_limpias = [c.replace('\ufeff', '').replace('ï»¿', '').strip() for c in columnas_limpias]
    df.columns = columnas_limpias
    
    
    df.rename(columns=lambda x: 'NRC' if 'NRC' in str(x).upper() else x, inplace=True)
    df.rename(columns=lambda x: 'Materia' if 'MATERIA' in str(x).upper() else x, inplace=True)
    df.rename(columns=lambda x: 'Dias' if 'DIA' in str(x).upper() else x, inplace=True)

    # horas al mismo formato universal
    for col in ['Hora_ini', 'Hora_fin']:
        if col in df.columns:
            df[col] = df[col].apply(_parse_hora)

    
    df = df.dropna(subset=['Hora_ini', 'Hora_fin', 'Dias'])

    return df.reset_index(drop=True)
# ==========================================
# 2. UTILIDADES DE TIEMPO
# ==========================================

def hms_a_decimal(hms_str: str) -> float:
    """Convierte '09:30:00' a 9.5 para poder graficarlo"""
    h, m, s = map(int, str(hms_str).split(":"))
    decimal = h + (m / 60.0) + (s / 3600.0)
    # Redondeo fino para evitar "huecos" visuales en las gráficas 
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
    # ==========================================
# 3. Empalmes y Generador
# ==========================================

def detectar_empalmes(df: pd.DataFrame) -> list:
    """Busca choques de horario en una estructura ya armada."""
    mensajes = []
    for dia, clases_del_dia in df.groupby("Dias"):
        clases = clases_del_dia.sort_values("start_dec").reset_index(drop=True)
        fin_anterior = clases["end_dec"].shift(1)
        empalme = clases["start_dec"] < fin_anterior
        for idx in clases[empalme].index:
            materia_actual = clases.loc[idx, "Materia"]
            materia_anterior = clases.loc[idx - 1, "Materia"]
            mensajes.append(f"El día {dia}, **{materia_anterior}** choca con **{materia_actual}**.")
    return mensajes

def _hay_empalme(df_combo: pd.DataFrame) -> bool:
    """Versión ultrarrápida para el motor de combinaciones: devuelve True al primer choque."""
    for _, clases in df_combo.groupby("Dias"):
        clases = clases.sort_values("start_dec").reset_index(drop=True)
        if (clases["start_dec"] < clases["end_dec"].shift(1)).any():
            return True
    return False

def _calcular_horas_muertas(df_combo: pd.DataFrame) -> float:
    """Suma los huecos vacíos entre clases del mismo día."""
    total = 0.0
    for _, clases in df_combo.groupby("Dias"):
        clases = clases.sort_values("start_dec").reset_index(drop=True)
        gaps = clases["start_dec"].iloc[1:].values - clases["end_dec"].iloc[:-1].values
        total += float(max(0, gaps.sum()))
    return round(total, 2)

def generar_horarios_optimos(df: pd.DataFrame, materias_deseadas: list, limite_horas: int = 4):
    """El cerebro combinatorio: busca combinaciones viables sin empalmes."""
    if "start_dec" not in df.columns:
        df = agregar_columnas_temporales(df)

    grupos_nrcs = []
    for materia in materias_deseadas:
        nrcs = df[df["Materia"] == materia]["NRC"].unique().tolist()
        if not nrcs:
            return None, f"No se encontraron secciones para '{materia}' en el catálogo."
        grupos_nrcs.append(nrcs)

    # Seguro de vida termodinámico
    total_combos = 1
    for grupo in grupos_nrcs:
        total_combos *= len(grupo)
    if total_combos > 50000:
        return None, f"Hay {total_combos:,} combinaciones posibles. El sistema se sobrecalentará. Reduce las materias."

    viables = []
    for combo_nrcs in product(*grupos_nrcs):
        df_combo = df[df["NRC"].isin(combo_nrcs)].copy()
        
        if _hay_empalme(df_combo):
            continue
            
        horas_muertas = _calcular_horas_muertas(df_combo)
        if horas_muertas > limite_horas:
            continue
            
        viables.append({
            "nrcs": list(combo_nrcs),
            "horas_muertas": horas_muertas,
            "df": df_combo,
        })

    viables.sort(key=lambda x: x["horas_muertas"])
    return viables, f"Se encontraron {len(viables)} horarios viables."

# ==========================================
# 4. Plotly a prueba de fallos
# ==========================================

def construir_figura(df: pd.DataFrame) -> go.Figure:
    """Dibuja el horario con programación defensiva para las columnas."""
    colors = px.colors.qualitative.Plotly
    materia_to_color = {materia: colors[i % len(colors)] for i, materia in enumerate(df["Materia"].unique())}
    
    df = df.copy()
    df["Color"] = df["Materia"].map(materia_to_color)

    fig = go.Figure()
    for materia, group in df.groupby("Materia"):
        
        # 🛡️ CÓDIGO DEFENSIVO: Buscamos el salón sin importar cómo venga escrito
        if 'Salón' in group.columns:
            salon_data = group['Salón']
        elif 'Salon' in group.columns: 
            salon_data = group['Salon']
        else:
            salon_data = ["Aula sin asignar"] * len(group)
            
        custom_data = list(zip(group['Profesor'], salon_data, group['Hora_ini'], group['Hora_fin']))
        
        fig.add_trace(go.Bar(
            name=materia, x=group["Dia_Num"], y=group["duration_dec"], base=group["start_dec"],
            marker_color=group["Color"].iloc[0], opacity=1.0,
            customdata=custom_data, text=group["Materia"],
            textposition="inside", insidetextanchor="middle",
            hovertemplate="<b>%{text}</b><br><br><b>Profesor:</b> %{customdata[0]}<br><b>Salón:</b> %{customdata[1]}<br><b>Horario:</b> %{customdata[2]} - %{customdata[3]}<br><extra></extra>"
        ))

    horas = list(range(7, 22))
    fig.update_layout(
        barmode="overlay", paper_bgcolor="white", plot_bgcolor="white", font=dict(color="black"), height=700,
        xaxis=dict(title="", side="top", tickmode="array", tickvals=[1, 2, 3, 4, 5, 6], ticktext=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"], showgrid=True, gridcolor="#e5e5e5", zeroline=False),
        yaxis=dict(title="Horario", range=[21.5, 6.5], tickmode="array", tickvals=horas, ticktext=[f"{h:02d}:00" for h in horas], showgrid=True, gridcolor="#e5e5e5", zeroline=False),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig
