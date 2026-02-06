import streamlit as st
import google.generativeai as genai
import requests
import PIL.Image
from audio_recorder_streamlit import audio_recorder
from streamlit_geolocation import streamlit_geolocation
import random

# --- 1. BACKEND & DYNAMIC AI CONFIGURATION ---
GEMINI_KEY = "AIzaSyBAnNjsQQDzO6RolFY8DvObnn8eg3sW-GA"
SMS_API_KEY = "8Xvcz3aZlYhB56qAFxt7s04RbGVUEgoJWINkOywPHTuCSMD1pLErO3a4D6R10Zx8cPYiSdIuLfwsmkXy"

genai.configure(api_key=GEMINI_KEY)

@st.cache_resource
def get_working_model():
    """Dynamically finds a working model to prevent 404 errors."""
    try:
        # Ask the API which models are available for your key
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Priority list (Flash 1.5 is preferred for multi-modal)
        targets = [
            'models/gemini-1.5-flash', 
            'models/gemini-1.5-flash-latest', 
            'models/gemini-pro'
        ]
        
        for t in targets:
            if t in available_models:
                return genai.GenerativeModel(t)
        
        # Fallback to the first available model if targets aren't found
        return genai.GenerativeModel(available_models[0])
    except Exception as e:
        st.error(f"AI Discovery Error: {e}")
        return None

# Initialize the model
model = get_working_model()

# --- 2. FRONTEND UI DESIGN ---
st.set_page_config(page_title="PulsePoint AI Pro", layout="wide", page_icon="🚑")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #e74c3c; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚑 PulsePoint: Multi-Modal Triage & Navigation")

# --- 3. SIDEBAR: LOCATION & PROFILE ---
with st.sidebar:
    st.header("📍 Location & Profile")
    location = streamlit_geolocation()
    
    if location['latitude']:
        st.success(f"GPS Locked: {location['latitude']:.4f}, {location['longitude']:.4f}")
    else:
        st.warning("Please allow GPS access in your browser.")
    
    st.divider()
    age = st.number_input("Patient Age", 1, 100, 25)
    contact = st.text_input("Emergency SMS Number", "9876543210")

# --- 4. MAIN INTERFACE ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📡 Multi-Modal Inputs")
    st.write("**Visual Assessment**")
    cam_image = st.camera_input("Scan physical symptoms")
    
    st.write("**Audio Analysis**")
    audio_bytes = audio_recorder(text="Record Cough (3s)", pause_threshold=3.0)
    if audio_bytes:
        st.audio(audio_bytes)

with col2:
    st.subheader("📝 Symptom Analysis")
    symptoms = st.text_area("Describe condition:", height=150, placeholder="e.g. Chest pain and dizziness...")

    if st.button("EXECUTE ADVANCED TRIAGE"):
        if not symptoms:
            st.warning("Please provide symptoms.")
        elif model is None:
            st.error("AI Model failed to initialize. Check internet/API key.")
        else:
            with st.spinner("Processing Multi-Modal Evidence..."):
                try:
                    # Prepare Data
                    data_payload = [f"Triage for {age}yo. Symptoms: {symptoms}."]
                    if cam_image:
                        data_payload.append(PIL.Image.open(cam_image))
                    
                    prompt = "Act as an Emergency Triage Physician. Provide: 1. URGENCY LEVEL, 2. REASONING, 3. NEXT STEP."
                    
                    # Inference
                    response = model.generate_content([prompt] + data_payload)
                    
                    st.success("## ✅ Triage Report")
                    st.markdown(response.text)
                    
                    # --- 5. EMERGENCY LOGIC ---
                    if "Level 1" in response.text or "Level 2" in response.text:
                        st.error("🚨 EMERGENCY DETECTED")
                        
                        # Navigation Logic
                        if location['latitude']:
                            lat, lon = location['latitude'], location['longitude']
                            maps_url = f"https://www.google.com/maps/search/hospital/@{lat},{lon},14z"
                            st.link_button("📍 START NAVIGATION TO NEAREST HOSPITAL", maps_url)
                        
                        # SMS Logic
                        sms_msg = f"EMERGENCY: Level 1/2 Triage for Patient Age {age}. Help Required."
                        requests.post("https://www.fast2sms.com/dev/bulkV2", 
                                      data={"message": sms_msg, "route": "q", "numbers": contact},
                                      headers={"authorization": SMS_API_KEY})
                        st.toast("Emergency SMS Sent!")

                    # Referral QR
                    st.divider()
                    st.subheader("📍 Smart Referral QR")
                    qr_code = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=PX_{age}_{random.randint(100,999)}"
                    st.image(qr_code, caption="Scan for instant clinic intake")
                    
                except Exception as e:
                    st.error(f"Error during analysis: {e}")

st.sidebar.markdown("---")
st.sidebar.caption("PulsePoint v3.0 | Auto-Discovery Backend")