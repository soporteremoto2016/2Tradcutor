import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from streamlit_autorefresh import st_autorefresh
from openai import OpenAI
import queue
import pydub
import os
import tempfile

st.set_page_config(page_title="2Bilingue Quick-Live", layout="wide")

# Refresco rápido para procesar la cola de audio
st_autorefresh(interval=1500, key="frequent_refresh")

if "history" not in st.session_state: st.session_state.history = []
if "audio_buffer" not in st.session_state: st.session_state.audio_buffer = pydub.AudioSegment.empty()

# --- LOGIN SIMPLIFICADO ---
if "auth" not in st.session_state:
    st.title("🔐 Acceso")
    p = st.text_input("Password", type="password")
    if st.button("Entrar"):
        if p == "Seguridad2026*+":
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- SIDEBAR ---
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

st.title("🎙️ Traducción Instantánea")

# Columnas fijas
col1, col2 = st.columns(2)
area_en = col1.empty()
area_es = col2.empty()

class SimpleAudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_queue = queue.Queue()
    def recv_audio(self, frame):
        self.audio_queue.put(frame)
        return frame

if client:
    webrtc_ctx = webrtc_streamer(
        key="simple-trans",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=SimpleAudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        async_processing=True,
    )

    if webrtc_ctx.audio_processor:
        # Extraer frames
        while True:
            try:
                frame = webrtc_ctx.audio_processor.audio_queue.get_nowait()
                sound = pydub.AudioSegment(
                    data=frame.to_ndarray().tobytes(),
                    sample_width=frame.format.bytes,
                    frame_rate=frame.sample_rate,
                    channels=len(frame.layout.channels)
                )
                st.session_state.audio_buffer += sound
            except queue.Empty:
                break

        # Procesar fragmento cada 2.5 segundos de audio capturado
        if len(st.session_state.audio_buffer) > 2500:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                st.session_state.audio_buffer.export(tmp.name, format="wav")
                try:
                    # 1. Escuchar
                    with open(tmp.name, "rb") as f:
                        trans = client.audio.transcriptions.create(model="whisper-1", file=f)
                    
                    if trans.text.strip():
                        # 2. Traducir
                        res = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": f"Traduce al español: {trans.text}"}]
                        )
                        # 3. Guardar y Mostrar
                        st.session_state.history.append({"en": trans.text, "es": res.choices[0].message.content})
                        st.session_state.audio_buffer = pydub.AudioSegment.empty()
                finally:
                    if os.path.exists(tmp.name): os.remove(tmp.name)

# Mostrar resultados
if st.session_state.history:
    last = st.session_state.history[-1]
    area_en.info(f"🇺🇸 **EN:** {last['en']}")
    area_es.success(f"🇪🇸 **ES:** {last['es']}")

    with st.expander("Historial Completo"):
        for h in reversed(st.session_state.history):
            st.write(f"**{h['en']}** ➔ {h['es']}")
