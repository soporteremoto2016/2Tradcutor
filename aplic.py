import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from openai import OpenAI
import queue
import pydub
import os
import tempfile

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="2Bilingue Pro - Real Time", layout="wide")

if "user" not in st.session_state: st.session_state.user = None
if "api_key" not in st.session_state: st.session_state.api_key = ""

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

# --- 3. PROCESADOR DE AUDIO (EL CEREBRO) ---
class VideoProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_queue = queue.Queue()

    def recv_audio(self, frame):
        # Captura los frames del micrófono y los pone en una fila
        self.audio_queue.put(frame)
        return frame

# --- 4. INTERFAZ ---
st.sidebar.header(f"👤 {st.session_state.user}")
st.session_state.api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=st.session_state.api_key)

st.title("🚀 Traducción Simultánea Profesional")
st.info("Instrucciones: Dale a 'Start', habla en inglés y el sistema procesará fragmentos automáticamente.")

col_en, col_es = st.columns(2)
area_en = col_en.empty()
area_es = col_es.empty()

# --- 5. LÓGICA DE WEBRTC Y OPENAI ---
if st.session_state.api_key:
    client = OpenAI(api_key=st.session_state.api_key)
    
    webrtc_ctx = webrtc_streamer(
        key="translator",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=VideoProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    )

    # Si el micrófono está encendido
    if webrtc_ctx.audio_processor:
        st.success("🎤 Micrófono conectado. Procesando flujo de datos...")
        
        # Buffer para acumular audio y enviarlo a traducir cada cierto tiempo
        if "audio_buffer" not in st.session_state:
            st.session_state.audio_buffer = pydub.AudioSegment.empty()

        # Intentamos extraer audio de la fila del procesador
        try:
            # Recuperamos los fragmentos de audio
            frames = []
            while True:
                try:
                    frames.append(webrtc_ctx.audio_processor.audio_queue.get_nowait())
                except queue.Empty:
                    break
            
            if len(frames) > 0:
                # Convertimos frames a audio procesable
                for frame in frames:
                    sound = pydub.AudioSegment(
                        data=frame.to_ndarray().tobytes(),
                        sample_width=frame.format.bytes,
                        frame_rate=frame.sample_rate,
                        channels=len(frame.layout.channels)
                    )
                    st.session_state.audio_buffer += sound

                # Cuando tenemos suficiente audio (ej. 5 segundos), traducimos
                if len(st.session_state.audio_buffer) > 5000:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                        st.session_state.audio_buffer.export(tmp_file.name, format="wav")
                        
                        # 1. Transcribir
                        with open(tmp_file.name, "rb") as f:
                            trans = client.audio.transcriptions.create(model="whisper-1", file=f, language="en")
                        
                        texto_en = trans.text
                        area_en.markdown(f"**Escuchado:**\n{texto_en}")

                        # 2. Traducir con Stream para velocidad
                        if texto_en:
                            res = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "system", "content": "Traduce al español."}, {"role": "user", "content": texto_en}],
                                stream=True
                            )
                            
                            traduccion = ""
                            for chunk in res:
                                if chunk.choices[0].delta.content:
                                    traduccion += chunk.choices[0].delta.content
                                    area_es.markdown(f"**Traducido:**\n{traduccion}▌")
                        
                        # Limpiamos buffer para la siguiente ráfaga
                        st.session_state.audio_buffer = pydub.AudioSegment.empty()
                        os.remove(tmp_file.name)
                        
        except Exception as e:
            pass # Manejo silencioso de buffers vacíos
else:
    st.warning("👈 Ingresa tu API Key para activar el motor.")
