import streamlit as st
from datetime import date

from utils.config import (
    init_connection, init_admin_connection, aplicar_estilos, requiere_sesion,
    cabecera, generar_password_temporal, subir_foto_jugador,
)

# ============================================================
# CONFIGURACIÓN Y SEGURIDAD
# ============================================================
st.set_page_config(page_title="Gestión de jugadores", page_icon="➕", layout="wide")
aplicar_estilos()
supabase = init_connection()
supabase_admin = init_admin_connection()

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

    crear_usuario = st.checkbox(
        "Crear también su cuenta de acceso a la aplicación",
        value=True,
        help="Genera un usuario de inicio de sesión para que el jugador pueda "
             "entrar directamente a su perfil.",
    )
    if crear_usuario and supabase_admin is None:
        st.warning(
            "⚠️ No se puede crear la cuenta de acceso: falta configurar "
            "`SUPABASE_SERVICE_KEY` en tu `.env`. El jugador se dará de alta "
            "igualmente, pero sin usuario. La sección más abajo del proyecto "
            "explica cómo obtener esa clave."
        )

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
        with c8:
            foto_archivo = st.file_uploader(
                "Foto del jugador", type=["jpg", "jpeg", "png", "webp"],
                help="Se sube automáticamente a Supabase Storage.",
            )
        url_foto_manual = st.text_input(
            "…o pega una URL de foto (opcional, solo si no subes archivo)",
            placeholder="https://…",
        )

        st.markdown("---")
        email_acceso = st.text_input(
            "Correo electrónico de acceso (para su usuario)",
            placeholder="jugador@ejemplo.com",
            disabled=not crear_usuario,
        )

        btn_guardar = st.form_submit_button("💾 Dar de alta jugador", type="primary")

        if btn_guardar:
            if not nombre or dorsal is None or not posicion:
                st.warning("⚠️ El nombre, el dorsal y la posición son obligatorios.")
            elif crear_usuario and supabase_admin is not None and not email_acceso:
                st.warning("⚠️ Indica el correo electrónico para crear su cuenta de acceso.")
            else:
                try:
                    insert_resp = supabase.table("jugadores").insert({
                        "nombre": nombre,
                        "dorsal": int(dorsal),
                        "posicion": posicion,
                        "pie_dominante": pie_dominante,
                        "fecha_nacimiento": str(fecha_nacimiento),
                        "nacionalidad": nacionalidad or None,
                        "altura_cm": int(altura_cm) if altura_cm else None,
                        "url_foto": url_foto_manual or None,
                    }).execute()

                    id_jugador_nuevo = insert_resp.data[0]["id_jugador"]

                    if foto_archivo is not None:
                        try:
                            url_publica = subir_foto_jugador(
                                supabase, id_jugador_nuevo, foto_archivo, supabase_admin
                            )
                            supabase.table("jugadores").update({"url_foto": url_publica}).eq(
                                "id_jugador", id_jugador_nuevo
                            ).execute()
                        except Exception as e:
                            st.warning(
                                f"El jugador se creó, pero la foto no se pudo subir: {e}. "
                                f"Comprueba que el bucket 'fotos-jugadores' existe y es público."
                            )

                    st.success(f"✅ {nombre} se ha añadido a la plantilla.")

                    if crear_usuario and supabase_admin is not None and email_acceso:
                        password_temporal = generar_password_temporal()
                        usuario_auth = supabase_admin.auth.admin.create_user({
                            "email": email_acceso,
                            "password": password_temporal,
                            "email_confirm": True,
                        })
                        supabase.table("usuarios_roles").insert({
                            "correo": email_acceso,
                            "rol": "Jugador",
                            "id_jugador": id_jugador_nuevo,
                            "auth_user_id": usuario_auth.user.id,
                        }).execute()

                        st.info(
                            f"🔑 Cuenta creada. Comparte estas credenciales con el jugador "
                            f"de forma segura (le recomendamos cambiar la contraseña al entrar):\n\n"
                            f"**Correo:** {email_acceso}\n\n"
                            f"**Contraseña temporal:** `{password_temporal}`"
                        )
                except Exception as e:
                    st.error(f"Error al guardar el jugador: {e}")

st.page_link("app.py", label="⬅️ Volver a la plantilla", icon=None)
