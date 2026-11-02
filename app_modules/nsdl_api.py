# app_modules/nsdl_api.py
import base64
import json
import requests
from Crypto.Cipher import AES
from google.genai import types as gemini_types
from app_modules import app_config
import datetime


def _decrypt_nsdl_result(encoded_ciphertext: str, key_hex: str) -> dict:
    try:
        key = key_hex.encode("ascii")
        if len(key) != 32:
            raise ValueError(
                f"Decryption key length mismatch. Expected 32 bytes for AES-256, got {len(key)} bytes."
            )

        cleaned_encoded_ciphertext = "".join(encoded_ciphertext.split())
        decoded_ciphertext = base64.b64decode(cleaned_encoded_ciphertext)

        extracted_iv = decoded_ciphertext[:16]
        actual_ciphertext = decoded_ciphertext[16:]

        cipher = AES.new(key, AES.MODE_CBC, iv=extracted_iv)
        decrypted_with_padding = cipher.decrypt(actual_ciphertext)

        pad_len = decrypted_with_padding[-1]
        if pad_len < 1 or pad_len > AES.block_size:
            raise ValueError("Invalid PKCS7 padding length detected.")
        decrypted_bytes = decrypted_with_padding[:-pad_len]

        decrypted_data_str = decrypted_bytes.decode("utf-8")
        decrypted_json = json.loads(decrypted_data_str)

        return decrypted_json

    except Exception as e:
        raise Exception(f"NSDL Decryption Error: {type(e).__name__}: {e}")


def get_nsdl_portfolio(client_code: str) -> str:
    nsdl_config = app_config.NSDL_API_SETTINGS
    base_url = nsdl_config.get("base_url")
    decryption_key_hex = nsdl_config.get("decryption_key_hex")
    param_map = nsdl_config.get("param_map", {})

    if not all([base_url, decryption_key_hex]):
        return json.dumps(
            {"error": "NSDL API base URL or decryption key not configured."}
        )

    try:
        api_url = f"{base_url}?{param_map.get('client_code')}={client_code}"
        response = requests.get(api_url, verify=False)
        response.raise_for_status()

        api_response_raw = response.json()

        if api_response_raw.get("STATUS") == "SUCCESS" and api_response_raw.get(
            "RESULT"
        ):
            decrypted_full_data = _decrypt_nsdl_result(
                api_response_raw["RESULT"], decryption_key_hex
            )
            return json.dumps(decrypted_full_data, default=str)
        else:
            return json.dumps(
                {
                    "status": "failure",
                    "message": f"NSDL API returned non-success status or missing result for client {client_code}: {api_response_raw.get('STATUS', 'N/A')}",
                    "raw_response": api_response_raw,
                }
            )

    except requests.exceptions.RequestException as e:
        return json.dumps(
            {
                "error": f"NSDL API request failed for client {client_code}: {str(e)}. Check URL or network."
            }
        )
    except ValueError as e:
        return json.dumps(
            {
                "error": f"NSDL Decryption/Parsing error for client {client_code}: {str(e)}. Check key/IV/padding or response format."
            }
        )
    except json.JSONDecodeError:
        return json.dumps(
            {
                "error": f"NSDL API response is not valid JSON or decrypted content is not JSON for client {client_code}."
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "error": f"An unexpected error occurred during NSDL API call for client {client_code}: {str(e)}"
            }
        )


# --- Tool Declarations for LLMs ---
GEMINI_GET_NSDL_PORTFOLIO = gemini_types.FunctionDeclaration(
    name="get_nsdl_portfolio",
    description="Retrieves detailed NSDL portfolio holdings and transaction data for a specific client. "
    "This tool provides comprehensive information including overall valuation, asset class breakdown, "
    "detailed holdings (equity, bonds, gold bonds), transaction history, and NPS account details. "
    "The tool automatically fetches data for current holdings and transactions within the available statement period (July 2024 for this client).",
    parameters=gemini_types.Schema(
        type=gemini_types.Type.OBJECT,
        properties={
            "client_code": gemini_types.Schema(  
                type=gemini_types.Type.STRING,
                description="The unique client identifier for which to fetch NSDL portfolio data (e.g., 'AA00051873').",
            )
        },
        required=["client_code"],  
    ),
)

OPENAI_GET_NSDL_PORTFOLIO = {
    "type": "function",
    "function": {
        "name": "get_nsdl_portfolio",
        "description": "Retrieves detailed NSDL portfolio holdings and transaction data for a specific client. "
        "This tool provides comprehensive information including overall valuation, asset class breakdown, "
        "detailed holdings (equity, bonds, gold bonds), transaction history, and NPS account details. "
        "The tool automatically fetches data for current holdings and transactions within the available statement period (July 2024 for this client). "
        "The AI should use the full structured data returned to answer specific questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "client_code": {
                    "type": "string",
                    "description": "The unique client identifier for which to fetch NSDL portfolio data (e.g., 'AA00051873').",
                }  
            },
            "required": ["client_code"],  
        },
    },
}

ANTHROPIC_GET_NSDL_PORTFOLIO = {
    "name": "get_nsdl_portfolio",
    "description": "Retrieves detailed NSDL portfolio holdings and transaction data for a specific client. "
    "This tool provides comprehensive information including overall valuation, asset class breakdown, "
    "detailed holdings (equity, bonds, gold bonds), transaction history, and NPS account details. "
    "The tool automatically fetches data for current holdings and transactions within the available statement period (July 2024 for this client). "
    "The AI should use the full structured data returned to answer specific questions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "client_code": {
                "type": "string",
                "description": "The unique client identifier for which to fetch NSDL portfolio data (e.g., 'AA00051873').",
            }
        }, 
        "required": ["client_code"],
    },
}

DEEPSEEK_GET_NSDL_PORTFOLIO = {
    "type": "function",
    "function": {
        "name": "get_nsdl_portfolio",
        "description": "Retrieves detailed NSDL portfolio holdings and transaction data for a specific client. "
        "This tool provides comprehensive information including overall valuation, asset class breakdown, "
        "detailed holdings (equity, bonds, gold bonds), transaction history, and NPS account details. "
        "The tool automatically fetches data for current holdings and transactions within the available statement period (July 2024 for this client). "
        "The AI should use the full structured data returned to answer specific questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "client_code": {
                    "type": "string",
                    "description": "The unique client identifier for which to fetch NSDL portfolio data (e.g., 'AA00051873').",
                }  
            },
            "required": ["client_code"],  
        },
    },
}

GROK_GET_NSDL_PORTFOLIO = OPENAI_GET_NSDL_PORTFOLIO
