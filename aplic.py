import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from openai import OpenAI
import queue
import pydub
import os
import tempfile

st.set_page_config(page_title="2Bilingue Rescue Mode", layout="wide")

# --- ESTADO DE SESIÓN ---
if "history" not in st.session_state: st.session_state.history = []
if "audio_buffer" not in st.session_state: st.session_state.audio_buffer = pydub.AudioSegment.empty()
if "frames_processed" not in st.session_state: st.session_state.frames_processed = 0

# --- LOGIN ---
if "auth" not in st.session_state:
    st.title("🔐 Acceso de Emergencia")
    p = st.text_input("Password", type="password")
    if st.button("Abrir Sistema"):
        if p == "Seguridad2026*+":
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- SIDEBAR ---
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

st.title("🎙️ Intérprete Pro: Diagnóstico Activo")

# --- CONSOLA DE DIAGNÓSTICO (Para saber qué pasa) ---
with st.expander("🛠️ Consola de Rastreo (Debug)", expanded=True):
    diag_col1, diag_col2 = st.columns(2)
    frames_info = diag_col1.empty()
    buffer_info = diag_col2.empty()
    api_status = st.empty()

# --- INTERFAZ DE TRADUCCIÓN ---
col_en, col_es = st.columns(2)
area_en = col_en.empty()
area_es = col_es.empty()

class DiagnosticProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_queue = queue.Queue()
    def recv_audio(self, frame):
        self.audio_queue.put(frame)
        return frame

if client:
    webrtc_ctx = webrtc_streamer(
        key="emergency-trans",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=DiagnosticProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        async_processing=True,
    )

    if webrtc_ctx.audio_processor:
        # 1. Capturar audio de la cola
        while True:
            try:
                frame = webrtc_ctx.audio_processor.audio_queue.get_nowait()
                st.session_state.frames_processed += 1
                
                # Convertir a audio real
                sound = pydub.AudioSegment(
                    data=frame.to_ndarray().tobytes(),
                    sample_width=frame.format.bytes,
                    frame_rate=frame.sample_rate,
                    channels=len(frame.layout.channels)
                )
                st.session_state.audio_buffer += sound
            except queue.Empty:
                break

        # Mostrar estado en la consola
        frames_info.metric("Frames Recibidos", st.session_state.frames_processed)
        buffer_info.metric("Segundos en Buffer", round(len(st.session_state.audio_buffer)/1000, 1))

        # 2. Procesar cada 3 segundos
        if len(st.session_state.audio_buffer) > 3000:
            api_status.warning("⏳ Enviando a OpenAI...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                st.session_state.audio_buffer.export(tmp.name, format="wav")
                try:
                    # Transcripción
                    with open(tmp.name, "rb") as f:
                        trans = client.audio.transcriptions.create(model="whisper-1", file=f)
                    
                    if trans.text.strip():
                        # Traducción
                        res = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": f"Translate to Spanish: {trans.text}"}]
                        )
                        st.session_state.history.append({"en": trans.text, "es": res.choices[0].message.content})
                        api_status.success("✅ ¡Traducción recibida!")
                    else:
                        api_status.info("ℹ️ Audio procesado, pero no se detectaron palabras.")
                    
                    # Limpiar
                    st.session_state.audio_buffer = pydub.AudioSegment.empty()
                except Exception as e:
                    api_status.error(f"❌ Error de API: {str(e)}")
                finally:
                    if os.path.exists(tmp.name): os.remove(tmp.name)
        
        # Refrescar automáticamente para procesar la siguiente tanda
        st.rerun()

# 3. Mostrar resultados
if st.session_state.history:
    last = st.session_state.history[-1]
    area_en.info(f"🇺🇸 **EN:** {last['en']}")
    area_es.success(f"🇪🇸 **ES:** {last['es']}")
