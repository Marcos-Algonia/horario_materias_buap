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
    # Diccionario adaptado al sistema BUAP (Martes = A, Miércoles = M)
    dias_map = {
        'LUNES': 'L', 'MARTES': 'A', 'MIERCOLES': 'M', 'MIÉRCOLES': 'M',
        'JUEVES': 'J', 'VIERNES': 'V', 'SABADO': 'S', 'SÁBADO': 'S'
    }

    # Buscamos qué columnas de días existen realmente en tu archivo
    dias_presentes = [c for c in df.columns if str(c).upper().strip() in dias_map.keys()]

    # Si el archivo ya viene en formato de lista (como tu primer Excel), no hacemos nada
    if not dias_presentes:
        return df

    # Separamos las columnas de identidad (NRC, Materia...) de las columnas de días
    id_vars = [c for c in df.columns if c not in dias_presentes]

    # MAGIA: Derretimos la tabla ancha hacia abajo
    df_largo = df.melt(id_vars=id_vars, value_vars=dias_presentes, var_name='Dia_Nombre', value_name='Horario_Rango')

    # Eliminamos las filas fantasma (días donde esa materia no da clases)
    df_largo = df_largo.dropna(subset=['Horario_Rango'])
    df_largo = df_largo[df_largo['Horario_Rango'].astype(str).str.strip() != '']

    # Convertimos la palabra "LUNES" en la letra "L"
    df_largo['Dias'] = df_largo['Dia_Nombre'].str.upper().str.strip().map(dias_map)

    # Función interna para partir "09:00 - 11:00" en dos pedazos
    def extraer_horas(texto):
        partes = str(texto).split('-')
        if len(partes) == 2:
            return partes[0].strip(), partes[1].strip()
        return None, None

    # Aplicamos el corte y creamos las dos columnas nuevas
    df_largo['Hora_ini'], df_largo['Hora_fin'] = zip(*df_largo['Horario_Rango'].apply(extraer_horas))

    # Tiramos a la basura las columnas que ya usamos para no ensuciar
    return df_largo.drop(columns=['Dia_Nombre', 'Horario_Rango'])

def cargar_materias(ruta: str) -> pd.DataFrame:
    """Lee el CSV y repara columnas rotas, símbolos fantasma (BOM) y horas."""
    df = pd.read_csv(ruta, encoding='latin1')
    df.columns = df.columns.str.strip()

    # MAGIA 1: Reparamos el Mojibake (Acentos y letras raras)
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
            
    # ESCUDO DEFENSIVO: Eliminamos el Fantasma de Excel (BOM)
    columnas_limpias = [c.replace('\ufeff', '').replace('ï»¿', '').strip() for c in columnas_limpias]
    df.columns = columnas_limpias
    
    # Aseguramos nombres clave
    df.rename(columns=lambda x: 'NRC' if 'NRC' in str(x).upper() else x, inplace=True)
    df.rename(columns=lambda x: 'Materia' if 'MATERIA' in str(x).upper() else x, inplace=True)

    # MAGIA 2: Desdoblamos el horario si viene en columnas (como el de Ingeniería Ambiental)
    df = _desdoblar_horarios(df)
    
    # En caso de que no haya entrado al desdoble, nos aseguramos de que 'Dias' exista
    df.rename(columns=lambda x: 'Dias' if 'DIA' in str(x).upper() else x, inplace=True)

    # MAGIA 3: Planchamos las horas al mismo formato militar
    for col in ['Hora_ini', 'Hora_fin']:
        if col in df.columns:
            df[col] = df[col].apply(_parse_hora)

    # Limpiamos remanentes
    df = df.dropna(subset=['Hora_ini', 'Hora_fin', 'Dias'])

    return df.reset_index(drop=True)
