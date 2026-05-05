import streamlit as st
from openai import OpenAI
import json

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="2Bilingue Pro Translator", layout="wide")

# Inicialización de estados
if "messages" not in st.session_state: st.session_state.messages = []
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "user" not in st.session_state: st.session_state.user = None

# --- 2. LOGIN (Mantenemos tu seguridad) ---
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
    st.info("Este traductor detecta si hablas en Español o Inglés y traduce al idioma contrario automáticamente.")

# --- 4. LÓGICA DE TRADUCCIÓN MEJORADA ---
st.title("🎙️ Traductor Inteligente (ES ↔ EN)")

if not st.session_state.api_key:
    st.warning("⚠️ Ingresa tu API Key para comenzar.")
    st.stop()

client = OpenAI(api_key=st.session_state.api_key)

# Contenedores visuales
col_input, col_output = st.columns(2)
placeholder_audio = st.empty()

# Entrada de audio
audio_data = st.audio_input("Escuchando...")

if audio_data:
    try:
        audio_data.name = "audio.wav"
        
        with st.status("🧠 Interpretando y Traduciendo...", expanded=True) as status:
            # 1. Transcripción (Whisper)
            # Usamos Whisper para pasar de Voz a Texto
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_data
            )
            texto_detectado = transcript.text.strip()
            
            if not texto_detectado:
                st.warning("No se detectó audio.")
            else:
                # 2. Traducción Inteligente con Prompt Reforzado
                # Aquí es donde arreglamos que traduzca TODO y al idioma correcto
                prompt_sistema = """
                Eres un traductor experto y preciso. 
                Tu tarea es detectar el idioma del texto:
                - Si el texto está en ESPAÑOL, tradúcelo íntegramente al INGLÉS.
                - Si el texto está en INGLÉS, tradúcelo íntegramente al ESPAÑOL.
                REGLAS CRÍTICAS:
                1. No resumas. Traduce cada palabra y detalle.
                2. No añadas comentarios tuyos (como "Aquí está la traducción").
                3. Solo devuelve el texto traducido.
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": prompt_sistema},
                        {"role": "user", "content": texto_detectado}
                    ],
                    temperature=0.3 # Baja temperatura para mayor fidelidad y menos "creatividad"
                )
                texto_traducido = response.choices[0].message.content.strip()

                # 3. Generación de Voz (TTS)
                # Detectamos qué voz usar según el idioma de salida
                # Si el original era español, la salida es inglés (voz nova). 
                # Si el original era inglés, la salida es español (voz nova tiene buen acento español).
                audio_gen = client.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=texto_traducido
                )

                # 4. Mostrar Resultados
                with col_input:
                    st.subheader("👂 Escuchado:")
                    st.info(texto_detectado)
                
                with col_output:
                    st.subheader("📢 Traducción:")
                    st.success(texto_traducido)

                # 5. Audio automático
                with placeholder_audio:
                    st.audio(audio_gen.content, format="audio/mp3", autoplay=True)
                
                # Guardar historial
                st.session_state.messages.append({"orig": texto_detectado, "trad": texto_traducido})
                status.update(label="✅ Traducción completada", state="complete", expanded=False)

    except Exception as e:
        st.error(f"Hubo un error: {e}")

# --- 5. HISTORIAL ---
if st.session_state.messages:
    st.divider()
    with st.expander("Historial de la conversación"):
        for m in reversed(st.session_state.messages):
            st.write(f"Entrada: {m['orig']}")
            st.write(f"Traducción: {m['trad']}")
            st.divider()
