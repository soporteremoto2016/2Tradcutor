import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from streamlit_autorefresh import st_autorefresh
from openai import OpenAI
import queue
import pydub
import os
import tempfile

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="2Bilingue Pro - Real Time", layout="wide")

if "user" not in st.session_state: st.session_state.user = None
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "history" not in st.session_state: st.session_state.history = []
if "buffer" not in st.session_state: st.session_state.buffer = pydub.AudioSegment.empty()

# Refresco automático cada 2 segundos para procesar el texto
st_autorefresh(interval=2000, key="datarefresh")

# --- 2. LOGIN ---
if not st.session_state.user:
    st.title("🎙️ Acceso Sistema Intérprete")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
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

# --- 4. INTERFAZ ---
st.sidebar.header(f"👤 {st.session_state.user}")
st.session_state.api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=st.session_state.api_key)

st.title("🚀 Traducción Simultánea Escrita (EN ➔ ES)")

col_en, col_es = st.columns(2)
area_en = col_en.empty()
area_es = col_es.empty()

# --- 5. MOTOR DE STREAMING ---
if st.session_state.api_key:
    client = OpenAI(api_key=st.session_state.api_key)
    
    ctx = webrtc_streamer(
        key="interpreter",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        async_processing=True
    )

    if ctx.audio_processor:
        # 1. Extraer audio de la cola
        frames = []
        while True:
            try:
                frames.append(ctx.audio_processor.audio_queue.get_nowait())
            except queue.Empty:
                break
        
        # 2. Convertir y acumular en el buffer
        if frames:
            for frame in frames:
                sound = pydub.AudioSegment(
                    data=frame.to_ndarray().tobytes(),
                    sample_width=frame.format.bytes,
                    frame_rate=frame.sample_rate,
                    channels=len(frame.layout.channels)
                )
                st.session_state.buffer += sound

        # 3. Procesar si tenemos más de 3 segundos de voz
        if len(st.session_state.buffer) > 3000:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                st.session_state.buffer.export(tmp.name, format="wav")
                
                try:
                    # Transcripción rápida
                    with open(tmp.name, "rb") as f:
                        trans = client.audio.transcriptions.create(model="whisper-1", file=f, language="en")
                    
                    if trans.text.strip():
                        # Traducción profesional
                        res = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "Traduce de inglés a español de forma directa."},
                                {"role": "user", "content": trans.text}
                            ]
                        )
                        traduccion = res.choices[0].message.content
                        
                        # Actualizar historial y limpiar buffer
                        st.session_state.history.append({"en": trans.text, "es": traduccion})
                        st.session_state.buffer = pydub.AudioSegment.empty()
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    if os.path.exists(tmp.name): os.remove(tmp.name)

# --- 6. RENDERIZADO DE RESULTADOS ---
# Mostramos siempre los últimos resultados en las cajas principales
if st.session_state.history:
    last = st.session_state.history[-1]
    area_en.info(f"🇺🇸 **Inglés:**\n{last['en']}")
    area_es.success(f"🇪🇸 **Español:**\n{last['es']}")

    with st.expander("Transcripción completa de la sesión"):
        for item in reversed(st.session_state.history):
            st.write(f"**EN:** {item['en']}")
            st.write(f"**ES:** {item['es']}")
            st.divider()
