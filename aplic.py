import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from openai import OpenAI
import queue
import pydub
import os
import tempfile

st.set_page_config(page_title="2Bilingue Pro", layout="wide")

# --- INICIALIZACIÓN ---
if "history" not in st.session_state: st.session_state.history = []
# Usamos un archivo temporal para el buffer en lugar de la memoria de Streamlit
if "temp_audio_path" not in st.session_state:
    st.session_state.temp_audio_path = tempfile.mktemp(suffix=".wav")
    pydub.AudioSegment.empty().export(st.session_state.temp_audio_path, format="wav")

# --- SIDEBAR ---
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

st.title("🎙️ Traducción Simultánea Pro")

# Columnas para ver el texto
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
    ctx = webrtc_streamer(
        key="streaming-fix",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        async_processing=True,
    )

    if ctx.audio_processor:
        # 1. Sacar audio de la cola
        new_audio = pydub.AudioSegment.empty()
        while True:
            try:
                frame = ctx.audio_processor.audio_queue.get_nowait()
                new_audio += pydub.AudioSegment(
                    data=frame.to_ndarray().tobytes(),
                    sample_width=frame.format.bytes,
                    frame_rate=frame.sample_rate,
                    channels=len(frame.layout.channels)
                )
            except queue.Empty:
                break

        if len(new_audio) > 0:
            # Añadir al archivo temporal
            current_audio = pydub.AudioSegment.from_wav(st.session_state.temp_audio_path)
            combined = current_audio + new_audio
            combined.export(st.session_state.temp_audio_path, format="wav")

            # 2. Si tenemos más de 4 segundos, procesamos
            if len(combined) > 4000:
                try:
                    with open(st.session_state.temp_audio_path, "rb") as f:
                        trans = client.audio.transcriptions.create(model="whisper-1", file=f)
                    
                    if trans.text.strip():
                        res = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": f"Translate to Spanish: {trans.text}"}]
                        )
                        # MOSTRAR RESULTADOS INMEDIATAMENTE
                        area_en.info(f"🇺🇸 {trans.text}")
                        area_es.success(f"🇪🇸 {res.choices[0].message.content}")
                        st.session_state.history.append({"en": trans.text, "es": res.choices[0].message.content})
                    
                    # Resetear el archivo temporal para la siguiente frase
                    pydub.AudioSegment.empty().export(st.session_state.temp_audio_path, format="wav")
                except Exception as e:
                    st.error(f"Error: {e}")

        # El truco para que el "Running" no bloquee la interfaz:
        st.button("Actualizar Vista") # Un pequeño ancla visual
        st.rerun()
