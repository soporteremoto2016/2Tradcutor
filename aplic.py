import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from openai import OpenAI
import queue
import pydub
import os
import tempfile

st.set_page_config(page_title="2Bilingue Final", layout="wide")

# --- LOGIN ---
if "auth" not in st.session_state:
    st.title("🔐 Acceso 2Bilingue")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if p == "Seguridad2026*+":
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- SIDEBAR ---
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

st.title("🎙️ Intérprete Simultáneo")

# Contenedores fijos para que NO desaparezcan
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
    # Este componente es el que ves en tu imagen
    ctx = webrtc_streamer(
        key="interpreter-v3",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    )

    # BOTÓN MÁGICO: En lugar de hacerlo automático y que se bloquee ("Running"),
    # vamos a usar un disparador manual de procesamiento para probar si traduce.
    if ctx.audio_processor:
        if st.button("🔄 PROCESAR AUDIO AHORA"):
            st.write("Analizando buffer...")
            
            audio_buffer = pydub.AudioSegment.empty()
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
                    audio_buffer += sound

                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    audio_buffer.export(tmp.name, format="wav")
                    try:
                        # 1. Transcribir
                        with open(tmp.name, "rb") as f:
                            trans = client.audio.transcriptions.create(model="whisper-1", file=f)
                        
                        if trans.text:
                            area_en.info(f"🇺🇸 **EN:** {trans.text}")
                            # 2. Traducir
                            res = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "user", "content": f"Traduce: {trans.text}"}]
                            )
                            area_es.success(f"🇪🇸 **ES:** {res.choices[0].message.content}")
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        if os.path.exists(tmp.name): os.remove(tmp.name)
            else:
                st.warning("No se ha detectado audio aún. Habla un poco más.")

else:
    st.warning("👈 Ingresa tu API Key.")
