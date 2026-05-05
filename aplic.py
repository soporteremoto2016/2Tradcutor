import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from openai import OpenAI
import queue
import pydub
import os
import tempfile
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="2Bilingue Pro - Real Time", layout="wide")

if "user" not in st.session_state: st.session_state.user = None
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "transcript_history" not in st.session_state: st.session_state.transcript_history = []

# --- 2. LOGIN ---
if not st.session_state.user:
    st.title("🔐 Acceso 2Bilingue Pro")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if p == "Seguridad2026*+":
            st.session_state.user = u
            st.rerun()
    st.stop()

# --- 3. PROCESADOR DE AUDIO EN TIEMPO REAL ---
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_queue = queue.Queue()

    def recv_audio(self, frame):
        # Captura cruda de audio del navegador
        self.audio_queue.put(frame)
        return frame

# --- 4. INTERFAZ ---
st.sidebar.header(f"👤 {st.session_state.user}")
st.session_state.api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=st.session_state.api_key)

st.title("🚀 Traducción Simultánea Continua")
st.markdown("---")

col_en, col_es = st.columns(2)
area_en = col_en.empty()
area_es = col_es.empty()

# --- 5. MOTOR DE STREAMING ---
if st.session_state.api_key:
    client = OpenAI(api_key=st.session_state.api_key)
    
    ctx = webrtc_streamer(
        key="translator-v2",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    )

    if ctx.audio_processor:
        # Contenedor de estado dinámico
        status_info = st.empty()
        status_info.success("🎤 ESCUCHANDO... Hable ahora.")

        # Buffer persistente en la sesión
        if "buffer" not in st.session_state:
            st.session_state.buffer = pydub.AudioSegment.empty()

        # BUCLE DE PROCESAMIENTO ACTIVO
        while ctx.state.playing:
            # 1. Extraer todos los fragmentos de la cola
            new_frames = []
            while True:
                try:
                    new_frames.append(ctx.audio_processor.audio_queue.get_nowait())
                except queue.Empty:
                    break
            
            # 2. Si hay audio nuevo, lo añadimos al buffer
            if new_frames:
                for frame in new_frames:
                    # Convertir frames de PyAV a Pydub
                    sound = pydub.AudioSegment(
                        data=frame.to_ndarray().tobytes(),
                        sample_width=frame.format.bytes,
                        frame_rate=frame.sample_rate,
                        channels=len(frame.layout.channels)
                    )
                    st.session_state.buffer += sound

            # 3. ¿Tenemos suficiente audio para procesar? (Cada 4 segundos)
            if len(st.session_state.buffer) > 4000:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                    st.session_state.buffer.export(tmp_file.name, format="wav")
                    
                    try:
                        # TRANSCRIPCIÓN
                        with open(tmp_file.name, "rb") as f:
                            transcript = client.audio.transcriptions.create(
                                model="whisper-1", 
                                file=f, 
                                language="en"
                            )
                        
                        texto_en = transcript.text
                        if texto_en.strip():
                            area_en.info(f"🇺🇸 **English:**\n{texto_en}")

                            # TRADUCCIÓN
                            res = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {"role": "system", "content": "Translate to Spanish. Be concise."},
                                    {"role": "user", "content": texto_en}
                                ]
                            )
                            texto_es = res.choices[0].message.content
                            area_es.success(f"🇪🇸 **Español:**\n{texto_es}")
                            
                            # Opcional: Acumular historial
                            st.session_state.transcript_history.append(f"EN: {texto_en} | ES: {texto_es}")

                    except Exception as e:
                        st.error(f"Error de procesamiento: {e}")
                    
                    # Reiniciar buffer para la siguiente ráfaga
                    st.session_state.buffer = pydub.AudioSegment.empty()
                    os.remove(tmp_file.name)

            # Pequeña pausa para no saturar el procesador, luego forzar actualización
            time.sleep(0.5)
            # Esto es lo que permite que el bucle siga corriendo sin intervención del usuario
            if len(new_frames) > 0:
                st.rerun()

else:
    st.warning("👈 Por favor, ingresa tu API Key para activar el motor profesional.")

# --- 6. HISTORIAL DE SESIÓN ---
if st.session_state.transcript_history:
    with st.expander("Ver transcripción completa de la sesión"):
        for line in st.session_state.transcript_history:
            st.write(line)
