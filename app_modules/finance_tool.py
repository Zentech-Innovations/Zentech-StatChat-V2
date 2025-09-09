#app_modules/finance_tool.py
import yfinance as yf
import datetime
import json
from google.genai import types as gemini_types

def get_historical_stock_price_impl(ticker_symbol: str, date_str: str):
    try:
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        stock = yf.Ticker(ticker_symbol)
        hist = stock.history(
            start=target_date.strftime("%Y-%m-%d"),
            end=(target_date + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
        )
        if hist.empty:
            return json.dumps({"error": f"No data found for {ticker_symbol} around {date_str}."})
        data_for_date_df = hist[hist.index.date == target_date]
        if data_for_date_df.empty:
            return json.dumps({"error": f"No trading data for {ticker_symbol} on {date_str}."})
        data = data_for_date_df.iloc[0]
        result = {
            "date": date_str, "ticker": ticker_symbol, "open": data.get("Open"),
            "high": data.get("High"), "low": data.get("Low"),
            "close": data.get("Close"), "volume": data.get("Volume"),
        }
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": f"An error occurred: {str(e)}"})

def get_historical_price_range_impl(ticker_symbol: str, start_date: str, end_date: str):
    try:
        stock = yf.Ticker(ticker_symbol)
        hist = stock.history(start=start_date, end=end_date)
        if hist.empty:
            return json.dumps({"error": f"No data found for {ticker_symbol} in the range {start_date} to {end_date}."})
        hist = hist.reset_index()
        hist = hist[["Date", "Close"]]
        hist["Date"] = hist["Date"].dt.strftime("%Y-%m-%d")
        return hist.to_json(orient="records")
    except Exception as e:
        return json.dumps({"error": f"An unexpected error occurred: {str(e)}"})

def get_historical_index_value_impl(index_symbol: str, date_str: str):
    return get_historical_stock_price_impl(index_symbol, date_str)

GEMINI_GET_STOCK_PRICE = gemini_types.FunctionDeclaration(
    name="get_historical_stock_price",
    description="Fetches historical stock data for a stock ticker on a specific date.",
    parameters=gemini_types.Schema(
        type=gemini_types.Type.OBJECT,
        properties={
            "ticker_symbol": gemini_types.Schema(
                type=gemini_types.Type.STRING, description="The stock ticker symbol (e.g., 'RELIANCE.NS').",
            ),
            "date_str": gemini_types.Schema(
                type=gemini_types.Type.STRING, description="The date in YYYY-MM-DD format.",
            ),
        },
        required=["ticker_symbol", "date_str"],
    ),
)
GEMINI_GET_INDEX_VALUE = gemini_types.FunctionDeclaration(
    name="get_historical_index_value",
    description="Fetches historical data for a market index on a specific date.",
    parameters=gemini_types.Schema(
        type=gemini_types.Type.OBJECT,
        properties={
            "index_symbol": gemini_types.Schema(
                type=gemini_types.Type.STRING, description="The market index symbol (e.g., '^NSEI').",
            ),
            "date_str": gemini_types.Schema(
                type=gemini_types.Type.STRING, description="The date in YYYY-MM-DD format.",
            ),
        },
        required=["index_symbol", "date_str"],
    ),
)
GEMINI_GET_PRICE_RANGE = gemini_types.FunctionDeclaration(
    name="get_historical_price_range",
    description="Fetches daily closing stock prices for a ticker over a specified date range.",
    parameters=gemini_types.Schema(
        type=gemini_types.Type.OBJECT,
        properties={
            "ticker_symbol": gemini_types.Schema(
                type=gemini_types.Type.STRING, description="The stock ticker symbol."
            ),
            "start_date": gemini_types.Schema(
                type=gemini_types.Type.STRING, description="The start date in YYYY-MM-DD format.",
            ),
            "end_date": gemini_types.Schema(
                type=gemini_types.Type.STRING, description="The end date in YYYY-MM-DD format.",
            ),
        },
        required=["ticker_symbol", "start_date", "end_date"],
    ),
)

OPENAI_GET_STOCK_PRICE = {
    "type": "function",
    "function": {
        "name": "get_historical_stock_price",
        "description": "Fetches historical stock data for a stock ticker on a specific date.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker_symbol": {"type": "string", "description": "The stock ticker symbol (e.g., 'RELIANCE.NS')."},
                "date_str": {"type": "string", "description": "The date in YYYY-MM-DD format."},
            },
            "required": ["ticker_symbol", "date_str"],
        },
    },
}
OPENAI_GET_INDEX_VALUE = {
    "type": "function",
    "function": {
        "name": "get_historical_index_value",
        "description": "Fetches historical data for a market index on a specific date.",
        "parameters": {
            "type": "object",
            "properties": {
                "index_symbol": {"type": "string", "description": "The market index symbol (e.g., '^NSEI')."},
                "date_str": {"type": "string", "description": "The date in YYYY-MM-DD format."},
            },
            "required": ["index_symbol", "date_str"],
        },
    },
}
OPENAI_GET_PRICE_RANGE = {
    "type": "function",
    "function": {
        "name": "get_historical_price_range",
        "description": "Fetches daily closing stock prices for a ticker over a specified date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker_symbol": {"type": "string", "description": "The stock ticker symbol."},
                "start_date": {"type": "string", "description": "The start date in YYYY-MM-DD format."},
                "end_date": {"type": "string", "description": "The end date in YYYY-MM-DD format."},
            },
            "required": ["ticker_symbol", "start_date", "end_date"],
        },
    },
}

