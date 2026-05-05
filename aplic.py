import streamlit as st
from openai import OpenAI
import json
import tempfile
import os

# --- 1. CONFIGURACIÓN DE ALTO RENDIMIENTO ---
# Aumentamos el límite de subida de archivos (útil para audios largos)
st.set_page_config(page_title="2Bilingue Pro Long-Audio", layout="wide")

if "messages" not in st.session_state: st.session_state.messages = []
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "user" not in st.session_state: st.session_state.user = None

# --- 2. LOGIN Y SEGURIDAD ---
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
    st.info("Optimizando para audios largos (>20 seg).")

# --- 4. LÓGICA DE TRADUCCIÓN PARA AUDIOS LARGOS ---
st.title("🎙️ Traductor de Alta Fidelidad (Audios Largos)")

if not st.session_state.api_key:
    st.warning("⚠️ Configura tu API Key.")
    st.stop()

client = OpenAI(api_key=st.session_state.api_key)

col_izq, col_der = st.columns(2)
placeholder_audio = st.empty()

# Usamos audio_input, pero con un mensaje de guía
audio_input = st.audio_input("Graba tu mensaje completo (sin prisa)")

if audio_input:
    try:
        # Guardado físico para procesar el archivo completo sin cortes de buffer
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_input.getvalue())
            tmp_path = tmp_file.name

        with st.status("🛸 Procesando audio extenso...", expanded=True) as status:
            # 1. Transcripción con PROMPT DE CONTEXTO
            # El 'prompt' aquí ayuda a Whisper a no detenerse y a mantener el estilo
            with open(tmp_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=f,
                    prompt="Este es un audio largo en español. Por favor, transcribe todo el contenido de forma literal, incluyendo cada frase hasta el final.",
                    response_format="text" # Solicitamos texto puro para evitar recortes de objetos JSON
                )
            
            texto_escuchado = transcript.strip()
            
            if not texto_escuchado or len(texto_escuchado) < 5:
                st.error("El audio parece no tener contenido legible.")
            else:
                # 2. Traducción Robusta (GPT-4o-mini)
                # Instrucción para que NO resuma
                prompt_traduccion = f"""
                Actúa como un traductor humano profesional. 
                TRADUCE EL SIGUIENTE TEXTO ÍNTEGRAMENTE AL IDIOMA OPUESTO (Si es ES -> EN / Si es EN -> ES).
                REGLA DE ORO: No omitas ninguna oración. Traduce del principio al fin. 
                TEXTO A TRADUCIR:
                {texto_escuchado}
                """
                
                traduccion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "Eres un traductor literal y completo. No resumes."},
                              {"role": "user", "content": prompt_traduccion}],
                    temperature=0.1
                )
                texto_traducido = traduccion.choices[0].message.content.strip()

                # 3. Voz de salida
                audio_res = client.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=texto_traducido
                )

                # 4. Resultados Visuales
                with col_izq:
                    st.subheader("👂 Texto Completo Detectado")
                    st.info(texto_escuchado)
                
                with col_der:
                    st.subheader("🇺🇸 Traducción Completa")
                    st.success(texto_traducido)

                # 5. Audio
                with placeholder_audio:
                    st.audio(audio_res.content, format="audio/mp3", autoplay=True)
                
                status.update(label="✅ Procesado completo", state="complete", expanded=False)
                st.session_state.messages.append({"orig": texto_escuchado, "trad": texto_traducido})

        os.remove(tmp_path)

    except Exception as e:
        st.error(f"Error: {e}")

# Historial
if st.session_state.messages:
    st.divider()
    with st.expander("Historial"):
        for m in reversed(st.session_state.messages):
            st.write(f"Original: {m['orig']}")
            st.write(f"Traducción: {m['trad']}")
            st.divider()
