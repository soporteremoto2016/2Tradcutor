import streamlit as st
from openai import OpenAI
import tempfile
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="2Bilingue - Traductor Persistente", layout="wide")

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

# --- 4. INTERFAZ Y CONTENEDORES (CRÍTICO) ---
st.title("🎙️ Traductor: Inglés a Español")

# Reservamos los espacios antes de procesar para que no desaparezcan
col_izq, col_der = st.columns(2)
placeholder_ingles = col_izq.empty()
placeholder_espanol = col_der.empty()
placeholder_audio = st.empty()

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

                # Paso 2: Transcripción (Inglés)
                with open(tmp_path, "rb") as f:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=f,
                        language="en",
                        temperature=0
                    )
                
                texto_ingles = transcript.text.strip()

                if texto_ingles:
                    # Paso 3: Traducción (Español)
                    res_traduccion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Traduce íntegramente del INGLÉS al ESPAÑOL. Solo entrega la traducción."},
                            {"role": "user", "content": texto_ingles}
                        ],
                        temperature=0
                    )
                    texto_espanol = res_traduccion.choices[0].message.content.strip()

                    # Paso 4: Generación de Voz
                    audio_tts = client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=texto_espanol
                    )

                    # --- PASO 5: RENDERIZADO EN CONTENEDORES RESERVADOS ---
                    # Esto asegura que el texto se mantenga visible
                    placeholder_ingles.markdown(f"### 🇺🇸 Escuchado\n{texto_ingles}")
                    placeholder_espanol.markdown(f"### 🇪🇸 Traducción\n{texto_espanol}")
                    
                    # El audio se coloca en su propio contenedor
                    with placeholder_audio:
                        st.audio(audio_tts.content, format="audio/mp3", autoplay=True)
                    
                    st.session_state.last_audio_id = current_id
                    status.update(label="✅ Traducción completada", state="complete")

                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except Exception as e:
            st.error(f"Error: {e}")
