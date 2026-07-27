import streamlit as st
from datetime import date

from utils.config import (
    init_connection, aplicar_estilos, requiere_sesion, cabecera, es_staff,
    CATEGORIAS_INFORME, ETIQUETAS_CATEGORIA, jugador_tiene_acceso,
)

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(page_title="Informes y Análisis", page_icon="📁", layout="wide")
aplicar_estilos()
supabase = init_connection()

requiere_sesion()
staff = es_staff()
rol = st.session_state.get("rol")
id_jugador_actual = st.session_state.get("id_jugador_vinculado")

cabecera("Gestor de Informes Técnicos", "Repositorio centralizado de análisis del club", icono="📁")


@st.cache_data(ttl=30)
def cargar_partidos():
    r = supabase.table("partidos").select("*").order("fecha", desc=True).execute()
    return r.data or []


def etiqueta_partido(p):
    return f"{p.get('fecha', '')} · {p.get('competicion', '')} vs {p.get('rival', '')}"


partidos = cargar_partidos()
mapa_partidos = {p["id_partido"]: etiqueta_partido(p) for p in partidos}

# ============================================================
# PESTAÑAS SEGÚN ROL
# ============================================================
if rol == "Admin":
    tabs = st.tabs(["📄 Consultar Informes", "📤 Añadir Nuevo Informe", "🗓️ Gestionar Partidos"])
    tab_consultar, tab_subir, tab_partidos = tabs[0], tabs[1], tabs[2]
else:
    tabs = st.tabs(["📄 Consultar Informes"])
    tab_consultar, tab_subir, tab_partidos = tabs[0], None, None

# ============================================================
# PESTAÑA 1: CONSULTAR INFORMES (todos los roles, con filtro de acceso)
# ============================================================
with tab_consultar:
    col1, col2 = st.columns([1.3, 2])
    with col1:
        filtro_categoria = st.selectbox(
            "Filtrar por categoría:",
            ["Todas"] + CATEGORIAS_INFORME,
            format_func=lambda x: "Todas" if x == "Todas" else ETIQUETAS_CATEGORIA[x],
        )
    with col2:
        opciones_partido = ["Todos"] + list(mapa_partidos.keys())
        filtro_partido = st.selectbox(
            "Filtrar por partido:",
            opciones_partido,
            format_func=lambda x: "Todos" if x == "Todos" else mapa_partidos[x],
        )

    st.markdown("### Documentos disponibles")

    try:
        query = supabase.table("informes_pdf").select("*")
        if filtro_categoria != "Todas":
            query = query.eq("tipo", filtro_categoria)
        if filtro_partido != "Todos":
            query = query.eq("id_partido", filtro_partido)
        response = query.order("fecha", desc=True).execute()
        datos_informes = response.data or []

        # -------- Filtro de visibilidad: los jugadores solo ven lo suyo --------
        if rol == "Jugador":
            visibles = []
            for informe in datos_informes:
                if informe.get("tipo") == "Individual":
                    if jugador_tiene_acceso(supabase, informe["id_informe"], id_jugador_actual):
                        visibles.append(informe)
                else:
                    visibles.append(informe)  # informes de partido/pretemporada: toda la plantilla
            datos_informes = visibles

        if datos_informes:
            for informe in datos_informes:
                with st.container(border=True):
                    c_texto, c_boton = st.columns([4, 1])
                    id_p = informe.get("id_partido")
                    linea_partido = f" · 🗓️ {mapa_partidos[id_p]}" if id_p in mapa_partidos else ""
                    c_texto.markdown(f"**{informe['titulo']}**")
                    c_texto.caption(
                        f"{ETIQUETAS_CATEGORIA.get(informe['tipo'], informe['tipo'])} · "
                        f"📅 {informe['fecha']}{linea_partido}"
                    )
                    c_boton.link_button("Abrir ↗", informe["url_archivo"], width='stretch')
        else:
            st.info("No hay informes disponibles con esos filtros.")

    except Exception as e:
        st.error(f"Error al cargar los informes: {e}")

