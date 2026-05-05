import streamlit as st
from openai import OpenAI
import json
import tempfile
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="2Bilingue Pro Translator", layout="wide")

if "messages" not in st.session_state: st.session_state.messages = []
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "user" not in st.session_state: st.session_state.user = None

# --- 2. LOGIN (Seguridad requerida) ---
if not st.session_state.user:
    st.title("🔐 Acceso 2Bilingue")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if p == "Seguridad2026*+":
            st.session_state.user = u
            st.rerun()
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title(f"👤 {st.session_state.user}")
    st.session_state.api_key = st.text_input("OpenAI API Key", value=st.session_state.api_key, type="password")
    st.divider()
    st.info("Traducción inteligente bidireccional (ES ↔ EN).")

# --- 4. LÓGICA DE TRADUCCIÓN ROBUSTA ---
st.title("🎙️ Traductor Simultáneo Corregido")

if not st.session_state.api_key:
    st.warning("⚠️ Ingresa tu API Key para comenzar.")
    st.stop()

client = OpenAI(api_key=st.session_state.api_key)

col_izq, col_der = st.columns(2)
placeholder_audio = st.empty()

# Widget de entrada de audio
audio_input = st.audio_input("Haz clic y habla ahora...")

if audio_input:
    try:
        # TÉCNICA DE EXPERTO: Uso de archivo temporal para asegurar que el audio no se pierda
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_input.getvalue())
            tmp_path = tmp_file.name

        with st.status("👂 Escuchando y procesando...", expanded=True) as status:
            # 1. Transcripción con archivo físico (Previene el error de 'No se detectó audio')
            with open(tmp_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=f
                )
            
            texto_escuchado = transcript.text.strip()
            
            if not texto_escuchado:
                st.error("No se detectó texto en el audio. Intenta hablar más cerca del micrófono.")
                status.update(label="❌ Audio vacío", state="error")
            else:
                # 2. Traducción Total (Bidireccional y Completa)
                prompt_sistema = """
                Eres un traductor simultáneo de alta fidelidad.
                Instrucciones:
                - Traduce TODO el texto sin omitir detalles.
                - Si el texto está en Español, traduce al Inglés.
                - Si el texto está en Inglés, traduce al Español.
                - Responde ÚNICAMENTE con la traducción.
                """
                
                traduccion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": prompt_sistema},
                        {"role": "user", "content": texto_escuchado}
                    ],
                    temperature=0
                )
                texto_traducido = traduccion.choices[0].message.content.strip()

                # 3. Generación de Audio de salida
                audio_res = client.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=texto_traducido
                )

                # 4. Mostrar en pantalla
                with col_izq:
                    st.subheader("🇪🇸 Escuchado")
                    st.info(texto_escuchado)
                
                with col_der:
                    st.subheader("🇺🇸 Traducido")
                    st.success(texto_traducido)

                # 5. Reproducción automática
                with placeholder_audio:
                    st.audio(audio_res.content, format="audio/mp3", autoplay=True)
                
                status.update(label="✅ Listo", state="complete", expanded=False)
                st.session_state.messages.append({"original": texto_escuchado, "traduccion": texto_traducido})

        # Limpieza del archivo temporal
        os.remove(tmp_path)

    except Exception as e:
        st.error(f"Error técnico: {e}")

# --- 5. HISTORIAL ---
if st.session_state.messages:
    st.divider()
    with st.expander("Historial de traducciones"):
        for m in reversed(st.session_state.messages):
            st.write(f"Voz: {m['original']}")
            st.write(f"Traducción: {m['traduccion']}")
            st.divider()
