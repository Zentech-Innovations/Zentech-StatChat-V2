# app_modules/cdsl_api.py
import base64
import json
import requests
from Crypto.Cipher import AES
from google.genai import types as gemini_types
from app_modules import app_config
import datetime


def _decrypt_cdsl_result(encoded_ciphertext: str, key_hex: str) -> dict:
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
        raise Exception(f"CDSL Decryption Error: {type(e).__name__}: {e}")


def get_cdsl_portfolio(client_code: str) -> str:
    cdsl_config = app_config.CDSL_API_SETTINGS
    base_url = cdsl_config.get("base_url")
    decryption_key_hex = cdsl_config.get("decryption_key_hex")
    param_map = cdsl_config.get("param_map", {})

    if not all([base_url, decryption_key_hex]):
        return json.dumps(
            {"error": "CDSL API base URL or decryption key not configured."}
        )

    try:
        api_url = f"{base_url}?{param_map.get('client_code')}={client_code}"
        response = requests.get(api_url, verify=False)
        response.raise_for_status()

        api_response_raw = response.json()

        if api_response_raw.get("STATUS") == "SUCCESS" and api_response_raw.get(
            "RESULT"
        ):
            decrypted_full_data = _decrypt_cdsl_result(
                api_response_raw["RESULT"], decryption_key_hex
            )

            CDSL_SENSITIVE_FIELDS = {
                "first_holder_name", "second_holder_name", "third_holder_name",
                "pan", "pan_of_first_holder", "pan_of_second_holder", "pan_of_third_holder",
                "all_pan_numbers", "mobile_no", "mobile_number", "email", "cas_email_id",
                "alternate_email_id1", "alternate_email_id2", "email_source1",
                "email_source2", "email_source3", "bank_account_no", "bank_ifsc",
                "address1", "address2", "address3", "city", "state", "pincode", "country",
                "input_file",
            }

            def redact_sensitive_info(data_item):
                if isinstance(data_item, dict):
                    processed_item = {}
                    for k, v in data_item.items():
                        lower_k = k.lower()
                        if lower_k in CDSL_SENSITIVE_FIELDS and isinstance(v, str):
                            processed_item[k] = "[REDACTED]"
                        elif isinstance(v, (dict, list)):
                            processed_item[k] = redact_sensitive_info(v)
                        else:
                            processed_item[k] = v
                    return processed_item
                elif isinstance(data_item, list):
                    return [redact_sensitive_info(item) for item in data_item]
                else:
                    return data_item

            redacted_data = redact_sensitive_info(decrypted_full_data)

            final_structured_output = {}
            summary_parts = []

            def get_nested_data(data, path, default=None):
                current = data
                for key in path:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        return default
                return current

            client_details_dpf9 = get_nested_data(
                redacted_data, ["DPF9", "ACC_HOLDERS", "1", "CLIENT_DETAILS"], {}
            )
            client_details_dpd9 = get_nested_data(
                redacted_data, ["DPD9", "CLIENT_DETAILS"], {}
            )

            first_holder = client_details_dpf9.get("FIRST_HOLDER_NAME", "N/A Client")
            total_valuation = client_details_dpf9.get("TOTAL_VALUATION", "0.00")

            summary_parts.append(f"Client: {first_holder} (ID: {client_code})")
            summary_parts.append(f"Total Portfolio Valuation: ₹{total_valuation}")

            final_structured_output["overall_summary"] = {
                "client_id": client_code,
                "first_holder_name": first_holder,
                "total_portfolio_valuation": total_valuation,
                "valuation_as_of_date": get_nested_data(
                    redacted_data,
                    ["DPF9", "ACC_HOLDERS", "1", "FROM_DATE"],
                    datetime.date.today().strftime("%d-%m-%Y"),
                ),
            }
            if client_details_dpd9:
                final_structured_output["overall_summary"][
                    "preferred_depository_indicator"
                ] = client_details_dpd9.get("PREFERRED_DEPOSITORY_INDICATOR", "N/A")
                final_structured_output["overall_summary"]["default_depository"] = (
                    client_details_dpd9.get("DEFAULT_DEPOSITORY", "N/A")
                )

            asset_breakdown = get_nested_data(
                redacted_data, ["DPF9", "ACC_HOLDERS", "1", "ASSETS"], []
            )
            final_structured_output["asset_class_breakdown"] = []
            if asset_breakdown:
                summary_parts.append("\nAsset Class Breakdown:")
                for asset in asset_breakdown:
                    asset_info = {
                        "asset_class": asset.get("ASSET_CLASS_DESCRIPTION", "N/A"),
                        "valuation": asset.get("VALUATION", "0.00"),
                        "percentage_of_total": asset.get(
                            "PERCENTAGE_OF_TOTAL_VAL", "0.00"
                        ),
                    }
                    final_structured_output["asset_class_breakdown"].append(asset_info)
                    summary_parts.append(
                        f"- {asset_info['asset_class']}: ₹{asset_info['valuation']} ({asset_info['percentage_of_total']}%)"
                    )
            else:
                summary_parts.append("\nNo detailed asset class breakdown available.")

            yearly_valuation = get_nested_data(
                redacted_data, ["DPF9", "ACC_HOLDERS", "1", "YEARLY_VALUATION"], []
            )
            if yearly_valuation:
                final_structured_output["yearly_valuation_trend"] = []
                summary_parts.append("\nYearly Valuation Trend:")
                for month_data in yearly_valuation:
                    monthly_val = {
                        "month": month_data.get("MONTH"),
                        "valuation": month_data.get("VALUATION"),
                        "business_date": month_data.get("BUSINESS_DATE"),
                    }
                    final_structured_output["yearly_valuation_trend"].append(
                        monthly_val
                    )
                    summary_parts.append(
                        f"- {monthly_val['month']}: ₹{monthly_val['valuation']}"
                    )
            else:
                summary_parts.append("\nNo yearly valuation trend available.")

            cdsl_acc_holdings = get_nested_data(
                redacted_data, ["DPC9", "ACC_HOLDERS", "1", "CDSL"], []
            )
            nsdl_acc_holdings = get_nested_data(
                redacted_data, ["DPC9", "ACC_HOLDERS", "1", "NSDL"], []
            )

            all_detailed_holdings = []
            for dp_holdings_container in cdsl_acc_holdings + nsdl_acc_holdings:
                for holding in dp_holdings_container.get("HOLDINGS", []):
                    processed_holding = {
                        "depository": (
                            "CDSL"
                            if get_nested_data(dp_holdings_container, ["BO_ID"])
                            else "NSDL"
                        ),
                        "isin": holding.get("ISIN_NO", holding.get("ISIN", "N/A")),
                        "isin_name": holding.get("ISIN_NAME"),
                        "current_balance_qty": holding.get(
                            "CUR_BAL_QTY", holding.get("CURRENT_BAL", "N/A")
                        ),
                        "free_balance_qty": holding.get(
                            "FREE_BAL_QTY", holding.get("FREE_BAL", "N/A")
                        ),
                        "valuation": holding.get(
                            "HOLDING_VALUATION", holding.get("VALUATION", "0.00")
                        ),
                        "security_type_desc": holding.get(
                            "SECURITY_TYPE", holding.get("SECURITY_DESC")
                        ),
                        "close_price": holding.get(
                            "ISIN_CLOSE_PRICE", holding.get("ISIN_PRICE")
                        ),
                        "close_date": holding.get("ISIN_CLOSE_DATE"),
                    }
                    all_detailed_holdings.append(processed_holding)
            final_structured_output["detailed_holdings"] = all_detailed_holdings
            summary_parts.append(
                f"\nTotal Demat Holdings: {len(all_detailed_holdings)} securities."
            )

            all_detailed_transactions = []
            for dp_transactions_container in cdsl_acc_holdings + nsdl_acc_holdings:
                for transaction in dp_transactions_container.get("TRANSACTIONS", []):
                    if "LINE_ITEMS" in transaction:
                        for line_item in transaction["LINE_ITEMS"]:
                            processed_transaction = {
                                "depository": (
                                    "CDSL"
                                    if get_nested_data(
                                        dp_transactions_container, ["BO_ID"]
                                    )
                                    else "NSDL"
                                ),
                                "date": line_item.get("DATE"),
                                "narration": line_item.get("NARRATION"),
                                "isin_name": line_item.get("ISIN_NAME"),
                                "credit_qty": line_item.get("CREDIT"),
                                "debit_qty": line_item.get("DEBIT"),
                                "closing_balance": line_item.get(
                                    "CLOSING_BALANCE",
                                    line_item.get("CLOSE_BAL_AFTER_TRANS"),
                                ),
                                "transaction_id": line_item.get(
                                    "TRANS_NUMBER", line_item.get("TRANSACTION_ID")
                                ),
                            }
                            all_detailed_transactions.append(processed_transaction)
                    else:
                        processed_transaction = {
                            "depository": (
                                "CDSL"
                                if get_nested_data(dp_transactions_container, ["BO_ID"])
                                else "NSDL"
                            ),
                            "date": transaction.get("TRADE_DATE"),
                            "narration": transaction.get("TRANSACTION_DESC"),
                            "isin_name": transaction.get("SCHEME_NAME"),
                            "credit_qty": (
                                transaction.get("AMOUNT")
                                if transaction.get("DR_CR") == "CR"
                                else None
                            ),
                            "debit_qty": (
                                transaction.get("AMOUNT")
                                if transaction.get("DR_CR") == "DR"
                                else None
                            ),
                            "closing_balance": transaction.get("CLOSING_BAL"),
                            "transaction_id": transaction.get("SR_NO"),
                        }
                        if any(
                            processed_transaction[k] not in ["", None, "--"]
                            for k in processed_transaction.keys()
                        ):
                            all_detailed_transactions.append(processed_transaction)
            final_structured_output["detailed_transactions"] = all_detailed_transactions
            summary_parts.append(
                f"Total Demat Transactions: {len(all_detailed_transactions)} entries."
            )

            nps_acc_details = get_nested_data(
                redacted_data, ["DPC9", "ACC_HOLDERS", "1", "NPS"], []
            )
            if nps_acc_details:
                final_structured_output["nps_details"] = {}
                nps_account_info = nps_acc_details[0].get("ACCOUNT_DETAILS", {})
                final_structured_output["nps_details"]["pran"] = nps_account_info.get(
                    "PRAN"
                )
                final_structured_output["nps_details"]["account_type"] = (
                    nps_account_info.get("ACCOUNT_TYPE")
                )
                final_structured_output["nps_details"]["pran_status"] = (
                    nps_account_info.get("PRAN_STATUS")
                )

                nps_investment_summary = nps_acc_details[0].get(
                    "INVESTMENT_SUMMARY", []
                )
                if nps_investment_summary:
                    final_structured_output["nps_details"]["investment_summary"] = (
                        nps_investment_summary[0]
                    )
                    summary_parts.append(
                        f"\nNPS Investment Summary (PRAN: {nps_account_info.get('PRAN')}):"
                    )
                    summary_parts.append(
                        f"- Valuation: ₹{nps_investment_summary[0].get('VALUATION')}"
                    )
                    summary_parts.append(
                        f"- Total Contribution: ₹{nps_investment_summary[0].get('TOTAL_CONTRIBUTION')}"
                    )
                    summary_parts.append(
                        f"- Total Gain/Loss: ₹{nps_investment_summary[0].get('TOTAL_GAIN_LOSS')}"
                    )
                    summary_parts.append(
                        f"- FY Return: {nps_investment_summary[0].get('FY_RETURN')}%"
                    )

                nps_holdings_list = nps_acc_details[0].get("HOLDINGS", [])
                if nps_holdings_list:
                    final_structured_output["nps_details"]["holdings"] = []
                    for h in nps_holdings_list:
                        final_structured_output["nps_details"]["holdings"].append(
                            {
                                "scheme_name": h.get("SCHEME_NAME"),
                                "units": h.get("NUMBER_OF_UNITS"),
                                "value": h.get("VALUE"),
                                "nav": h.get("NAV"),
                                "fund_manager": h.get("FUND_MANAGER"),
                            }
                        )
                    summary_parts.append(f"NPS Schemes: {len(nps_holdings_list)}")

                nps_transactions_list = nps_acc_details[0].get("TRANSACTIONS", [])
                if nps_transactions_list:
                    final_structured_output["nps_details"]["transactions"] = []
                    for t in nps_transactions_list:
                        if t.get("TRANSACTION_DESC") in [
                            "Opening Balance",
                            "Closing Balance",
                        ] and not t.get("AMOUNT"):
                            continue
                        final_structured_output["nps_details"]["transactions"].append(
                            {
                                "date": t.get("TRADE_DATE"),
                                "description": t.get("TRANSACTION_DESC"),
                                "amount": t.get("AMOUNT"),
                                "dr_cr": t.get("DR_CR"),
                                "units": t.get("UNITS"),
                                "scheme_name": t.get("SCHEME_NAME"),
                            }
                        )
                    summary_parts.append(
                        f"NPS Transactions: {len(final_structured_output['nps_details']['transactions'])} entries."
                    )
            else:
                summary_parts.append("\nNo NPS details available.")

            final_summary_str = "\n".join(summary_parts)

            return json.dumps(
                {
                    "status": "success",
                    "summary": final_summary_str,
                    "detailed_data": final_structured_output,
                }
            )
        else:
            return json.dumps(
                {
                    "status": "failure",
                    "message": f"CDSL API returned non-success status or missing result for client {client_code}: {api_response_raw.get('STATUS', 'N/A')}",
                    "raw_response": api_response_raw,
                }
            )

    except requests.exceptions.RequestException as e:
        return json.dumps(
            {
                "error": f"CDSL API request failed for client {client_code}: {str(e)}. Check URL or network."
            }
        )
    except ValueError as e:
        return json.dumps(
            {
                "error": f"CDSL Decryption/Parsing error for client {client_code}: {str(e)}. Check key/IV/padding or response format."
            }
        )
    except json.JSONDecodeError:
        return json.dumps(
            {
                "error": f"CDSL API response is not valid JSON or decrypted content is not JSON for client {client_code}."
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "error": f"An unexpected error occurred during CDSL API call for client {client_code}: {str(e)}"
            }
        )