# ============================================================
# PESTAÑA 2: AÑADIR INFORME (solo Admin)
# ============================================================
if tab_subir is not None:
    with tab_subir:
        st.markdown("#### Registrar un nuevo análisis")
        st.info("💡 Consejo: sube tu PDF a una nube y pega aquí el enlace público.")

        categoria_sel = st.selectbox(
            "Categoría del informe",
            CATEGORIAS_INFORME,
            format_func=lambda x: ETIQUETAS_CATEGORIA[x],
            key="categoria_nuevo_informe",
        )

        requiere_partido = categoria_sel in (
            "Analisis Propio Pre", "Analisis Propio Post",
            "Analisis Rival Pre", "Analisis Rival Post",
        )
        id_partido_sel = None
        if requiere_partido:
            if partidos:
                id_partido_sel = st.selectbox(
                    "Partido asociado",
                    list(mapa_partidos.keys()),
                    format_func=lambda x: mapa_partidos[x],
                    key="partido_nuevo_informe",
                )
            else:
                st.warning(
                    "No hay ningún partido creado todavía. Crea uno en la pestaña "
                    "'🗓️ Gestionar Partidos' antes de subir este informe."
                )

        jugadores_acceso_sel = []
        if categoria_sel == "Individual":
            try:
                jugadores_resp = supabase.table("jugadores").select("id_jugador, nombre").order("nombre").execute()
                lista_jugadores = jugadores_resp.data or []
                jugadores_acceso_sel = st.multiselect(
                    "¿Qué jugador(es) pueden ver este informe?",
                    options=[j["id_jugador"] for j in lista_jugadores],
                    format_func=lambda id_j: next(
                        (j["nombre"] for j in lista_jugadores if j["id_jugador"] == id_j), str(id_j)
                    ),
                    key="jugadores_acceso_nuevo_informe",
                )
            except Exception as e:
                st.error(f"No se pudo cargar la lista de jugadores: {e}")

        with st.form("form_nuevo_informe", clear_on_submit=True):
            nuevo_titulo = st.text_input("Título del informe")
            nueva_fecha = st.date_input("Fecha correspondiente", value=date.today())
            nuevo_enlace = st.text_input("Enlace URL del PDF")

            btn_guardar = st.form_submit_button("Guardar en la base de datos", type="primary")

            if btn_guardar:
                if not nuevo_titulo or not nuevo_enlace:
                    st.warning("⚠️ El título y el enlace son campos obligatorios.")
                elif categoria_sel == "Individual" and not jugadores_acceso_sel:
                    st.warning("⚠️ Selecciona al menos un jugador con acceso para un informe individual.")
                elif requiere_partido and id_partido_sel is None:
                    st.warning("⚠️ Este tipo de informe necesita un partido asociado.")
                else:
                    try:
                        insert_resp = supabase.table("informes_pdf").insert({
                            "titulo": nuevo_titulo,
                            "tipo": categoria_sel,
                            "fecha": str(nueva_fecha),
                            "url_archivo": nuevo_enlace,
                            "id_partido": id_partido_sel,
                        }).execute()

                        # Si es individual, guardamos también los accesos concedidos
                        if categoria_sel == "Individual" and insert_resp.data:
                            id_informe_nuevo = insert_resp.data[0]["id_informe"]
                            filas_acceso = [
                                {"id_informe": id_informe_nuevo, "id_jugador": id_j}
                                for id_j in jugadores_acceso_sel
                            ]
                            supabase.table("informes_acceso").insert(filas_acceso).execute()

                        st.success("✅ ¡Informe registrado con éxito!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

# ============================================================
# PESTAÑA 3: GESTIONAR PARTIDOS (solo Admin)
# ============================================================
if tab_partidos is not None:
    with tab_partidos:
        st.markdown("#### Crear un nuevo partido")
        with st.form("form_nuevo_partido", clear_on_submit=True):
            c1, c2 = st.columns(2)
            fecha_partido = c1.date_input("Fecha del partido", value=date.today())
            rival = c2.text_input("Rival")

            c3, c4 = st.columns(2)
            competicion = c3.text_input("Competición")
            condicion = c4.selectbox("Condición", ["Local", "Visitante"])

            if st.form_submit_button("💾 Crear partido", type="primary"):
                if not rival or not competicion:
                    st.warning("⚠️ Rival y competición son obligatorios.")
                else:
                    try:
                        supabase.table("partidos").insert({
                            "fecha": str(fecha_partido),
                            "rival": rival,
                            "competicion": competicion,
                            "condicion": condicion,
                        }).execute()
                        st.success("✅ Partido creado correctamente.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al crear el partido: {e}")

        st.markdown("---")
        st.markdown("#### Partidos existentes")
        if partidos:
            st.dataframe(partidos, width='stretch')
        else:
            st.info("Todavía no hay partidos creados.")
