"""
utils.py — Motor Maestro Krea-t
Contiene: Purificador de datos (Melt/BOM), Motor Matemático y Arquitecto Visual.
"""
import re
from itertools import product
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ==========================================
# 1. EL PURIFICADOR DE DATOS
# ==========================================

def _parse_hora(s: str) -> str:
    """Convierte horas con 'a.m./p.m.' a formato militar 24h ('HH:MM:SS')"""
    s = str(s).strip()
    if re.match(r'^\d{1,2}:\d{2}:\d{2}$', s):
        return s
        
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

def _desdoblar_horarios(df: pd.DataFrame) -> pd.DataFrame:
    """Derrama las columnas de días (LUNES, MARTES...) en filas individuales Tidy Data."""
    dias_map = {
        'LUNES': 'L', 'MARTES': 'A', 'MIERCOLES': 'M', 'MIÉRCOLES': 'M',
        'JUEVES': 'J', 'VIERNES': 'V', 'SABADO': 'S', 'SÁBADO': 'S'
    }

    dias_presentes = [c for c in df.columns if str(c).upper().strip() in dias_map.keys()]

    if not dias_presentes:
        return df

    id_vars = [c for c in df.columns if c not in dias_presentes]
    df_largo = df.melt(id_vars=id_vars, value_vars=dias_presentes, var_name='Dia_Nombre', value_name='Horario_Rango')

    df_largo = df_largo.dropna(subset=['Horario_Rango'])
    df_largo = df_largo[df_largo['Horario_Rango'].astype(str).str.strip() != '']

    df_largo['Dias'] = df_largo['Dia_Nombre'].str.upper().str.strip().map(dias_map)

    def extraer_horas(texto):
        partes = str(texto).split('-')
        if len(partes) == 2:
            return partes[0].strip(), partes[1].strip()
        return None, None

    df_largo['Hora_ini'], df_largo['Hora_fin'] = zip(*df_largo['Horario_Rango'].apply(extraer_horas))

    return df_largo.drop(columns=['Dia_Nombre', 'Horario_Rango'])

def cargar_materias(ruta: str) -> pd.DataFrame:
    """Lee el CSV y repara columnas rotas, símbolos fantasma (BOM) y horas."""
    
    # 🧠 MAGIA CERO: Detección automática de delimitador (Comas vs Puntos y Comas)
    df = pd.read_csv(ruta, encoding='latin1', sep=None, engine='python')
    
    df.columns = df.columns.str.strip()
    # ... (El resto de tu código sigue exactamente igual hacia abajo)

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
            
    columnas_limpias = [c.replace('\ufeff', '').replace('ï»¿', '').strip() for c in columnas_limpias]
    df.columns = columnas_limpias
    
    df.rename(columns=lambda x: 'NRC' if 'NRC' in str(x).upper() else x, inplace=True)
    df.rename(columns=lambda x: 'Materia' if 'MATERIA' in str(x).upper() else x, inplace=True)

    df = _desdoblar_horarios(df)
    
    df.rename(columns=lambda x: 'Dias' if 'DIA' in str(x).upper() else x, inplace=True)

    for col in ['Hora_ini', 'Hora_fin']:
        if col in df.columns:
            df[col] = df[col].apply(_parse_hora)

   # ... (código anterior de cargar_materias)
    df = _desdoblar_horarios(df)
    
    # En caso de que no haya entrado al desdoble, nos aseguramos de que 'Dias' exista
    df.rename(columns=lambda x: 'Dias' if 'DIA' in str(x).upper() else x, inplace=True)

    # MAGIA 3: Planchamos las horas al mismo formato militar
    for col in ['Hora_ini', 'Hora_fin']:
        if col in df.columns:
            df[col] = df[col].apply(_parse_hora)

    # 🛡️ ESCUDO ANTI-COLAPSO: Verificamos si el purificador fabricó las columnas
    columnas_requeridas = ['Hora_ini', 'Hora_fin', 'Dias']
    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    
    if faltantes:
        # Si falló, detenemos el motor y le mostramos al ingeniero qué columnas leyó realmente
        raise ValueError(f"Falla de purificación. Columnas reales detectadas en el CSV: {list(df.columns)}")

    # Limpiamos remanentes
    df = df.dropna(subset=['Hora_ini', 'Hora_fin', 'Dias'])

    return df.reset_index(drop=True)
