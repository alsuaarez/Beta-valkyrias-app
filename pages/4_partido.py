import streamlit as st
import uuid

from utils.config import (
    init_connection, aplicar_estilos, requiere_sesion, cabecera,
    FORMACIONES, COLOR_SECUNDARIO, renderizar_html,
)

# ============================================================
# CONFIGURACIÓN Y SEGURIDAD
# ============================================================
st.set_page_config(page_title="Partido", page_icon="🧩", layout="wide")
aplicar_estilos()
supabase = init_connection()
requiere_sesion()

if st.session_state.get("rol") not in ("Admin", "Tecnico"):
    st.error("🚫 Acceso denegado. Esta sección es solo para Admin y Técnico.")
    st.stop()

cabecera("Partido", "Convocatoria y pizarra táctica", icono="🧩")


# ============================================================
# DATOS COMPARTIDOS
# ============================================================
@st.cache_data(ttl=15)
def cargar_partidos():
    r = supabase.table("partidos").select("*").order("fecha", desc=True).execute()
    return r.data or []


@st.cache_data(ttl=15)
def cargar_plantilla():
    r = (
        supabase.table("jugadores")
        .select("id_jugador, nombre, dorsal, posicion, url_foto")
        .order("dorsal")
        .execute()
    )
    return r.data or []


def etiqueta_partido(p):
    return f"{p.get('fecha', '')} · {p.get('competicion', '')} vs {p.get('rival', '')}"


partidos = cargar_partidos()
if not partidos:
    st.info(
        "Todavía no hay ningún partido creado. Ve a Informes → "
        "🗓️ Gestionar Partidos para crear el primero."
    )
    st.page_link("pages/2_informes.py", label="Ir a Gestionar Partidos", icon="🗓️")
    st.stop()

mapa_partidos = {p["id_partido"]: etiqueta_partido(p) for p in partidos}
id_partido_sel = st.selectbox(
    "Selecciona el partido",
    list(mapa_partidos.keys()),
    format_func=lambda x: mapa_partidos[x],
)

plantilla = cargar_plantilla()
mapa_jugadores = {j["id_jugador"]: j for j in plantilla}

tab_convocatoria, tab_estrategia = st.tabs(["📋 Convocatoria", "🎯 Estrategia"])


# ============================================================
# HELPERS DE DIBUJO (HTML/CSS + SVG, sin dependencias externas)
# ============================================================
def render_campo_convocatoria(slots, asignaciones):
    marcas = ""
    for slot in slots:
        j_id = asignaciones.get(slot["clave"])
        if j_id and j_id in mapa_jugadores:
            jugador = mapa_jugadores[j_id]
            foto = jugador.get("url_foto") or "https://placehold.co/60x60?text=%20"
            nombre_corto = jugador["nombre"].split()[0]
            contenido = f"""
                <img src="{foto}" style="width:40px;height:40px;border-radius:50%;
                    border:2px solid white;object-fit:cover;box-shadow:0 2px 6px rgba(0,0,0,.4);">
                <div style="font-size:0.65rem;color:white;font-weight:700;
                    text-shadow:0 1px 3px rgba(0,0,0,.8);white-space:nowrap;">{nombre_corto}</div>
            """
        else:
            contenido = f"""
                <div style="width:40px;height:40px;border-radius:50%;
                    border:2px dashed rgba(255,255,255,.65);"></div>
                <div style="font-size:0.6rem;color:rgba(255,255,255,.85);white-space:nowrap;">{slot['etiqueta']}</div>
            """
        marcas += f"""
        <div style="position:absolute; left:{slot['x']}%; top:{slot['y']}%;
            transform:translate(-50%,-50%); text-align:center;">
            {contenido}
        </div>"""

    return f"""
    <div style="position:relative; width:100%; padding-top:135%;
        background: repeating-linear-gradient(0deg, #2E7D46, #2E7D46 10%, #33884C 10%, #33884C 20%);
        border-radius:14px; border:3px solid white; overflow:hidden;
        box-shadow:0 4px 16px rgba(0,0,0,.15);">
        <div style="position:absolute; top:4%; left:8%; right:8%; bottom:4%;
            border:2px solid rgba(255,255,255,.55); border-radius:6px;"></div>
        <div style="position:absolute; top:0; left:0; right:0; bottom:0;">
            {marcas}
        </div>
    </div>
    """


