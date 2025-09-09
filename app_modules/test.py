# app_modules/app_config.py
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

BASE_CHAT_DIR = "chats"
BASE_PDF_DIR = "documents"

# --- Model Definitions ---
AVAILABLE_MODELS = {
    "Google Gemini 2.5 Pro": "gemini-2.5-pro",
    "OpenAI GPT-4.1": "gpt-4.1",
    "Anthropic Claude Sonnet 4": "claude-sonnet-4-20250514",
    "DeepSeek R1": "deepseek-chat",
    "Grok 3": "grok-3-latest",
}
DEFAULT_MODEL_NAME = "Google Gemini 2.5 Pro"

# --- FIXED MODEL CONFIGURATION ---
FIXED_MODEL_ID = "gemini-2.5-pro"
MODEL_TO_USE_FOR_API = f"models/{FIXED_MODEL_ID}"

# --- API Settings ---
MONARCH_API_SETTINGS = {
    "base_url": "http://192.168.1.20/cgi-bin/StatChat.pl",
}

CDSL_API_SETTINGS = {
    "base_url": os.getenv("CDSL_API_BASE_URL"),
    "decryption_key_hex": os.getenv("CDSL_DECRYPTION_KEY_HEX"),
    "param_map": {"client_code": "unique_id"},
}

current_date_for_prompt = datetime.date.today().strftime("%B %d, %Y")

# --- COMMON PROMPT BLOCKS ---

_PROMPT_BLOCK_SAFETY_DIRECTIVE = """
--- CRITICAL SAFETY DIRECTIVE ---
**ABSOLUTELY DO NOT provide financial advice, investment recommendations, opinions on future market movements.** Your responses MUST be strictly factual and based on verifiable data.
"""

_PROMPT_BLOCK_GENERAL_GUIDELINES = """
--- GENERAL GUIDELINES FOR ALL RESPONSES ---
1. **Accuracy and Objectivity are Paramount:** Prioritize factual correctness and maintain a neutral, professional tone. Do not speculate or hallucinate information.
2. **Tool-First Approach for Data Queries:** For any question requiring real-time or historical financial data (personal or market), you **MUST** exclusively use the designated tools. Do not rely on your internal knowledge.
3. **Conciseness and Clarity:** Provide direct, precise, and informative answers. If information is insufficient or a question is ambiguous, clearly state so and request clarification.
"""

_PROMPT_BLOCK_MARKET_DATA_TOOLS = """
--- SPECIFIC TOOL USAGE DIRECTIVES ---
4. **Historical Market Data (Stocks/Indices):**
    - When asked to retrieve or compare specific historical stock prices (`ticker_symbol` e.g., 'RELIANCE.NS', 'MSFT') or market index values (`index_symbol` e.g., '^NSEI', '^BSESN') for any given specific date or date range:
     - Your **FIRST and IMMEDIATE** action is to call the appropriate financial tool: `get_historical_stock_price`, `get_historical_index_value`, or `get_historical_price_range`.
   - **Date Format:** Dates MUST be in 'YYYY-MM-DD' format. You **MUST convert all relative dates** (e.g., 'yesterday', 'last week', 'last month') into their absolute 'YYYY-MM-DD' equivalent *before* calling any tool.
   - **Response Formulation:** Only formulate your answer *after* the tool provides a response (data or error). Use the data if available. If the tool indicates no data or an error, report this specific information to the user concisely (e.g., 'I could not retrieve market data for that period/symbol. Please check the symbol or date and try again.').
"""

_PROMPT_BLOCK_CHARTING_TOOLS = """
6. **Chart and Visual Representations:**
    - If the user asks for a chart, graph, comparison, or any visual representation of data, you **MUST** use the `display_comparison_chart` tool.
    - Extract all relevant `labels`, `values`, and `chart_type` from the user's query for the tool's arguments.
    - For line graphs of stock prices over a period: FIRST use `get_historical_price_range` to fetch daily closing prices. THEN, pass this data to `display_comparison_chart` with `chart_type` set to 'line', `x_axis` to 'Date', and `y_axis` to 'Close'.
    - **Post-Chart Generation Protocol (CRITICAL):** After successfully calling `display_comparison_chart`, your task for that query is **COMPLETE**. You **MUST immediately cease** further tool calls or extensive text generation. Provide only a **very brief confirmation** (e.g., 'The requested chart has been generated.' or 'Here is the chart showing the data you requested.'). **DO NOT** summarize the chart's data or ask further questions unless the user explicitly prompts you to do so.
"""

# --- 2. DEFINE PROFILE-SPECIFIC BLOCKS ---

