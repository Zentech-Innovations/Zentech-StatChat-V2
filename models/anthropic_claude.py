# models/anthropic_claude.py
import streamlit as st
import anthropic 
import json
from app_modules import tool_declaration

def generate_claude_response(
    api_key: str,
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
        client = anthropic.Anthropic(api_key=api_key)

        messages_for_claude = []
        
        for msg in current_chat_messages:
            if msg["role"] == "user":
                if isinstance(msg.get("content"), list) and any(item.get("type") == "tool_result" for item in msg["content"]):
                    messages_for_claude.append({"role": "user", "content": msg["content"]})
                else:
                    messages_for_claude.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                if isinstance(msg.get("content"), list) and any(item.get("type") == "tool_use" for item in msg["content"]):
                    messages_for_claude.append({"role": "assistant", "content": msg["content"]})
                else:
                    messages_for_claude.append({"role": "assistant", "content": msg["content"]})
            elif msg["role"] == "tool": 
                parsed_tool_content = json.loads(msg["content"])
                
                if isinstance(parsed_tool_content, list) and all(isinstance(item, dict) and "type" in item and item["type"] == "tool_result" for item in parsed_tool_content):
                    messages_for_claude.append({"role": "user", "content": parsed_tool_content})
                else:
                    if isinstance(parsed_tool_content, dict) and "tool_call_id" in parsed_tool_content:
                        messages_for_claude.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": parsed_tool_content["tool_call_id"],
                                    "content": json.dumps(parsed_tool_content.get("content", {}))
                                }
                            ]
                        })
                    else:
                        messages_for_claude.append({"role": "user", "content": json.dumps(parsed_tool_content)})

        messages_for_claude.append({"role": "user", "content": user_query})

        claude_tool_declarations = available_tools

        MAX_TOOL_CALL_ITERATIONS = 5
        num_tool_calls = 0
        
        generated_history_for_save = list(messages_for_claude) 

        while num_tool_calls < MAX_TOOL_CALL_ITERATIONS:
            try:
                response = client.messages.create(
                    model=model_id,
                    max_tokens=4000,
                    system=system_instruction,
                    messages=generated_history_for_save, 
                    tools=claude_tool_declarations,
                    tool_choice={"type": "auto"}
                )
            except anthropic.APIStatusError as e:
                final_text_response = f"Anthropic API Error: {e.status_code} - {e.response.text}"
                return final_text_response, generated_history_for_save, updated_chat_metadata
            except Exception as e:
                final_text_response = f"Anthropic API Request Failed: {str(e)}"
                return final_text_response, generated_history_for_save, updated_chat_metadata

            if response.content:
                generated_history_for_save.append({"role": "assistant", "content": response.content})

            tool_uses = [block for block in response.content if block.type == 'tool_use']
            
            if tool_uses:
                tool_results_for_claude_api = []
                for tool_use in tool_uses:
                    tool_name = tool_use.name
                    tool_args = tool_use.input
                    
                    if tool_name in tool_declaration.TOOL_IMPLEMENTATIONS:
                        implementation = tool_declaration.TOOL_IMPLEMENTATIONS[tool_name]

                        if tool_name in ["get_personal_financial_trades", "get_cdsl_portfolio"]: 
                            tool_args["client_code"] = client_code_from_session

                        try:
                            tool_output_raw = implementation(**tool_args)  
                            
                            if not isinstance(tool_output_raw, str):
                                tool_output_raw = json.dumps(tool_output_raw)

                            tool_results_for_claude_api.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": tool_output_raw 
                            })
                            
                            generated_history_for_save.append({
                                "role": "user", 
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": tool_use.id,
                                    "content": tool_output_raw 
                                }]
                            })
                        except Exception as e_tool_exec:
                            error_content_dict = {"error": f"Tool {tool_name} execution failed: {str(e_tool_exec)}"}
                            error_content_str = json.dumps(error_content_dict)
                            tool_results_for_claude_api.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": error_content_str
                            })

                            generated_history_for_save.append({
                                "role": "user",
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": tool_use.id,
                                    "content": error_content_str
                                }]
                            })
                    else:
                        error_content_dict = {"error": f"Tool {tool_name} not found."}
                        error_content_str = json.dumps(error_content_dict)
                        tool_results_for_claude_api.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": error_content_str
                        })
                        generated_history_for_save.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": error_content_str
                            }]
                        })
                
                num_tool_calls += 1
                continue 

            else: 
                final_response_content = "".join([block.text for block in response.content if block.type == 'text'])
                break 

        if num_tool_calls >= MAX_TOOL_CALL_ITERATIONS:
            final_text_response = "Exceeded max function calls."
        elif final_response_content:
            final_text_response = final_response_content
        else:
            final_response_content = "Empty response."

    except Exception as e:
        final_text_response = f"Unexpected error: {str(e)}"
        st.exception(e)

    return final_text_response, generated_history_for_save, updated_chat_metadata