def render_media_pitch(elementos):
    flechas_svg = ""
    for e in elementos:
        if e["tipo"] == "flecha":
            flechas_svg += (
                f"<line x1='{e['x1']}' y1='{e['y1']}' x2='{e['x2']}' y2='{e['y2']}' "
                f"stroke='{COLOR_SECUNDARIO}' stroke-width='0.9' marker-end='url(#punta)' />"
            )

    marcas_html = ""
    for e in elementos:
        if e["tipo"] == "jugador":
            j = mapa_jugadores.get(e.get("id_jugador"))
            foto = (j.get("url_foto") if j else None) or "https://placehold.co/50x50?text=%20"
            nombre = j["nombre"].split()[0] if j else "?"
            marcas_html += f"""
            <div style="position:absolute;left:{e['x']}%;top:{e['y']}%;transform:translate(-50%,-50%);text-align:center;">
                <img src="{foto}" style="width:36px;height:36px;border-radius:50%;
                    border:2px solid #2E86DE;object-fit:cover;box-shadow:0 2px 6px rgba(0,0,0,.4);">
                <div style="font-size:0.6rem;color:white;font-weight:700;text-shadow:0 1px 3px rgba(0,0,0,.8);">{nombre}</div>
            </div>"""
        elif e["tipo"] == "rival":
            marcas_html += f"""
            <div style="position:absolute;left:{e['x']}%;top:{e['y']}%;transform:translate(-50%,-50%);
                width:30px;height:30px;border-radius:50%;background:#E74C3C;color:white;
                display:flex;align-items:center;justify-content:center;font-weight:700;
                font-size:0.7rem;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,.4);">{e.get('etiqueta','R')}</div>"""
        elif e["tipo"] == "balon":
            marcas_html += f"""
            <div style="position:absolute;left:{e['x']}%;top:{e['y']}%;transform:translate(-50%,-50%);font-size:1.4rem;">⚽</div>"""

    return f"""
    <div style="position:relative; width:100%; padding-top:65%;
        background: repeating-linear-gradient(0deg, #2E7D46, #2E7D46 10%, #33884C 10%, #33884C 20%);
        border-radius:14px; border:3px solid white; overflow:hidden;
        box-shadow:0 4px 16px rgba(0,0,0,.15);">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none"
            style="position:absolute;top:0;left:0;width:100%;height:100%;">
            <defs>
                <marker id="punta" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                    <path d="M0,0 L6,3 L0,6 Z" fill="{COLOR_SECUNDARIO}"/>
                </marker>
            </defs>
            <circle cx="50" cy="100" r="16" fill="none" stroke="rgba(255,255,255,.5)" stroke-width="0.6"/>
            {flechas_svg}
        </svg>
        <div style="position:absolute;top:0;left:0;right:0;bottom:0;">
            {marcas_html}
        </div>
    </div>
    """


def descripcion_elemento(e):
    if e["tipo"] == "jugador":
        j = mapa_jugadores.get(e.get("id_jugador"))
        return f"🔵 {j['nombre'] if j else 'Jugador'}"
    if e["tipo"] == "rival":
        return f"🔴 Rival ({e.get('etiqueta', 'R')})"
    if e["tipo"] == "balon":
        return "⚽ Balón"
    if e["tipo"] == "flecha":
        return "➡️ Flecha de movimiento"
    return "Elemento"


