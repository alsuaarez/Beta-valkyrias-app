import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd

# Configuración y conexión
st.set_page_config(page_title="Perfil del jugador", page_icon="👤", layout="wide")

@st.cache_resource
def init_connection():
    return create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

supabase: Client = init_connection()

# Comprobar si venimos de la página principal
if 'jugador_seleccionado' not in st.session_state:
    st.warning("No has seleccionado a ningún jugador. Por favor, vuelve a la Plantilla.")
    st.stop() # Detiene la ejecución si no hay jugador

id_jugador = st.session_state['jugador_seleccionado']
nombre_jugador = st.session_state['nombre_seleccionado']

# Cabecera del Perfil
st.title(f"Perfil del jugador: {nombre_jugador}")
st.markdown("---")

# Asistente de Configuración de Datos (Wizard)
st.subheader("Configuración del análisis")

# Paso 1: Tipo de informe
tipo_analisis = st.radio(
    "Paso 1: ¿Qué área deseas analizar?",
    ["Rendimiento físico", "Estadísticas de partido"],
    horizontal=True
)

if tipo_analisis == "Rendimiento físico":
    # Paso 2: Selección manual de columnas
    columnas_disponibles = {
        "Peso (kg)": "peso_kg",
        "Salto (cm)": "salto_cm",
        "Velocidad 10m (s)": "velocidad_10m_s",
        "Velocidad 30m (s)": "velocidad_30m_s",
        "Cambio de Ritmo (s)": "cambio_ritmo_s"
    }
    
    metricas_seleccionadas = st.multiselect(
        "Paso 2: Selecciona las métricas que deseas visualizar en la gráfica",
        options=list(columnas_disponibles.keys()),
        default=["Peso (kg)"] # Columnas por defecto
    )
    
    # Paso 3: Visualización dinámica en gráficas individuales
    if metricas_seleccionadas:
        st.markdown("### Evolución del jugador")
        
        # Pedimos los datos a Supabase
        response = supabase.table("tests_fisicos").select("*").eq("id_jugador", id_jugador).order("fecha_test").execute()
        datos_tests = response.data
        
        if datos_tests:
            # Convertimos a Pandas DataFrame
            df = pd.DataFrame(datos_tests)
            df['fecha_test'] = pd.to_datetime(df['fecha_test'])
            df.set_index('fecha_test', inplace=True)
            
            # Creamos una gráfica independiente por cada métrica seleccionada
            for metrica in metricas_seleccionadas:
                columna_real = columnas_disponibles[metrica]
                with st.container(border=True):
                    st.markdown(f"#### {metrica}")
                    st.line_chart(df[[columna_real]], height=250) 
            
            # Mostramos la tabla en crudo
            with st.expander("Ver tabla de datos crudos"):
                columnas_reales = [columnas_disponibles[m] for m in metricas_seleccionadas]
                st.dataframe(df[columnas_reales])
        else:
            st.info("No hay registros de tests físicos para este jugador todavía.")
    else:
        st.warning("Selecciona al menos una métrica para visualizar la gráfica.")

elif tipo_analisis == "Estadísticas de partido":
    st.markdown("### Rendimiento en el terreno de juego")
    
    # Hacer consulta para traer estadísticas + datos del partido
    response = supabase.table("estadisticas_partidos") \
        .select("*, partidos(fecha, rival, competicion, condicion)") \
        .eq("id_jugador", id_jugador) \
        .execute()
        
    datos_partidos = response.data
    
    if datos_partidos:
        # Aplanar los datos
        lista_plana = []
        for row in datos_partidos:
            partido_info = row.get('partidos', {})
            lista_plana.append({
                'ID Partido': row['id_partido'],
                'Fecha': partido_info.get('fecha', ''),
                'Rival': partido_info.get('rival', ''),
                'Competición': partido_info.get('competicion', ''),
                'Condición': partido_info.get('condicion', ''),
                'Minutos': row['minutos_jugados'],
                'Goles': row['goles'],
                'Asistencias': row['asistencias'],
                'Amarillas': row['tarjetas_amarillas']
            })
            
        df_partidos = pd.DataFrame(lista_plana)
        
        # --- SECCIÓN A: ACUMULADO GLOBAL ---
        st.subheader("Acumulado total")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Minutos Jugados", int(df_partidos['Minutos'].sum()))
        col2.metric("Goles", int(df_partidos['Goles'].sum()))
        col3.metric("Asistencias", int(df_partidos['Asistencias'].sum()))
        col4.metric("Tarjetas Amarillas", int(df_partidos['Amarillas'].sum()))
        
        st.markdown("---")
        
        # --- SECCIÓN B: DESGLOSE INDIVIDUAL ---
        st.subheader("Análisis individual por partido")
        
        opciones_partidos = df_partidos.apply(
            lambda x: f"{x['Competición']} | {x['Fecha']} vs {x['Rival']}", axis=1
        ).tolist()
        
        partido_seleccionado = st.selectbox(
            "Selecciona un partido para ver los datos específicos:",
            options=opciones_partidos
        )
        
        if partido_seleccionado:
            idx_seleccion = opciones_partidos.index(partido_seleccionado)
            datos_partido_elegido = df_partidos.iloc[idx_seleccion]
            
            st.info(f"Condición: Jugó como **{datos_partido_elegido['Condición']}**")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Minutos", int(datos_partido_elegido['Minutos']))
            col_b.metric("Goles", int(datos_partido_elegido['Goles']))
            col_c.metric("Asistencias", int(datos_partido_elegido['Asistencias']))
            col_d.metric("Amarillas", int(datos_partido_elegido['Amarillas']))
        
        with st.expander("Ver tabla completa de registros"):
            st.dataframe(df_partidos)
            
    else:
        st.info("No hay registros de partidos para este jugador todavía.")