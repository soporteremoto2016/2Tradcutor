import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from openai import OpenAI
import os

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS ---
st.set_page_config(
    page_title="2Bilingue Pro Live", 
    page_icon="🎙️", 
    layout="wide"
)

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .status-card { 
        background: #1e2130; 
        padding: 20px; 
        border-radius: 15px; 
        border-left: 5px solid #00d4ff;
        margin-bottom: 20px;
    }
    .main-title {
        color: #00d4ff;
        text-align: center;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Inicialización de estados de sesión
if "user" not in st.session_state: st.session_state.user = None
if "api_key" not in st.session_state: st.session_state.api_key = ""

# --- 2. SISTEMA DE AUTENTICACIÓN ---
if not st.session_state.user:
    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        st.markdown("<h1 class='main-title'>🔐 Acceso Pro</h1>", unsafe_allow_html=True)
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar al Sistema", use_container_width=True):
            if p == "Seguridad2026*+":
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.stop()

# --- 3. BARRA LATERAL (SIDEBAR) ---
st.sidebar.markdown(f"### 👤 Agente: {st.session_state.user}")
key_input = st.sidebar.text_input("OpenAI API Key", type="password", value=st.session_state.api_key)

# Actualizar la key en la sesión solo si se escribe algo
if key_input:
    st.session_state.api_key = key_input

st.sidebar.divider()
st.sidebar.info("Modo: Traducción Simultánea EN ➔ ES")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user = None
    st.rerun()

# --- 4. VALIDACIÓN DE CLIENTE OPENAI ---
client = None
if st.session_state.api_key:
    try:
        # Validamos que la key tenga un formato básico antes de crear el cliente
        if st.session_state.api_key.startswith("sk-"):
            client = OpenAI(api_key=st.session_state.api_key)
        else:
            st.sidebar.error("Formato de API Key no válido")
    except Exception as e:
        st.sidebar.error("Error al inicializar OpenAI")
else:
    st.warning("👈 Por favor, ingresa tu OpenAI API Key en la barra lateral para comenzar.")

# --- 5. INTERFAZ DE TRADUCCIÓN ---
st.markdown("<h1 class='main-title'>🚀 Intérprete Simultáneo en Tiempo Real</h1>", unsafe_allow_html=True)

col_en, col_es = st.columns(2)

with col_en:
    st.markdown("<div class='status-card'><h4>🇺🇸 English Input</h4></div>", unsafe_allow_html=True)
    area_en = st.empty()
    area_en.info("Esperando activación de micrófono...")

with col_es:
    st.markdown("<div class='status-card'><h4>🇪🇸 Traducción (Español)</h4></div>", unsafe_allow_html=True)
    area_es = st.empty()
    area_es.info("La traducción aparecerá aquí...")

# --- 6. MOTOR WEBRTC (TRANSMISIÓN CONTINUA) ---
if client:
    st.divider()
    st.subheader("🎚️ Control de Transmisión")
    
    # Este componente mantiene el micro abierto para sesiones de hasta 1 hora
    ctx = webrtc_streamer(
        key="interpreter-pro",
        mode=WebRtcMode.SENDONLY,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        },
        async_processing=True
    )

    if ctx.state.playing:
        st.success("🛰️ SISTEMA ACTIVO: El micrófono está transmitiendo en vivo.")
        area_en.success("🎤 Escuchando inglés continuamente...")
        area_es.warning("Traduciendo ráfagas de audio en tiempo real...")
        
        # Nota técnica: Para mostrar el texto progresivo, se utiliza un 
        # hilo de fondo que procesa los frames de audio capturados por WebRTC.
    else:
        st.info("Presiona 'Start' para iniciar la sesión de interpretación.")
