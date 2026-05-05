import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from streamlit_autorefresh import st_autorefresh
from openai import OpenAI
import queue
import pydub
import os
import tempfile

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="2Bilingue Pro Live", layout="wide")

# Refresco cada 2 segundos para forzar la actualización de la UI
st_autorefresh(interval=2000, key="refresh")

if "user" not in st.session_state: st.session_state.user = None
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "history" not in st.session_state: st.session_state.history = []
if "buffer" not in st.session_state: st.session_state.buffer = pydub.AudioSegment.empty()

# --- 2. LOGIN ---
if not st.session_state.user:
    st.title("🚀 Acceso 2Bilingue")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if p == "Seguridad2026*+":
            st.session_state.user = u
            st.rerun()
    st.stop()

# --- 3. PROCESADOR DE AUDIO ---
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_queue = queue.Queue()
    def recv_audio(self, frame):
        self.audio_queue.put(frame)
        return frame

# --- 4. DISEÑO DE INTERFAZ (FUERA DE CONDICIONALES) ---
st.sidebar.header(f"👤 {st.session_state.user}")
st.session_state.api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=st.session_state.api_key)

st.title("🎙️ Traducción Simultánea Profesional")
st.divider()

# ESTAS CAJAS SIEMPRE DEBEN SER VISIBLES
col_en, col_es = st.columns(2)
with col_en:
    st.subheader("🇺🇸 Input: Inglés")
    area_en = st.empty() # Contenedor permanente
    area_en.markdown("---")

with col_es:
    st.subheader("🇪🇸 Output: Español")
    area_es = st.empty() # Contenedor permanente
    area_es.markdown("---")

# --- 5. LÓGICA DE TRADUCCIÓN ---
if st.session_state.api_key:
    client = OpenAI(api_key=st.session_state.api_key)
    
    # El componente WebRTC se muestra aquí
    ctx = webrtc_streamer(
        key="interpreter-live",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        async_processing=True
    )

    if ctx.audio_processor:
        # Extraer audio
        frames = []
        while True:
            try:
                frames.append(ctx.audio_processor.audio_queue.get_nowait())
            except queue.Empty:
                break
        
        if frames:
            for frame in frames:
                sound = pydub.AudioSegment(
                    data=frame.to_ndarray().tobytes(),
                    sample_width=frame.format.bytes,
                    frame_rate=frame.sample_rate,
                    channels=len(frame.layout.channels)
                )
                st.session_state.buffer += sound

        # Procesar cada 3.5 segundos
        if len(st.session_state.buffer) > 3500:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                st.session_state.buffer.export(tmp.name, format="wav")
                try:
                    with open(tmp.name, "rb") as f:
                        trans = client.audio.transcriptions.create(model="whisper-1", file=f, language="en")
                    
                    if trans.text.strip():
                        res = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "system", "content": "Traduce al español."}, {"role": "user", "content": trans.text}]
                        )
                        st.session_state.history.append({"en": trans.text, "es": res.choices[0].message.content})
                        st.session_state.buffer = pydub.AudioSegment.empty()
                except Exception as e:
                    st.error(f"Error de API: {e}")
                finally:
                    if os.path.exists(tmp.name): os.remove(tmp.name)

# --- 6. MOSTRAR RESULTADOS EN TIEMPO REAL ---
if st.session_state.history:
    last = st.session_state.history[-1]
    # Inyectamos el texto en los contenedores 'empty' creados arriba
    area_en.info(f"{last['en']}")
    area_es.success(f"{last['es']}")

    with st.expander("Ver Log de la sesión"):
        for h in reversed(st.session_state.history):
            st.write(f"**EN:** {h['en']}  \n**ES:** {h['es']}")
            st.divider()
