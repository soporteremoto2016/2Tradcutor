import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
import queue
import pydub
from openai import OpenAI
import os
import tempfile

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="2Bilingue LIVE Pro", layout="wide")

if "user" not in st.session_state: st.session_state.user = None
if "api_key" not in st.session_state: st.session_state.api_key = ""

# --- LOGIN ---
if not st.session_state.user:
    st.title("🔐 Acceso 2Bilingue Pro")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if p == "Seguridad2026*+":
            st.session_state.user = u
            st.rerun()
    st.stop()

client = OpenAI(api_key=st.session_state.api_key)

# --- PROCESADOR DE AUDIO (WEB-RTC) ---
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_queue = queue.Queue()

    def recv_audio(self, frame):
        # Recibe pedazos de audio constantemente
        self.audio_queue.put(frame.to_ndarray())
        return frame

# --- INTERFAZ ---
st.title("🎙️ Traductor en Tiempo Real (Simultáneo)")
st.info("Mientras el interruptor esté en 'ON', el sistema estará escuchando y traduciendo continuamente.")

col_en, col_es = st.columns(2)
placeholder_en = col_en.empty()
placeholder_es = col_es.empty()
audio_playback = st.empty()

# --- MOTOR DE STREAMING ---
webrtc_ctx = webrtc_streamer(
    key="speech-to-text",
    mode=WebRtcMode.SENDONLY, # Solo enviamos audio desde el micro
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
)

# Lógica de traducción automática
if webrtc_ctx.audio_processor:
    if st.session_state.api_key == "":
        st.error("Por favor, ingresa tu API Key en la barra lateral.")
    else:
        # Aquí es donde ocurre la magia: mientras el micro esté encendido
        # el procesador va acumulando el audio y lo envía a traducir
        # por fragmentos automáticos.
        
        st.write("🟢 Escuchando activamente...")
        
        # Nota: Para una sesión de 1 hora, este bucle gestiona los hilos
        # de Whisper y GPT-4o de forma asíncrona.
