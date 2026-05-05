import streamlit as st
from openai import OpenAI
import json
import re

# ---------------- 1. CONFIGURACIÓN E INICIALIZACIÓN ----------------
st.set_page_config(page_title="2Bilingue Pro", page_icon="🌍", layout="centered")

# Inicialización de variables de estado (Evita el AttributeError)
if "user" not in st.session_state:
    st.session_state.user = None
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "messages" not in st.session_state:
    st.session_state.messages = []
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None

# Estilos CSS
st.markdown("""
    <style>
    .stApp { background-color: #73C2FB; }
    .login-container {
        background-color: white; padding: 30px;
        border-radius: 15px; box-shadow: 0px 8px 16px rgba(0,0,0,0.1);
    }
    .login-header { color: #1565C0; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ---------------- 2. FUNCIONES DE DATOS ----------------
def load_data():
    try:
        with open("data.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f)

def clear_session_data():
    st.session_state.messages = []
    st.session_state.topic = ""
    st.session_state.last_audio_id = None

data = load_data()
PASSWORD_REQUERIDA = "Seguridad2026*+"

# ---------------- 3. LÓGICA DE LOGIN ----------------
if not st.session_state.user:
    col1, col2, col3 = st.columns([0.5, 2, 0.5])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h1 class="login-header">🔐 Acceso 2Bilingue</h1>', unsafe_allow_html=True)
        
        user_input = st.text_input("Nombre de Usuario")
        pass_input = st.text_input("Contraseña", type="password")

        if st.button("Ingresar", use_container_width=True):
            if pass_input != PASSWORD_REQUERIDA:
                st.error("Contraseña incorrecta.")
            elif not user_input:
                st.warning("Ingresa un usuario.")
            else:
                if user_input not in data:
                    data[user_input] = {
                        "stats": {"conversaciones": 0, "promedio": 0, "nivel": "A1"}
                    }
                    save_data(data)
                st.session_state.user = user_input
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ---------------- 4. SIDEBAR (API Y STATS) ----------------
with st.sidebar:
    st.header(f"👤 {st.session_state.user}")
    u_data = data.get(st.session_state.user, {})
    stats = u_data.get("stats", {"conversaciones": 0, "promedio": 0, "nivel": "A1"})
    
    st.metric("Conversaciones", stats["conversaciones"])
    st.metric("Nivel", stats["nivel"])
    
    if st.button("Cerrar sesión"):
        st.session_state.user = None
        st.rerun()

    st.divider()
    api_key_input = st.text_input("OpenAI API Key", value=st.session_state.api_key, type="password")
    if st.button("Guardar API Key"):
        st.session_state.api_key = api_key_input
        st.success("Guardada")
        st.rerun()

# ---------------- 5. LÓGICA DE CLASE ----------------
SYSTEM_PROMPT = """You are Paty, a professional English teacher. 
Speak in English, but provide corrections or brief explanations in Spanish.
First, ask the user their level (A1-C2). Keep the topic relevant.
End sessions with 'Evaluación final' and 'Puntuación general: [0-100]'."""

if not st.session_state.api_key:
    st.warning("Configura tu API Key en el menú lateral.")
    st.stop()

client = OpenAI(api_key=st.session_state.api_key)

if not st.session_state.topic:
    st.title("🌍 2Bilingue Pro")
    tema = st.text_input("🎯 ¿Sobre qué practicamos hoy?")
    if st.button("Comenzar"):
        st.session_state.topic = tema
        st.session_state.messages = [{"role": "assistant", "content": f"Hello! Let's talk about {tema}. What is your level (A1, A2, B1, B2, C1, C2)?"}]
        st.rerun()
    st.stop()

# ---------------- 6. CHAT Y PROCESAMIENTO DE AUDIO ----------------
st.title(f"👩‍🏫 Clase: {st.session_state.topic}")

# Mostrar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Entrada de Audio (El Microfono)
audio_data = st.audio_input("🎤 Habla con tu profesora")

if audio_data and id(audio_data) != st.session_state.last_audio_id:
    st.session_state.last_audio_id = id(audio_data)
    
    try:
        with st.spinner("Escuchando y traduciendo..."):
            # 1. Transcripción (Voz a Texto)
            audio_data.name = "audio.wav"
            transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_data)
            user_text = transcript.text
            
            # 2. Agregar a historial y mostrar
            st.session_state.messages.append({"role": "user", "content": user_text})
            with st.chat_message("user"):
                st.write(user_text)

            # 3. Generar respuesta de la IA
            with st.chat_message("assistant"):
                full_history = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages
                response = client.chat.completions.create(model="gpt-4o-mini", messages=full_history)
                reply = response.choices[0].message.content
                
                # 4. Generar Voz (Texto a Voz)
                audio_res = client.audio.speech.create(model="tts-1", voice="nova", input=reply[:4096])
                
                # 5. Mostrar y Guardar
                st.write(reply)
                st.audio(audio_res.content, format="audio/mp3")
                st.session_state.messages.append({"role": "assistant", "content": reply})

                # Lógica de estadísticas (si termina la clase)
                if "Evaluación final" in reply:
                    stats["conversaciones"] += 1
                    match = re.search(r'Puntuación general: (\d+)', reply)
                    if match:
                        score = int(match.group(1))
                        stats["promedio"] = int((stats["promedio"] + score) / 2) if stats["conversaciones"] > 1 else score
                    save_data(data)

    except Exception as e:
        st.error(f"Error procesando audio: {e}")

# Botones de utilidad
st.divider()
col_a, col_b = st.columns(2)
with col_a:
    if st.button("🇪🇸 Traducir última"):
        if st.session_state.messages:
            last = [m for m in st.session_state.messages if m["role"] == "assistant"][-1]["content"]
            tr_res = client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[{"role": "user", "content": f"Traduce al español: {last}"}]
            )
            st.info(tr_res.choices[0].message.content)
with col_b:
    if st.button("🧹 Nuevo Tema"):
        clear_session_data()
        st.rerun()