# ============================================================
# PESTAÑA 1: CONVOCATORIA
# ============================================================
with tab_convocatoria:

    @st.cache_data(ttl=10)
    def cargar_convocatoria(id_partido):
        r = (
            supabase.table("convocatorias")
            .select("*, convocatoria_jugadores(*)")
            .eq("id_partido", id_partido)
            .execute()
        )
        return r.data[0] if r.data else None

    convocatoria_actual = cargar_convocatoria(id_partido_sel)

    lista_formaciones = list(FORMACIONES.keys())
    formacion_previa = convocatoria_actual["formacion"] if convocatoria_actual else lista_formaciones[0]
    idx_formacion = lista_formaciones.index(formacion_previa) if formacion_previa in lista_formaciones else 0

    formacion_sel = st.selectbox("Formación", lista_formaciones, index=idx_formacion)
    slots = FORMACIONES[formacion_sel]

    # Estado en sesión: se recarga desde la BBDD si cambias de partido o de formación
    state_key = f"conv_{id_partido_sel}_{formacion_sel}"
    if state_key not in st.session_state:
        asign = {}
        suplentes_prev = []
        if convocatoria_actual and convocatoria_actual["formacion"] == formacion_sel:
            for row in convocatoria_actual.get("convocatoria_jugadores", []):
                if row["rol"] == "Titular":
                    asign[row["slot_posicion"]] = row["id_jugador"]
                else:
                    suplentes_prev.append(row["id_jugador"])
        st.session_state[state_key] = {"titulares": asign, "suplentes": suplentes_prev}

    estado_conv = st.session_state[state_key]
    asignaciones = estado_conv["titulares"]

    st.markdown("#### Once inicial")
    col_pitch, col_form = st.columns([1.2, 1])

    with col_form:
        for slot in slots:
            clave, etiqueta = slot["clave"], slot["etiqueta"]
            usados_en_otros_slots = {
                v for k, v in asignaciones.items() if k != clave
            }
            opciones = [None] + [
                j["id_jugador"] for j in plantilla if j["id_jugador"] not in usados_en_otros_slots
            ]
            valor_actual = asignaciones.get(clave)
            idx = opciones.index(valor_actual) if valor_actual in opciones else 0

            seleccion = st.selectbox(
                etiqueta,
                opciones,
                index=idx,
                format_func=lambda x: "—" if x is None else mapa_jugadores[x]["nombre"],
                key=f"{state_key}_slot_{clave}",
            )
            if seleccion is not None:
                asignaciones[clave] = seleccion
            elif clave in asignaciones:
                del asignaciones[clave]

    with col_pitch:
        renderizar_html(render_campo_convocatoria(slots, asignaciones))
        st.caption(f"{len(asignaciones)}/11 posiciones asignadas")

    st.markdown("#### Banquillo (máximo 6)")
    disponibles_banquillo = [
        j["id_jugador"] for j in plantilla if j["id_jugador"] not in asignaciones.values()
    ]
    suplentes_validos = [s for s in estado_conv["suplentes"] if s in disponibles_banquillo]

    suplentes_sel = st.multiselect(
        "Selecciona hasta 6 suplentes",
        options=disponibles_banquillo,
        default=suplentes_validos,
        format_func=lambda x: mapa_jugadores[x]["nombre"],
        max_selections=6,
        key=f"{state_key}_banquillo",
    )
    estado_conv["suplentes"] = suplentes_sel

    st.markdown("---")
    if st.button("💾 Guardar convocatoria", type="primary"):
        if len(asignaciones) < 11:
            st.warning(f"Has asignado {len(asignaciones)}/11 posiciones. Completa el once antes de guardar.")
        else:
            try:
                if convocatoria_actual:
                    id_conv = convocatoria_actual["id_convocatoria"]
                    supabase.table("convocatorias").update({"formacion": formacion_sel}).eq(
                        "id_convocatoria", id_conv
                    ).execute()
                    supabase.table("convocatoria_jugadores").delete().eq(
                        "id_convocatoria", id_conv
                    ).execute()
                else:
                    insert_resp = (
                        supabase.table("convocatorias")
                        .insert({"id_partido": id_partido_sel, "formacion": formacion_sel})
                        .execute()
                    )
                    id_conv = insert_resp.data[0]["id_convocatoria"]

                filas = [
                    {
                        "id_convocatoria": id_conv,
                        "id_jugador": id_j,
                        "rol": "Titular",
                        "slot_posicion": slot_clave,
                    }
                    for slot_clave, id_j in asignaciones.items()
                ] + [
                    {
                        "id_convocatoria": id_conv,
                        "id_jugador": id_j,
                        "rol": "Suplente",
                        "slot_posicion": None,
                    }
                    for id_j in suplentes_sel
                ]
                if filas:
                    supabase.table("convocatoria_jugadores").insert(filas).execute()

                st.success("✅ Convocatoria guardada correctamente para este partido.")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Error al guardar la convocatoria: {e}")

