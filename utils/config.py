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
import io
import urllib.request
from datetime import date, datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps

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


def nombre_mostrar(jugador: dict) -> str:
    """Nombre a mostrar en Convocatoria y Pizarra táctica: usa el apodo si el
    jugador tiene uno asignado; si no, cae al primer nombre de pila. Así, en
    todo lo relacionado con 'Partido' nunca se expone el nombre completo."""
    apodo = (jugador or {}).get("apodo")
    if apodo:
        return apodo
    nombre = (jugador or {}).get("nombre", "") or ""
    return nombre.split()[0] if nombre else "Jugador"


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


# ============================================================
# GENERADOR DE IMÁGENES PNG DESCARGABLES (para llevar las pizarras y el
# Once a la tablet sin necesidad de imprimir ni de tener conexión en el
# momento del partido)
# ============================================================
def _fuente(tamano: int, negrita: bool = False):
    """Fuente con soporte completo de tildes y eñes (á é í ó ú ñ, etc.).
    Usa la DejaVu Sans incluida en assets/fuentes/; si por lo que sea no
    está disponible, cae a la fuente básica de Pillow (sin tildes)."""
    nombre_archivo = "DejaVuSans-Bold.ttf" if negrita else "DejaVuSans.ttf"
    ruta = os.path.join(os.path.dirname(__file__), "..", "assets", "fuentes", nombre_archivo)
    try:
        return ImageFont.truetype(ruta, tamano)
    except Exception:
        try:
            return ImageFont.load_default(size=tamano)
        except TypeError:
            return ImageFont.load_default()


def _foto_circular(url: str, diametro: int):
    """Descarga una foto de jugador y la recorta en círculo. Si falla
    (sin conexión, URL rota, etc.) devuelve None y se dibuja un círculo liso."""
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=6) as resp:
            datos = resp.read()
        img = Image.open(io.BytesIO(datos)).convert("RGBA")
        img = ImageOps.fit(img, (diametro, diametro), Image.LANCZOS)
        mascara = Image.new("L", (diametro, diametro), 0)
        ImageDraw.Draw(mascara).ellipse((0, 0, diametro, diametro), fill=255)
        img.putalpha(mascara)
        return img
    except Exception:
        return None