# ==========================================
# 2. UTILIDADES DE TIEMPO
# ==========================================

def hms_a_decimal(hms_str: str) -> float:
    """Convierte '09:30:00' a 9.5 para graficar"""
    h, m, s = map(int, str(hms_str).split(":"))
    decimal = h + (m / 60.0) + (s / 3600.0)
    if abs(decimal - round(decimal)) < 0.05:
        return round(decimal)
    return decimal

def agregar_columnas_temporales(df: pd.DataFrame) -> pd.DataFrame:
    """Inyecta la matemática de horas decimales para detectar empalmes"""
    df = df.copy()
    map_dias = {"L": 1, "A": 2, "M": 3, "J": 4, "V": 5, "S": 6}
    df["Dia_Num"] = df["Dias"].map(map_dias)
    df["start_dec"] = df["Hora_ini"].astype(str).apply(hms_a_decimal)
    df["end_dec"] = df["Hora_fin"].astype(str).apply(hms_a_decimal)
    df["duration_dec"] = df["end_dec"] - df["start_dec"]
    return df

# ==========================================
# 3. EL MOTOR MATEMÁTICO
# ==========================================

def detectar_empalmes(df: pd.DataFrame) -> list:
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
    for _, clases in df_combo.groupby("Dias"):
        clases = clases.sort_values("start_dec").reset_index(drop=True)
        if (clases["start_dec"] < clases["end_dec"].shift(1)).any():
            return True
    return False

def _calcular_horas_muertas(df_combo: pd.DataFrame) -> float:
    total = 0.0
    for _, clases in df_combo.groupby("Dias"):
        clases = clases.sort_values("start_dec").reset_index(drop=True)
        gaps = clases["start_dec"].iloc[1:].values - clases["end_dec"].iloc[:-1].values
        total += float(max(0, gaps.sum()))
    return round(total, 2)

def generar_horarios_optimos(df: pd.DataFrame, materias_deseadas: list, limite_horas: int = 4):
    if "start_dec" not in df.columns:
        df = agregar_columnas_temporales(df)

    grupos_nrcs = []
    for materia in materias_deseadas:
        nrcs = df[df["Materia"] == materia]["NRC"].unique().tolist()
        if not nrcs:
            return None, f"No se encontraron secciones para '{materia}' en el catálogo."
        grupos_nrcs.append(nrcs)

    total_combos = 1
    for grupo in grupos_nrcs:
        total_combos *= len(grupo)
    if total_combos > 50000:
        return None, f"Hay {total_combos:,} combinaciones posibles. Reduce las materias."

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
# 4. EL ARQUITECTO VISUAL
# ==========================================

def construir_figura(df: pd.DataFrame) -> go.Figure:
    colors = px.colors.qualitative.Plotly
    materia_to_color = {materia: colors[i % len(colors)] for i, materia in enumerate(df["Materia"].unique())}
    
    df = df.copy()
    df["Color"] = df["Materia"].map(materia_to_color)

    fig = go.Figure()
    for materia, group in df.groupby("Materia"):
        
        if 'Salón' in group.columns:
            salon_data = group['Salón']
        elif 'Salon' in group.columns: 
            salon_data = group['Salon']
        else:
            salon_data = ["Aula sin asignar"] * len(group)
            
        # Programación defensiva en caso de que no haya columna Profesor
        if 'Profesor' in group.columns:
            prof_data = group['Profesor']
        else:
            prof_data = ["Sin Profesor"] * len(group)

        custom_data = list(zip(prof_data, salon_data, group['Hora_ini'], group['Hora_fin']))
        
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
