import streamlit as st
from dotenv import load_dotenv
import os
from supabase import create_client, Client

# Configuración de página
st.set_page_config(page_title="Valkyrias Analytics", page_icon="⚽", layout="wide")
load_dotenv()

# Conexión a la BBDD
@st.cache_resource
def init_connection():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase: Client = init_connection()

# Interfaz Principal
st.title("⚽ CD Valkyrias Becerril - Plantilla")
st.markdown("Selecciona a un jugador para acceder a su ficha individual y consultar sus métricas.")

# Obtener datos de Supabase
try:
    response = supabase.table("jugadores").select("*").order("dorsal").execute()
    lista_jugadores = response.data
    
    # Crear la cuadrícula (4 columnas)
    if lista_jugadores:
        columnas = st.columns(4)
        
        for index, jugador in enumerate(lista_jugadores):
            # El módulo calcula en qué columna va cada jugador para hacer filas perfectas
            col = columnas[index % 4] 
            
            with col:
                # Contenedor visual para cada jugador
                with st.container(border=True):
                    # Forzamos un poco el CSS para centrar la foto y el texto
                    st.markdown(f"""
                        <div style='text-align: center;'>
                            <img src='{jugador["url_foto"]}' width='100' style='border-radius: 50%;'>
                            <h3 style='margin-bottom: 0px;'>{jugador["nombre"]}</h3>
                            <p style='color: gray;'>Dorsal: {jugador["dorsal"]} | {jugador["posicion"]}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Botón interactivo que guarda el ID del jugador en la memoria de la sesión
                    if st.button("Abrir Perfil", key=f"btn_{jugador['id_jugador']}", use_container_width=True):
                        st.session_state['jugador_seleccionado'] = jugador['id_jugador']
                        st.session_state['nombre_seleccionado'] = jugador['nombre']
                        st.success(f"Has seleccionado a {jugador['nombre']}. ¡En el próximo paso conectaremos esto con su ficha!")
                        
except Exception as e:
    st.error(f"Error al cargar los datos: {e}")