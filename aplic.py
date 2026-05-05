import streamlit as st
from openai import OpenAI
import tempfile
import os

# --- 1. CONFIGURACIÓN PROFESIONAL ---
st.set_page_config(page_title="2Bilingue - Real Time Pro", layout="wide", page_icon="🎙️")

# Estilo de consola de traducción en vivo
st.markdown("""
    <style>
    .live-text-box {
        background-color: #f8f9fa;
        border-left: 5px solid #1565C0;
        padding: 20px;
        border-radius: 10px;
        min-height: 200px;
        font-size: 1.3rem;
        color: #1e1e1e;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    .status-tag {
        color: #1565C0;
        font-weight: bold;
        text-transform: uppercase;
        font-size: 0.8rem;
    }
    </style>
""", unsafe_allow_html=True)

if "user" not in st.session_state: st.session_state.user = None
if "api_key" not in st.session_state: st.session_state.api_key = ""

# --- 2. LOGIN ---
if not st.session_state.user:
    st.title("🔐 Acceso 2Bilingue Pro")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if p == "Seguridad2026*+":
            st.session_state.user = u
            st.rerun()
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header(f"🎧 Terminal de {st.session_state.user}")
    st.session_state.api_key = st.text_input("OpenAI API Key", value=st.session_state.api_key, type="password")
    st.divider()
    st.info("Nota: Para traducción continua sin cortes, use fragmentos de voz claros.")

# --- 4. MOTOR DE TRADUCCIÓN SIMULTÁNEA ---
st.title("🚀 Traducción Simultánea Escrita y de Voz")

if not st.session_state.api_key:
    st.warning("⚠️ Configura la API Key para iniciar.")
    st.stop()

client = OpenAI(api_key=st.session_state.api_key)

# Contenedores dinámicos
col1, col2 = st.columns(2)
with col1:
    st.markdown("<p class='status-tag'>🇺🇸 Transcripción (EN)</p>", unsafe_allow_html=True)
    area_en = st.empty()

with col2:
    st.markdown("<p class='status-tag'>🇪🇸 Traducción en Vivo (ES)</p>", unsafe_allow_html=True)
    area_es = st.empty()

placeholder_audio = st.empty()

# El secreto para el "Tiempo Real": Procesamiento inmediato al detectar bytes
audio_input = st.audio_input("Dictado continuo (Inglés)")

if audio_input:
    try:
        # 1. Guardado ultra-rápido en RAM/Temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_input.getvalue())
            tmp_path = tmp_file.name

        # 2. Transcripción instantánea
        with open(tmp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=f,
                language="en",
                temperature=0
            )
        
        texto_ingles = transcript.text.strip()

        if texto_ingles:
            # Mostramos el inglés inmediatamente
            area_en.markdown(f'<div class="live-text-box">{texto_ingles}</div>', unsafe_allow_html=True)

            # 3. TRADUCCIÓN EN STREAMING (Aquí es donde se ve el texto escribiéndose)
            response_stream = client.chat.completions.create(
                model="gpt-4o", # Usamos el modelo más rápido (Omni)
                messages=[
                    {"role": "system", "content": "Eres un intérprete simultáneo. Traduce del inglés al español de forma fluida. Solo devuelve el texto traducido."},
                    {"role": "user", "content": texto_ingles}
                ],
                stream=True # ESTO PERMITE QUE EL TEXTO APAREZCA MIENTRAS SE GENERA
            )

            texto_traducido_acumulado = ""
            for chunk in response_stream:
                if chunk.choices[0].delta.content:
                    texto_traducido_acumulado += chunk.choices[0].delta.content
                    # Actualizamos la pantalla palabra por palabra
                    area_es.markdown(f'<div class="live-text-box">{texto_traducido_acumulado}▌</div>', unsafe_allow_html=True)

            # 4. Voz final automática
            audio_out = client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=texto_traducido_acumulado
            )
            with placeholder_audio:
                st.audio(audio_out.content, format="audio/mp3", autoplay=True)

        os.remove(tmp_path)

    except Exception as e:
        st.error(f"Error de flujo: {e}")
