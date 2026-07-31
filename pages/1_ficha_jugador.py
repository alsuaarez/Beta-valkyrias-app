import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date

from utils.config import (
    init_connection, init_admin_connection, aplicar_estilos, requiere_sesion, es_staff,
    color_posicion, badge_html, calcular_edad, generar_password_temporal, subir_foto_jugador,
    COLOR_PRIMARIO, COLOR_SECUNDARIO,
)

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(page_title="Perfil del jugador", page_icon="👤", layout="wide")
aplicar_estilos()
supabase = init_connection()
supabase_admin = init_admin_connection()

requiere_sesion()

if "jugador_seleccionado" not in st.session_state:
    st.warning("No has seleccionado a ningún jugador. Por favor, vuelve a la Plantilla.")
    st.page_link("app.py", label="Volver a la plantilla", icon="⬅️")
    st.stop()

id_jugador = st.session_state["jugador_seleccionado"]
puede_editar = es_staff()               # Admin y Técnico: registrar tests y estadísticas
puede_editar_perfil = st.session_state.get("rol") == "Admin"  # Solo Admin: editar/eliminar ficha


@st.cache_data(ttl=30)
def cargar_jugador(id_jugador):
    r = supabase.table("jugadores").select("*").eq("id_jugador", id_jugador).execute()
    return r.data[0] if r.data else None


jugador = cargar_jugador(id_jugador)

if not jugador:
    st.error("No se ha podido cargar la información de este jugador.")
    st.stop()

nombre_jugador = jugador.get("nombre", "Jugador")
posicion = jugador.get("posicion", "")
edad = calcular_edad(jugador.get("fecha_nacimiento"))

# ============================================================
# CABECERA DE PERFIL
# ============================================================
foto = jugador.get("url_foto") or "https://placehold.co/240x240?text=%20"

col_foto, col_datos = st.columns([1, 4])
with col_foto:
    st.image(foto, width=160)

with col_datos:
    st.markdown(
        f"""
        <h1 style='margin-bottom:4px;'>{nombre_jugador}</h1>
        <div style='margin-bottom:10px;'>{badge_html(posicion, color_posicion(posicion))}
        &nbsp;&nbsp;<span style='color:#5A6472;'>Dorsal #{jugador.get("dorsal", "-")}</span></div>
        """,
        unsafe_allow_html=True,
    )
    info_cols = st.columns(4)
    info_cols[0].metric("Edad", f"{edad} años" if edad is not None else "—")
    info_cols[1].metric("Nacionalidad", jugador.get("nacionalidad") or "—")
    info_cols[2].metric("Altura", f'{jugador["altura_cm"]} cm' if jugador.get("altura_cm") else "—")
    info_cols[3].metric("Pie dominante", jugador.get("pie_dominante") or "—")

st.markdown("---")

# ============================================================
# PESTAÑAS
# ============================================================
nombres_tabs = ["📈 Rendimiento físico", "⚽ Estadísticas de partido"]
if puede_editar_perfil:
    nombres_tabs.append("✏️ Editar ficha")

tabs = st.tabs(nombres_tabs)
tab_fisico, tab_partidos = tabs[0], tabs[1]
tab_editar = tabs[2] if puede_editar_perfil else None

