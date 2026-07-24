import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd

# Configuración de página
st.set_page_config(page_title="Informes y Análisis", page_icon="📁", layout="wide")

@st.cache_resource
def init_connection():
    return create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

supabase: Client = init_connection()

st.title("📁 Gestor de Informes Técnicos")
st.markdown("Repositorio centralizado para los análisis del CD Valkyrias Becerril.")
st.markdown("---")

# Separar la interfaz en Pestañas
tab_consultar, tab_subir = st.tabs(["📄 Consultar Informes", "📤 Añadir Nuevo Informe"])

# ==========================================
# PESTAÑA 1: LECTURA DE INFORMES
# ==========================================
with tab_consultar:
    col1, col2 = st.columns([1, 3])
    with col1:
        filtro_tipo = st.selectbox("Filtrar por categoría:", ["Todos", "Pretemporada", "Partido", "Individual"])
    
    st.markdown("### Documentos Disponibles")
    
    # Hacer la llamada a Supabase dependiendo del filtro
    try:
        if filtro_tipo == "Todos":
            response = supabase.table("informes_pdf").select("*").order("fecha", desc=True).execute()
        else:
            response = supabase.table("informes_pdf").select("*").eq("tipo", filtro_tipo).order("fecha", desc=True).execute()
            
        datos_informes = response.data
        
        if datos_informes:
            # Crear una tarjeta visual para cada informe
            for informe in datos_informes:
                with st.container(border=True):
                    c_texto, c_boton = st.columns([4, 1])
                    c_texto.markdown(f"**{informe['titulo']}**")
                    c_texto.caption(f"📅 Fecha: {informe['fecha']} | 🏷️ Etiqueta: {informe['tipo']}")
                    
                    # Streamlit tiene un botón nativo para abrir URLs en otra pestaña
                    c_boton.link_button("Abrir Documento ↗", informe['url_archivo'], use_container_width=True)
        else:
            st.info("No hay informes guardados en esta categoría.")
            
    except Exception as e:
        st.error(f"Error al cargar los informes: {e}")

# ==========================================
# PESTAÑA 2: ESCRITURA EN BBDD
# ==========================================
with tab_subir:
    st.subheader("Registrar un nuevo análisis")
    st.info("💡 Consejo: Sube tu PDF a una nube (Google Drive, OneDrive o Supabase Storage) y pega aquí el enlace público.")
    
    # Formulario para evitar recargas hasta que le des al botón de guardar
    with st.form("form_nuevo_informe", clear_on_submit=True):
        nuevo_titulo = st.text_input("Título del Informe (Ej: Análisis Jornada 1)")
        
        c_tipo, c_fecha = st.columns(2)
        nuevo_tipo = c_tipo.selectbox("Tipo de documento", ["Pretemporada", "Partido", "Individual"])
        nueva_fecha = c_fecha.date_input("Fecha correspondiente")
        
        nuevo_enlace = st.text_input("Enlace URL del PDF")
        
        btn_guardar = st.form_submit_button("Guardar en la Base de Datos")
        
        if btn_guardar:
            if nuevo_titulo and nuevo_enlace:
                try:
                    # Inserción directa a Supabase desde la web
                    supabase.table("informes_pdf").insert({
                        "titulo": nuevo_titulo,
                        "tipo": nuevo_tipo,
                        "fecha": str(nueva_fecha),
                        "url_archivo": nuevo_enlace
                    }).execute()
                    
                    st.success("✅ ¡Informe registrado con éxito! Ve a la pestaña 'Consultar' para verlo.")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("⚠️ El título y el enlace son campos obligatorios.")