import streamlit as st
from openai import OpenAI
import json
import re

# ---------------- 1. SETUP DE EXPERTO ----------------
st.set_page_config(page_title="2Bilingue Live Translator", page_icon="🎙️", layout="wide")

# Inicialización segura del estado
if "messages" not in st.session_state: st.session_state.messages = []
if "user" not in st.session_state: st.session_state.user = None
if "api_key" not in st.session_state: st.session_state.api_key = ""

# Estilos refinados
st.markdown("""
    <style>
    .stApp { background-color: #F0F2F6; }
    .main-card { background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .translation-box { border-left: 5px solid #1565C0; background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 10px 0; }
    </style>
""", unsafe_allow_html=True)

# ---------------- 2. GESTIÓN DE DATOS ----------------
def load_db():
    try:
        with open("data.json", "r") as f: return json.load(f)
    except: return {}

def save_db(data):
    with open("data.json", "w") as f: json.dump(data, f)

db = load_db()

# ---------------- 3. AUTENTICACIÓN ----------------
if not st.session_state.user:
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.title("🔐 Acceso 2Bilingue")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Entrar", use_container_width=True):
            if p == "Seguridad2026*+":
                st.session_state.user = u
                if u not in db:
                    db[u] = {"stats": {"conversaciones": 0, "nivel": "A1"}}
                    save_db(db)
                st.rerun()
            else: st.error("Clave incorrecta")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ---------------- 4. INTERFAZ PRINCIPAL ----------------
with st.sidebar:
    st.title(f"👤 {st.session_state.user}")
    st.session_state.api_key = st.text_input("OpenAI API Key", value=st.session_state.api_key, type="password")
    if st.button("Cerrar Sesión"):
        st.session_state.user = None
        st.rerun()

st.title("🎙️ Traductor Simultáneo Pro")
st.info("Instrucciones: Activa el micro, habla y el sistema traducirá al inglés automáticamente.")

if not st.session_state.api_key:
    st.warning("⚠️ Inserta tu API Key en la barra lateral para comenzar.")
    st.stop()

client = OpenAI(api_key=st.session_state.api_key)

# ---------------- 5. LÓGICA DE TRADUCCIÓN "EN LÍNEA" ----------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("👂 Escucha (Español)")
    # El widget de audio_input es el trigger
    audio_file = st.audio_input("Grabar voz para traducir")

if audio_file:
    with st.spinner("Interpretando..."):
        # 1. Transcripción inmediata del audio original
        audio_file.name = "input.wav"
        transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        texto_original = transcript.text
        
        with col_left:
            st.markdown(f"**Dijeron:** *{texto_original}*")

        # 2. Traducción y Respuesta de IA (Simultaneidad simulada)
        # Usamos gpt-4o-mini para máxima velocidad
        prompt_traduccion = f"Translate the following Spanish text to natural English: '{texto_original}'. Provide only the translation."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a professional simultaneous interpreter."},
                      {"role": "user", "content": prompt_traduccion}]
        )
        traduccion_texto = response.choices[0].message.content

        with col_right:
            st.subheader("🇺🇸 Traducción (Inglés)")
            st.markdown(f'<div class="translation-box"><h4>{traduccion_texto}</h4></div>', unsafe_allow_html=True)
            
            # 3. Voz automática (TTS)
            tts = client.audio.speech.create(
                model="tts-1",
                voice="onyx",
                input=traduccion_texto
            )
            st.audio(tts.content, format="audio/mp3", autoplay=True)

# ---------------- 6. HISTORIAL VISUAL ----------------
with st.expander("Ver historial de traducción"):
    if texto_original := locals().get('texto_original'):
        st.session_state.messages.append({"es": texto_original, "en": traduccion_texto})
    
    for m in reversed(st.session_state.messages):
        st.write(f"🇪🇸 {m['es']}")
        st.write(f"🇬🇧 {m['en']}")
        st.divider()