# ============================================================
# PESTAÑA 1: RENDIMIENTO FÍSICO
# ============================================================
with tab_fisico:
    columnas_disponibles = {
        "Peso (kg)": "peso_kg",
        "Salto (cm)": "salto_cm",
        "Velocidad 10m (s)": "velocidad_10m_s",
        "Velocidad 30m (s)": "velocidad_30m_s",
        "Cambio de Ritmo (s)": "cambio_ritmo_s",
    }

    c_sel, c_add = st.columns([3, 1])
    with c_sel:
        metricas_seleccionadas = st.multiselect(
            "Métricas a visualizar",
            options=list(columnas_disponibles.keys()),
            default=["Peso (kg)"],
        )

    response = (
        supabase.table("tests_fisicos")
        .select("*")
        .eq("id_jugador", id_jugador)
        .order("fecha_test")
        .execute()
    )
    datos_tests = response.data

    if datos_tests:
        df = pd.DataFrame(datos_tests)
        df["fecha_test"] = pd.to_datetime(df["fecha_test"])
        # Orden cronológico ascendente: lo más antiguo a la izquierda, lo más
        # reciente a la derecha (nunca al revés, aunque cambie el orden de Supabase)
        df.sort_values("fecha_test", ascending=True, inplace=True)

        if metricas_seleccionadas:
            st.markdown("#### Evolución del jugador")
            for metrica in metricas_seleccionadas:
                columna_real = columnas_disponibles[metrica]
                if columna_real not in df.columns:
                    continue
                serie = df[["fecha_test", columna_real]].dropna()
                if serie.empty:
                    continue

                valor_inicial = serie[columna_real].iloc[0]
                valor_final = serie[columna_real].iloc[-1]
                variacion = valor_final - valor_inicial

                with st.container(border=True):
                    c_titulo, c_delta = st.columns([3, 1])
                    c_titulo.markdown(f"**{metrica}**")
                    c_delta.metric("Último valor", f"{valor_final:g}", delta=f"{variacion:+.2f}")

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=serie["fecha_test"], y=serie[columna_real],
                        mode="lines+markers",
                        line=dict(color=COLOR_PRIMARIO, width=3),
                        marker=dict(color=COLOR_SECUNDARIO, size=8),
                        fill="tozeroy",
                        fillcolor="rgba(11,31,58,0.06)",
                    ))
                    fig.update_layout(
                        height=230,
                        margin=dict(l=10, r=10, t=10, b=10),
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                        xaxis=dict(showgrid=False, autorange=True, type="date"),
                        yaxis=dict(showgrid=True, gridcolor="#EEF1F5"),
                    )
                    st.plotly_chart(fig, width='stretch')

            with st.expander("Ver tabla de datos crudos"):
                columnas_reales = [columnas_disponibles[m] for m in metricas_seleccionadas]
                st.dataframe(df[["fecha_test"] + columnas_reales], width='stretch')
        else:
            st.warning("Selecciona al menos una métrica para visualizar la gráfica.")
    else:
        st.info("No hay registros de tests físicos para este jugador todavía.")

    # -------- Alta de un nuevo test físico (solo staff) --------
    if puede_editar:
        with st.expander("➕ Registrar nuevo test físico"):
            with st.form("form_nuevo_test", clear_on_submit=True):
                fecha_test = st.date_input("Fecha del test", value=date.today())
                c1, c2, c3 = st.columns(3)
                peso = c1.number_input("Peso (kg)", min_value=0.0, step=0.1, format="%.1f")
                salto = c2.number_input("Salto (cm)", min_value=0.0, step=0.5, format="%.1f")
                vel10 = c3.number_input("Velocidad 10m (s)", min_value=0.0, step=0.01, format="%.2f")
                c4, c5 = st.columns(2)
                vel30 = c4.number_input("Velocidad 30m (s)", min_value=0.0, step=0.01, format="%.2f")
                cambio_ritmo = c5.number_input("Cambio de ritmo (s)", min_value=0.0, step=0.01, format="%.2f")

                if st.form_submit_button("Guardar test", type="primary"):
                    try:
                        supabase.table("tests_fisicos").insert({
                            "id_jugador": id_jugador,
                            "fecha_test": str(fecha_test),
                            "peso_kg": peso or None,
                            "salto_cm": salto or None,
                            "velocidad_10m_s": vel10 or None,
                            "velocidad_30m_s": vel30 or None,
                            "cambio_ritmo_s": cambio_ritmo or None,
                        }).execute()
                        st.success("✅ Test guardado correctamente.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar el test: {e}")