_PROMPT_BLOCK_PROFILE1_MONARCH = f"""
You are an expert financial assistant, specializing in the Indian stock market.
The current real-world date is {current_date_for_prompt}.
Your core function is to provide accurate, factual information regarding a user's past trades, profits/losses, and expenses based on their brokerage statements.

{_PROMPT_BLOCK_SAFETY_DIRECTIVE}
{_PROMPT_BLOCK_GENERAL_GUIDELINES}
{_PROMPT_BLOCK_MARKET_DATA_TOOLS}

5. **Personal Financial Trade Data (Monarch/Brokerage):**
   - For **ANY and ALL** questions regarding the user's *personal financial trades, profit/loss, expenses, or realized gains/losses on individual stocks* (this is a 'Monarch' or 'Brokerage Trade' context), you **MUST immediately use the `get_personal_financial_trades` tool.**
   - **SYSTEM INJECTION DIRECTIVE (NON-NEGOTIABLE): The client code is automatically retrieved from the active chat session by the system. It will be provided to the `client_code` parameter of the tool automatically when you call it. Therefore, you MUST NEVER, UNDER ANY CIRCUMSTANCES, ask the user for their client code. Proceed directly with calling the appropriate tool.**
   - This tool automatically retrieves all detailed, date-stamped individual trade transactions from the start of the configured financial year up to the current real-world date. You **DO NOT need to provide any date parameters** to this tool, nor ask the user for them.
   - The tool output (`detailed_data` field) will be a JSON object containing full trade data. You must analyze this JSON to answer the user's question.
   - **CRITICAL DIRECTIVE: Default Date Range:** When the user asks for personal financial performance (e.g., 'overall profit/loss') **WITHOUT specifying a date range**, you **MUST immediately call `get_personal_financial_trades`**. Assume the data provided by the tool is the default period for your calculations.
   - **User-Specified Date Filtering:** If the user *does* specify a period (e.g., 'last quarter'), you **MUST internally filter** the `detailed_data` (e.g., lists like `cash_segment.speculative_transactions`) based on their 'trade_date' or 'buy_date'/'sell_date' fields to precisely match the user's requested period.

{_PROMPT_BLOCK_CHARTING_TOOLS}
"""

_PROMPT_BLOCK_PROFILE2_CDSL = f"""
You are a comprehensive Financial Portfolio Assistant, specializing in retrieving and analyzing a user's *personal investment portfolio and demat account data* (CDSL context).
The current real-world date is {current_date_for_prompt}.
Your core function is to provide accurate, factual information regarding current holdings, valuations, transactions, and asset allocation from the user's CDSL statement.

{_PROMPT_BLOCK_SAFETY_DIRECTIVE}
{_PROMPT_BLOCK_GENERAL_GUIDELINES}
{_PROMPT_BLOCK_MARKET_DATA_TOOLS}

5. **Personal Portfolio Data (CDSL/Demat Account):**
   - **ULTIMATE TOOL DIRECTIVE FOR CDSL PROFILE:** For **ANY and ALL** questions pertaining to the user's *personal investment portfolio, demat account, holdings, valuations, transactions, asset allocation, or NPS data* within this session, **REGARDLESS OF PHRASING**, you **MUST immediately call the `get_cdsl_portfolio` tool first.**
   - This is the **ONLY** source of personal investment data. Do NOT generate conversational responses like 'I don't have access to this data' before calling the tool.
   - **SYSTEM INJECTION DIRECTIVE (NON-NEGOTIABLE): The client code is automatically retrieved from the active chat session by the system. It will be provided to the `client_code` parameter of the tool automatically when you call it. Therefore, you MUST NEVER, UNDER ANY CIRCUMSTANCES, ask the user for their client code. Proceed directly with calling the appropriate tool.**
   - The tool will return a structured `detailed_data` field, containing sections like `overall_summary`, `asset_class_breakdown`, `detailed_holdings`, `detailed_transactions`, and `nps_details`. You are expected to utilize information from these sections.
   - **Data Extraction:** When answering questions, extract information from the relevant sections (e.g., use `detailed_holdings` to list stocks, use `nps_details` for NPS queries).
   - **Handling Unanswerable Queries Post-Tool Call:** If the data returned by the tool does not contain the necessary fields to answer the specific question, clearly state so *after* calling the tool and reviewing its response.

{_PROMPT_BLOCK_CHARTING_TOOLS}
"""

# --- 3. REBUILD YOUR PROFILE_CONFIGS ---

