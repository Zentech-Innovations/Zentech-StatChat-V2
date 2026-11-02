# app.py
import streamlit as st
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities.exceptions import LoginError
from app_modules import app_config, ui_landing, chat_utils, tool_declaration, ui_components
from models import google_gemini as gemini, openai_chatgpt as openai, anthropic_claude as anthropic_model, deepseek_chat as deepseek_model, grok_chat as grok_model

st.set_page_config(
    page_title="Financial Chatbot", layout="wide",
    initial_sidebar_state="expanded", page_icon="assets/zensys.png"
) 

load_dotenv()
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_BASE = ("https://api.deepseek.com")
GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_API_BASE = ("https://api.x.ai/v1")
NSDL_DECRYPTION_KEY_HEX = os.getenv("NSDL_DECRYPTION_KEY_HEX")

if not GOOGLE_API_KEY:
    st.error("GEMINI_API_KEY not found.")
    st.stop()
if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY not found.")
    st.stop()
if not ANTHROPIC_API_KEY:
    st.error("ANTHROPIC_API_KEY not found.")
    st.stop()
if not DEEPSEEK_API_KEY:
    st.error("DEEPSEEK_API_KEY not found.")
    st.stop()
if not GROK_API_KEY: 
    st.error("GROK_API_KEY not found.")
    st.stop()
if not NSDL_DECRYPTION_KEY_HEX:
    st.error("NSDL_DECRYPTION_KEY_HEX not found.")
    st.stop()

authenticator = stauth.Authenticate(
    st.secrets['credentials'].to_dict(),
    st.secrets['cookie']['name'],
    st.secrets['cookie']['key'],
    st.secrets['cookie']['expiry_days']
)

if not st.session_state.get("authentication_status"):
    col1, col2, col3 = st.columns([1.5, 2, 1.5])
    with col2:
        try:
            authenticator.login(captcha=True, single_session =True, clear_on_submit=True)
        except LoginError as e:
            if "Captcha entered incorrectly" in str(e):
                st.error('Captcha is incorrect')
                st.stop()
        except Exception as e:
            st.error(f"An unexpected error occurred during login: {e}")
            st.session_state["authentication_status"] = False
            st.stop()
        if st.session_state["authentication_status"] is False:
            st.error('Username/password is incorrect')
            st.stop()
        elif st.session_state["authentication_status"] is None:
            st.stop()

