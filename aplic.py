import streamlit as st
from openai import OpenAI
import tempfile
import os
import time

# --- 1. CONFIGURACIÓN PROFESIONAL ---
st.set_page_config(page_title="2Bilingue LIVE - Intérprete Pro", layout="wide", page_icon="🎙️")

# CSS para estilo de "Consola de Transmisión"
st.markdown("""
    <style>
    .live-box {
        background-color: #0e1117;
        color: #00ff00;
        padding: 20px;
        border-radius: 10px;
        font-family: 'Courier New', Courier, monospace;
        height: 300px;
        overflow-y: auto;
        border: 1px solid #333;
    }
    .translation-live {
        background-color: #ffffff;
        color: #1e1e1e;
        padding: 20px;
        border-radius: 10px;
        font-size: 1.2rem;
        min-height: 300px;
        border-left: 5px solid #1565C0;
    }
    </style>
""", unsafe_allow_html=True)

if "history" not in st.session_state: st.session_state.history = []
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "user" not in st.session_state: st.session_state.user = None

# --- 2. ACCESO ---
if not st.session_state.user:
    st.title("🔐 Acceso 2Bilingue Pro")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if p == "Seguridad2026*+":
            st.session_state.user = u
            st.rerun()
    st.stop()

# --- 3. DASHBOARD ---
with st.sidebar:
    st.header(f"🎙️ Terminal: {st.session_state.user}")
    st.session_state.api_key = st.text_input("API Key", value=st.session_state.api_key, type="password")
    st.divider()
    st.caption("Estado: Optimizado para sesiones largas")
    if st.button("Limpiar Consola"):
        st.session_state.history = []
        st.rerun()

st.title("🚀 Intérprete en Tiempo Real (EN ➔ ES)")

if not st.session_state.api_key:
    st.warning("⚠️ Ingrese su API Key para iniciar el motor de streaming.")
    st.stop()

client = OpenAI(api_key=st.session_state.api_key)

# --- 4. INTERFAZ DE TIEMPO REAL ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🇺🇸 Input: English Live")
    container_en = st.empty() # Espacio dinámico para texto original

with col2:
    st.subheader("🇪🇸 Output: Traducción Profesional")
    container_es = st.empty() # Espacio dinámico para traducción

# Widget de entrada de audio (versión moderna)
audio_chunk = st.audio_input("Pulse para iniciar la sesión (Soporta larga duración)")

if audio_chunk:
    try:
        # Iniciamos el proceso de interpretación
        with st.spinner("Conectando con el motor de traducción..."):
            
            # Guardamos el chunk de audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(audio_chunk.getvalue())
                tmp_path = tmp_file.name

            # 1. TRANSCRIPCIÓN RÁPIDA (Whisper)
            with open(tmp_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=f,
                    language="en",
                    response_format="text"
                )

            if transcript.strip():
                # Actualizamos la consola de inglés
                container_en.markdown(f'<div class="live-box">{transcript}</div>', unsafe_allow_html=True)

                # 2. TRADUCCIÓN EN STREAMING (GPT-4o)
                # Esto permite que la traducción aparezca palabra por palabra
                stream = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Eres un intérprete de conferencias. Traduce del inglés al español de forma fluida y profesional. Solo entrega el texto traducido."},
                        {"role": "user", "content": transcript}
                    ],
                    stream=True # ACTIVAMOS STREAMING
                )

                # Renderizado dinámico de la traducción
                full_translation = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_translation += chunk.choices[0].delta.content
                        container_es.markdown(f'<div class="translation-live">{full_translation} ▌</div>', unsafe_allow_html=True)

                # 3. SÍNTESIS DE VOZ (Opcional para el resultado final)
                audio_res = client.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=full_translation
                )
                st.audio(audio_res.content, format="audio/mp3", autoplay=True)

            os.remove(tmp_path)

    except Exception as e:
        st.error(f"Error de conexión en tiempo real: {e}")

# --- 5. LOG DE SESIÓN ---
if st.session_state.history:
    with st.expander("Ver Log de la sesión completa"):
        for h in st.session_state.history:
            st.text(f"EN: {h['en']}\nES: {h['es']}\n---")