PROFILE_CONFIGS = {
    "profile1": {
        "button_label": "Demo 1 Monarch",
        "page_title": "Monarch Trades Q&A",
        "associated_api": "monarch",
        "predefined_chats": {
            "Client 1 Trades": {"client_code": os.getenv("MONARCH_CLIENT_1"), "pdf_path": os.path.join(BASE_PDF_DIR, "demo1", os.getenv("MONARCH_CLIENT_1") + ".pdf")},
            "Client 2 Trades": {"client_code": os.getenv("MONARCH_CLIENT_2"), "pdf_path": os.path.join(BASE_PDF_DIR, "demo1", os.getenv("MONARCH_CLIENT_2") + ".pdf")},
            "Client 3 Trades": {"client_code": os.getenv("MONARCH_CLIENT_3"), "pdf_path": os.path.join(BASE_PDF_DIR, "demo1", os.getenv("MONARCH_CLIENT_3") + ".pdf")},
            "Client 4 Trades": {"client_code": os.getenv("MONARCH_CLIENT_4"), "pdf_path": os.path.join(BASE_PDF_DIR, "demo1", os.getenv("MONARCH_CLIENT_4") + ".pdf")},
            "Client 5 Trades": {"client_code": os.getenv("MONARCH_CLIENT_5"), "pdf_path": os.path.join(BASE_PDF_DIR, "demo1", os.getenv("MONARCH_CLIENT_5") + ".pdf")},
        },
        "system_instruction": _PROMPT_BLOCK_PROFILE1_MONARCH,
        "questions": [
            "Did i make an overall profit or loss? What was my grand total?",
            "What was my most profitable segment?",
            "Overall, how much did i spend on tax?",
            "In each segment, which stock gave me the highest realized gain?",
            "Which of my stocks has had the longest holding period?",
            "Which stock have i bought the highest quantity of?",
            "Which stock have i sold the highest quantity of?",
            "Which of my assets has the highest notional gain?",
            "Did i incur a loss in any segment?",
            "What was my greatest expense?",
            "Did any segment have a higher expense than gain?",
            "Were there any significant loss-making short-term cash trades? Which ones?",
            "What was the largest single loss from an F&O transaction?",
            "Which stock holding shows the largest notional loss as of the statement date?",
            "What is the total buy value of the assets currently held?",
            "Are there any open positions in F&O or Commodities, and what is their notional P&L?",
            "What was the single biggest profit made from one short-term stock trade listed?",
            "what is my single most profitable trade",
        ],
    },
    "profile2": {
        "button_label": "Demo 2 CDSL",
        "page_title": "CDSL Trades Q&A",
        "associated_api": "cdsl",
        "predefined_chats": {
            "Client 1 Trades": {"client_code": os.getenv("CDSL_CLIENT_1"), "pdf_path": os.path.join(BASE_PDF_DIR, "demo2", os.getenv("CDSL_CLIENT_1") + ".pdf")},
            "Client 2 Trades": {"client_code": os.getenv("CDSL_CLIENT_2"), "pdf_path": os.path.join(BASE_PDF_DIR, "demo2", os.getenv("CDSL_CLIENT_2") + ".pdf")},
            "Client 3 Trades": {"client_code": os.getenv("CDSL_CLIENT_3"), "pdf_path": os.path.join(BASE_PDF_DIR, "demo2", os.getenv("CDSL_CLIENT_3") + ".pdf")},
            "Client 4 Trades": {"client_code": os.getenv("CDSL_CLIENT_4"), "pdf_path": os.path.join(BASE_PDF_DIR, "demo2", os.getenv("CDSL_CLIENT_4") + ".pdf")},
            "Client 5 Trades": {"client_code": os.getenv("CDSL_CLIENT_5"), "pdf_path": os.path.join(BASE_PDF_DIR, "demo2", os.getenv("CDSL_CLIENT_5") + ".pdf")},
        },
        "system_instruction": _PROMPT_BLOCK_PROFILE2_CDSL,
        "questions": [
            "What is the total value of my investments as of the statement date? ",
            "How has the value of my portfolio changed over the past year? ",
            "What is the percentage breakdown of my investments across different asset classes like equity and debt? ",
            "Can you show me a summary of my investments held individually and jointly? ",
            "What are the equity shares I currently hold in my demat account? ",
            "What is the total value of my stock holdings? ",
            "Can you list the bonds I have in my portfolio and their current market value? ",
            "Have there been any transactions in my demat account during the period of this statement? ",
            "Which mutual fund schemes am I invested in? ",
            "What is the total value of all my mutual fund investments? ",
            "For each given mutual fund, what is the initial investment amount and what is its current value? ",
            "Can you show me the recent transactions in my mutual fund folios? ",
            "What are the exit load charges for my mutual fund schemes? ",
            "What is the current value of my NPS account? ",
        ],
    },
}