import streamlit as st
from openai import OpenAI
import tempfile
import os

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="2Bilingue Pro - Flujo Corregido", layout="wide")

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
    st.info("Dirección: Voz (ES/EN) ➔ Texto ➔ Traducción ➔ Voz")

# --- 4. LÓGICA DE TRADUCCIÓN CON FLUJO CORREGIDO ---
st.title("🎙️ Traductor Profesional Corregido")

if not st.session_state.api_key:
    st.warning("⚠️ Ingresa tu API Key para comenzar.")
    st.stop()

client = OpenAI(api_key=st.session_state.api_key)

# Widget de entrada
audio_input = st.audio_input("Graba ahora tu mensaje")

if audio_input is not None:
    # Evitar doble procesamiento por recarga de Streamlit
    current_id = f"{audio_input.size}_{audio_input.name}"
    
    if current_id != st.session_state.last_audio_id:
        try:
            with st.status("🧠 Procesando flujo de datos...", expanded=True) as status:
                
                # Paso 1: Guardado y Transcripción (LO QUE SE ESCUCHA)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                    tmp_file.write(audio_input.getvalue())
                    tmp_path = tmp_file.name

                with open(tmp_path, "rb") as f:
                    # Forzamos parámetros para evitar alucinaciones (como lo de Amara.org)
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=f,
                        prompt="Transcripción literal de voz humana. No inventar subtítulos.",
                        temperature=0
                    )
                
                # Esta es la variable de entrada real
                texto_escuchado_original = transcript.text.strip()

                if not texto_escuchado_original or len(texto_escuchado_original) < 3:
                    st.error("No se detectó audio claro. Intenta de nuevo.")
                else:
                    # Paso 2: Traducción (LO QUE SE TRADUCE)
                    # Usamos un prompt que garantiza la inversión del idioma
                    res_traduccion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Eres un traductor exacto. Si el texto está en español, tradúcelo al inglés. Si está en inglés, al español. Solo devuelve la traducción íntegra."},
                            {"role": "user", "content": texto_escuchado_original}
                        ],
                        temperature=0
                    )
                    texto_traducido_final = res_traduccion.choices[0].message.content.strip()

                    # Paso 3: Generación de Voz de la traducción
                    audio_tts = client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=texto_traducido_final
                    )

                    # Paso 4: Visualización en columnas (MAPEO CORREGIDO)
                    # Columna Izquierda: Siempre lo que el usuario habló (Original)
                    # Columna Derecha: Siempre el resultado de la IA (Traducción)
                    c1, c2 = st.columns(2)
                    
                    with c1:
                        st.info("👂 **Lo que el sistema escuchó:**")
                        st.write(texto_escuchado_original)
                    
                    with c2:
                        st.success("🇺🇸 **Traducción realizada:**")
                        st.subheader(texto_traducido_final)

                    # Paso 5: Reproducción de la traducción
                    st.audio(audio_tts.content, format="audio/mp3", autoplay=True)
                    
                    # Actualizar ID para evitar bucles
                    st.session_state.last_audio_id = current_id
                    status.update(label="✅ Finalizado correctamente", state="complete")

                # Limpieza de archivo temporal
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except Exception as e:
            st.error(f"Error en el sistema: {e}")
