import streamlit as st
import google.generativeai as genai
import requests
import PIL.Image
from audio_recorder_streamlit import audio_recorder
from streamlit_geolocation import streamlit_geolocation

# --- 1. SECURE CONFIGURATION ---
# Pulls from your "Secrets" tab securely
try:
    GEMINI_KEY = st.secrets["GEMINI_KEY"]
    SMS_API_KEY = st.secrets["SMS_API_KEY"]
    genai.configure(api_key=GEMINI_KEY)
except Exception:
    st.error("Secrets not found! Add them in Streamlit Settings > Secrets.")

@st.cache_resource
def get_working_model():
    """Automatically finds an available model to prevent 404 errors."""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        targets = ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-pro']
        for model_name in targets:
            if model_name in available_models:
                return genai.GenerativeModel(model_name)
        return genai.GenerativeModel(available_models[0])
    except Exception:
        return genai.GenerativeModel('gemini-1.5-flash')

model = get_working_model()

# --- 2. UI & APP LOGIC ---
st.set_page_config(page_title="PulsePoint AI", layout="wide", page_icon="🚑")
st.title("🚑 PulsePoint: Multi-Modal Triage")

with st.sidebar:
    st.header("📍 Location & Patient")
    location = streamlit_geolocation()
    age = st.number_input("Patient Age", 1, 100, 25)
    contact = st.text_input("Emergency Contact SMS", "9876543210")

col1, col2 = st.columns(2)
with col1:
    cam_image = st.camera_input("Visual Symptoms")
    audio_bytes = audio_recorder(text="Record Cough", pause_threshold=2.0)

with col2:
    symptoms = st.text_area("Describe the condition:", height=150)
    if st.button("EXECUTE AI TRIAGE"):
        if not symptoms:
            st.warning("Please enter symptoms.")
        else:
            with st.spinner("Analyzing..."):
                try:
                    payload = [f"Triage for {age}yo. Symptoms: {symptoms}"]
                    if cam_image:
                        payload.append(PIL.Image.open(cam_image))
                    
                    response = model.generate_content(payload)
                    st.success("### ✅ Triage Report")
                    st.write(response.text)
                    
                    # --- EMERGENCY AUTOMATION ---
                    if "Level 1" in response.text or "Level 2" in response.text:
                        st.error("🚨 CRITICAL ALERT")
                        if location['latitude']:
                            lat, lon = location['latitude'], location['longitude']
                            st.link_button("📍 NAVIGATE TO HOSPITAL", f"https://www.google.com/maps/search/hospital/@{lat},{lon},14z")
                        
                        requests.post("https://www.fast2sms.com/dev/bulkV2", 
                                      data={"message": "EMERGENCY: Level 1/2 Triage.", "route": "q", "numbers": contact},
                                      headers={"authorization": SMS_API_KEY})
                except Exception as e:
                    st.error(f"Error: {e}")
