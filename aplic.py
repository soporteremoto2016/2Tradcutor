import streamlit as st
from openai import OpenAI
import json

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="2Bilingue Pro Translator", layout="wide")

if "messages" not in st.session_state: st.session_state.messages = []
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "user" not in st.session_state: st.session_state.user = None

# --- 2. LOGIN ---
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
    if st.button("Limpiar Historial"):
        st.session_state.messages = []
        st.rerun()

# --- 4. CUERPO PRINCIPAL ---
st.title("🎙️ Traductor Simultáneo (Voz a Voz)")

if not st.session_state.api_key:
    st.warning("⚠️ Ingresa tu API Key en la barra lateral.")
    st.stop()

client = OpenAI(api_key=st.session_state.api_key)

# Contenedores para evitar saltos visuales
col_izq, col_der = st.columns(2)
placeholder_audio = st.empty()

# Widget de Micrófono
audio_input = st.audio_input("Escuchando español...")

if audio_input:
    try:
        # Aseguramos que el archivo tenga nombre para Whisper
        audio_input.name = "input.wav"
        
        with st.status("🚀 Procesando...", expanded=True) as status:
            # 1. Transcripción (Whisper)
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_input
            )
            texto_es = transcript.text.strip()
            
            if len(texto_es) < 2:
                st.warning("No se detectó audio claro.")
                status.update(label="Error de captura", state="error")
            else:
                # 2. Traducción (GPT-4o-mini)
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Translate from Spanish to English. Only output the translation, no talk."},
                        {"role": "user", "content": texto_es}
                    ]
                )
                texto_en = res.choices[0].message.content.strip()

                # 3. Generación de Voz (TTS)
                # IMPORTANTE: Usamos .content para obtener los bytes puros
                audio_response = client.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=texto_en
                )
                audio_bytes = audio_response.content # Estos son los bytes reales

                # 4. MOSTRAR RESULTADOS
                with col_izq:
                    st.info("🇪🇸 Escuchado")
                    st.write(texto_es)
                
                with col_der:
                    st.success("🇺🇸 Traducido")
                    st.markdown(f"### {texto_en}")

                # 5. REPRODUCCIÓN AUTOMÁTICA
                # Aquí es donde fallaba: pasamos audio_bytes directamente
                with placeholder_audio:
                    st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                
                st.session_state.messages.append({"es": texto_es, "en": texto_en})
                status.update(label="✅ Traducido con éxito", state="complete", expanded=False)

    except Exception as e:
        st.error(f"Error técnico: {str(e)}")

# --- 5. HISTORIAL ---
if st.session_state.messages:
    st.divider()
    for m in reversed(st.session_state.messages):
        with st.expander(f"Frase: {m['es'][:30]}...", expanded=False):
            st.write(f"**ES:** {m['es']}")
            st.write(f"**EN:** {m['en']}")
