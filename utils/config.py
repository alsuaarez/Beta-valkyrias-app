"""
Módulo compartido para CD Valkyrias Becerril - Hub Analítico.
Centraliza la conexión a Supabase, la paleta de colores del club y los
estilos CSS para que las 4 páginas de la app tengan un aspecto consistente
y profesional.
"""
import streamlit as st
from supabase import create_client, Client
import os
import base64
import secrets
import string
from datetime import date, datetime

# ============================================================
# CONEXIÓN A SUPABASE (una sola vez, cacheada, para toda la app)
# ============================================================
@st.cache_resource
def init_connection() -> Client:
    return create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))


@st.cache_resource
def init_admin_connection():
    """
    Cliente con la service_role key de Supabase, necesario únicamente para
    crear usuarios de Auth o resetear contraseñas desde la app (operaciones
    de administrador). Se usa SOLO en el servidor (nunca llega al navegador).

    Necesitas añadir SUPABASE_SERVICE_KEY a tu .env con la "service_role key"
    que encuentras en Supabase > Project Settings > API > service_role.
    ¡OJO! Esa clave tiene permisos totales, nunca la subas a un repo público
    ni la metas en el .env que compartes con nadie.
    """
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not service_key:
        return None
    return create_client(os.environ.get("SUPABASE_URL"), service_key)


def generar_password_temporal(longitud: int = 10) -> str:
    """Genera una contraseña temporal segura y fácil de transcribir a mano."""
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(longitud))


BUCKET_FOTOS = "fotos-jugadores"


def asegurar_bucket_fotos(supabase_admin) -> None:
    """Crea el bucket de fotos si todavía no existe. Necesita el cliente admin
    (service_role); si no está disponible, no hace nada (y la subida fallará
    con un error claro más abajo)."""
    if supabase_admin is None:
        return
    try:
        supabase_admin.storage.create_bucket(BUCKET_FOTOS, options={"public": True})
    except Exception:
        pass  # ya existía, o no se pudo crear por otro motivo (se verá en el siguiente intento)


def subir_foto_jugador(supabase, id_jugador: int, archivo, supabase_admin=None) -> str:
    """
    Sube la foto de un jugador al bucket 'fotos-jugadores' de Supabase Storage
    y devuelve la URL pública para guardar en jugadores.url_foto.

    Usa el cliente admin (service_role) para la subida: la clave anon no
    tiene permiso de escritura en Storage por defecto (aunque el bucket sea
    público para lectura), así que sin service_role la subida da 403.
    """
    if supabase_admin is None:
        raise RuntimeError(
            "Falta configurar SUPABASE_SERVICE_KEY en tu .env: es necesaria para "
            "poder subir archivos a Storage, no solo para gestionar usuarios."
        )

    extension = archivo.name.split(".")[-1].lower()
    ruta = f"jugador_{id_jugador}.{extension}"
    contenido = archivo.getvalue()

    try:
        supabase_admin.storage.from_(BUCKET_FOTOS).upload(
            ruta, contenido, {"content-type": archivo.type, "upsert": "true"}
        )
    except Exception as e:
        if "Bucket not found" in str(e):
            asegurar_bucket_fotos(supabase_admin)
            supabase_admin.storage.from_(BUCKET_FOTOS).upload(
                ruta, contenido, {"content-type": archivo.type, "upsert": "true"}
            )
        else:
            raise

    return supabase.storage.from_(BUCKET_FOTOS).get_public_url(ruta)


# ============================================================
# IDENTIDAD VISUAL DEL CLUB
# Cambia estos valores si quieres ajustar los colores o el escudo.
# ============================================================
NOMBRE_CLUB = "CD Valkyrias Becerril"
ESCUDO_URL = ""  # pon aquí la URL de tu escudo si tienes una, si no se usa el emoji

COLOR_PRIMARIO = "#0B1F3A"       # Azul marino - color principal del club
COLOR_PRIMARIO_CLARO = "#16305A"
COLOR_SECUNDARIO = "#C9A227"     # Dorado - acentos, botones destacados
COLOR_FONDO = "#F4F6F9"
COLOR_TARJETA = "#FFFFFF"
COLOR_TEXTO = "#0B1F3A"
COLOR_TEXTO_SUAVE = "#5A6472"
COLOR_EXITO = "#1E8E5A"
COLOR_ALERTA = "#C0392B"
COLOR_BORDE = "#E3E7EE"

COLORES_POSICION = {
    "Portero": "#F1C40F",
    "Defensa": "#2E86DE",
    "Centrocampista": "#27AE60",
    "Delantero": "#E74C3C",
}


