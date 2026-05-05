import streamlit as st
from openai import OpenAI
import tempfile
import os

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS ---
st.set_page_config(
    page_title="2Bilingue Pro - Traductor de Voz", 
    page_icon="🎙️", 
    layout="wide"
)

# Estilos CSS para mejorar la interfaz
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stStatus { border-radius: 15px; }
    .stAudioInput { border: 2px solid #1565C0; border-radius: 10px; }
    h1 { color: #1565C0; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# Inicialización de estados de sesión
if "user" not in st.session_state: st.session_state.user = None
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "last_audio_id" not in st.session_state: st.session_state.last_audio_id = None

# --- 2. SISTEMA DE AUTENTICACIÓN ---
if not st.session_state.user:
    _, col_login, _ = st.columns([1, 1, 1])
    with col_login:
        st.markdown("<h1>🔐 Acceso 2Bilingue</h1>", unsafe_allow_html=True)
        user_input = st.text_input("Usuario")
        pass_input = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", use_container_width=True):
            if pass_input == "Seguridad2026*+":
                st.session_state.user = user_input
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    st.stop()

# --- 3. BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.title(f"👤 {st.session_state.user}")
    st.session_state.api_key = st.text_input("OpenAI API Key", value=st.session_state.api_key, type="password")
    st.divider()
    st.success("✅ Modo: Inglés ➔ Español")
    st.info("Configurado para audios de larga duración y alta precisión.")
    if st.button("Cerrar Sesión"):
        st.session_state.user = None
        st.rerun()

# --- 4. INTERFAZ PRINCIPAL Y CONTENEDORES ---
st.markdown("<h1>🎙️ Traductor: Inglés a Español</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Habla en inglés y recibe la traducción escrita y en voz al español.</p>", unsafe_allow_html=True)

# Reservamos los espacios fijos para evitar que el texto desaparezca al reproducir audio
col_izq, col_der = st.columns(2)
with col_izq:
    st.markdown("### 🇺🇸 Escuchado (Inglés)")
    placeholder_ingles = st.empty()

with col_der:
    st.markdown("### 🇪🇸 Traducción (Español)")
    placeholder_espanol = st.empty()

placeholder_audio = st.empty()

# --- 5. LÓGICA DE PROCESAMIENTO ---
if not st.session_state.api_key:
    st.warning("⚠️ Por favor, ingresa tu OpenAI API Key en la barra lateral para activar el sistema.")
    st.stop()

client = OpenAI(api_key=st.session_state.api_key)

# Widget de entrada de audio
audio_input = st.audio_input("Haz clic en el micrófono para hablar en inglés")

if audio_input is not None:
    # Generamos un ID único para evitar re-procesamientos infinitos
    current_audio_id = f"{audio_input.size}_{audio_input.name}"
    
    if current_audio_id != st.session_state.last_audio_id:
        try:
            with st.status("🚀 Procesando...", expanded=True) as status:
                
                # PASO 1: Captura física del audio (Evita pérdida de datos en audios largos)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                    tmp_file.write(audio_input.getbuffer())
                    tmp_path = tmp_file.name

                # PASO 2: Transcripción (Whisper) - Optimizada contra alucinaciones
                status.write("👂 Analizando audio en inglés...")
                with open(tmp_path, "rb") as f:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=f,
                        language="en", # Forzamos detección de inglés
                        prompt="Transcripción literal de una lección o conversación en inglés. No añadas subtítulos externos.",
                        temperature=0 # Máxima precisión
                    )
                
                texto_ingles = transcript.text.strip()

                # PASO 3: Validación y Traducción (GPT-4o-mini)
                if len(texto_ingles) < 3:
                    st.error("No se detectó contenido claro. Por favor, habla más cerca del micrófono.")
                    status.update(label="❌ Error de captura", state="error")
                else:
                    status.write("🧠 Traduciendo al español...")
                    res_traduccion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Eres un traductor experto. Traduce el texto íntegramente del INGLÉS al ESPAÑOL. No resumas, no omitas nada y no respondas en inglés."},
                            {"role": "user", "content": texto_ingles}
                        ],
                        temperature=0
                    )
                    texto_espanol = res_traduccion.choices[0].message.content.strip()

                    # PASO 4: Generación de Voz (TTS)
                    status.write("🔊 Generando voz en español...")
                    audio_tts = client.audio.speech.create(
                        model="tts-1",
                        voice="nova", # Voz clara y profesional
                        input=texto_espanol
                    )

                    # PASO 5: Renderizado Persistente
                    placeholder_ingles.info(texto_ingles)
                    placeholder_espanol.success(texto_espanol)
                    
                    with placeholder_audio:
                        st.audio(audio_tts.content, format="audio/mp3", autoplay=True)
                    
                    # Guardamos el ID para finalizar el ciclo
                    st.session_state.last_audio_id = current_audio_id
                    status.update(label="✅ Traducción completada con éxito", state="complete", expanded=False)

                # Limpieza de seguridad
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except Exception as e:
            st.error(f"Hubo un problema técnico: {str(e)}")
