
#app.py Interfaz de usuario para el generador de horarios.
#Solo contiene cadigo de Streamlit; la logica vive en utils.py.

#Si te paseas por acá¡ recuerda: no soy un experto ni un amateur, solo alguien curioso que tenÃÂ­a una laptop, YouTube y ayuda de IA.

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from utils import generar_horarios_optimos, hms_a_decimal, cargar_materias

# --- CONFIGURACIÃÂN BÃÂSICA ---
st.set_page_config(page_title="Mi Horario", layout="wide", initial_sidebar_state="collapsed")
st.title("Ã¢ÂÂÃ¯Â¸Â Krea-t tu horario")

# ---------------------------------------------------------------------------
# SelecciÃÂ³n de Colegio y Carga de datos
# ---------------------------------------------------------------------------

# 1. Creamos el diccionario (El mapa de rutas)
mapa_colegios = {
    "IngenierÃÂ­a QuÃÂ­mica (IQ)": "materiasIQ.csv",
    "IngenierÃÂ­a Ambiental (IA)": "materiasIA.csv",
    "IngenierÃÂ­a en Alimentos (IAL)": "materiasIAL.csv",
    "IngenierÃÂ­a en Materiales (MT)": "materiasMT.csv"
}

# 2. Le preguntamos al usuario su colegio
colegio_elegido = st.selectbox(
    "Ã°ÂÂÂ Selecciona tu licenciatura para cargar el catÃÂ¡logo correspondiente:", 
    list(mapa_colegios.keys())
)

# 3. Obtenemos el nombre del archivo correcto basado en su elecciÃÂ³n
archivo_objetivo = mapa_colegios[colegio_elegido]

# 4. Modificamos el cachÃÂ© para que recuerde el archivo dependiendo de la ruta
# 4. Modificamos el cachÃÂ© para que recuerde el archivo dependiendo de la ruta
@st.cache_data
def load_data(ruta):
    # cargar_materias limpia columnas, encoding y formato de horas automaticamente
    return cargar_materias(ruta)

try:
    # Ahora le pasamos la variable dinÃÂ¡mica
    df = load_data(archivo_objetivo)
    st.success(f"CatÃÂ¡logo de {colegio_elegido} cargado exitosamente.")
except FileNotFoundError:
    st.error(f"Ã¢ÂÂ Ã¯Â¸Â AÃÂºn no se ha subido el archivo {archivo_objetivo} al servidor.")
    st.stop()

