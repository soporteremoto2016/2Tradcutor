import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from openai import OpenAI
import pydub
import os
import tempfile

st.set_page_config(page_title="2Bilingue Pro - Conector Total", layout="wide")

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
api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=st.session_state.get("api_key", ""))
if api_key: st.session_state.api_key = api_key
client = OpenAI(api_key=st.session_state.api_key) if st.session_state.get("api_key") else None

st.title("🎙️ Traductor: Conexión Garantizada")

# --- PROCESADOR CON AUTO-DETECCIÓN ---
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.buffer = pydub.AudioSegment.empty()

    def recv_audio(self, frame):
        # Esta es la parte crítica: convertimos el audio a un formato estándar
        # que Whisper SIEMPRE entiende (16000Hz, Mono, 16-bit)
        array = frame.to_ndarray()
        sound = pydub.AudioSegment(
            data=array.tobytes(),
            sample_width=frame.format.bytes,
            frame_rate=frame.sample_rate,
            channels=len(frame.layout.channels)
        )
        # Normalizamos el audio para que el sistema no sea "sordo"
        self.buffer += sound.set_frame_rate(16000).set_channels(1)
        return frame

# --- INTERFAZ ---
if client:
    # Mostramos un mensaje de ayuda visual
    st.info("1. Dale a START | 2. Habla fuerte | 3. Dale al botón de Traducir")
    
    ctx = webrtc_streamer(
        key="conector-universal",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=AudioProcessor,
        # Forzamos al navegador a usar configuraciones de audio estándar
        media_stream_constraints={
            "audio": {
                "sampleRate": 16000,
                "channelCount": 1,
                "echoCancellation": True,
                "noiseSuppression": True,
            },
            "video": False,
        },
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        async_processing=True,
    )

    st.divider()

    # BOTÓN DE ACCIÓN
    if st.button("🚀 TRADUCIR AHORA", use_container_width=True):
        if ctx.audio_processor and len(ctx.audio_processor.buffer) > 500: # Si hay al menos medio segundo
            with st.spinner("Procesando voz..."):
                audio_data = ctx.audio_processor.buffer
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    audio_data.export(tmp.name, format="wav")
                    
                    try:
                        with open(tmp.name, "rb") as f:
                            trans = client.audio.transcriptions.create(model="whisper-1", file=f)
                        
                        if trans.text.strip():
                            st.chat_message("user").write(f"**Inglés:** {trans.text}")
                            
                            res = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "user", "content": f"Traduce al español: {trans.text}"}]
                            )
                            st.chat_message("assistant").write(f"**Español:** {res.choices[0].message.content}")
                            
                            # Limpiamos el buffer para la siguiente frase
                            ctx.audio_processor.buffer = pydub.AudioSegment.empty()
                        else:
                            st.error("El sistema no detectó palabras claras. ¡Intenta hablar más cerca del micro!")
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        if os.path.exists(tmp.name): os.remove(tmp.name)
        else:
            st.warning("No hay audio detectado. Por favor, verifica que tu micrófono no esté silenciado físicamente.")

else:
    st.warning("👈 Por favor, ingresa tu API Key en la izquierda.")
