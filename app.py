# app.py — Interfaz de usuario Krea-t tu horario
# Si te paseas por acá recuerda: no soy un experto ni un amateur, solo alguien curioso que tenía una laptop, YouTube y ayuda de IA.

import streamlit as st
import pandas as pd

# Importamos el motor pesado desde nuestra sala de máquinas
from utils import (
    cargar_materias, 
    agregar_columnas_temporales, 
    detectar_empalmes, 
    generar_horarios_optimos, 
    construir_figura
)

# --- CONFIGURACIÓN BÁSICA ---
st.set_page_config(page_title="Mi Horario", layout="wide", initial_sidebar_state="collapsed")
st.title("⚙️ Krea-t tu horario")

# --- CARGA DE DATOS MULTICARRERA ---
mapa_colegios = {
    "Ingeniería Química (IQ)": "materiasIQ.csv",
    "Ingeniería Ambiental (IA)": "materiasIA.csv",
    "Ingeniería en Alimentos (IAL)": "materiasIAL.csv",
    "Ingeniería en Materiales (MT)": "materiasMT.csv"
}

colegio_elegido = st.selectbox(
    "🎓 Selecciona tu licenciatura para cargar el catálogo correspondiente:", 
    list(mapa_colegios.keys())
)

archivo_objetivo = mapa_colegios[colegio_elegido]

# El caché ahora llama al purificador de datos
@st.cache_data
def load_data(ruta):
    return cargar_materias(ruta)

try:
    df = load_data(archivo_objetivo)
    st.success(f"Catálogo de {colegio_elegido} cargado exitosamente.")
except FileNotFoundError:
    st.error(f"⚠️ Aún no se ha subido el archivo {archivo_objetivo} al servidor.")
    st.stop()

# --- LAS PESTAÑAS ---
tab_manual, tab_algoritmo = st.tabs(["🛠️ Ya tienes tus NRCs", "🤖 Generador Automático"])

# ==========================================
# PESTAÑA 1: MODO MANUAL
# ==========================================
with tab_manual:
    st.markdown("Consulta el catálogo y crea tu horario para este periodo.")
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("🔍 Catálogo")
        busqueda = st.text_input("Buscar materia por nombre:")
        if busqueda:
            resultados = df[df['Materia'].str.contains(busqueda, case=False, na=False)].copy()
            if resultados.empty:
                st.info("No se encontraron resultados.")
            else:
                resultados['Horario'] = resultados['Hora_ini'].astype(str) + " - " + resultados['Hora_fin'].astype(str)
                st.dataframe(resultados[['NRC', 'Materia', 'Dias', 'Horario', 'Profesor']], hide_index=True, use_container_width=True)

    with col2:
        st.subheader("🗓️ Horario Interperiodo")
        nrc_texto = st.text_input("📚 Ingresa tus NRCs (separados por comas):", "40568")
        mis_nrcs = [int(nrc.strip()) for nrc in nrc_texto.split(",") if nrc.strip().isdigit()]

        if len(mis_nrcs) > 0:
            mi_horario = df[df['NRC'].isin(mis_nrcs)].copy()
            if mi_horario.empty:
                st.warning("No se encontraron materias con esos NRC.")
            else:
                # El motor temporal procesa los datos
                mi_horario = agregar_columnas_temporales(mi_horario)
                empalmes = detectar_empalmes(mi_horario)
                
                if empalmes:
                    st.error("🚨 **¡EMPALME DETECTADO!**")
                    for e in empalmes:
                        st.write("- " + e)
                else:
                    st.success("✅ No se detectaron empalmes.")
                    # El arquitecto visual dibuja la gráfica
                    fig = construir_figura(mi_horario)
                    st.plotly_chart(fig, use_container_width=True, theme=None)

# ==========================================
# PESTAÑA 2: GENERADOR AUTOMÁTICO
# ==========================================
with tab_algoritmo:
    st.markdown("Selecciona las materias y deja que el algoritmo encuentre las mejores combinaciones sin empalmes.")
    
    todas_las_materias = sorted(df['Materia'].unique())
    materias_deseadas = st.multiselect("Elige tus materias:", todas_las_materias)
    limite_horas = st.slider("Máximo de horas libres por semana:", 0, 20, 4)

    if st.button("Generar Horario Óptimo"):
        if len(materias_deseadas) > 0:
            with st.spinner('Procesando combinaciones...'):
                horarios_generados, mensaje = generar_horarios_optimos(df, materias_deseadas, limite_horas)
                
                if horarios_generados is None:
                    st.error(mensaje)
                elif len(horarios_generados) == 0:
                    st.warning("No se encontró ningún horario con esas restricciones.")
                else:
                    st.success(f"¡Se encontraron {len(horarios_generados)} horarios viables sin empalmes!")
                    
                    mejor_horario = horarios_generados[0]
                    st.markdown(f"### 🏆 Mejor horario con tus selecciones")
                    st.write(f"**NRCs a inscribir:** {', '.join(map(str, mejor_horario['nrcs']))}")
                    st.write(f"**Horas libres a la semana:** {mejor_horario['horas_muertas']} hrs")
                    
                    # Preparamos al ganador y lo graficamos
                    df_ganador = mejor_horario['df']
                    df_ganador = agregar_columnas_temporales(df_ganador)
                    fig_ganador = construir_figura(df_ganador)
                    st.plotly_chart(fig_ganador, use_container_width=True, theme=None)
        else:
            st.info("Por favor selecciona al menos una materia para comenzar.")

st.markdown("---")
st.markdown("Recuerda tomar captura de tu horario.")
st.markdown("Aún no tomo en cuenta los créditos, entonces eso debería de quedar a tu consideración :p ")
    
st.markdown(
    "Si alguien me pregunta por ti, diré que estoy todos los días "
    "alejando mi yo de ti — Marcos Algonia")
