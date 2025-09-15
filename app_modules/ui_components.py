# app_modules/ui_components.py
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
import os
import plotly.io as pio
from . import app_config
from . import chat_utils

def render_sidebar_content(authenticator):
    if "processing" not in st.session_state:
        st.session_state.processing = False
    
    is_processing = st.session_state.processing

    active_profile_key = st.session_state.active_profile
    current_profile_config = app_config.PROFILE_CONFIGS.get(active_profile_key, {})
    predefined_chats_for_profile = current_profile_config.get("predefined_chats", {})
    questions_for_profile = current_profile_config.get("questions", [])

    st.markdown("### 📄Talk to Your Statement")
    side_col1,side_col3 = st.columns([1, 1])
    with side_col1:
        if st.button("🏠 Home", use_container_width=True, disabled=is_processing):
            st.session_state.active_profile = None
            st.session_state.active_chat = None
            st.rerun()
    
    with side_col3:
        authenticator.logout('👋 Logout', 'main', key='logout_button', use_container_width=True)

    with st.container(border=True):
        available_model_names = list(app_config.AVAILABLE_MODELS.keys())
        if "selected_model_name" not in st.session_state or st.session_state.selected_model_name not in available_model_names:
            st.session_state.selected_model_name = app_config.DEFAULT_MODEL_NAME

        selected_model_name_from_ui = st.selectbox(
            "Choose a model:",
            options=available_model_names,
            index=available_model_names.index(st.session_state.selected_model_name),
            key="model_selector_sidebar",
            disabled=is_processing
        )

        if selected_model_name_from_ui != st.session_state.selected_model_name:
            st.session_state.selected_model_name = selected_model_name_from_ui
            st.toast(f"Model changed to: {st.session_state.selected_model_name}", icon="🤖")

    current_selected_model_name = st.session_state.selected_model_name
    if "(OpenAI)" in current_selected_model_name:
        if not st.session_state.get("openai_api_key_session"):
            st.warning("OpenAI API Key not found for this session.")
    elif "(Google)" in current_selected_model_name:
        if not (st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")):
            st.warning("GEMINI_API_KEY not found.")

    st.markdown("---")
    
    combined_titles_to_display = [t for t, p in predefined_chats_for_profile.items() if p.get("pdf_path") and os.path.exists(p.get("pdf_path"))]

    if combined_titles_to_display:
        with st.container(border=True):
            current_active_chat_index = 0
            if st.session_state.active_chat in combined_titles_to_display:
                current_active_chat_index = combined_titles_to_display.index(st.session_state.active_chat)
            
            selected_chat_title = st.selectbox(
                "Select a Statement:", options=combined_titles_to_display,
                index=current_active_chat_index, key="chat_selector_dropdown",
                disabled=is_processing
            )
            if selected_chat_title != st.session_state.active_chat:
                st.session_state.active_chat = selected_chat_title
                st.session_state.pdf_to_display_in_dialog = None
                st.rerun()

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(f"🗑️ Clear Chat", key=f"delete_{st.session_state.active_chat}", help="Delete all messages", use_container_width=True, disabled=is_processing):
                    pdf_path_for_chat = predefined_chats_for_profile[st.session_state.active_chat].get("pdf_path")
                    client_code_for_chat = predefined_chats_for_profile[st.session_state.active_chat].get("client_code")
                    chat_utils.save_chat(active_profile_key, st.session_state.active_chat, {"pdf_path": pdf_path_for_chat, "client_code": client_code_for_chat, "messages": []})
                    st.session_state.chats[st.session_state.active_chat]["messages"] = []
                    st.rerun()
            with col2:
                if st.button("📄 View PDF", key=f"view_pdf_{st.session_state.active_chat}", use_container_width=True, disabled=is_processing):
                    pdf_path = st.session_state.chats[st.session_state.active_chat].get("pdf_path")
                    if pdf_path and os.path.exists(pdf_path):
                        st.session_state.pdf_to_display_in_dialog = pdf_path
                        st.rerun()
    
    st.markdown("---")
    st.markdown("## ❓ Select a Question")
    with st.container(border=True, height=380):
        for i, question in enumerate(questions_for_profile):
            if st.button(
                question, key=f"q_btn_{active_profile_key}_{i}",
                use_container_width=True, disabled=is_processing
            ):
                st.session_state.process_button_question = True
                st.session_state.question_from_button = question
                st.rerun()

def display_pdf_modal():
    if st.session_state.get("pdf_to_display_in_dialog"):
        _pdf_path_for_dialog_display = st.session_state.pdf_to_display_in_dialog
        st.session_state.pdf_to_display_in_dialog = None
        if _pdf_path_for_dialog_display and os.path.exists(_pdf_path_for_dialog_display):
            if hasattr(st, 'dialog'):
                @st.dialog(title=" ", width="large")
                def view_pdf_in_dialog_function_content():
                    with open(_pdf_path_for_dialog_display, "rb") as f:
                        binary_content = f.read()
                    pdf_viewer(input=binary_content, height=1000, annotations=[])
                    st.markdown(os.path.basename(_pdf_path_for_dialog_display), unsafe_allow_html=True)
                view_pdf_in_dialog_function_content()

def display_chat_history(current_chat_messages):
    for msg in current_chat_messages:
        with st.chat_message(msg["role"]):
            content_type = msg.get("type", "text")
            if content_type == "chart":
                try:
                    fig = pio.from_json(msg["content"])
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Could not display chart from history: {e}")
            else:
                st.markdown(msg["content"])