# ============================================================
# PESTAÑA 2: ESTADÍSTICAS DE PARTIDO
# ============================================================
with tab_partidos:
    response = (
        supabase.table("estadisticas_partidos")
        .select("*, partidos(fecha, rival, competicion, condicion)")
        .eq("id_jugador", id_jugador)
        .execute()
    )
    datos_partidos = response.data

    if datos_partidos:
        lista_plana = []
        for row in datos_partidos:
            partido_info = row.get("partidos") or {}
            lista_plana.append({
                "ID Partido": row["id_partido"],
                "Fecha": partido_info.get("fecha", ""),
                "Rival": partido_info.get("rival", ""),
                "Competición": partido_info.get("competicion", ""),
                "Condición": partido_info.get("condicion", ""),
                "Minutos": row["minutos_jugados"],
                "Goles": row["goles"],
                "Asistencias": row["asistencias"],
                "Amarillas": row["tarjetas_amarillas"],
            })

        df_partidos = pd.DataFrame(lista_plana).sort_values("Fecha", ascending=False)

        st.markdown("#### Acumulado total")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Minutos jugados", int(df_partidos["Minutos"].sum()))
        col2.metric("Goles", int(df_partidos["Goles"].sum()))
        col3.metric("Asistencias", int(df_partidos["Asistencias"].sum()))
        col4.metric("Tarjetas amarillas", int(df_partidos["Amarillas"].sum()))

        st.markdown("---")
        st.markdown("#### Análisis individual por partido")

        opciones_partidos = df_partidos.apply(
            lambda x: f"{x['Competición']} | {x['Fecha']} vs {x['Rival']}", axis=1
        ).tolist()

        partido_seleccionado = st.selectbox(
            "Selecciona un partido para ver los datos específicos:",
            options=opciones_partidos,
        )

        if partido_seleccionado:
            idx_seleccion = opciones_partidos.index(partido_seleccionado)
            datos_partido_elegido = df_partidos.iloc[idx_seleccion]

            st.info(f"Condición: jugó como **{datos_partido_elegido['Condición']}**")

            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Minutos", int(datos_partido_elegido["Minutos"]))
            col_b.metric("Goles", int(datos_partido_elegido["Goles"]))
            col_c.metric("Asistencias", int(datos_partido_elegido["Asistencias"]))
            col_d.metric("Amarillas", int(datos_partido_elegido["Amarillas"]))

        with st.expander("Ver tabla completa de registros"):
            st.dataframe(df_partidos, width='stretch')
    else:
        st.info("No hay registros de partidos para este jugador todavía.")

    # -------- Alta de estadísticas de un partido (solo staff) --------
    if puede_editar:
        with st.expander("➕ Registrar estadísticas de un partido"):
            st.caption(
                "Si el partido ya existe en la tabla `partidos`, indica su ID. "
                "Si no existe todavía, créalo primero en tu gestor de partidos "
                "(o pídeme que te añada esa pantalla) y luego vuelve aquí a asociar al jugador."
            )
            with st.form("form_stats_partido", clear_on_submit=True):
                id_partido = st.number_input("ID del partido", min_value=1, step=1)
                c1, c2, c3, c4 = st.columns(4)
                minutos = c1.number_input("Minutos jugados", min_value=0, max_value=120, step=1)
                goles = c2.number_input("Goles", min_value=0, step=1)
                asistencias = c3.number_input("Asistencias", min_value=0, step=1)
                amarillas = c4.number_input("Amarillas", min_value=0, max_value=2, step=1)

                if st.form_submit_button("Guardar estadísticas", type="primary"):
                    try:
                        supabase.table("estadisticas_partidos").insert({
                            "id_jugador": id_jugador,
                            "id_partido": int(id_partido),
                            "minutos_jugados": int(minutos),
                            "goles": int(goles),
                            "asistencias": int(asistencias),
                            "tarjetas_amarillas": int(amarillas),
                        }).execute()
                        st.success("✅ Estadísticas guardadas correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar las estadísticas: {e}")

