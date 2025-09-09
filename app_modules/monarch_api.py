# app.py
import json
import requests
from google.genai import types as gemini_types
from app_modules import app_config


def get_monarch_personal_financial_trades_impl(client_code: str):
    monarch_config = app_config.MONARCH_API_SETTINGS
    base_url = monarch_config.get("base_url")

    if not client_code:
        return json.dumps({"error": "Client code cannot be empty."})

    try:
        full_api_url = f"{base_url}?client_code={client_code}"

        response = requests.get(full_api_url)
        response.raise_for_status()

        api_response_data = response.json()

        return json.dumps({
            "status": "success",
            "detailed_data": api_response_data
        })
    
    except requests.exceptions.RequestException as e:
        return json.dumps({
            "error": f"API request failed for client {client_code}: {str(e)}. Check if the API server at {base_url} is running and accessible."
        })
    except json.JSONDecodeError:
        return json.dumps({
            "error": "Invalid JSON response from the new Monarch API. Check the API endpoint or response format."
        })
    except Exception as e:
        return json.dumps({
            "error": f"An unexpected error occurred while fetching trades for client {client_code}: {str(e)}"
        })


# --- Gemini-specific tool declaration ---
GEMINI_GET_PERSONAL_FINANCIAL_TRADES = gemini_types.FunctionDeclaration(
    name="get_personal_financial_trades",
    description="Retrieves personal financial trade records and portfolio summaries for a client. ",
    parameters=gemini_types.Schema(
        type=gemini_types.Type.OBJECT,
        properties={},
        required=[],
    ),
)

# --- OpenAI-specific tool declaration ---
OPENAI_GET_PERSONAL_FINANCIAL_TRADES = {
    "type": "function",
    "function": {
        "name": "get_personal_financial_trades",
        "description": "Retrieves personal financial trade records and portfolio summaries for a client. ",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

# --- ANTHROPIC-SPECIFIC TOOL DECLARATIONS ---
ANTHROPIC_GET_PERSONAL_FINANCIAL_TRADES = {
    "name": "get_personal_financial_trades",
    "description": "Retrieves personal financial trade records and portfolio summaries for a client. ",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

# --- DEEPSEEK-SPECIFIC TOOL DECLARATIONS ---
DEEPSEEK_GET_PERSONAL_FINANCIAL_TRADES = {
    "type": "function",
    "function": {
        "name": "get_personal_financial_trades",
        "description": "Retrieves personal financial trade records and portfolio summaries for a client. ",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}