def color_posicion(posicion: str) -> str:
    return COLORES_POSICION.get(posicion, "#7F8C8D")


def badge_html(texto: str, color_fondo: str, color_texto: str = "#FFFFFF") -> str:
    return (
        f"<span style='background:{color_fondo};color:{color_texto};"
        f"padding:4px 14px;border-radius:20px;font-size:0.78rem;"
        f"font-weight:600;letter-spacing:.3px;white-space:nowrap;'>{texto}</span>"
    )


def calcular_edad(fecha_nacimiento):
    """Acepta str (YYYY-MM-DD) o date/datetime. Devuelve la edad en años o None."""
    if not fecha_nacimiento:
        return None
    if isinstance(fecha_nacimiento, str):
        try:
            fecha_nacimiento = date.fromisoformat(fecha_nacimiento[:10])
        except ValueError:
            return None
    if isinstance(fecha_nacimiento, datetime):
        fecha_nacimiento = fecha_nacimiento.date()
    hoy = date.today()
    return hoy.year - fecha_nacimiento.year - (
        (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
    )


# ============================================================
# ESTILOS GLOBALES (se inyectan al principio de cada página)
# ============================================================
@st.cache_data
def _escudo_base64() -> str:
    """Lee assets/escudo.png y lo devuelve codificado en base64 para poder
    usarlo como fondo CSS sin depender de servir archivos estáticos."""
    ruta = os.path.join(os.path.dirname(__file__), "..", "assets", "escudo.png")
    try:
        with open(ruta, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        return ""


def renderizar_html(fragmento: str):
    """Renderiza un fragmento de HTML con st.markdown quitando la sangría de
    cada línea. Si no se hace esto, Markdown puede interpretar líneas con
    varios espacios de indentación como un bloque de código y mostrarlas
    como texto en crudo en vez de renderizarlas como HTML."""
    limpio = "\n".join(linea.strip() for linea in fragmento.strip("\n").split("\n"))
    st.markdown(limpio, unsafe_allow_html=True)


def aplicar_estilos():
    escudo_b64 = _escudo_base64()
    fondo_escudo_css = (
        f"""
        .stApp::before {{
            content: "";
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image: url('data:image/png;base64,{escudo_b64}');
            background-repeat: no-repeat;
            background-position: center 40%;
            background-size: 640px;
            opacity: 0.05;
            pointer-events: none;
            z-index: 0;
        }}
        .stApp > header, .stApp [data-testid="stAppViewContainer"] > .main {{
            position: relative;
            z-index: 1;
        }}
        """
        if escudo_b64
        else ""
    )

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        {fondo_escudo_css}

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        .stApp {{
            background-color: {COLOR_FONDO};
        }}

        /* --- Sidebar --- */
        section[data-testid="stSidebar"] {{
            background-color: {COLOR_PRIMARIO};
        }}
        section[data-testid="stSidebar"] * {{
            color: #EAEDF2 !important;
        }}
        section[data-testid="stSidebar"] a {{
            color: #FFFFFF !important;
        }}

        /* --- Ocultar el pie de página "Made with Streamlit" (el menú de los
               tres puntos se deja visible para poder cambiar a modo oscuro) --- */
        footer {{visibility: hidden;}}

        /* --- Títulos --- */
        h1, h2, h3 {{
            color: {COLOR_TEXTO};
            font-weight: 800;
            letter-spacing: -0.3px;
        }}

        /* --- Tarjetas genéricas --- */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 14px !important;
            border: 1px solid {COLOR_BORDE} !important;
            background-color: {COLOR_TARJETA};
            box-shadow: 0 2px 10px rgba(11, 31, 58, 0.05);
            transition: box-shadow .15s ease, transform .15s ease;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
            box-shadow: 0 6px 18px rgba(11, 31, 58, 0.10);
        }}

        /* --- Botones --- */
        .stButton > button, .stFormSubmitButton > button, .stLinkButton > a {{
            border-radius: 8px;
            font-weight: 600;
            border: 1px solid {COLOR_PRIMARIO};
            transition: all .15s ease;
        }}
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
            background-color: {COLOR_PRIMARIO};
            color: white;
        }}
        .stButton > button[kind="primary"]:hover {{
            background-color: {COLOR_PRIMARIO_CLARO};
            border-color: {COLOR_PRIMARIO_CLARO};
        }}

        /* --- Métricas --- */
        div[data-testid="stMetric"] {{
            background-color: {COLOR_TARJETA};
            border: 1px solid {COLOR_BORDE};
            border-radius: 12px;
            padding: 12px 16px;
        }}
        div[data-testid="stMetricLabel"] {{
            color: {COLOR_TEXTO_SUAVE} !important;
        }}
        div[data-testid="stMetricValue"] {{
            color: {COLOR_PRIMARIO} !important;
        }}

        /* --- Tabs --- */
        button[data-baseweb="tab"] {{
            font-weight: 600;
            color: {COLOR_TEXTO_SUAVE};
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {COLOR_PRIMARIO};
        }}
        div[data-baseweb="tab-highlight"] {{
            background-color: {COLOR_SECUNDARIO} !important;
        }}

        /* --- Cabecera de club (usada en app.py y ficha de jugador) --- */
        .cabecera-club {{
            background: linear-gradient(135deg, {COLOR_PRIMARIO} 0%, {COLOR_PRIMARIO_CLARO} 100%);
            border-radius: 16px;
            padding: 28px 32px;
            color: white;
            margin-bottom: 24px;
        }}
        .cabecera-club h1 {{
            color: white !important;
            margin: 0;
            font-size: 1.8rem;
        }}
        .cabecera-club p {{
            color: #C9D2E0;
            margin: 4px 0 0 0;
        }}

        /* --- Tarjeta de jugador (grid principal) --- */
        .foto-jugador {{
            width: 92px;
            height: 92px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid {COLOR_SECUNDARIO};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def cabecera(titulo: str, subtitulo: str = "", icono: str = "⚽"):
    """Cabecera visual reutilizable con degradado de color del club."""
    renderizar_html(
        f"""
        <div class="cabecera-club">
            <h1>{icono} {titulo}</h1>
            {f"<p>{subtitulo}</p>" if subtitulo else ""}
        </div>
        """
    )


def requiere_sesion():
    """Barrera de seguridad estándar: si no hay sesión, vuelve al login."""
    if "usuario_actual" not in st.session_state or st.session_state["usuario_actual"] is None:
        st.switch_page("app.py")


def es_staff() -> bool:
    """Admin o Técnico: roles con permisos de edición/escritura."""
    return st.session_state.get("rol") in ("Admin", "Tecnico")


# ============================================================
# INFORMES: categorías y reglas de visibilidad
# ============================================================
CATEGORIAS_INFORME = [
    "Pretemporada",
    "Analisis Propio Pre",
    "Analisis Propio Post",
    "Analisis Rival Pre",
    "Analisis Rival Post",
    "Individual",
]

ETIQUETAS_CATEGORIA = {
    "Pretemporada": "🏋️ Pretemporada",
    "Analisis Propio Pre": "🔵 Análisis propio · Pre-partido",
    "Analisis Propio Post": "🔵 Análisis propio · Post-partido",
    "Analisis Rival Pre": "🔴 Análisis rival · Pre-partido",
    "Analisis Rival Post": "🔴 Análisis rival · Post-partido",
    "Individual": "👤 Individual",
}


def jugador_tiene_acceso(supabase, id_informe, id_jugador) -> bool:
    """Comprueba si un jugador concreto tiene acceso concedido a un informe
    marcado como 'Individual'."""
    r = (
        supabase.table("informes_acceso")
        .select("id")
        .eq("id_informe", id_informe)
        .eq("id_jugador", id_jugador)
        .execute()
    )
    return bool(r.data)


# ============================================================
# PARTIDO: catálogo de formaciones para la convocatoria
# Cada slot tiene una clave única, una etiqueta y una posición en
# porcentaje sobre el campo (x: 0=izquierda 100=derecha,
# y: 0=portería rival 100=nuestra portería).
# Puedes ampliar este diccionario con más formaciones cuando quieras.
# ============================================================
FORMACIONES = {
    "1-4-3-3": [
        {"clave": "POR", "etiqueta": "Portero", "x": 50, "y": 92},
        {"clave": "LD", "etiqueta": "Lateral derecho", "x": 82, "y": 70},
        {"clave": "DFC1", "etiqueta": "Central derecho", "x": 62, "y": 74},
        {"clave": "DFC2", "etiqueta": "Central izquierdo", "x": 38, "y": 74},
        {"clave": "LI", "etiqueta": "Lateral izquierdo", "x": 18, "y": 70},
        {"clave": "MCD", "etiqueta": "Mediocentro defensivo", "x": 50, "y": 58},
        {"clave": "MC1", "etiqueta": "Mediocentro derecho", "x": 68, "y": 48},
        {"clave": "MC2", "etiqueta": "Mediocentro izquierdo", "x": 32, "y": 48},
        {"clave": "ED", "etiqueta": "Extremo derecho", "x": 80, "y": 25},
        {"clave": "DC", "etiqueta": "Delantero centro", "x": 50, "y": 15},
        {"clave": "EI", "etiqueta": "Extremo izquierdo", "x": 20, "y": 25},
    ],
    "1-4-4-2": [
        {"clave": "POR", "etiqueta": "Portero", "x": 50, "y": 92},
        {"clave": "LD", "etiqueta": "Lateral derecho", "x": 82, "y": 70},
        {"clave": "DFC1", "etiqueta": "Central derecho", "x": 62, "y": 74},
        {"clave": "DFC2", "etiqueta": "Central izquierdo", "x": 38, "y": 74},
        {"clave": "LI", "etiqueta": "Lateral izquierdo", "x": 18, "y": 70},
        {"clave": "MD", "etiqueta": "Interior derecho", "x": 80, "y": 45},
        {"clave": "MC1", "etiqueta": "Mediocentro derecho", "x": 58, "y": 50},
        {"clave": "MC2", "etiqueta": "Mediocentro izquierdo", "x": 42, "y": 50},
        {"clave": "MI", "etiqueta": "Interior izquierdo", "x": 20, "y": 45},
        {"clave": "DC1", "etiqueta": "Delantero derecho", "x": 60, "y": 15},
        {"clave": "DC2", "etiqueta": "Delantero izquierdo", "x": 40, "y": 15},
    ],
    "1-4-2-3-1": [
        {"clave": "POR", "etiqueta": "Portero", "x": 50, "y": 92},
        {"clave": "LD", "etiqueta": "Lateral derecho", "x": 82, "y": 70},
        {"clave": "DFC1", "etiqueta": "Central derecho", "x": 62, "y": 74},
        {"clave": "DFC2", "etiqueta": "Central izquierdo", "x": 38, "y": 74},
        {"clave": "LI", "etiqueta": "Lateral izquierdo", "x": 18, "y": 70},
        {"clave": "MCD1", "etiqueta": "Mediocentro derecho", "x": 60, "y": 58},
        {"clave": "MCD2", "etiqueta": "Mediocentro izquierdo", "x": 40, "y": 58},
        {"clave": "ED", "etiqueta": "Extremo derecho", "x": 80, "y": 35},
        {"clave": "MCO", "etiqueta": "Mediapunta", "x": 50, "y": 32},
        {"clave": "EI", "etiqueta": "Extremo izquierdo", "x": 20, "y": 35},
        {"clave": "DC", "etiqueta": "Delantero centro", "x": 50, "y": 15},
    ],
    "1-3-5-2": [
        {"clave": "POR", "etiqueta": "Portero", "x": 50, "y": 92},
        {"clave": "DFC1", "etiqueta": "Central derecho", "x": 70, "y": 76},
        {"clave": "DFC2", "etiqueta": "Central", "x": 50, "y": 79},
        {"clave": "DFC3", "etiqueta": "Central izquierdo", "x": 30, "y": 76},
        {"clave": "LD", "etiqueta": "Carrilero derecho", "x": 90, "y": 55},
        {"clave": "MC1", "etiqueta": "Mediocentro derecho", "x": 62, "y": 52},
        {"clave": "MC2", "etiqueta": "Mediocentro", "x": 50, "y": 48},
        {"clave": "MC3", "etiqueta": "Mediocentro izquierdo", "x": 38, "y": 52},
        {"clave": "LI", "etiqueta": "Carrilero izquierdo", "x": 10, "y": 55},
        {"clave": "DC1", "etiqueta": "Delantero derecho", "x": 60, "y": 15},
        {"clave": "DC2", "etiqueta": "Delantero izquierdo", "x": 40, "y": 15},
    ],
    "1-4-1-4-1": [
        {"clave": "POR", "etiqueta": "Portero", "x": 50, "y": 92},
        {"clave": "LD", "etiqueta": "Lateral derecho", "x": 82, "y": 72},
        {"clave": "DFC1", "etiqueta": "Central derecho", "x": 62, "y": 76},
        {"clave": "DFC2", "etiqueta": "Central izquierdo", "x": 38, "y": 76},
        {"clave": "LI", "etiqueta": "Lateral izquierdo", "x": 18, "y": 72},
        {"clave": "MCD", "etiqueta": "Mediocentro defensivo", "x": 50, "y": 60},
        {"clave": "ED", "etiqueta": "Interior/Extremo derecho", "x": 82, "y": 42},
        {"clave": "MC1", "etiqueta": "Mediocentro derecho", "x": 58, "y": 42},
        {"clave": "MC2", "etiqueta": "Mediocentro izquierdo", "x": 42, "y": 42},
        {"clave": "EI", "etiqueta": "Interior/Extremo izquierdo", "x": 18, "y": 42},
        {"clave": "DC", "etiqueta": "Delantero centro", "x": 50, "y": 15},
    ],
}