# ============================================================
# PESTAÑA 2: ESTRATEGIA
# ============================================================
with tab_estrategia:

    convocatoria_actual = cargar_convocatoria(id_partido_sel)
    titulares_ids = []
    if convocatoria_actual:
        titulares_ids = [
            row["id_jugador"]
            for row in convocatoria_actual.get("convocatoria_jugadores", [])
            if row["rol"] == "Titular"
        ]

    if len(titulares_ids) < 11:
        st.info(
            "Primero completa y guarda el **Once inicial** de este partido en la "
            "pestaña Convocatoria. La pizarra táctica solo puede usar a los "
            "jugadores que juegan de inicio en este partido concreto."
        )
    else:

        @st.cache_data(ttl=10)
        def cargar_pizarras(id_partido):
            r = (
                supabase.table("pizarras_tacticas")
                .select("*")
                .eq("id_partido", id_partido)
                .order("creado_en", desc=True)
                .execute()
            )
            return r.data or []

        pizarras = cargar_pizarras(id_partido_sel)

        opciones_pizarra = ["➕ Nueva pizarra"] + [p["id_pizarra"] for p in pizarras]
        pizarra_elegida = st.selectbox(
            "Pizarra de este partido",
            opciones_pizarra,
            format_func=lambda x: "➕ Nueva pizarra"
            if x == "➕ Nueva pizarra"
            else next(p["nombre"] for p in pizarras if p["id_pizarra"] == x),
        )

        editor_key = f"pizarra_{id_partido_sel}_{pizarra_elegida}"

        if editor_key not in st.session_state and pizarra_elegida == "➕ Nueva pizarra":
            st.markdown("##### ¿Cómo quieres empezar esta pizarra?")
            origen = st.radio(
                "Origen de la pizarra",
                ["Empezar desde cero", "Duplicar una pizarra ya existente"],
                key=f"origen_{editor_key}",
                horizontal=True,
                label_visibility="collapsed",
            )

            if origen == "Empezar desde cero":
                st.session_state[editor_key] = {"nombre": "", "elementos": []}

            else:
                todas_resp = (
                    supabase.table("pizarras_tacticas")
                    .select("*, partidos(fecha, rival, competicion)")
                    .order("creado_en", desc=True)
                    .execute()
                )
                todas_pizarras = todas_resp.data or []

                if not todas_pizarras:
                    st.info("Todavía no hay ninguna otra pizarra creada para duplicar.")
                    if st.button("Empezar desde cero de todas formas"):
                        st.session_state[editor_key] = {"nombre": "", "elementos": []}
                        st.rerun()
                    st.stop()
                else:
                    opciones_origen = {
                        p["id_pizarra"]: (
                            f"{p['nombre']} · {p['partidos']['fecha']} vs {p['partidos']['rival']}"
                        )
                        for p in todas_pizarras
                    }
                    id_origen = st.selectbox(
                        "Selecciona la pizarra que quieres duplicar",
                        list(opciones_origen.keys()),
                        format_func=lambda x: opciones_origen[x],
                    )
                    st.caption(
                        "Se copiará el dibujo (posiciones, marcas rivales, balón y flechas). "
                        "Los círculos de jugador propio quedarán sin asignar, para que elijas "
                        "quién ocupa cada uno según el once de este partido."
                    )
                    if st.button("📋 Duplicar esta pizarra", type="primary"):
                        origen_pizarra = next(p for p in todas_pizarras if p["id_pizarra"] == id_origen)
                        elementos_copiados = []
                        for e in (origen_pizarra["elementos_json"] or []):
                            nuevo = dict(e)
                            nuevo["id"] = uuid.uuid4().hex
                            if nuevo["tipo"] == "jugador":
                                nuevo["id_jugador"] = None
                            elementos_copiados.append(nuevo)
                        st.session_state[editor_key] = {
                            "nombre": f"{origen_pizarra['nombre']} (copia)",
                            "elementos": elementos_copiados,
                        }
                        st.rerun()
                    st.stop()

        elif editor_key not in st.session_state:
            p = next(p for p in pizarras if p["id_pizarra"] == pizarra_elegida)
            st.session_state[editor_key] = {
                "nombre": p["nombre"],
                "elementos": p["elementos_json"] or [],
            }

        estado = st.session_state[editor_key]

        estado["nombre"] = st.text_input(
            "Nombre de la pizarra", value=estado["nombre"], placeholder="Ej. Saque de esquina"
        )

        col_pizarra, col_controles = st.columns([1.2, 1])

        with col_controles:
            st.markdown("##### Añadir elemento")
            tipo_elem = st.selectbox(
                "Tipo de elemento", ["Jugador propio", "Marca rival", "Balón", "Flecha de movimiento"]
            )

            if tipo_elem == "Jugador propio":
                usados = {
                    e["id_jugador"] for e in estado["elementos"]
                    if e["tipo"] == "jugador" and e.get("id_jugador")
                }
                disponibles = [tid for tid in titulares_ids if tid not in usados]
                if disponibles:
                    jugador_elem = st.selectbox(
                        "Jugador", disponibles, format_func=lambda x: mapa_jugadores[x]["nombre"]
                    )
                    x_j = st.slider("Posición horizontal", 0, 100, 50, key="x_jugador_nuevo")
                    y_j = st.slider("Posición vertical", 0, 100, 50, key="y_jugador_nuevo")
                    if st.button("➕ Añadir jugador a la pizarra"):
                        estado["elementos"].append(
                            {"id": uuid.uuid4().hex, "tipo": "jugador", "id_jugador": jugador_elem, "x": x_j, "y": y_j}
                        )
                        st.rerun()
                else:
                    st.caption("Ya has colocado a los 11 titulares en esta pizarra.")

            elif tipo_elem == "Marca rival":
                etiqueta_rival = st.text_input("Dorsal o etiqueta rival", value="R", max_chars=3)
                x_r = st.slider("Posición horizontal", 0, 100, 50, key="x_rival_nuevo")
                y_r = st.slider("Posición vertical", 0, 100, 50, key="y_rival_nuevo")
                if st.button("➕ Añadir marca rival"):
                    estado["elementos"].append(
                        {"id": uuid.uuid4().hex, "tipo": "rival", "etiqueta": etiqueta_rival, "x": x_r, "y": y_r}
                    )
                    st.rerun()

            elif tipo_elem == "Balón":
                x_b = st.slider("Posición horizontal", 0, 100, 50, key="x_balon_nuevo")
                y_b = st.slider("Posición vertical", 0, 100, 50, key="y_balon_nuevo")
                if st.button("⚽ Colocar balón"):
                    estado["elementos"] = [e for e in estado["elementos"] if e["tipo"] != "balon"]
                    estado["elementos"].append({"id": uuid.uuid4().hex, "tipo": "balon", "x": x_b, "y": y_b})
                    st.rerun()

            else:  # Flecha
                st.caption("Indica el origen y el destino del movimiento")
                cx1, cy1 = st.columns(2)
                x1 = cx1.slider("Origen X", 0, 100, 30, key="x1_flecha_nuevo")
                y1 = cy1.slider("Origen Y", 0, 100, 70, key="y1_flecha_nuevo")
                cx2, cy2 = st.columns(2)
                x2 = cx2.slider("Destino X", 0, 100, 60, key="x2_flecha_nuevo")
                y2 = cy2.slider("Destino Y", 0, 100, 30, key="y2_flecha_nuevo")
                if st.button("➡️ Añadir flecha"):
                    estado["elementos"].append(
                        {"id": uuid.uuid4().hex, "tipo": "flecha", "x1": x1, "y1": y1, "x2": x2, "y2": y2}
                    )
                    st.rerun()

            st.markdown("---")
            st.markdown("##### Elementos ya colocados")
            if not estado["elementos"]:
                st.caption("Todavía no has añadido nada a esta pizarra.")
            for elem in list(estado["elementos"]):
                with st.expander(descripcion_elemento(elem)):
                    if elem["tipo"] == "jugador":
                        usados_otros = {
                            e["id_jugador"] for e in estado["elementos"]
                            if e["tipo"] == "jugador" and e["id"] != elem["id"] and e.get("id_jugador")
                        }
                        opciones_j = [t for t in titulares_ids if t not in usados_otros]
                        nuevo_jugador = st.selectbox(
                            "Reasignar jugador", opciones_j,
                            index=opciones_j.index(elem["id_jugador"]) if elem["id_jugador"] in opciones_j else 0,
                            format_func=lambda x: mapa_jugadores[x]["nombre"],
                            key=f"edit_jugador_{elem['id']}",
                        )
                        nx = st.slider("X", 0, 100, int(elem["x"]), key=f"edit_x_{elem['id']}")
                        ny = st.slider("Y", 0, 100, int(elem["y"]), key=f"edit_y_{elem['id']}")
                        if st.button("Actualizar", key=f"upd_{elem['id']}"):
                            elem["id_jugador"], elem["x"], elem["y"] = nuevo_jugador, nx, ny
                            st.rerun()

                    elif elem["tipo"] == "rival":
                        nueva_etq = st.text_input(
                            "Etiqueta", value=elem.get("etiqueta", "R"), max_chars=3, key=f"edit_etq_{elem['id']}"
                        )
                        nx = st.slider("X", 0, 100, int(elem["x"]), key=f"edit_x_{elem['id']}")
                        ny = st.slider("Y", 0, 100, int(elem["y"]), key=f"edit_y_{elem['id']}")
                        if st.button("Actualizar", key=f"upd_{elem['id']}"):
                            elem["etiqueta"], elem["x"], elem["y"] = nueva_etq, nx, ny
                            st.rerun()

                    elif elem["tipo"] == "balon":
                        nx = st.slider("X", 0, 100, int(elem["x"]), key=f"edit_x_{elem['id']}")
                        ny = st.slider("Y", 0, 100, int(elem["y"]), key=f"edit_y_{elem['id']}")
                        if st.button("Actualizar", key=f"upd_{elem['id']}"):
                            elem["x"], elem["y"] = nx, ny
                            st.rerun()

                    else:  # flecha
                        cx1, cy1 = st.columns(2)
                        nx1 = cx1.slider("Origen X", 0, 100, int(elem["x1"]), key=f"edit_x1_{elem['id']}")
                        ny1 = cy1.slider("Origen Y", 0, 100, int(elem["y1"]), key=f"edit_y1_{elem['id']}")
                        cx2, cy2 = st.columns(2)
                        nx2 = cx2.slider("Destino X", 0, 100, int(elem["x2"]), key=f"edit_x2_{elem['id']}")
                        ny2 = cy2.slider("Destino Y", 0, 100, int(elem["y2"]), key=f"edit_y2_{elem['id']}")
                        if st.button("Actualizar", key=f"upd_{elem['id']}"):
                            elem["x1"], elem["y1"], elem["x2"], elem["y2"] = nx1, ny1, nx2, ny2
                            st.rerun()

                    if st.button("🗑️ Eliminar elemento", key=f"del_{elem['id']}"):
                        estado["elementos"] = [e for e in estado["elementos"] if e["id"] != elem["id"]]
                        st.rerun()

        with col_pizarra:
            renderizar_html(render_media_pitch(estado["elementos"]))

        st.markdown("---")
        if st.button("💾 Guardar pizarra", type="primary"):
            if not estado["nombre"]:
                st.warning("⚠️ Ponle un nombre a la pizarra antes de guardar.")
            else:
                try:
                    if pizarra_elegida == "➕ Nueva pizarra":
                        supabase.table("pizarras_tacticas").insert({
                            "id_partido": id_partido_sel,
                            "nombre": estado["nombre"],
                            "elementos_json": estado["elementos"],
                        }).execute()
                    else:
                        supabase.table("pizarras_tacticas").update({
                            "nombre": estado["nombre"],
                            "elementos_json": estado["elementos"],
                        }).eq("id_pizarra", pizarra_elegida).execute()

                    st.success("✅ Pizarra guardada correctamente.")
                    st.cache_data.clear()
                    del st.session_state[editor_key]
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar la pizarra: {e}")