# --- Tool Declarations for LLMs ---
GEMINI_GET_CDSL_PORTFOLIO = gemini_types.FunctionDeclaration(
    name="get_cdsl_portfolio",
    description="Retrieves detailed CDSL portfolio holdings and transaction data for a specific client. "
    "This tool provides comprehensive information including overall valuation, asset class breakdown, "
    "detailed holdings (equity, bonds, gold bonds), transaction history, and NPS account details. "
    "The tool automatically fetches data for current holdings and transactions within the available statement period (July 2024 for this client).",
    parameters=gemini_types.Schema(
        type=gemini_types.Type.OBJECT,
        properties={
            "client_code": gemini_types.Schema(  
                type=gemini_types.Type.STRING,
                description="The unique client identifier for which to fetch CDSL portfolio data (e.g., 'AA00051873').",
            )
        },
        required=["client_code"],  
    ),
)

OPENAI_GET_CDSL_PORTFOLIO = {
    "type": "function",
    "function": {
        "name": "get_cdsl_portfolio",
        "description": "Retrieves detailed CDSL portfolio holdings and transaction data for a specific client. "
        "This tool provides comprehensive information including overall valuation, asset class breakdown, "
        "detailed holdings (equity, bonds, gold bonds), transaction history, and NPS account details. "
        "The tool automatically fetches data for current holdings and transactions within the available statement period (July 2024 for this client). "
        "The AI should use the full structured data returned to answer specific questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "client_code": {
                    "type": "string",
                    "description": "The unique client identifier for which to fetch CDSL portfolio data (e.g., 'AA00051873').",
                }  
            },
            "required": ["client_code"],  
        },
    },
}

