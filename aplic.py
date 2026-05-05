import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from openai import OpenAI
import queue
import pydub
import os
import tempfile

st.set_page_config(page_title="2Bilingue Pro - Live", layout="wide")

# --- ESTADO DE SESIÓN ---
if "history" not in st.session_state: st.session_state.history = []
if "audio_buffer" not in st.session_state: st.session_state.audio_buffer = pydub.AudioSegment.empty()

# --- SIDEBAR ---
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

st.title("🎙️ Traducción Simultánea por Bloques")
st.info("Habla frases cortas. El sistema traducirá automáticamente cada vez que detecte una pausa.")

# Contenedores para el texto
col_en, col_es = st.columns(2)
area_en = col_en.empty()
area_es = col_es.empty()

class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_queue = queue.Queue()
    def recv_audio(self, frame):
        self.audio_queue.put(frame)
        return frame

if client:
    webrtc_ctx = webrtc_streamer(
        key="block-translator",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        async_processing=True,
    )

    if webrtc_ctx.audio_processor:
        # 1. Recoger audio de la cola
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

        # 2. PROCESAMIENTO POR UMBRAL (Cada 4 segundos de audio)
        # Esto evita que el "Running" bloquee la visualización constante
        if len(st.session_state.audio_buffer) > 4000:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                st.session_state.audio_buffer.export(tmp.name, format="wav")
                
                try:
                    with open(tmp.name, "rb") as f:
                        trans = client.audio.transcriptions.create(model="whisper-1", file=f)
                    
                    if trans.text.strip():
                        res = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": f"Traduce al español: {trans.text}"}]
                        )
                        # ACTUALIZACIÓN DIRECTA
                        traduccion = res.choices[0].message.content
                        area_en.markdown(f"**🇺🇸 Inglés:**\n{trans.text}")
                        area_es.markdown(f"**🇪🇸 Español:**\n{traduccion}")
                        st.session_state.history.append({"en": trans.text, "es": traduccion})
                    
                    # Limpiar buffer para la siguiente frase
                    st.session_state.audio_buffer = pydub.AudioSegment.empty()
                except Exception as e:
                    st.error(f"Error en el proceso: {e}")
                finally:
                    if os.path.exists(tmp.name): os.remove(tmp.name)
            
            # Solo refrescamos después de procesar un bloque completo
            st.rerun()

# Historial acumulado debajo
if st.session_state.history:
    with st.expander("Ver conversación completa"):
        for h in reversed(st.session_state.history):
            st.write(f"**EN:** {h['en']} | **ES:** {h['es']}")