# ============================================================
# PESTAÑA 3: EDITAR FICHA (solo Admin / Técnico)
# ============================================================
if tab_editar is not None:
    with tab_editar:
        st.markdown("#### Datos personales y deportivos")
        with st.form("form_editar_jugador"):
            c1, c2 = st.columns(2)
            nombre_edit = c1.text_input("Nombre completo", value=jugador.get("nombre", ""))
            dorsal_edit = c2.number_input(
                "Dorsal", min_value=0, max_value=99, step=1,
                value=int(jugador.get("dorsal") or 0),
            )

            c3, c4 = st.columns(2)
            posicion_edit = c3.selectbox(
                "Posición",
                ["Portero", "Defensa", "Centrocampista", "Delantero"],
                index=["Portero", "Defensa", "Centrocampista", "Delantero"].index(posicion)
                if posicion in ["Portero", "Defensa", "Centrocampista", "Delantero"] else 0,
            )
            pie_edit = c4.selectbox(
                "Pie dominante", ["Derecho", "Izquierdo", "Ambidiestro"],
                index=["Derecho", "Izquierdo", "Ambidiestro"].index(jugador["pie_dominante"])
                if jugador.get("pie_dominante") in ["Derecho", "Izquierdo", "Ambidiestro"] else 0,
            )

            c5, c6 = st.columns(2)
            fecha_nac_actual = jugador.get("fecha_nacimiento")
            try:
                valor_fecha = date.fromisoformat(fecha_nac_actual[:10]) if fecha_nac_actual else date(2005, 1, 1)
            except Exception:
                valor_fecha = date(2005, 1, 1)
            fecha_nac_edit = c5.date_input("Fecha de nacimiento", value=valor_fecha)
            nacionalidad_edit = c6.text_input("Nacionalidad", value=jugador.get("nacionalidad", "") or "")

            c7, c8 = st.columns(2)
            altura_edit = c7.number_input(
                "Altura (cm)", min_value=0, max_value=230, step=1,
                value=int(jugador.get("altura_cm") or 0),
            )
            with c8:
                foto_archivo_edit = st.file_uploader(
                    "Cambiar foto", type=["jpg", "jpeg", "png", "webp"],
                    help="Se sube automáticamente a Supabase Storage. Si no subes nada, se mantiene la foto actual.",
                )
            foto_edit = st.text_input(
                "…o pega una URL de foto (opcional, solo si no subes archivo)",
                value=jugador.get("url_foto", "") or "",
            )

            guardar = st.form_submit_button("💾 Guardar cambios", type="primary")

            if guardar:
                try:
                    url_foto_final = foto_edit
                    if foto_archivo_edit is not None:
                        try:
                            url_foto_final = subir_foto_jugador(
                                supabase, id_jugador, foto_archivo_edit, supabase_admin
                            )
                        except Exception as e:
                            st.warning(
                                f"No se pudo subir la nueva foto: {e}. Se mantiene la anterior. "
                                f"Comprueba que el bucket 'fotos-jugadores' existe y es público."
                            )
                            url_foto_final = jugador.get("url_foto", "")

                    supabase.table("jugadores").update({
                        "nombre": nombre_edit,
                        "dorsal": int(dorsal_edit),
                        "posicion": posicion_edit,
                        "pie_dominante": pie_edit,
                        "fecha_nacimiento": str(fecha_nac_edit),
                        "nacionalidad": nacionalidad_edit,
                        "altura_cm": int(altura_edit) if altura_edit else None,
                        "url_foto": url_foto_final,
                    }).eq("id_jugador", id_jugador).execute()
                    st.success("✅ Ficha actualizada correctamente.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al actualizar la ficha: {e}")

        st.markdown("---")
        st.markdown("#### Cuenta de acceso")

        if supabase_admin is None:
            st.warning(
                "⚠️ Falta configurar `SUPABASE_SERVICE_KEY` en tu `.env` para poder "
                "crear usuarios o resetear contraseñas desde aquí."
            )
        else:
            usuario_resp = (
                supabase.table("usuarios_roles")
                .select("*")
                .eq("id_jugador", id_jugador)
                .execute()
            )
            usuario_existente = usuario_resp.data[0] if usuario_resp.data else None

            if usuario_existente:
                st.success(f"Este jugador ya tiene acceso con el correo **{usuario_existente['correo']}**.")
                if st.button("🔑 Generar nueva contraseña temporal"):
                    try:
                        nueva_password = generar_password_temporal()
                        supabase_admin.auth.admin.update_user_by_id(
                            usuario_existente["auth_user_id"],
                            {"password": nueva_password},
                        )
                        st.info(
                            f"Nueva contraseña temporal para **{usuario_existente['correo']}**:\n\n"
                            f"`{nueva_password}`\n\n"
                            "Compártela con el jugador de forma segura."
                        )
                    except Exception as e:
                        st.error(f"Error al restablecer la contraseña: {e}")
            else:
                st.info("Este jugador todavía no tiene cuenta de acceso.")
                with st.form("form_crear_usuario_jugador"):
                    email_nuevo = st.text_input("Correo electrónico de acceso")
                    if st.form_submit_button("Crear cuenta de acceso"):
                        if not email_nuevo:
                            st.warning("⚠️ Indica un correo electrónico.")
                        else:
                            try:
                                password_temporal = generar_password_temporal()
                                usuario_auth = supabase_admin.auth.admin.create_user({
                                    "email": email_nuevo,
                                    "password": password_temporal,
                                    "email_confirm": True,
                                })
                                supabase.table("usuarios_roles").insert({
                                    "correo": email_nuevo,
                                    "rol": "Jugador",
                                    "id_jugador": id_jugador,
                                    "auth_user_id": usuario_auth.user.id,
                                }).execute()
                                st.success(
                                    f"✅ Cuenta creada. Contraseña temporal: `{password_temporal}`"
                                )
                            except Exception as e:
                                st.error(f"Error al crear la cuenta: {e}")

        st.markdown("---")
        with st.expander("🗑️ Eliminar jugador", expanded=False):
            st.warning(
                "Esta acción borra al jugador de la plantilla. Los tests físicos y "
                "estadísticas de partido asociados no se eliminan automáticamente."
            )
            confirmar = st.checkbox("Confirmo que quiero eliminar a este jugador")
            if st.button("Eliminar definitivamente", disabled=not confirmar):
                try:
                    supabase.table("jugadores").delete().eq("id_jugador", id_jugador).execute()
                    st.success("Jugador eliminado.")
                    del st.session_state["jugador_seleccionado"]
                    st.switch_page("app.py")
                except Exception as e:
                    st.error(f"Error al eliminar: {e}")
