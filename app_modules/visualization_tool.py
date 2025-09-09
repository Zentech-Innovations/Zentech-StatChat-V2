# app_modules/visualization_tool.py
import streamlit as st
import plotly.express as px
import pandas as pd
from google.genai.types import FunctionDeclaration, Schema, Type

def create_comparison_chart(data, title, chart_type='bar', x_axis='item', y_axis='value'):
    if not data or not all(x_axis in d and y_axis in d for d in data):
        st.warning("Chart could not be generated due to incomplete data from the AI.")
        return f"Error: Chart could not be generated due to incomplete or malformed data for '{title}'."

    df = pd.DataFrame(data)

    if chart_type.lower() == 'line':
        if x_axis == 'Date' and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values(by='Date')
        fig = px.line(df, x=x_axis, y=y_axis, title=title, markers=True, text=y_axis)
        fig.update_traces(textposition="top center")

    else:
        fig = px.bar(df, x=x_axis, y=y_axis, title=title, text=y_axis, color=x_axis)
        fig.update_traces(texttemplate='%{text:,.2f}', textposition='outside')

    fig.update_layout(
        title_x=0.5,
        yaxis_title=None,
        xaxis_title=None,
        legend_title=None,
        showlegend=(chart_type.lower() != 'line')
    )
    st.session_state.figure_to_display = fig
    st.session_state.chart_just_generated = True
    return f"Success: The chart titled '{title}' has been generated and is ready for display."

VISUALIZATION_TOOL_GEMINI = FunctionDeclaration(
    name="display_comparison_chart",
    description="Displays a bar or line chart to visually compare financial data or show trends over time.",
    parameters=Schema(
        type=Type.OBJECT,
        properties={
            "chart_type": Schema(type=Type.STRING, enum=["bar", "line"], description="The type of chart. 'bar' or 'line'."),
            "title": Schema(type=Type.STRING, description="The title for the chart."),
            "data": Schema(
                type=Type.ARRAY,
                description="The data to plot. A list of objects. For line charts, objects MUST contain a 'Date' key and a 'Close' key.",
                items=Schema(
                    type=Type.OBJECT,
                    properties={
                        "item": Schema(type=Type.STRING, description="The label for data points (e.g., stock or segment name, or a Date for line chart if x_axis='Date')."),
                        "value": Schema(type=Type.NUMBER, description="The numerical value for data points (e.g., profit amount, or a Close price for line chart if y_axis='Close')."),
                        "Date": Schema(type=Type.STRING, description="Required for 'line' chart_type. The date for a data point in 'YYYY-MM-DD' format."),
                        "Close": Schema(type=Type.NUMBER, description="Required for 'line' chart_type. The closing price for the date.")
                    },
                )
            ),
            "x_axis": Schema(type=Type.STRING, description="The key from the data object to use for the x-axis. For line charts, this is typically 'Date'."),
            "y_axis": Schema(type=Type.STRING, description="The key from the data object to use for the y-axis. For line charts, this is typically 'Close'.")
        },
        required=["title", "data", "chart_type", "x_axis", "y_axis"]
    )
)

OPENAI_VISUALIZATION_TOOL = {
    "type": "function",
    "function": {
        "name": "display_comparison_chart",
        "description": "Displays a bar or line chart to visually compare financial data or show trends over time.",
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line"],
                    "description": "The type of chart to display."
                },
                "title": {"type": "string", "description": "The title for the chart."},
                "data": {
                    "type": "array",
                    "description": "The data to be plotted. A list of objects. For line charts, objects MUST contain a 'Date' key (YYYY-MM-DD string) and a 'Close' key (number).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item": {"type": "string", "description": "The label for a data point (e.g., stock name, segment, or Date for line chart)."},
                            "value": {"type": "number", "description": "The numerical value for a data point (e.g., profit amount, or Close price for line chart)."},
                            "Date": {"type": "string", "description": "Required for 'line' chart_type. The date for a data point in 'YYYY-MM-DD' format."},
                            "Close": {"type": "number", "description": "Required for 'line' chart_type. The closing price for the date."}
                        },
                    }
                },
                "x_axis": {"type": "string", "description": "The key from the data object to use for the x-axis. For line charts, this is typically 'Date'."},
                "y_axis": {"type": "string", "description": "The key from the data object to use for the y-axis. For line charts, this is typically 'Close'."}
            },
            "required": ["title", "data", "chart_type", "x_axis", "y_axis"]
        }
    }
}

ANTHROPIC_VISUALIZATION_TOOL = {
    "name": "display_comparison_chart",
    "description": "Displays a bar or line chart to visually compare financial data or show trends over time.",
    "input_schema": {
        "type": "object",
        "properties": {
            "chart_type": {
                "type": "string",
                "enum": ["bar", "line"],
                "description": "The type of chart. 'bar' or 'line'."
            },
            "title": {"type": "string", "description": "The title for the chart."},
            "data": {
                "type": "array",
                "description": "The data to plot. A list of objects. For line charts, objects MUST contain a 'Date' key and a 'Close' key.",
                "items": {
                    "type": "object",
                    "properties": {
                        "item": {"type": "string", "description": "The label for data points (e.g., stock or segment name, or a Date for line chart if x_axis='Date')."},
                        "value": {"type": "number", "description": "The numerical value for data points (e.g., profit amount, or a Close price for line chart if y_axis='Close')."},
                        "Date": {"type": "string", "description": "Required for 'line' chart_type. The date for a data point in 'YYYY-MM-DD' format."},
                        "Close": {"type": "number", "description": "Required for 'line' chart_type. The closing price for the date."}
                    },
                }
            },
            "x_axis": {"type": "string", "description": "The key from the data object to use for the x-axis. For line charts, this is typically 'Date'."},
            "y_axis": {"type": "string", "description": "The key from the data object to use for the y-axis. For line charts, this is typically 'Close'."}
        },
        "required": ["title", "data", "chart_type", "x_axis", "y_axis"]
    },
}

DEEPSEEK_VISUALIZATION_TOOL = {
    "type": "function",
    "function": {
        "name": "display_comparison_chart",
        "description": "Displays a bar or line chart to visually compare financial data or show trends over time.",
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line"],
                    "description": "The type of chart to display."
                },
                "title": {"type": "string", "description": "The title for the chart."},
                "data": {
                    "type": "array",
                    "description": "The data to be plotted. A list of objects. For line charts, objects MUST contain a 'Date' key (YYYY-MM-DD string) and a 'Close' key (number).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item": {"type": "string", "description": "The label for a data point (e.g., stock name, segment, or Date for line chart)."},
                            "value": {"type": "number", "description": "The numerical value for a data point (e.g., profit amount, or Close price for line chart)."},
                            "Date": {"type": "string", "description": "Required for 'line' chart_type. The date for a data point in 'YYYY-MM-DD' format."},
                            "Close": {"type": "number", "description": "Required for 'line' chart_type. The closing price for the date."}
                        },
                    }
                },
                "x_axis": {"type": "string", "description": "The key from the data object to use for the x-axis. For line charts, this is typically 'Date'."},
                "y_axis": {"type": "string", "description": "The key from the data object to use for the y-axis. For line charts, this is typically 'Close'."}
            },
            "required": ["title", "data", "chart_type", "x_axis", "y_axis"]
        }
    }
}