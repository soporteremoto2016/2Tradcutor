import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
from openai import OpenAI
import pydub
import os
import tempfile

st.set_page_config(page_title="2Bilingue Pro - Fix", layout="wide")

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

st.title("🎙️ Intérprete Simultáneo (Modo Tanque)")

# --- PROCESADOR ROBUSTO ---
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        # El buffer ahora vive AQUÍ adentro, no en la sesión
        self.buffer = pydub.AudioSegment.empty()

    def recv_audio(self, frame):
        # Convertimos cada pedacito de audio y lo pegamos al tanque
        sound = pydub.AudioSegment(
            data=frame.to_ndarray().tobytes(),
            sample_width=frame.format.bytes,
            frame_rate=frame.sample_rate,
            channels=len(frame.layout.channels)
        )
        self.buffer += sound
        return frame

# --- INTERFAZ ---
col_en, col_es = st.columns(2)
area_en = col_en.empty()
area_es = col_es.empty()

if client:
    ctx = webrtc_streamer(
        key="tanque-audio",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        async_processing=True,
    )

    st.markdown("---")
    # Este botón ahora le pide al procesador su tanque de audio acumulado
    if st.button("🚀 TRADUCIR LO QUE DIJE", use_container_width=True):
        if ctx.audio_processor and len(ctx.audio_processor.buffer) > 0:
            with st.spinner("Extrayendo audio del tanque..."):
                # Sacamos el audio acumulado
                audio_to_process = ctx.audio_processor.buffer
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    audio_to_process.export(tmp.name, format="wav")
                    
                    try:
                        # 1. Whisper
                        with open(tmp.name, "rb") as f:
                            trans = client.audio.transcriptions.create(model="whisper-1", file=f)
                        
                        if trans.text.strip():
                            area_en.info(f"🇺🇸 **Original:** {trans.text}")
                            
                            # 2. GPT Traducción
                            res = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "user", "content": f"Traduce al español: {trans.text}"}]
                            )
                            area_es.success(f"🇪🇸 **Traducción:** {res.choices[0].message.content}")
                            
                            # Limpiamos el tanque del procesador para la siguiente frase
                            ctx.audio_processor.buffer = pydub.AudioSegment.empty()
                        else:
                            st.warning("El audio parece estar en silencio. Prueba a hablar más fuerte.")
                            
                    except Exception as e:
                        st.error(f"Error de API: {e}")
                    finally:
                        if os.path.exists(tmp.name): os.remove(tmp.name)
        else:
            st.warning("⚠️ No hay audio acumulado. Dale a START y habla un momento.")

else:
    st.warning("👈 Ingresa tu API Key.")
