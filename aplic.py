import streamlit as st
from openai import OpenAI
import json
import tempfile
import os
import time

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="2Bilingue Pro - Registro Total", layout="wide")

# Inicializamos variables críticas para que no se pierdan entre recargas
if "user" not in st.session_state: st.session_state.user = None
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "history" not in st.session_state: st.session_state.history = []
if "last_processed_id" not in st.session_state: st.session_state.last_processed_id = None

# --- 2. LOGIN (Seguridad requerida) ---
if not st.session_state.user:
    st.title("🔐 Acceso 2Bilingue")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if p == "Seguridad2026*+":
            st.session_state.user = u
            st.rerun()
    st.stop()

# --- 3. INTERFAZ ---
with st.sidebar:
    st.title(f"👤 {st.session_state.user}")
    st.session_state.api_key = st.text_input("OpenAI API Key", value=st.session_state.api_key, type="password")
    if st.button("Nueva Sesión"):
        st.session_state.history = []
        st.session_state.last_processed_id = None
        st.rerun()

st.title("🎙️ Traductor de Registro Completo")
st.info("Este sistema asegura que cada segundo de audio sea procesado y registrado.")

if not st.session_state.api_key:
    st.warning("⚠️ Ingresa tu API Key para activar el micrófono.")
    st.stop()

client = OpenAI(api_key=st.session_state.api_key)

# Contenedores de interfaz
col_es, col_en = st.columns(2)
area_reproductor = st.empty()

# --- 4. WIDGET DE AUDIO CON CONTROL DE ESTADO ---
# Usamos un ID único para el widget para forzar su estabilidad
audio_data = st.audio_input("Habla ahora (puedes hablar todo el tiempo que necesites)")

# Verificamos si hay un nuevo audio y si es diferente al último que procesamos
if audio_data is not None:
    # Creamos un identificador único basado en el tamaño y nombre para evitar repeticiones
    current_audio_id = f"{audio_data.size}_{audio_data.name}"
    
    if current_audio_id != st.session_state.last_processed_id:
        try:
            with st.status("🔍 Registrando y Traduciendo...", expanded=True) as status:
                # PASO 1: Captura física del buffer
                # Guardamos en un archivo temporal para que Whisper lea el archivo completo del disco
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                    tmp_file.write(audio_data.getbuffer())
                    tmp_path = tmp_file.name

                # PASO 2: Transcripción Literal
                # Usamos un prompt para forzar a la IA a no saltarse nada
                with open(tmp_path, "rb") as f:
                    transcript_res = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=f,
                        prompt="Transcripción exacta de un audio largo en español. No omitas ninguna palabra.",
                        response_format="verbose_json"
                    )
                
                texto_original = transcript_res.text.strip()

                if texto_original:
                    # PASO 3: Traducción Profesional sin recortes
                    traduccion_res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Eres un traductor simultáneo. Traduce el texto íntegramente al idioma opuesto. Si es español a inglés, y viceversa. No resumas, no omitas nada."},
                            {"role": "user", "content": texto_original}
                        ],
                        temperature=0
                    )
                    texto_traducido = traduccion_res.choices[0].message.content.strip()

                    # PASO 4: Voz de salida (TTS)
                    audio_out = client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=texto_traducido
                    )

                    # PASO 5: Registro y Visualización
                    with col_es:
                        st.subheader("🇪🇸 Escuchado")
                        st.info(texto_original)
                    
                    with col_en:
                        st.subheader("🇺🇸 Traducido")
                        st.success(texto_traducido)

                    with area_reproductor:
                        st.audio(audio_out.content, format="audio/mp3", autoplay=True)

                    # Guardamos en el historial de la sesión
                    st.session_state.history.append({
                        "id": current_audio_id,
                        "es": texto_original,
                        "en": texto_traducido
                    })
                    
                    # Marcamos como procesado para no repetir
                    st.session_state.last_processed_id = current_audio_id
                    status.update(label="✅ Registro completado", state="complete", expanded=False)
                
                # Limpieza
                os.remove(tmp_path)
                
        except Exception as e:
            st.error(f"Error en el registro: {e}")

# --- 5. HISTORIAL DE REGISTRO ---
if st.session_state.history:
    st.divider()
    st.subheader("📜 Registro de la Sesión")
    for item in reversed(st.session_state.history):
        with st.expander(f"Registro: {item['es'][:50]}...", expanded=False):
            st.write(f"**Original:** {item['es']}")
            st.write(f"**Traducción:** {item['en']}")
