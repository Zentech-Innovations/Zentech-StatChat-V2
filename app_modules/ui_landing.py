#app_modules/ui_landing.py
import streamlit as st
import os
from .app_config import PROFILE_CONFIGS
from .chat_utils import load_chats

def show_landing_page(authenticator):
    col1, col2 = st.columns([0.85, 0.15])
    with col2:
        authenticator.logout('Logout', 'main', key='landing_page_logout')
    with st.container():
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col2:
            landing_image_path = "assets/zensys.png"
            if os.path.exists(landing_image_path):
                st.image(landing_image_path, use_container_width=True)
            else:
                st.warning(f"Landing image not found at {landing_image_path}")
        with col3:
            landing_image_path = "assets/NSDL_logo.png"
            if os.path.exists(landing_image_path):
                st.image(landing_image_path, use_container_width=True)
            else:
                st.warning(f"Landing image not found at {landing_image_path}")


    st.title("🔍 Welcome to Your Financial Chatbot")

    num_profiles = len(PROFILE_CONFIGS)
    cols = st.columns(num_profiles)

    for i, (profile_key, config) in enumerate(PROFILE_CONFIGS.items()):
        with cols[i]:
            if st.button(
                config.get("button_label", profile_key),
                key=f"profile_btn_{profile_key}",
                use_container_width=True,
                help=f"Open {config.get('page_title', 'Profile')}"
            ):
                st.session_state.active_profile = profile_key
                st.session_state.active_chat = None
                st.session_state.chats = load_chats(profile_key)
                st.session_state.current_loaded_profile_for_chats = profile_key
                st.rerun()

    disclaimer_text_landing = """
    <div style="text-align: center; margin-top: 30px; font-size: 0.9em; color: #666;">
        <p><strong>Disclaimer:</strong> This tool is for informational and analytical purposes based on the data you provide.
        It does not constitute financial, investment, or legal advice.</p>
        <p>Please consult with a qualified professional before making any financial decisions.
        The accuracy of AI-generated insights depends on the quality of the input data and inherent AI limitations.</p>
    </div>
    """
    st.markdown(disclaimer_text_landing, unsafe_allow_html=True)
