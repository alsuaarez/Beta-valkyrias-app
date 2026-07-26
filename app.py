import streamlit as st
from dotenv import load_dotenv

from utils.config import (
    init_connection, aplicar_estilos, cabecera, color_posicion, badge_html,
    NOMBRE_CLUB, COLOR_SECUNDARIO,
)

# ============================================================
# CONFIGURACIÓN INICIAL
# ============================================================
st.set_page_config(page_title=f"{NOMBRE_CLUB} · Hub Analítico", page_icon="⚽", layout="wide")
load_dotenv()
aplicar_estilos()

supabase = init_connection()

# Memoria de sesión
if "usuario_actual" not in st.session_state:
    st.session_state["usuario_actual"] = None
    st.session_state["rol"] = None
    st.session_state["id_jugador_vinculado"] = None

# ============================================================
# PANTALLA DE LOGIN
# ============================================================
if st.session_state["usuario_actual"] is None:
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown(
            f"""
            <div style='text-align:center; margin-top: 60px; margin-bottom: 10px;'>
                <div style='font-size: 3rem;'>⚽</div>
                <h1 style='margin-bottom:0;'>{NOMBRE_CLUB}</h1>
                <p style='color:#5A6472;'>Hub Analítico del cuerpo técnico</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            with st.form("login_form"):
                st.markdown("#### Iniciar sesión")
                email = st.text_input("Correo electrónico")
                password = st.text_input("Contraseña", type="password")
                btn_acceder = st.form_submit_button(
                    "Acceder", width='stretch', type="primary"
                )

                if btn_acceder:
                    if not email or not password:
                        st.warning("Introduce tu correo y contraseña.")
                    else:
                        try:
                            supabase.auth.sign_in_with_password(
                                {"email": email, "password": password}
                            )
                            rol_response = (
                                supabase.table("usuarios_roles")
                                .select("*")
                                .eq("correo", email)
                                .execute()
                            )

                            if rol_response.data:
                                datos_usuario = rol_response.data[0]
                                st.session_state["usuario_actual"] = email
                                st.session_state["rol"] = datos_usuario["rol"]
                                st.session_state["id_jugador_vinculado"] = datos_usuario["id_jugador"]
                                st.rerun()
                            else:
                                st.error("Tu usuario no tiene un rol asignado en el sistema.")
                        except Exception:
                            st.error("Credenciales incorrectas. Vuelve a intentarlo.")

# ============================================================
# PANTALLA PRINCIPAL (SESIÓN INICIADA)
# ============================================================
else:
    c_titulo, c_boton = st.columns([5, 1])
    with c_titulo:
        cabecera(
            NOMBRE_CLUB,
            f"Conectado como <b>{st.session_state['usuario_actual']}</b> · "
            f"Nivel de acceso: <b>{st.session_state['rol']}</b>",
        )
    with c_boton:
        st.write("")
        if st.button("🔒 Cerrar sesión", width='stretch'):
            st.session_state["usuario_actual"] = None
            st.session_state["rol"] = None
            st.session_state["id_jugador_vinculado"] = None
            st.rerun()

    # --------------------------------------------------------
    # ROL JUGADOR: acceso directo a su propio perfil
    # --------------------------------------------------------
    if st.session_state["rol"] == "Jugador":
        st.success("¡Bienvenido a tu portal personal!")
        st.info("Aquí puedes consultar tu evolución física y tus métricas de partido.")

        st.session_state["jugador_seleccionado"] = st.session_state["id_jugador_vinculado"]
        st.session_state["nombre_seleccionado"] = "Tu Perfil"

        c_link1, c_link2 = st.columns(2)
        with c_link1:
            st.page_link(
                "pages/1_ficha_jugador.py",
                label="Ir a mis estadísticas personales",
                icon="📊",
            )
        with c_link2:
            st.page_link(
                "pages/2_informes.py",
                label="Ver mis informes",
                icon="📁",
            )

    # --------------------------------------------------------
    # ROL ADMIN / TÉCNICO: plantilla completa
    # --------------------------------------------------------
    elif st.session_state["rol"] in ["Admin", "Tecnico"]:

        c_busq, c_filtro, c_add = st.columns([2, 1.3, 1])
        with c_busq:
            busqueda = st.text_input("🔎 Buscar jugador", placeholder="Nombre o dorsal…")
        with c_filtro:
            filtro_posicion = st.selectbox(
                "Posición",
                ["Todos", "Portero", "Defensa", "Centrocampista", "Delantero"],
            )
        with c_add:
            st.write("")
            if st.session_state["rol"] == "Admin":
                st.page_link(
                    "pages/3_gestion_jugadores.py",
                    label="➕ Añadir jugador",
                    icon=None,
                    width='stretch',
                )

        st.markdown("### Plantilla")

        try:
            response = supabase.table("jugadores").select("*").order("dorsal").execute()
            lista_jugadores = response.data or []

            # Filtros en memoria
            if busqueda:
                b = busqueda.lower().strip()
                lista_jugadores = [
                    j for j in lista_jugadores
                    if b in (j.get("nombre", "") or "").lower() or b == str(j.get("dorsal", ""))
                ]
            if filtro_posicion != "Todos":
                lista_jugadores = [j for j in lista_jugadores if j.get("posicion") == filtro_posicion]

            if lista_jugadores:
                columnas = st.columns(4)
                for index, jugador in enumerate(lista_jugadores):
                    col = columnas[index % 4]
                    with col:
                        with st.container(border=True):
                            foto = jugador.get("url_foto") or "https://placehold.co/200x200?text=%20"
                            pos = jugador.get("posicion", "")
                            st.markdown(
                                f"""
                                <div style='text-align:center; padding: 6px 0 2px 0;'>
                                    <img src='{foto}' class='foto-jugador'>
                                    <h4 style='margin: 10px 0 2px 0;'>{jugador.get("nombre", "")}</h4>
                                    <p style='color:#5A6472; margin:0 0 8px 0;'>Dorsal #{jugador.get("dorsal", "-")}</p>
                                    <div style='margin-bottom: 10px;'>{badge_html(pos, color_posicion(pos))}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            if st.button(
                                "Ver perfil",
                                key=f"btn_{jugador['id_jugador']}",
                                width='stretch',
                                type="primary",
                            ):
                                st.session_state["jugador_seleccionado"] = jugador["id_jugador"]
                                st.session_state["nombre_seleccionado"] = jugador["nombre"]
                                st.switch_page("pages/1_ficha_jugador.py")
            else:
                st.info("No se ha encontrado ningún jugador con esos filtros.")
        except Exception as e:
            st.error(f"Error al cargar los datos: {e}")
