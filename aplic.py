import streamlit as st
from openai import OpenAI
import json

# ---------------- 1. SETUP ----------------
st.set_page_config(page_title="2Bilingue Live", page_icon="🎙️", layout="wide")

if "messages" not in st.session_state: st.session_state.messages = []
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "user" not in st.session_state: st.session_state.user = None

# ---------------- 2. AUTENTICACIÓN (Simplificada para el ejemplo) ----------------
if not st.session_state.user:
    st.title("🔐 Acceso 2Bilingue")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if p == "Seguridad2026*+":
            st.session_state.user = u
            st.rerun()
    st.stop()

# ---------------- 3. SIDEBAR ----------------
with st.sidebar:
    st.title(f"👤 {st.session_state.user}")
    st.session_state.api_key = st.text_input("OpenAI API Key", value=st.session_state.api_key, type="password")
    if st.button("Limpiar Historial"):
        st.session_state.messages = []
        st.rerun()

# ---------------- 4. LÓGICA PRINCIPAL ----------------
st.title("🎙️ Traductor Simultáneo Voz a Voz")

if not st.session_state.api_key:
    st.warning("⚠️ Inserta tu API Key para continuar.")
    st.stop()

client = OpenAI(api_key=st.session_state.api_key)

col_es, col_en = st.columns(2)

# Widget de entrada de audio
audio_file = st.audio_input("Haz clic para hablar (Español)")

if audio_file:
    try:
        with st.spinner("Procesando..."):
            # 1. Transcripción
            audio_file.name = "input.wav"
            transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
            texto_original = transcript.text.strip()

            # --- VALIDACIÓN CRÍTICA ---
            # Si el texto está vacío o solo tiene puntos/espacios, detenemos el proceso
            if not texto_original or len(texto_original) < 2:
                st.warning("No se detectó voz clara. Por favor, intenta de nuevo.")
            else:
                # 2. Traducción
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Translate the following text from Spanish to English. Only provide the translation, no extra comments."},
                        {"role": "user", "content": texto_original}
                    ]
                )
                traduccion_texto = response.choices[0].message.content.strip()

                # 3. Mostrar Resultados
                with col_es:
                    st.success("Escuchado (ES):")
                    st.write(texto_original)
                
                with col_en:
                    st.success("Traducido (EN):")
                    st.markdown(f"### {traduccion_texto}")
                    
                    # 4. Generar Voz (Solo si hay texto válido)
                    if traduccion_texto:
                        tts = client.audio.speech.create(
                            model="tts-1",
                            voice="nova",
                            input=traduccion_texto
                        )
                        st.audio(tts.content, format="audio/mp3", autoplay=True)
                        
                        # Guardar en historial
                        st.session_state.messages.append({"es": texto_original, "en": traduccion_texto})

    except Exception as e:
        st.error(f"Error técnico: {e}")

# ---------------- 5. HISTORIAL ----------------
if st.session_state.messages:
    st.divider()
    st.subheader("Historial de la sesión")
    for m in reversed(st.session_state.messages):
        st.text(f"🇪🇸 {m['es']}  ➡️  🇺🇸 {m['en']}")