ANTHROPIC_GET_STOCK_PRICE = {
    "name": "get_historical_stock_price",
    "description": "Fetches historical stock data for a stock ticker on a specific date.",
    "input_schema": { 
        "type": "object",
        "properties": {
            "ticker_symbol": {"type": "string", "description": "The stock ticker symbol (e.g., 'RELIANCE.NS')."},
            "date_str": {"type": "string", "description": "The date in 'YYYY-MM-DD' format."},
        },
        "required": ["ticker_symbol", "date_str"],
    },
}
ANTHROPIC_GET_INDEX_VALUE = {
    "name": "get_historical_index_value",
    "description": "Fetches historical data for a market index on a specific date.",
    "input_schema": {
        "type": "object",
        "properties": {
            "index_symbol": {"type": "string", "description": "The market index symbol (e.g., '^NSEI')."},
            "date_str": {"type": "string", "description": "The date in 'YYYY-MM-DD' format."},
        },
        "required": ["index_symbol", "date_str"],
    },
}
ANTHROPIC_GET_PRICE_RANGE = {
    "name": "get_historical_price_range",
    "description": "Fetches daily closing stock prices for a ticker over a specified date range.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker_symbol": {"type": "string", "description": "The stock ticker symbol."},
            "start_date": {"type": "string", "description": "The start date in 'YYYY-MM-DD' format."},
            "end_date": {"type": "string", "description": "The end date in 'YYYY-MM-DD' format."},
        },
        "required": ["ticker_symbol", "start_date", "end_date"],
    },
}

DEEPSEEK_GET_STOCK_PRICE = {
    "type": "function",
    "function": {
        "name": "get_historical_stock_price",
        "description": "Fetches historical stock data for a stock ticker on a specific date.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker_symbol": {"type": "string", "description": "The stock ticker symbol (e.g., 'RELIANCE.NS')."},
                "date_str": {"type": "string", "description": "The date in 'YYYY-MM-DD' format."},
            },
            "required": ["ticker_symbol", "date_str"],
        },
    },
}
DEEPSEEK_GET_INDEX_VALUE = {
    "type": "function",
    "function": {
        "name": "get_historical_index_value",
        "description": "Fetches historical data for a market index on a specific date.",
        "parameters": {
            "type": "object",
            "properties": {
                "index_symbol": {"type": "string", "description": "The market index symbol (e.g., '^NSEI')."},
                "date_str": {"type": "string", "description": "The date in 'YYYY-MM-DD' format."},
            },
            "required": ["index_symbol", "date_str"],
        },
    },
}
DEEPSEEK_GET_PRICE_RANGE = {
    "type": "function",
    "function": {
        "name": "get_historical_price_range",
        "description": "Fetches daily closing stock prices for a ticker over a specified date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker_symbol": {"type": "string", "description": "The stock ticker symbol."},
                "start_date": {"type": "string", "description": "The start date in 'YYYY-MM-DD' format."},
                "end_date": {"type": "string", "description": "The end date in 'YYYY-MM-DD' format."},
            },
            "required": ["ticker_symbol", "start_date", "end_date"],
        },
    },
}