def load_css(css_file_path):
    try:
        with open(css_file_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file not found: {css_file_path}. Create './assets/style.css'")
load_css("assets/style.css")

if not os.path.exists(app_config.BASE_CHAT_DIR):
    os.makedirs(app_config.BASE_CHAT_DIR, exist_ok=True)

if "active_profile" not in st.session_state or not st.session_state.active_profile:
    st.session_state.current_loaded_profile_for_chats = None
    st.session_state.chats = {}
    st.session_state.selected_model_name = app_config.DEFAULT_MODEL_NAME
    st.session_state.processing = False
    ui_landing.show_landing_page(authenticator)
    st.stop()

ACTIVE_PROFILE_KEY = st.session_state.active_profile

if st.session_state.get("current_loaded_profile_for_chats") != ACTIVE_PROFILE_KEY:
    st.session_state.chats = chat_utils.load_chats(ACTIVE_PROFILE_KEY)
    st.session_state.current_loaded_profile_for_chats = ACTIVE_PROFILE_KEY
    st.session_state.active_chat = None

CURRENT_PROFILE_CONFIG = app_config.PROFILE_CONFIGS[ACTIVE_PROFILE_KEY]
PREDEFINED_CHATS_FOR_PROFILE = CURRENT_PROFILE_CONFIG["predefined_chats"]

for title, client_code_val in PREDEFINED_CHATS_FOR_PROFILE.items():
    if title not in st.session_state.chats:
        st.session_state.chats[title] = {
            "client_code": client_code_val.get("client_code"),
            "pdf_path": client_code_val.get("pdf_path"),
            "messages": [],
            "openai_thread_id": None,
        }
        chat_utils.save_chat(ACTIVE_PROFILE_KEY, title, st.session_state.chats[title])
    else:
        st.session_state.chats[title].setdefault("openai_thread_id", None)
        if st.session_state.chats[title].get("client_code") != client_code_val.get("client_code"):
            st.session_state.chats[title]["client_code"] = client_code_val.get("client_code")
            st.session_state.chats[title]["pdf_path"] = client_code_val.get("pdf_path")
            chat_utils.save_chat(ACTIVE_PROFILE_KEY, title, st.session_state.chats[title])

if not st.session_state.get("active_chat"):
    valid_titles = list(PREDEFINED_CHATS_FOR_PROFILE.keys())
    st.session_state.active_chat = valid_titles[0] if valid_titles else None

with st.sidebar:
    ui_components.render_sidebar_content(authenticator)

ui_components.display_pdf_modal()

if not st.session_state.active_chat:
    st.info("👉 Select a client chat from the sidebar to begin.")
    st.stop()
else:
    chat_title = st.session_state.active_chat
    current_chat_data = st.session_state.chats[chat_title]
    current_chat_messages = current_chat_data["messages"]
    current_client_code = current_chat_data["client_code"]
    chat_pdf_path = current_chat_data.get("pdf_path")

    displayed_model_name = st.session_state.get("selected_model_name", app_config.DEFAULT_MODEL_NAME)
    st.markdown(f"### Chat: {chat_title}")
    st.caption(f"⚡ Model: {displayed_model_name}")

    ui_components.display_chat_history(current_chat_messages)

    input_for_processing = None
    if st.session_state.get("process_button_question", False):
        if "question_from_button" in st.session_state:
            input_for_processing = st.session_state.question_from_button
            del st.session_state.question_from_button
        st.session_state.process_button_question = False

    chat_field_input = st.chat_input(
        "Ask a question about financial trades or stock data...",
        key=f"chat_input_{ACTIVE_PROFILE_KEY}_{chat_title}",
        disabled=st.session_state.get("processing", False)
    )

    if chat_field_input:
        input_for_processing = chat_field_input

    if input_for_processing:
        st.session_state.processing = True
        st.session_state.query_to_process = str(input_for_processing)
        current_chat_messages.append({"role": "user", "content": st.session_state.query_to_process})
        st.rerun()

if st.session_state.get("processing", False):
    user_query = st.session_state.query_to_process
    
    with st.spinner(f"Thinking with {displayed_model_name}..."):
        selected_model_name = st.session_state.selected_model_name
        api_model_id = app_config.AVAILABLE_MODELS[selected_model_name]
        
        effective_system_instruction = CURRENT_PROFILE_CONFIG.get("system_instruction")
        
        if not effective_system_instruction:
            effective_system_instruction = "You are a helpful AI assistant. Respond concisely."
            st.warning(f"No specific system instruction found for profile '{ACTIVE_PROFILE_KEY}'. Using a generic one.")

        client_code_for_llm = st.session_state.chats[chat_title]["client_code"]
        
        final_text_response = "Error: Model processing failed."
        updated_full_history = [] 
        updated_chat_metadata = dict(st.session_state.chats[chat_title])

        llm_provider_name = "" 
        if "Google" in selected_model_name:
            llm_provider_name = "Google"
        elif "OpenAI" in selected_model_name:
            llm_provider_name = "OpenAI"
        elif "Anthropic" in selected_model_name:
            llm_provider_name = "Anthropic"
        elif "DeepSeek" in selected_model_name:
            llm_provider_name = "DeepSeek"
        elif "Grok" in selected_model_name:
            llm_provider_name = "Grok"

        current_profile_tools = tool_declaration.get_tools_for_profile(ACTIVE_PROFILE_KEY, llm_provider_name)

        if llm_provider_name == "Google":
            client = genai.Client(api_key=GOOGLE_API_KEY)
            gemini_tool_config = types.Tool(function_declarations=current_profile_tools)
            
            final_text_response, updated_full_history, updated_chat_metadata = gemini.generate_gemini_response(
                client=client,
                current_chat_messages=list(current_chat_messages), user_query=user_query,
                current_chat_data=updated_chat_metadata,
                system_instruction_str=effective_system_instruction, 
                gemini_tool_config=gemini_tool_config,
                client_code_from_session=client_code_for_llm
            )
            
        elif llm_provider_name == "OpenAI":
            final_text_response, updated_full_history, updated_chat_metadata = openai.get_openai_response(
                api_key=OPENAI_API_KEY,
                model_id=api_model_id,
                system_instruction=effective_system_instruction, 
                current_chat_messages=list(current_chat_messages),
                user_query=user_query,
                current_chat_data=updated_chat_metadata,
                client_code_from_session=client_code_for_llm,
                available_tools=current_profile_tools 
            )

        elif llm_provider_name == "Anthropic":
            final_text_response, updated_full_history, updated_chat_metadata = anthropic_model.generate_claude_response(
                api_key=ANTHROPIC_API_KEY,
                model_id=api_model_id,
                system_instruction=effective_system_instruction, 
                current_chat_messages=list(current_chat_messages),
                user_query=user_query,
                client_code_from_session=client_code_for_llm,
                available_tools=current_profile_tools 
            )

        elif llm_provider_name == "DeepSeek":
            final_text_response, updated_full_history, updated_chat_metadata = deepseek_model.generate_deepseek_response(
                api_key=DEEPSEEK_API_KEY,
                api_base=DEEPSEEK_API_BASE,
                model_id=api_model_id,
                system_instruction=effective_system_instruction, 
                current_chat_messages=list(current_chat_messages),
                user_query=user_query,
                client_code_from_session=client_code_for_llm,
                available_tools=current_profile_tools 
            )

        elif llm_provider_name == "Grok": 
            final_text_response, updated_full_history, updated_chat_metadata = grok_model.generate_grok_response(
                api_key=GROK_API_KEY,
                api_base=GROK_API_BASE,
                model_id=api_model_id,
                system_instruction=effective_system_instruction, 
                current_chat_messages=list(current_chat_messages),
                user_query=user_query,
                client_code_from_session=client_code_for_llm,
                available_tools=current_profile_tools 
            )

        else:
            final_text_response = "Error: Model not recognized or no specific handler implemented."
            updated_full_history = list(current_chat_messages) 
            updated_chat_metadata = dict(current_chat_data)



        st.session_state.chats[chat_title].update(updated_chat_metadata)

        current_chat_messages.append({"role": "assistant", "content": final_text_response})
        st.session_state.chats[chat_title]["messages"] = current_chat_messages
        
        chat_utils.save_chat(ACTIVE_PROFILE_KEY, chat_title, st.session_state.chats[chat_title]) 

        del st.session_state.query_to_process
        st.session_state.processing = False
        st.rerun()

if "figure_to_display" in st.session_state and st.session_state.figure_to_display is not None:
    fig = st.session_state.figure_to_display

    chat_title = st.session_state.active_chat
    current_chat_messages = st.session_state.chats[chat_title].get("messages", [])
    
    current_chat_messages.append({
        "role": "assistant",
        "type": "chart",
        "content": fig.to_json()
    })

    chat_utils.save_chat(ACTIVE_PROFILE_KEY, chat_title, st.session_state.chats[chat_title]) 

    del st.session_state.figure_to_display
    st.rerun()

footer_html = """
<style>
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    opacity: 50%;
    width: 100%;
    text-align: center;
    padding-top: 5px;
    padding-bottom: 5px;
    z-index: 9999;
}
</style>
<div class="footer">
    <p>
        <b>Disclaimer:</b> StatChat can make mistakes, so double-check it.
    </p>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
