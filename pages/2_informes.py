import streamlit as st

from utils.config import init_connection, aplicar_estilos, requiere_sesion, cabecera

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(page_title="Informes y Análisis", page_icon="📁", layout="wide")
aplicar_estilos()
supabase = init_connection()

# ============================================================
# BARRERA DE SEGURIDAD Y ROLES
# ============================================================
requiere_sesion()

if st.session_state.get("rol") == "Jugador":
    st.error("🚫 Acceso denegado. Los jugadores no tienen permisos para ver los informes técnicos.")
    st.stop()

# ============================================================
# INTERFAZ DE INFORMES
# ============================================================
cabecera("Gestor de Informes Técnicos", "Repositorio centralizado de análisis del club", icono="📁")

if st.session_state.get("rol") == "Admin":
    tabs = st.tabs(["📄 Consultar Informes", "📤 Añadir Nuevo Informe"])
    tab_consultar, tab_subir = tabs[0], tabs[1]
else:
    tabs = st.tabs(["📄 Consultar Informes"])
    tab_consultar, tab_subir = tabs[0], None

# ============================================================
# PESTAÑA 1: LECTURA DE INFORMES (Admin y Técnico)
# ============================================================
with tab_consultar:
    col1, col2 = st.columns([1, 3])
    with col1:
        filtro_tipo = st.selectbox("Filtrar por categoría:", ["Todos", "Pretemporada", "Partido", "Individual"])

    st.markdown("### Documentos disponibles")

    try:
        query = supabase.table("informes_pdf").select("*")
        if filtro_tipo != "Todos":
            query = query.eq("tipo", filtro_tipo)
        response = query.order("fecha", desc=True).execute()

        datos_informes = response.data

        if datos_informes:
            for informe in datos_informes:
                with st.container(border=True):
                    c_texto, c_boton = st.columns([4, 1])
                    c_texto.markdown(f"**{informe['titulo']}**")
                    c_texto.caption(f"📅 {informe['fecha']} · 🏷️ {informe['tipo']}")
                    c_boton.link_button("Abrir ↗", informe["url_archivo"], width='stretch')
        else:
            st.info("No hay informes guardados en esta categoría.")

    except Exception as e:
        st.error(f"Error al cargar los informes: {e}")

# ============================================================
# PESTAÑA 2: ESCRITURA EN BBDD (Solo Admin)
# ============================================================
if tab_subir is not None:
    with tab_subir:
        st.markdown("#### Registrar un nuevo análisis")
        st.info("💡 Consejo: sube tu PDF a una nube y pega aquí el enlace público.")

        with st.form("form_nuevo_informe", clear_on_submit=True):
            nuevo_titulo = st.text_input("Título del informe")

            c_tipo, c_fecha = st.columns(2)
            nuevo_tipo = c_tipo.selectbox("Tipo de documento", ["Pretemporada", "Partido", "Individual"])
            nueva_fecha = c_fecha.date_input("Fecha correspondiente")

            nuevo_enlace = st.text_input("Enlace URL del PDF")

            btn_guardar = st.form_submit_button("Guardar en la base de datos", type="primary")

            if btn_guardar:
                if nuevo_titulo and nuevo_enlace:
                    try:
                        supabase.table("informes_pdf").insert({
                            "titulo": nuevo_titulo,
                            "tipo": nuevo_tipo,
                            "fecha": str(nueva_fecha),
                            "url_archivo": nuevo_enlace,
                        }).execute()
                        st.success("✅ ¡Informe registrado con éxito!")
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
                else:
                    st.warning("⚠️ El título y el enlace son campos obligatorios.")
