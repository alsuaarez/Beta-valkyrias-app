import streamlit as st
from datetime import date

from utils.config import init_connection, aplicar_estilos, requiere_sesion, cabecera

# ============================================================
# CONFIGURACIÓN Y SEGURIDAD
# ============================================================
st.set_page_config(page_title="Gestión de jugadores", page_icon="➕", layout="wide")
aplicar_estilos()
supabase = init_connection()

requiere_sesion()

if st.session_state.get("rol") != "Admin":
    st.error("🚫 Acceso denegado. Solo el perfil Admin puede dar de alta jugadores.")
    st.stop()

cabecera("Gestión de jugadores", "Da de alta nuevos futbolistas en la plantilla", icono="➕")

# ============================================================
# FORMULARIO DE ALTA
# ============================================================
with st.container(border=True):
    st.markdown("#### Nuevo jugador")
    with st.form("form_nuevo_jugador", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre completo *")
        dorsal = c2.number_input("Dorsal *", min_value=0, max_value=99, step=1)

        c3, c4 = st.columns(2)
        posicion = c3.selectbox("Posición *", ["Portero", "Defensa", "Centrocampista", "Delantero"])
        pie_dominante = c4.selectbox("Pie dominante", ["Derecho", "Izquierdo", "Ambidiestro"])

        c5, c6 = st.columns(2)
        fecha_nacimiento = c5.date_input("Fecha de nacimiento", value=date(2005, 1, 1))
        nacionalidad = c6.text_input("Nacionalidad")

        c7, c8 = st.columns(2)
        altura_cm = c7.number_input("Altura (cm)", min_value=0, max_value=230, step=1)
        url_foto = c8.text_input("URL de la foto", placeholder="https://…")

        btn_guardar = st.form_submit_button("💾 Dar de alta jugador", type="primary")

        if btn_guardar:
            if not nombre or dorsal is None or not posicion:
                st.warning("⚠️ El nombre, el dorsal y la posición son obligatorios.")
            else:
                try:
                    supabase.table("jugadores").insert({
                        "nombre": nombre,
                        "dorsal": int(dorsal),
                        "posicion": posicion,
                        "pie_dominante": pie_dominante,
                        "fecha_nacimiento": str(fecha_nacimiento),
                        "nacionalidad": nacionalidad or None,
                        "altura_cm": int(altura_cm) if altura_cm else None,
                        "url_foto": url_foto or None,
                    }).execute()
                    st.success(f"✅ {nombre} se ha añadido a la plantilla.")
                except Exception as e:
                    st.error(f"Error al guardar el jugador: {e}")

st.page_link("app.py", label="⬅️ Volver a la plantilla", icon=None)
