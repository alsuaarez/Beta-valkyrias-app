"""
Módulo compartido para CD Valkyrias Becerril - Hub Analítico.
Centraliza la conexión a Supabase, la paleta de colores del club y los
estilos CSS para que las 4 páginas de la app tengan un aspecto consistente
y profesional.
"""
import streamlit as st
from supabase import create_client, Client
import os
from datetime import date, datetime

# ============================================================
# CONEXIÓN A SUPABASE (una sola vez, cacheada, para toda la app)
# ============================================================
@st.cache_resource
def init_connection() -> Client:
    return create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))


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
def aplicar_estilos():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

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
    st.markdown(
        f"""
        <div class="cabecera-club">
            <h1>{icono} {titulo}</h1>
            {f"<p>{subtitulo}</p>" if subtitulo else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def requiere_sesion():
    """Barrera de seguridad estándar: si no hay sesión, vuelve al login."""
    if "usuario_actual" not in st.session_state or st.session_state["usuario_actual"] is None:
        st.switch_page("app.py")


def es_staff() -> bool:
    """Admin o Técnico: roles con permisos de edición/escritura."""
    return st.session_state.get("rol") in ("Admin", "Tecnico")
