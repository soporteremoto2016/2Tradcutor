import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from openai import OpenAI
import queue
import pydub
import os
import tempfile
import time

st.set_page_config(page_title="2Bilingue Pro - Live Streaming", layout="wide")

# --- LOGIN Y CONFIG ---
if "history" not in st.session_state: st.session_state.history = []
if "api_key" not in st.session_state: st.session_state.api_key = ""

st.sidebar.title("⚙️ Configuración")
st.session_state.api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=st.session_state.api_key)

# --- PROCESADOR DE AUDIO EN TIEMPO REAL ---
class LiveAudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_queue = queue.Queue()

    def recv_audio(self, frame):
        # Captura frames y los mete en la cola sin detener el flujo
        self.audio_queue.put(frame)
        return frame

# --- INTERFAZ PRINCIPAL ---
st.title("🎙️ Intérprete Simultáneo en Vivo")
st.caption("El texto aparecerá automáticamente cada pocos segundos mientras hablas.")

col_en, col_es = st.columns(2)
container_en = col_en.empty()
container_es = col_es.empty()

if st.session_state.api_key:
    client = OpenAI(api_key=st.session_state.api_key)

    webrtc_ctx = webrtc_streamer(
        key="live-translator-v4",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=LiveAudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        async_processing=True,
    )

    # Lógica de procesamiento "en caliente"
    if webrtc_ctx.audio_processor:
        if "audio_buffer" not in st.session_state:
            st.session_state.audio_buffer = pydub.AudioSegment.empty()

        # Extraemos frames de la cola mientras el micro sigue abierto
        new_frames = []
        while True:
            try:
                new_frames.append(webrtc_ctx.audio_processor.audio_queue.get_nowait())
            except queue.Empty:
                break
        
        if new_frames:
            for frame in new_frames:
                sound = pydub.AudioSegment(
                    data=frame.to_ndarray().tobytes(),
                    sample_width=frame.format.bytes,
                    frame_rate=frame.sample_rate,
                    channels=len(frame.layout.channels)
                )
                st.session_state.audio_buffer += sound

        # UMBRAL DE TIEMPO: Procesamos cada 4 segundos de audio acumulado
        if len(st.session_state.buffer) > 4000:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                st.session_state.buffer.export(tmp.name, format="wav")
                
                try:
                    # 1. Whisper transcribe el bloque actual
                    with open(tmp.name, "rb") as f:
                        transcript = client.audio.transcriptions.create(model="whisper-1", file=f)
                    
                    if transcript.text.strip():
                        # 2. GPT traduce el bloque
                        res = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": f"Traduce: {transcript.text}"}]
                        )
                        
                        # Actualizamos la pantalla sin detener el micro
                        container_en.info(f"**🇺🇸 Inglés:**\n{transcript.text}")
                        container_es.success(f"**🇪🇸 Español:**\n{res.choices[0].message.content}")
                        
                        # Guardamos en el historial
                        st.session_state.history.append({"en": transcript.text, "es": res.choices[0].message.content})
                        
                    # IMPORTANTE: Vaciamos el buffer para la siguiente tanda, pero el micro sigue START
                    st.session_state.buffer = pydub.AudioSegment.empty()
                    
                except Exception as e:
                    pass # Manejo silencioso para no interrumpir el flujo
                finally:
                    if os.path.exists(tmp.name): os.remove(tmp.name)

        # Forzamos un pequeño delay y rerun para que Streamlit vuelva a mirar la cola
        time.sleep(0.1)
        st.rerun()

# --- HISTORIAL ACUMULADO ---
if st.session_state.history:
    with st.expander("Historial de la conversación"):
        for item in reversed(st.session_state.history):
            st.write(f"**EN:** {item['en']}  \n**ES:** {item['es']}")
            st.divider()
