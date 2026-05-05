import streamlit as st
from openai import OpenAI
import tempfile
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="2Bilingue - Traductor EN to ES", layout="wide")

if "user" not in st.session_state: st.session_state.user = None
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "last_audio_id" not in st.session_state: st.session_state.last_audio_id = None

# --- 2. LOGIN ---
if not st.session_state.user:
    st.title("🔐 Acceso 2Bilingue")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if p == "Seguridad2026*+":
            st.session_state.user = u
            st.rerun()
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title(f"👤 {st.session_state.user}")
    st.session_state.api_key = st.text_input("OpenAI API Key", value=st.session_state.api_key, type="password")
    st.divider()
    st.success("Modo: Inglés ➔ Español")

# --- 4. LÓGICA DE TRADUCCIÓN UNIDIRECCIONAL ---
st.title("🎙️ Traductor: Inglés a Español")
st.info("Habla en inglés y el sistema traducirá todo al español automáticamente.")

if not st.session_state.api_key:
    st.warning("⚠️ Ingresa tu API Key para comenzar.")
    st.stop()

client = OpenAI(api_key=st.session_state.api_key)

audio_input = st.audio_input("Escuchando inglés...")

if audio_input is not None:
    current_id = f"{audio_input.size}_{audio_input.name}"
    
    if current_id != st.session_state.last_audio_id:
        try:
            with st.status("📡 Procesando traducción...", expanded=True) as status:
                
                # Paso 1: Guardar audio temporal
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                    tmp_file.write(audio_input.getvalue())
                    tmp_path = tmp_file.name

                # Paso 2: Transcripción FORZADA A INGLÉS
                with open(tmp_path, "rb") as f:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=f,
                        language="en",  # Forzamos a que entienda solo inglés
                        prompt="This is a recording in English. Transcribe it literally.",
                        temperature=0
                    )
                
                texto_ingles = transcript.text.strip()

                if not texto_ingles or len(texto_ingles) < 3:
                    st.error("No se detectó audio claro en inglés.")
                else:
                    # Paso 3: Traducción FORZADA A ESPAÑOL
                    res_traduccion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Eres un traductor experto. Tu única tarea es traducir el texto que recibas del INGLÉS al ESPAÑOL de forma natural y completa. No respondas en inglés, solo en español."},
                            {"role": "user", "content": texto_ingles}
                        ],
                        temperature=0
                    )
                    texto_espanol = res_traduccion.choices[0].message.content.strip()

                    # Paso 4: Generación de Voz en Español
                    audio_tts = client.audio.speech.create(
                        model="tts-1",
                        voice="nova", # Voz clara para español
                        input=texto_espanol
                    )

                    # Paso 5: Mostrar en pantalla (Mapeo Correcto)
                    c1, c2 = st.columns(2)
                    
                    with c1:
                        st.markdown("### 🇺🇸 Escuchado (Inglés)")
                        st.info(texto_ingles)
                    
                    with c2:
                        st.markdown("### 🇪🇸 Traducción (Español)")
                        st.success(texto_espanol)

                    # Reproducción automática
                    st.audio(audio_tts.content, format="audio/mp3", autoplay=True)
                    
                    st.session_state.last_audio_id = current_id
                    status.update(label="✅ Traducción completada", state="complete")

                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except Exception as e:
            st.error(f"Error: {e}")
