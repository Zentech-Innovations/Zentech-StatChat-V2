#app_modules/chat_utils.py
import os
import json
from .app_config import BASE_CHAT_DIR

def get_profile_chat_dir(profile_key):
    safe_profile_key = "".join(c if c.isalnum() else "_" for c in profile_key)
    return os.path.join(BASE_CHAT_DIR, safe_profile_key)

def load_chats(profile_key):
    profile_chat_dir = get_profile_chat_dir(profile_key)
    os.makedirs(profile_chat_dir, exist_ok=True)
    chats = {}
    if os.path.exists(profile_chat_dir) and os.path.isdir(profile_chat_dir):
        for file_name in os.listdir(profile_chat_dir):
            if file_name.endswith(".json"):
                file_path = os.path.join(profile_chat_dir, file_name)
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                        if isinstance(data, dict) and "messages" in data:
                            data.setdefault("client_code", None)
                            data.setdefault("openai_thread_id", None)
                            chats[os.path.splitext(file_name)[0]] = data
                except Exception as e:
                    print(f"Warning: Error loading chat file {file_path}: {e}")
    return chats

def save_chat(profile_key, title, chat_data):
    profile_chat_dir = get_profile_chat_dir(profile_key)
    os.makedirs(profile_chat_dir, exist_ok=True)
    safe_title = "".join(c if c.isalnum() or c in [' ', '-'] else "_" for c in title)
    file_path = os.path.join(profile_chat_dir, f"{safe_title}.json")
    try:
        with open(file_path, "w") as f:
            json.dump(chat_data, f, indent=2)
    except Exception as e:
        print(f"Error saving chat file {file_path}: {e}")