class _LienzoCampo:
    """Dibuja un campo (completo o medio campo) sobre una imagen PIL, con las
    mismas proporciones y líneas que se ven en la app, listo para pegar
    jugadores, marcas rivales, balón y flechas encima."""

    def __init__(self, medio_campo: bool, ancho: int = 1000):
        self.ancho = ancho
        self.medio_campo = medio_campo
        self.alto_pitch = int(ancho * (0.70 if medio_campo else 1.35))
        self.margen_top = 110
        self.margen_bottom = 60  # colchón de seguridad para que las etiquetas cerca del borde no se corten
        self.alto = self.alto_pitch + self.margen_top + self.margen_bottom

        self.img = Image.new("RGB", (self.ancho, self.alto), COLOR_PRIMARIO)
        self.draw = ImageDraw.Draw(self.img, "RGBA")

        self._dibujar_cesped()
        self._dibujar_lineas()

    def px(self, x_pct, y_pct):
        return (x_pct / 100 * self.ancho, self.margen_top + y_pct / 100 * self.alto_pitch)

    def bbox(self, cx, cy, r):
        # OJO: aquí NO se puede usar px() para los dos extremos del radio,
        # porque px() escala X según self.ancho e Y según self.alto_pitch
        # (valores distintos, ya que el medio campo es más ancho que alto).
        # Si se usa esa escala para el radio, los círculos y arcos del área
        # salen aplastados en vez de redondos. Por eso aquí se aplica
        # SIEMPRE la escala de self.ancho, igual en X que en Y.
        cx_px, cy_px = self.px(cx, cy)
        radio = r * (self.ancho / 100)
        return [cx_px - radio, cy_px - radio, cx_px + radio, cy_px + radio]

    def _dibujar_cesped(self):
        franjas = 10
        alto_franja = self.alto_pitch / franjas
        verdes = ["#2E7D46", "#33884C"]
        for i in range(franjas):
            y1 = self.margen_top + i * alto_franja
            y2 = self.margen_top + (i + 1) * alto_franja
            self.draw.rectangle([0, y1, self.ancho, y2], fill=verdes[i % 2])
        # Colchón de seguridad debajo de la línea de gol, del mismo verde que
        # la última franja, para que las etiquetas cercanas al borde tengan
        # sitio y no se corten contra el final de la imagen.
        self.draw.rectangle(
            [0, self.margen_top + self.alto_pitch, self.ancho, self.alto],
            fill=verdes[(franjas - 1) % 2],
        )

    def _dibujar_lineas(self):
        blanco = (255, 255, 255, 190)
        grosor = 3
        d = self.draw

        # Borde del campo (líneas de banda, fondo y medio campo si aplica)
        d.rectangle([self.px(0, 0), self.px(100, 100)], outline=blanco, width=grosor)

        if self.medio_campo:
            d.arc(self.bbox(50, 0, 15), start=0, end=180, fill=blanco, width=grosor)
            d.ellipse(self.bbox(50, 0, 0.9), fill=blanco)

            d.rectangle([self.px(21, 82), self.px(79, 100)], outline=blanco, width=grosor)
            d.rectangle([self.px(37, 94), self.px(63, 100)], outline=blanco, width=grosor)
            d.ellipse(self.bbox(50, 88, 0.9), fill=blanco)
            d.arc(self.bbox(50, 88, 10), start=180, end=360, fill=blanco, width=grosor)

            d.arc(self.bbox(0, 100, 3), start=180, end=270, fill=blanco, width=grosor)
            d.arc(self.bbox(100, 100, 3), start=270, end=360, fill=blanco, width=grosor)
        else:
            d.line([self.px(0, 50), self.px(100, 50)], fill=blanco, width=grosor)
            d.ellipse(self.bbox(50, 50, 9), outline=blanco, width=grosor)
            d.ellipse(self.bbox(50, 50, 0.9), fill=blanco)

            d.rectangle([self.px(21, 0), self.px(79, 14)], outline=blanco, width=grosor)
            d.rectangle([self.px(37, 0), self.px(63, 5)], outline=blanco, width=grosor)
            d.ellipse(self.bbox(50, 10, 0.9), fill=blanco)
            d.arc(self.bbox(50, 10, 8), start=0, end=180, fill=blanco, width=grosor)

            d.rectangle([self.px(21, 86), self.px(79, 100)], outline=blanco, width=grosor)
            d.rectangle([self.px(37, 95), self.px(63, 100)], outline=blanco, width=grosor)
            d.ellipse(self.bbox(50, 90, 0.9), fill=blanco)
            d.arc(self.bbox(50, 86, 8), start=180, end=360, fill=blanco, width=grosor)

    def titulo(self, linea1: str, linea2: str = ""):
        self.draw.text((24, 20), linea1, font=_fuente(34, negrita=True), fill="white")
        if linea2:
            self.draw.text((24, 60), linea2, font=_fuente(20), fill=COLOR_SECUNDARIO)

    def jugador(self, x_pct, y_pct, url_foto, nombre, borde="#2E86DE"):
        cx, cy = self.px(x_pct, y_pct)
        diametro = 64
        foto = _foto_circular(url_foto, diametro)
        if foto is not None:
            self.img.paste(foto, (int(cx - diametro / 2), int(cy - diametro / 2)), foto)
            self.draw.ellipse(
                [cx - diametro / 2, cy - diametro / 2, cx + diametro / 2, cy + diametro / 2],
                outline=borde, width=4,
            )
        else:
            self.draw.ellipse(
                [cx - diametro / 2, cy - diametro / 2, cx + diametro / 2, cy + diametro / 2],
                fill=borde, outline="white", width=3,
            )
        self._texto_centrado(cx, cy + diametro / 2 + 8, nombre, tamano=18)

    def marca_rival(self, x_pct, y_pct, etiqueta):
        cx, cy = self.px(x_pct, y_pct)
        r = 26
        self.draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#E74C3C", outline="white", width=3)
        self._texto_centrado(cx, cy, etiqueta or "R", tamano=18, color="white")

    def balon(self, x_pct, y_pct):
        cx, cy = self.px(x_pct, y_pct)
        r = 14
        self.draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="white", outline="black", width=2)

    def flecha(self, x1, y1, x2, y2):
        p1 = self.px(x1, y1)
        p2 = self.px(x2, y2)
        color = COLOR_SECUNDARIO
        self.draw.line([p1, p2], fill=color, width=5)
        import math
        ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        largo, ancho_punta = 18, 10
        punta = [
            p2,
            (p2[0] - largo * math.cos(ang - math.pi / 7), p2[1] - largo * math.sin(ang - math.pi / 7)),
            (p2[0] - largo * math.cos(ang + math.pi / 7), p2[1] - largo * math.sin(ang + math.pi / 7)),
        ]
        self.draw.polygon(punta, fill=color)

    def _texto_centrado(self, cx, cy, texto, tamano=18, color="white", negrita=True):
        fuente = _fuente(tamano, negrita=negrita)
        bbox = self.draw.textbbox((0, 0), texto, font=fuente)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        # sombra ligera para que se lea sobre el césped
        self.draw.text((cx - w / 2 + 1, cy - h / 2 + 1), texto, font=fuente, fill="black")
        self.draw.text((cx - w / 2, cy - h / 2), texto, font=fuente, fill=color)

    def bytes_png(self) -> bytes:
        buffer = io.BytesIO()
        self.img.save(buffer, format="PNG")
        return buffer.getvalue()


def imagen_pizarra_png(elementos, mapa_jugadores, nombre_pizarra, nombre_partido) -> bytes:
    lienzo = _LienzoCampo(medio_campo=True)
    lienzo.titulo(nombre_pizarra, nombre_partido)
    for e in elementos:
        if e["tipo"] == "flecha":
            lienzo.flecha(e["x1"], e["y1"], e["x2"], e["y2"])
    for e in elementos:
        if e["tipo"] == "jugador":
            j = mapa_jugadores.get(e.get("id_jugador"))
            lienzo.jugador(
                e["x"], e["y"],
                j.get("url_foto") if j else None,
                nombre_mostrar(j) if j else "?",
            )
        elif e["tipo"] == "rival":
            lienzo.marca_rival(e["x"], e["y"], e.get("etiqueta", "R"))
        elif e["tipo"] == "balon":
            lienzo.balon(e["x"], e["y"])
    return lienzo.bytes_png()


def imagen_convocatoria_png(slots, asignaciones, mapa_jugadores, formacion, nombre_partido) -> bytes:
    lienzo = _LienzoCampo(medio_campo=False)
    lienzo.titulo(f"Once inicial · {formacion}", nombre_partido)
    for slot in slots:
        j_id = asignaciones.get(slot["clave"])
        j = mapa_jugadores.get(j_id) if j_id else None
        lienzo.jugador(
            slot["x"], slot["y"],
            j.get("url_foto") if j else None,
            nombre_mostrar(j) if j else slot["etiqueta"],
        )
    return lienzo.bytes_png()
