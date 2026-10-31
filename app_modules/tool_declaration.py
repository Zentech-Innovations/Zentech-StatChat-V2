# app_modules/tool_declaration.py
from . import finance_tool, visualization_tool, monarch_api, cdsl_api

COMMON_FINANCE_TOOLS_GEMINI = [
    finance_tool.GEMINI_GET_STOCK_PRICE,
    finance_tool.GEMINI_GET_INDEX_VALUE,
    finance_tool.GEMINI_GET_PRICE_RANGE,
    visualization_tool.VISUALIZATION_TOOL_GEMINI,
]
COMMON_FINANCE_TOOLS_OPENAI = [
    finance_tool.OPENAI_GET_STOCK_PRICE,
    finance_tool.OPENAI_GET_INDEX_VALUE,
    finance_tool.OPENAI_GET_PRICE_RANGE,
    visualization_tool.OPENAI_VISUALIZATION_TOOL,
]
COMMON_FINANCE_TOOLS_ANTHROPIC = [
    finance_tool.ANTHROPIC_GET_STOCK_PRICE,
    finance_tool.ANTHROPIC_GET_INDEX_VALUE,
    finance_tool.ANTHROPIC_GET_PRICE_RANGE,
    visualization_tool.ANTHROPIC_VISUALIZATION_TOOL,
]
COMMON_FINANCE_TOOLS_DEEPSEEK = [
    finance_tool.DEEPSEEK_GET_STOCK_PRICE,
    finance_tool.DEEPSEEK_GET_INDEX_VALUE,
    finance_tool.DEEPSEEK_GET_PRICE_RANGE,
    visualization_tool.DEEPSEEK_VISUALIZATION_TOOL,
]
COMMON_FINANCE_TOOLS_GROK = [
    finance_tool.OPENAI_GET_STOCK_PRICE, 
    finance_tool.OPENAI_GET_INDEX_VALUE, 
    finance_tool.OPENAI_GET_PRICE_RANGE, 
    visualization_tool.OPENAI_VISUALIZATION_TOOL, 
]


def get_tools_for_profile(profile_key: str, llm_provider: str):

    tools = []

    if llm_provider == "Google":
        tools.extend(COMMON_FINANCE_TOOLS_GEMINI)
    elif llm_provider == "OpenAI":
        tools.extend(COMMON_FINANCE_TOOLS_OPENAI)
    elif llm_provider == "Anthropic":
        tools.extend(COMMON_FINANCE_TOOLS_ANTHROPIC)
    elif llm_provider == "DeepSeek":
        tools.extend(COMMON_FINANCE_TOOLS_DEEPSEEK)
    elif llm_provider == "Grok":
        tools.extend(COMMON_FINANCE_TOOLS_GROK)


    if profile_key == "profile2":  
        if llm_provider == "Google":
            tools.append(monarch_api.GEMINI_GET_PERSONAL_FINANCIAL_TRADES)
        elif llm_provider == "OpenAI":
            tools.append(monarch_api.OPENAI_GET_PERSONAL_FINANCIAL_TRADES)
        elif llm_provider == "Anthropic":
            tools.append(monarch_api.ANTHROPIC_GET_PERSONAL_FINANCIAL_TRADES)
        elif llm_provider == "DeepSeek":
            tools.append(monarch_api.DEEPSEEK_GET_PERSONAL_FINANCIAL_TRADES)
        elif llm_provider == "Grok":
            tools.append(monarch_api.OPENAI_GET_PERSONAL_FINANCIAL_TRADES) 

    elif profile_key == "profile1":  
        if llm_provider == "Google":
            tools.append(cdsl_api.GEMINI_GET_CDSL_PORTFOLIO)
        elif llm_provider == "OpenAI":
            tools.append(cdsl_api.OPENAI_GET_CDSL_PORTFOLIO)
        elif llm_provider == "Anthropic":
            tools.append(cdsl_api.ANTHROPIC_GET_CDSL_PORTFOLIO)
        elif llm_provider == "DeepSeek":
            tools.append(cdsl_api.DEEPSEEK_GET_CDSL_PORTFOLIO)
        elif llm_provider == "Grok":
            tools.append(cdsl_api.GROK_GET_CDSL_PORTFOLIO)

    return tools

TOOL_IMPLEMENTATIONS = {
    "get_historical_stock_price": finance_tool.get_historical_stock_price_impl,
    "get_historical_index_value": finance_tool.get_historical_index_value_impl,
    "get_historical_price_range": finance_tool.get_historical_price_range_impl,
    "display_comparison_chart": visualization_tool.create_comparison_chart,
    "get_personal_financial_trades": monarch_api.get_monarch_personal_financial_trades_impl,
    "get_cdsl_portfolio": cdsl_api.get_cdsl_portfolio,
}