# --- FUNCIÃÂN DE DIBUJO  ---
def dibujar_horario(mi_horario):
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    materia_to_color = {materia: colors[i % len(colors)] for i, materia in enumerate(mi_horario['Materia'].unique())}
    mi_horario['Color'] = mi_horario['Materia'].map(materia_to_color)

    for materia, group in mi_horario.groupby('Materia'):
        custom_data = group[['Profesor', 'SalÃÂ³n', 'Hora_ini', 'Hora_fin']].values
        fig.add_trace(go.Bar(
            name=materia, x=group['Dia_Num'], y=group['duration_dec'], base=group['start_dec'],
            marker_color=group['Color'].iloc[0], opacity=1.0,
            customdata=custom_data, text=group['Materia'],
            textposition='inside', insidetextanchor='middle',
            hovertemplate="<b>%{text}</b><br><br><b>Profesor:</b> %{customdata[0]}<br><b>SalÃÂ³n:</b> %{customdata[1]}<br><b>Horario:</b> %{customdata[2]} - %{customdata[3]}<br><extra></extra>"
        ))

    horas_numeros = list(range(7, 22)) 
    horas_texto = [f"{h:02d}:00" for h in horas_numeros]

    fig.update_layout(
        barmode='overlay', paper_bgcolor='white', plot_bgcolor='white', font=dict(color='black'), height=700,
        xaxis=dict(title="", side='top', tickmode='array', tickvals=[1, 2, 3, 4, 5], ticktext=['Lunes', 'Martes', 'MiÃÂ©rcoles', 'Jueves', 'Viernes'], showgrid=True, gridcolor='#e5e5e5', zeroline=False),
        yaxis=dict(title="Horario", range=[21.5, 6.5], tickmode='array', tickvals=horas_numeros, ticktext=horas_texto, showgrid=True, gridcolor='#e5e5e5', zeroline=False),
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return fig


# --- LAS PESTAÃÂAS ---
tab_manual, tab_algoritmo = st.tabs(["Ya tienes tus NRCs", "Ã°ÂÂ¤Â Generador AutomÃÂ¡tico"])

# ==========================================
# PESTAÃÂA 1: MODO MANUAL
# ==========================================
with tab_manual:
    st.markdown("Consulta el catÃÂ¡logo crea tu horario para este periodo.")
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Ã°ÂÂÂ CatÃÂ¡logo")
        busqueda = st.text_input("Buscar materia por nombre:")
        if busqueda:
            resultados = df[df['Materia'].str.contains(busqueda, case=False, na=False)].copy()
            if resultados.empty:
                st.info("No se encontraron resultados.")
            else:
                resultados['Horario'] = resultados['Hora_ini'].astype(str) + " - " + resultados['Hora_fin'].astype(str)
                st.dataframe(resultados[['NRC', 'Materia', 'Dias', 'Horario', 'Profesor']], hide_index=True, use_container_width=True)

    with col2:
        st.subheader("Ã°ÂÂÂÃ¯Â¸Â Horario Interperiodo")
        nrc_texto = st.text_input("Ã°ÂÂÂ Ingresa tus NRCs (separados por comas):", "40568")
        mis_nrcs = [int(nrc.strip()) for nrc in nrc_texto.split(",") if nrc.strip().isdigit()]

        if len(mis_nrcs) > 0:
            mi_horario = df[df['NRC'].isin(mis_nrcs)].copy()
            if mi_horario.empty:
                st.warning("No se encontraron materias con esos NRC.")
            else:
                map_dias_num = {'L': 1, 'A': 2, 'M': 3, 'J': 4, 'V': 5}
                mi_horario['Dia_Num'] = mi_horario['Dias'].map(map_dias_num)
                mi_horario['Hora_ini'] = mi_horario['Hora_ini'].astype(str)
                mi_horario['Hora_fin'] = mi_horario['Hora_fin'].astype(str)
                mi_horario['start_dec'] = mi_horario['Hora_ini'].apply(hms_a_decimal)
                mi_horario['end_dec'] = mi_horario['Hora_fin'].apply(hms_a_decimal)
                mi_horario['duration_dec'] = mi_horario['end_dec'] - mi_horario['start_dec']
                mi_horario['duration_dec'] = mi_horario['duration_dec'].apply(lambda x: round(x) if abs(x - round(x)) < 0.05 else x)

                empalmes = []
                for dia, clases_del_dia in mi_horario.groupby('Dias'):
                    clases = clases_del_dia.sort_values('start_dec').reset_index(drop=True)
                    for i in range(len(clases) - 1):
                        if clases.loc[i+1, 'start_dec'] < clases.loc[i, 'end_dec']:
                            empalmes.append(f"El dÃÂ­a {dia}, **{clases.loc[i, 'Materia']}** choca con **{clases.loc[i+1, 'Materia']}**.")
                
                if empalmes:
                    st.error("Ã°ÂÂÂ¨ **ÃÂ¡EMPALME DETECTADO!**")
                    for e in empalmes:
                        st.write("- " + e)
                else:
                    st.success("Ã¢ÂÂ No se detectaron empalmes.")
                    fig = dibujar_horario(mi_horario)
                    st.plotly_chart(fig, use_container_width=True, theme=None)


# ==========================================
# PESTAÃÂA 2: GENERADOR AUTOMÃÂTICO
# ==========================================
with tab_algoritmo:
    st.markdown("Selecciona las materias y deja que el algoritmo encuentre las mejores combinaciones sin empalmes.")
    
    todas_las_materias = sorted(df['Materia'].unique())
    materias_deseadas = st.multiselect("Elige tus materias:", todas_las_materias)
    limite_horas = st.slider("MÃÂ¡ximo de horas libres toleradas por semana:", 0, 20, 4)

    if st.button("Generar Horario ÃÂptimo"):
        if len(materias_deseadas) > 0:
            with st.spinner('Procesando combinaciones...'):
                horarios_generados, mensaje = generar_horarios_optimos(df, materias_deseadas, limite_horas)
                
                if horarios_generados is None:
                    st.error(mensaje)
                elif len(horarios_generados) == 0:
                    st.warning("No se encontrÃÂ³ ningÃÂºn horario viable con esas restricciones.")
                else:
                    st.success(f"ÃÂ¡Se encontraron {len(horarios_generados)} horarios viables sin empalmes!")
                    
                    mejor_horario = horarios_generados[0]
                    st.markdown(f"### Ã°ÂÂÂ OpciÃÂ³n ÃÂptima")
                    st.write(f"**NRCs a inscribir:** {', '.join(map(str, mejor_horario['nrcs']))}")
                    st.write(f"**Horas libres a la semana:** {mejor_horario['horas_muertas']} hrs")
                    
                    # Preparamos el dataframe ganador para graficarlo
                    df_ganador = mejor_horario['df']
                    map_dias_num = {'L': 1, 'A': 2, 'M': 3, 'J': 4, 'V': 5}
                    df_ganador['Dia_Num'] = df_ganador['Dias'].map(map_dias_num)
                    df_ganador['duration_dec'] = df_ganador['end_dec'] - df_ganador['start_dec']
                    df_ganador['duration_dec'] = df_ganador['duration_dec'].apply(lambda x: round(x) if abs(x - round(x)) < 0.05 else x)
                    
                    # Dibujamos el horario ganador
                    fig_ganador = dibujar_horario(df_ganador)
                    st.plotly_chart(fig_ganador, use_container_width=True, theme=None)
        else:
            st.info("Por favor selecciona al menos una materia para comenzar.")
st.markdown("Recuerda tomar captura de tu horario.")
st.markdown(
    "AÃÂºn no tomo en cuenta los crÃÂ©ditos, entonces eso deberÃÂ­a de quedar a tu consideraciÃÂ³n :p ")
    

st.markdown(
    "Si alguien me pregunta por ti, dirÃÂ© que estoy todos los dÃÂ­as "
    "alejando mi yo de ti Ã¢ÂÂ Marcos Algonia")