ANTHROPIC_GET_CDSL_PORTFOLIO = {
    "name": "get_cdsl_portfolio",
    "description": "Retrieves detailed CDSL portfolio holdings and transaction data for a specific client. "
    "This tool provides comprehensive information including overall valuation, asset class breakdown, "
    "detailed holdings (equity, bonds, gold bonds), transaction history, and NPS account details. "
    "The tool automatically fetches data for current holdings and transactions within the available statement period (July 2024 for this client). "
    "The AI should use the full structured data returned to answer specific questions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "client_code": {
                "type": "string",
                "description": "The unique client identifier for which to fetch CDSL portfolio data (e.g., 'AA00051873').",
            }
        }, 
        "required": ["client_code"],
    },
}

DEEPSEEK_GET_CDSL_PORTFOLIO = {
    "type": "function",
    "function": {
        "name": "get_cdsl_portfolio",
        "description": "Retrieves detailed CDSL portfolio holdings and transaction data for a specific client. "
        "This tool provides comprehensive information including overall valuation, asset class breakdown, "
        "detailed holdings (equity, bonds, gold bonds), transaction history, and NPS account details. "
        "The tool automatically fetches data for current holdings and transactions within the available statement period (July 2024 for this client). "
        "The AI should use the full structured data returned to answer specific questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "client_code": {
                    "type": "string",
                    "description": "The unique client identifier for which to fetch CDSL portfolio data (e.g., 'AA00051873').",
                }  
            },
            "required": ["client_code"],  
        },
    },
}

GROK_GET_CDSL_PORTFOLIO = OPENAI_GET_CDSL_PORTFOLIO