# models/grok_chat.py
import streamlit as st
import openai
import json
from app_modules import tool_declaration

ASSISTANT_NAME = "Financial_Assistant_Grok" 

def get_or_create_assistant(client, system_instruction, model_id, assistant_name, available_tools):
    assistant_fingerprint = f"{assistant_name}_{model_id}"
    try:
        assistants = client.beta.assistants.list(limit=100) 
        for assistant in assistants.data:
            if assistant.name == assistant_fingerprint:
                current_assistant_tool_names = sorted([t.function.name for t in assistant.tools])
                new_tools_names = sorted([t['function']['name'] for t in available_tools])
                if current_assistant_tool_names != new_tools_names:
                    client.beta.assistants.update(
                        assistant_id=assistant.id,
                        tools=available_tools,
                        instructions=system_instruction
                    )
                    return client.beta.assistants.retrieve(assistant.id)
                return assistant

        all_tools = available_tools

        assistant = client.beta.assistants.create(
            name=assistant_fingerprint,
            instructions=system_instruction,
            model=model_id,
            tools=all_tools,
        )
        return assistant
    except AttributeError:
        return None
    except Exception as e:
        st.error(f"Error getting/creating Grok assistant: {e}")
        return None

def generate_grok_response(
    api_key: str,
    api_base: str, 
    model_id: str,
    system_instruction: str,
    current_chat_messages: list,
    user_query: str,
    client_code_from_session: str,
    available_tools: list
):
    final_text_response = "Error: Model processing failed."
    updated_chat_metadata = {} 

    try:
        client = openai.OpenAI(api_key=api_key, base_url=api_base)

        messages_for_grok = []
        messages_for_grok.append({"role": "system", "content": system_instruction})

        for msg in current_chat_messages:
            if msg["role"] == "user":
                messages_for_grok.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                if "tool_calls" in msg and isinstance(msg["tool_calls"], list):
                    messages_for_grok.append({"role": "assistant", "tool_calls": msg["tool_calls"]})
                else:
                    messages_for_grok.append({"role": "assistant", "content": msg["content"]})
            elif msg["role"] == "tool":
                messages_for_grok.append({
                    "role": "tool",
                    "tool_call_id": msg["tool_call_id"],
                    "content": msg["content"] 
                })

        messages_for_grok.append({"role": "user", "content": user_query})

        grok_tool_declarations = available_tools

        MAX_TOOL_CALL_ITERATIONS = 5 
        num_tool_calls = 0

        generated_history_for_save = list(messages_for_grok)

        while num_tool_calls < MAX_TOOL_CALL_ITERATIONS:
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=generated_history_for_save, 
                    tools=grok_tool_declarations,
                    tool_choice="auto", 
                    temperature=0.1,
                    max_tokens=4000 
                )
            except openai.APIStatusError as e:
                final_text_response = f"Grok API Error: {e.status_code} - {e.response.text}"
                return final_text_response, generated_history_for_save, updated_chat_metadata
            except Exception as e:
                final_text_response = f"Grok API Request Failed: {str(e)}"
                return final_text_response, generated_history_for_save, updated_chat_metadata

            response_message = response.choices[0].message

            if response_message.content or response_message.tool_calls:
                msg_to_store = {"role": "assistant"}
                if response_message.content:
                    msg_to_store["content"] = response_message.content
                if response_message.tool_calls:
                    tool_calls_list = []
                    for tc in response_message.tool_calls:
                        tool_calls_list.append({
                            "id": tc.id,
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                            "type": tc.type 
                        })
                    msg_to_store["tool_calls"] = tool_calls_list
                generated_history_for_save.append(msg_to_store)


            if response_message.tool_calls:
                tool_outputs = []
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    if tool_name in tool_declaration.TOOL_IMPLEMENTATIONS:
                        implementation = tool_declaration.TOOL_IMPLEMENTATIONS[tool_name]

                        if tool_name in ["get_personal_financial_trades", "get_cdsl_portfolio"]: 
                            tool_args["client_code"] = client_code_from_session

                        try:
                            tool_output_raw = implementation(**tool_args)
                            
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "content": tool_output_raw 
                            })
                            generated_history_for_save.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": tool_output_raw
                            })
                        except Exception as e_tool_exec:
                            error_content = json.dumps({"error": f"Tool {tool_name} failed: {str(e_tool_exec)}"})
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "content": error_content
                            })
                            generated_history_for_save.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": error_content
                            })
                    else:
                        error_content = json.dumps({"error": f"Tool {tool_name} not found."})
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "content": error_content
                        })
                        generated_history_for_save.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": error_content
                        })

                num_tool_calls += 1
                continue 

            else:

                final_response_content = response_message.content
                break

        if num_tool_calls >= MAX_TOOL_CALL_ITERATIONS:
            final_text_response = "Exceeded max function calls."
        elif final_response_content:
            final_text_response = final_response_content
        else:
            final_text_response = "Empty response."

    except Exception as e:
        final_text_response = f"An unexpected error occurred: {str(e)}"
        st.exception(e) 

    return final_text_response, generated_history_for_save, updated_chat_metadata