import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from openai import OpenAI
import queue
import pydub
import os
import tempfile

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="2Bilingue - Texto Simultáneo", layout="wide")

if "user" not in st.session_state: st.session_state.user = None
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "transcript" not in st.session_state: st.session_state.transcript = []

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

# --- 3. PROCESADOR DE AUDIO ---
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_queue = queue.Queue()

    def recv_audio(self, frame):
        # Esta función corre en un hilo separado del sistema
        # capturando el audio constantemente
        self.audio_queue.put(frame)
        return frame

# --- 4. INTERFAZ ---
st.sidebar.header(f"👤 {st.session_state.user}")
st.session_state.api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=st.session_state.api_key)

st.title("🎙️ Traductor Simultáneo Escrito (EN ➔ ES)")
st.info("Habla en inglés. El sistema procesará ráfagas de texto automáticamente.")

col_en, col_es = st.columns(2)
area_en = col_en.empty()
area_es = col_es.empty()

# --- 5. LÓGICA DE PROCESAMIENTO ---
if st.session_state.api_key:
    client = OpenAI(api_key=st.session_state.api_key)
    
    # Configuramos WebRTC con servidores STUN de Google para saltar Firewalls
    ctx = webrtc_streamer(
        key="live-translator",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        },
        async_processing=True # Permite que el audio no congele la pantalla
    )

    if ctx.audio_processor:
        # Buffer de audio en la sesión
        if "audio_buffer" not in st.session_state:
            st.session_state.audio_buffer = pydub.AudioSegment.empty()

        # Extraer frames de la cola
        new_frames = []
        while True:
            try:
                new_frames.append(ctx.audio_processor.audio_queue.get_nowait())
            except queue.Empty:
                break
        
        if len(new_frames) > 0:
            # Construir el audio desde los frames recibidos
            for frame in new_frames:
                sound = pydub.AudioSegment(
                    data=frame.to_ndarray().tobytes(),
                    sample_width=frame.format.bytes,
                    frame_rate=frame.sample_rate,
                    channels=len(frame.layout.channels)
                )
                st.session_state.audio_buffer += sound

            # Cada 3.5 segundos de audio acumulado, disparamos la traducción
            if len(st.session_state.audio_buffer) > 3500:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    st.session_state.audio_buffer.export(tmp.name, format="wav")
                    
                    try:
                        # TRANSCRIPCIÓN
                        with open(tmp.name, "rb") as f:
                            trans = client.audio.transcriptions.create(
                                model="whisper-1", file=f, language="en"
                            )
                        
                        text_en = trans.text.strip()
                        if text_en:
                            # TRADUCCIÓN
                            res = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {"role": "system", "content": "Traduce al español."},
                                    {"role": "user", "content": text_en}
                                ]
                            )
                            text_es = res.choices[0].message.content
                            
                            # Mostrar resultados
                            area_en.markdown(f"🇺🇸 **Inglés:**\n{text_en}")
                            area_es.markdown(f"🇪🇸 **Español:**\n{text_es}")
                            
                            # Guardar historial
                            st.session_state.transcript.append(f"EN: {text_en} | ES: {text_es}")
                    except Exception as e:
                        st.error(f"Error de procesamiento: {e}")
                    
                    # Limpiar buffer para la siguiente frase
                    st.session_state.audio_buffer = pydub.AudioSegment.empty()
                    os.remove(tmp.name)
            
            # EL SECRETO: Forzar la recarga para procesar el siguiente pedazo
            st.rerun()

else:
    st.warning("👈 Ingresa tu API Key en la barra lateral para comenzar.")

# --- 6. HISTORIAL ---
if st.session_state.transcript:
    with st.expander("Ver conversación completa"):
        for line in st.session_state.transcript:
            st.write(line)
