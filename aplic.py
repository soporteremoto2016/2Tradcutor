import streamlit as st
from audio_recorder_streamlit import audio_recorder
from openai import OpenAI
import tempfile
import os

st.set_page_config(page_title="2Bilingue Pro - Estable", page_icon="🎙️")

# --- LOGIN ---
if "auth" not in st.session_state:
    st.title("🔐 Acceso 2Bilingue")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if p == "Seguridad2026*+":
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- CONFIGURACIÓN ---
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
client = OpenAI(api_key=api_key) if api_key else None

st.title("🎙️ Traductor de Voz a Texto (Modo Estable)")
st.write("Este modo garantiza la captura de audio en cualquier navegador.")

# --- INTERFAZ DE GRABACIÓN ---
if client:
    st.write("### 1. Pulsa el micrófono para grabar")
    # Este componente muestra una onda real mientras hablas
    audio_bytes = audio_recorder(
        text="Haz clic para grabar...",
        recording_color="#e8b62c",
        neutral_color="#6aa36f",
        icon_size="3x",
    )

    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav")
        st.write("### 2. Procesando traducción...")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            # 1. Transcripción con Whisper
            with open(tmp_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=f, 
                    language="en"
                )
            
            text_en = transcript.text
            
            if text_en:
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"🇺🇸 **Inglés:**\n\n{text_en}")
                
                # 2. Traducción con GPT
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Traduce este texto al español de forma profesional."},
                        {"role": "user", "content": text_en}
                    ]
                )
                text_es = response.choices[0].message.content
                
                with col2:
                    st.success(f"🇪🇸 **Español:**\n\n{text_es}")
            else:
                st.warning("No se detectó voz clara. Intenta de nuevo.")

        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
else:
    st.warning("👈 Ingresa tu OpenAI API Key para comenzar.")
