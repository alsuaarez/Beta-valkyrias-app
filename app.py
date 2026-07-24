import streamlit as st
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Configuración inicial
st.set_page_config(page_title="Valkyrias Auth", page_icon="⚽", layout="wide")
load_dotenv()

@st.cache_resource
def init_connection():
    return create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

supabase: Client = init_connection()

# Inicializar la memoria de la sesión
if 'usuario_actual' not in st.session_state:
    st.session_state['usuario_actual'] = None
    st.session_state['rol'] = None
    st.session_state['id_jugador_vinculado'] = None

# ==========================================
# PANTALLA DE LOGIN
# ==========================================
if st.session_state['usuario_actual'] is None:
    # Diseño centrado para el login
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso Plataforma")
        st.markdown("Introduce tus credenciales del CD Valkyrias Becerril.")
        
        with st.form("login_form"):
            email = st.text_input("Correo electrónico")
            password = st.text_input("Contraseña", type="password")
            btn_acceder = st.form_submit_button("Iniciar Sesión", use_container_width=True)
            
            if btn_acceder:
                try:
                    # A. Intentar login en Supabase
                    auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    
                    # B. Buscar el rol del usuario
                    rol_response = supabase.table("usuarios_roles").select("*").eq("correo", email).execute()
                    
                    if rol_response.data:
                        datos_usuario = rol_response.data[0]
                        st.session_state['usuario_actual'] = email
                        st.session_state['rol'] = datos_usuario['rol']
                        st.session_state['id_jugador_vinculado'] = datos_usuario['id_jugador']
                        st.rerun() # Recarga la página instantáneamente
                    else:
                        st.error("Tu usuario no tiene un rol asignado en el sistema.")
                        
                except Exception as e:
                    st.error("Credenciales incorrectas. Vuelve a intentarlo.")

# ==========================================
# PANTALLA PRINCIPAL (SI HAY SESIÓN INICIADA)
# ==========================================
else:
    # Cabecera con botón de cerrar sesión
    c_titulo, c_boton = st.columns([4, 1])
    c_titulo.title("⚽ CD Valkyrias Becerril - Hub Analítico")
    c_titulo.caption(f"Conectado como: {st.session_state['usuario_actual']} | Nivel de acceso: {st.session_state['rol']}")
    
    if c_boton.button("Cerrar Sesión", use_container_width=True):
        st.session_state['usuario_actual'] = None
        st.session_state['rol'] = None
        st.session_state['id_jugador_vinculado'] = None
        st.rerun()
        
    st.markdown("---")

    # --- LÓGICA DE ROLES ---
    
    # ROL JUGADOR: Solo puede ver su propio acceso
    if st.session_state['rol'] == 'Jugador':
        st.success("¡Bienvenido a tu portal personal!")
        st.info("Aquí puedes consultar tu evolución física y tus métricas de partido.")
        
        # Automatizamos la selección para que no tenga que buscarse en la plantilla
        st.session_state['jugador_seleccionado'] = st.session_state['id_jugador_vinculado']
        st.session_state['nombre_seleccionado'] = "Tu Perfil"
        
        # Le ponemos un botón directo a su ficha
        st.page_link("pages/1_Ficha_Jugador.py", label="Ir a mis Estadísticas Personales", icon="📊")

    # ROL ADMIN / TÉCNICO: Ven la plantilla completa
    elif st.session_state['rol'] in ['Admin', 'Tecnico']:
        st.markdown("### Selecciona un jugador para consultar sus métricas")
        
        try:
            response = supabase.table("jugadores").select("*").order("dorsal").execute()
            lista_jugadores = response.data
            
            if lista_jugadores:
                columnas = st.columns(4)
                for index, jugador in enumerate(lista_jugadores):
                    col = columnas[index % 4] 
                    with col:
                        with st.container(border=True):
                            st.markdown(f"""
                                <div style='text-align: center;'>
                                    <img src='{jugador["url_foto"]}' width='100' style='border-radius: 50%;'>
                                    <h3 style='margin-bottom: 0px;'>{jugador["nombre"]}</h3>
                                    <p style='color: gray;'>Dorsal: {jugador["dorsal"]} | {jugador["posicion"]}</p>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button("Abrir Perfil", key=f"btn_{jugador['id_jugador']}", use_container_width=True):
                                st.session_state['jugador_seleccionado'] = jugador['id_jugador']
                                st.session_state['nombre_seleccionado'] = jugador['nombre']
                                st.switch_page("pages/1_Ficha_Jugador.py") # Redirige automáticamente
        except Exception as e:
            st.error(f"Error al cargar los datos: {e}")