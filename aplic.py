import streamlit as st
from openai import OpenAI
import json
import re

# ---------------- 1. CONFIGURACIÓN E INICIALIZACIÓN ----------------
st.set_page_config(page_title="2Bilingue Pro", page_icon="🌍", layout="centered")

# Funciones de utilidad movidas para limpieza
def get_client():
    return OpenAI(api_key=st.session_state.api_key)

def process_audio_to_text(audio_file, client):
    """Convierte audio a texto usando Whisper."""
    audio_file.name = "audio.wav" # Necesario para que Whisper reconozca el formato
    transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcript.text

def get_ai_response(messages, client):
    """Obtiene respuesta y audio de OpenAI."""
    response = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
    reply = response.choices[0].message.content
    
    # Generar TTS
    audio_res = client.audio.speech.create(model="tts-1", voice="nova", input=reply[:4096])
    return reply, audio_res.content

# ---------------- 2. LÓGICA DE PERSISTENCIA (Resumida) ----------------
# [Mantener tus funciones load_data y save_data aquí]

# ---------------- 3. ESTRUCTURA DE LA APP ----------------
# [Mantener tu lógica de login y Sidebar]

# ---------------- 4. PROCESAMIENTO PRINCIPAL ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Área de interacción de voz
audio_input = st.audio_input("🎤 Presiona para hablar con Paty")

if audio_input and st.session_state.api_key:
    client = get_client()
    
    with st.spinner("Procesando tu voz..."):
        # 1. Transcripción
        user_text = process_audio_to_text(audio_input, client)
        st.session_state.messages.append({"role": "user", "content": user_text})
        
        # 2. IA Responder
        full_system_prompt = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages
        reply, audio_bytes = get_ai_response(full_system_prompt, client)
        
        # 3. Mostrar resultado
        st.chat_message("user").write(user_text)
        with st.chat_message("assistant"):
            st.write(reply)
            st.audio(audio_bytes, format="audio/mp3")
            
        st.session_state.messages.append({"role": "assistant", "content": reply})

# ---------------- 5. TRADUCCIÓN RÁPIDA ----------------
# Sugerencia: Usa un botón en el chat para traducir el último mensaje
if st.button("🌐 Traducir última respuesta"):
    if st.session_state.messages:
        last_msg = st.session_state.messages[-1]["content"]
        # Traducción directa
        trans = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": f"Traduce al español: {last_msg}"}]
        )
        st.info(f"Traducción: {trans.choices[0].message.content}")
