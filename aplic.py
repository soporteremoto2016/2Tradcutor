import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from openai import OpenAI
import queue
import pydub
import os
import tempfile

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="2Bilingue - Solo Texto Live", layout="wide")

if "user" not in st.session_state: st.session_state.user = None
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "full_transcript" not in st.session_state: st.session_state.full_transcript = []

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

# --- 3. PROCESADOR DE AUDIO (CAPTURA CRUDA) ---
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_queue = queue.Queue()

    def recv_audio(self, frame):
        self.audio_queue.put(frame)
        return frame

# --- 4. INTERFAZ ---
st.sidebar.header(f"👤 {st.session_state.user}")
st.session_state.api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=st.session_state.api_key)

st.title("🎙️ Traductor Simultáneo Escrito (EN ➔ ES)")
st.caption("Modo optimizado: Solo texto para máxima velocidad y estabilidad.")

col_en, col_es = st.columns(2)
area_en = col_en.empty()
area_es = col_es.empty()

# --- 5. LÓGICA DE PROCESAMIENTO ---
if st.session_state.api_key:
    client = OpenAI(api_key=st.session_state.api_key)
    
    # Iniciamos WebRTC
    ctx = webrtc_streamer(
        key="text-translator",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    )

    if ctx.audio_processor:
        st.toast("🎤 Micrófono activo. El sistema procesará cada 3-4 segundos.")
        
        if "buffer" not in st.session_state:
            st.session_state.buffer = pydub.AudioSegment.empty()

        # Recolectar frames de la cola
        frames = []
        while True:
            try:
                frames.append(ctx.audio_processor.audio_queue.get_nowait())
            except queue.Empty:
                break
        
        # Si hay audio, procesamos
        if len(frames) > 0:
            for frame in frames:
                sound = pydub.AudioSegment(
                    data=frame.to_ndarray().tobytes(),
                    sample_width=frame.format.bytes,
                    frame_rate=frame.sample_rate,
                    channels=len(frame.layout.channels)
                )
                st.session_state.buffer += sound

            # Procesar cuando tengamos ~3.5 segundos de audio
            if len(st.session_state.buffer) > 3500:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    st.session_state.buffer.export(tmp.name, format="wav")
                    
                    try:
                        # 1. Transcribir Inglés
                        with open(tmp.name, "rb") as f:
                            transcript = client.audio.transcriptions.create(
                                model="whisper-1", file=f, language="en"
                            )
                        
                        text_en = transcript.text
                        if text_en.strip():
                            area_en.info(f"🇺🇸 **English:**\n{text_en}")

                            # 2. Traducir a Español
                            res = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {"role": "system", "content": "Traduce al español de forma natural."},
                                    {"role": "user", "content": text_en}
                                ]
                            )
                            text_es = res.choices[0].message.content
                            area_es.success(f"🇪🇸 **Español:**\n{text_es}")
                            
                            # Guardar en historial
                            st.session_state.full_transcript.append(f"EN: {text_en} | ES: {text_es}")
                    except Exception as e:
                        st.error(f"Error de conexión: {e}")
                    
                    # Limpiar buffer y reiniciar ciclo
                    st.session_state.buffer = pydub.AudioSegment.empty()
                    os.remove(tmp.name)
            
            # Forzar recarga automática para seguir escuchando
            st.rerun()

else:
    st.warning("👈 Ingresa tu API Key en la barra lateral.")

# --- 6. HISTORIAL ---
if st.session_state.full_transcript:
    with st.expander("Ver conversación completa"):
        for line in st.session_state.full_transcript:
            st.write(line)
