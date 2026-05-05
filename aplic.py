import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from openai import OpenAI
import queue
import pydub
import os
import tempfile
import time

st.set_page_config(page_title="2Bilingue Pro - Live", layout="wide")

# --- 1. INICIALIZACIÓN CRÍTICA (Evita el AttributeError) ---
if "buffer" not in st.session_state:
    st.session_state.buffer = pydub.AudioSegment.empty()
if "history" not in st.session_state:
    st.session_state.history = []

# --- 2. CONFIGURACIÓN ---
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

# --- 3. PROCESADOR ---
class LiveAudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_queue = queue.Queue()

    def recv_audio(self, frame):
        self.audio_queue.put(frame)
        return frame

# --- 4. INTERFAZ ---
st.title("🎙️ Traducción en Tiempo Real")

col_en, col_es = st.columns(2)
area_en = col_en.empty()
area_es = col_es.empty()

if client:
    webrtc_ctx = webrtc_streamer(
        key="live-v5",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=LiveAudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        async_processing=True,
    )

    if webrtc_ctx.audio_processor:
        # Extraer audios de la cola
        while True:
            try:
                frame = webrtc_ctx.audio_processor.audio_queue.get_nowait()
                sound = pydub.AudioSegment(
                    data=frame.to_ndarray().tobytes(),
                    sample_width=frame.format.bytes,
                    frame_rate=frame.sample_rate,
                    channels=len(frame.layout.channels)
                )
                st.session_state.buffer += sound
            except queue.Empty:
                break

        # PROCESAMIENTO (Cotejamos que el buffer exista y tenga audio)
        # Usamos 3000ms (3 seg) para mayor rapidez
        if len(st.session_state.buffer) > 3000:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                st.session_state.buffer.export(tmp.name, format="wav")
                
                try:
                    with open(tmp.name, "rb") as f:
                        trans = client.audio.transcriptions.create(model="whisper-1", file=f)
                    
                    if trans.text.strip():
                        # Traducción
                        res = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": f"Traduce: {trans.text}"}]
                        )
                        traduccion = res.choices[0].message.content
                        
                        # Mostrar
                        area_en.info(f"🇺🇸 {trans.text}")
                        area_es.success(f"🇪🇸 {traduccion}")
                        st.session_state.history.append({"en": trans.text, "es": traduccion})
                        
                    # Limpiar buffer
                    st.session_state.buffer = pydub.AudioSegment.empty()
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    if os.path.exists(tmp.name): os.remove(tmp.name)

        # Bucle de refresco para que no se detenga
        time.sleep(0.1)
        st.rerun()
else:
    st.warning("Ingresa la API Key para comenzar.")

# Historial
if st.session_state.history:
    with st.expander("Historial"):
        for h in reversed(st.session_state.history):
            st.write(f"**EN:** {h['en']} | **ES:** {h['es']}")
