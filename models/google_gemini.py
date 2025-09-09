# models/google_gemini.py
import streamlit as st
import json
from google import genai
from google.genai import types
from app_modules import app_config, tool_declaration


def generate_gemini_response(
    client: genai.Client,
    current_chat_messages: list,
    user_query: str,
    current_chat_data: dict,
    system_instruction_str: str,
    gemini_tool_config: types.Tool,
    client_code_from_session: str,
):
    api_conversation_history = [
        types.Content(role="user", parts=[types.Part(text=system_instruction_str)])
    ]

    for msg_idx, msg in enumerate(current_chat_messages):
        role_for_api = "model" if msg["role"] == "assistant" else msg["role"]

        if (
            msg["role"] == "user"
            and msg["content"] == system_instruction_str
            and len(api_conversation_history) == 1
            and api_conversation_history[0].parts[0].text == system_instruction_str
        ):
            continue

        if role_for_api == "user":
            if isinstance(msg["content"], list) and any(
                item.get("type") == "tool_result" for item in msg["content"]
            ):
                parts = []
                for tool_res_block_idx, tool_res_block in enumerate(msg["content"]):
                    if tool_res_block.get("type") == "tool_result":
                        response_content = tool_res_block.get("content")
                        if isinstance(response_content, str):
                            try:
                                response_content = json.loads(response_content)
                            except json.JSONDecodeError:
                                response_content = {"error": f"Invalid JSON in tool_result: {response_content[:100]}..."}
                        
                        if isinstance(response_content, list):
                            response_content = {"data": response_content}
                        elif not isinstance(response_content, dict):
                            response_content = {"result": str(response_content)}

                        parts.append(
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=tool_res_block.get("name"),
                                    response=response_content,
                                )
                            )
                        )
                    else:
                        parts.append(types.Part(text=tool_res_block.get("text", "")))
                if parts:
                    api_conversation_history.append(
                        types.Content(role="user", parts=parts)
                    )

            elif msg["role"] == "tool" or msg["role"] == "function":
                parsed_msg_content = None
                if isinstance(msg["content"], str):
                    try:
                        parsed_msg_content = json.loads(msg["content"])
                    except json.JSONDecodeError:
                        parsed_msg_content = {"error": f"Invalid JSON from saved tool content: {msg['content'][:100]}..."}
                else:
                    parsed_msg_content = msg["content"]

                tool_results_list = []
                if isinstance(parsed_msg_content, dict) and "name" in parsed_msg_content and "content" in parsed_msg_content:
                    tool_results_list.append(parsed_msg_content)
                elif isinstance(parsed_msg_content, list):
                    tool_results_list.extend(parsed_msg_content)
                else:
                    tool_results_list.append({"name": "unknown_tool_history", "content": {"error": f"Malformed tool content from history: {str(parsed_msg_content)}"} })


                parts = []
                for tool_res_idx, tool_res in enumerate(tool_results_list):
                    response_payload = tool_res.get("content")
                    if isinstance(response_payload, str):
                        try:
                            response_payload = json.loads(response_payload)
                        except json.JSONDecodeError:
                            response_payload = {"error": f"Invalid JSON in old tool_res content: {response_payload[:100]}..."}

                    if isinstance(response_payload, list):
                        response_payload = {"data": response_payload}
                    elif not isinstance(response_payload, dict):
                        response_payload = {"result": str(response_payload)}

                    parts.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=tool_res.get("name"),
                                response=response_payload,
                            )
                        )
                    )
                if parts:
                    api_conversation_history.append(
                        types.Content(role="function", parts=parts)
                    )

            else:
                api_conversation_history.append(
                    types.Content(role="user", parts=[types.Part(text=msg["content"])])
                )

        elif role_for_api == "model":
            if isinstance(msg["content"], list) and any(
                hasattr(part, "function_call") for part in msg["content"]
            ):
                api_conversation_history.append(
                    types.Content(role="model", parts=msg["content"])
                )
            else:
                api_conversation_history.append(
                    types.Content(role="model", parts=[types.Part(text=msg["content"])])
                )
    api_conversation_history.append(
        types.Content(role="user", parts=[types.Part(text=user_query)])
    )

    answer_text = "Error: Model processing failed."
    generated_history_for_save = list(api_conversation_history)

    try:
        MAX_FUNCTION_CALLS = 10
        num_function_calls = 0

        while num_function_calls < MAX_FUNCTION_CALLS:
            gen_config_args = {"temperature": 0.1}
            gen_config_args["tools"] = [gemini_tool_config]
            effective_gen_config = types.GenerateContentConfig(**gen_config_args)

            response = client.models.generate_content(
                model=app_config.MODEL_TO_USE_FOR_API,
                contents=generated_history_for_save,
                config=effective_gen_config,
            )

            if not response.candidates:
                answer_text = "No response candidates."
                if response.prompt_feedback:
                    answer_text += f" PF: {response.prompt_feedback}"
                break

            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                generated_history_for_save.append(candidate.content)

            function_call_to_execute = None
            if candidate.content and candidate.content.parts:
                for part_idx, part in enumerate(candidate.content.parts):
                    if (
                        hasattr(part, "function_call")
                        and part.function_call
                        and part.function_call.name
                    ):
                        function_call_to_execute = part.function_call
                        break

            if function_call_to_execute:
                fc_name = function_call_to_execute.name
                fc_args_struct = function_call_to_execute.args

                if fc_name in tool_declaration.TOOL_IMPLEMENTATIONS:
                    tool_function = tool_declaration.TOOL_IMPLEMENTATIONS[fc_name]
                    args_dict = {key: value for key, value in fc_args_struct.items()}

                    if fc_name == "get_personal_financial_trades" or fc_name == "get_cdsl_portfolio": 
                        args_dict["client_code"] = client_code_from_session

                    try:
                        tool_output_raw = tool_function(**args_dict)

                        parsed_tool_output = None
                        if isinstance(tool_output_raw, str):
                            try:
                                parsed_tool_output = json.loads(tool_output_raw)
                            except json.JSONDecodeError:
                                parsed_tool_output = {"error": f"Invalid JSON from tool '{fc_name}': {tool_output_raw[:100]}..."}
                        else:
                            parsed_tool_output = tool_output_raw

                        tool_response_payload = {} 

                        if fc_name == "get_historical_price_range":
                            if isinstance(parsed_tool_output, list):
                                tool_response_payload = {"historical_prices_data": parsed_tool_output}
                            elif isinstance(parsed_tool_output, dict) and "historical_prices" in parsed_tool_output:
                                tool_response_payload = parsed_tool_output
                            else:
                                tool_response_payload = {"data": parsed_tool_output}
                        elif isinstance(parsed_tool_output, list):
                            tool_response_payload = {"data": parsed_tool_output}
                        elif isinstance(parsed_tool_output, dict):
                            tool_response_payload = parsed_tool_output
                        else:
                            tool_response_payload = {"result": str(parsed_tool_output)}

                    except Exception as e_tool_exec:
                        tool_response_payload = {"error": f"Failed to execute tool {fc_name}: {str(e_tool_exec)}"}

                    generated_history_for_save.append(
                        types.Content(
                            parts=[
                                types.Part(
                                    function_response=types.FunctionResponse(
                                        name=fc_name, response=tool_response_payload
                                    )
                                )
                            ],
                            role="function",
                        )
                    )
                    num_function_calls += 1
                else:
                    answer_text = f"Error: Unavailable tool: {fc_name}."
                    break
            else:
                if candidate.content and candidate.content.parts:
                    answer_text = "".join(
                        part.text
                        for part in candidate.content.parts
                        if hasattr(part, "text")
                    )
                elif candidate.finish_reason not in [
                    types.Candidate.FinishReason.STOP,
                    types.Candidate.FinishReason.FINISH_REASON_UNSPECIFIED,
                    types.Candidate.FinishReason.MAX_TOKENS,
                ]:
                    try:
                        finish_reason_name = types.Candidate.FinishReason(
                            candidate.finish_reason
                        ).name
                    except ValueError:
                        finish_reason_name = (
                            f"UNKNOWN_REASON_({candidate.finish_reason})"
                        )
                    answer_text = f"No content. Reason: {finish_reason_name}."
                    if candidate.safety_ratings:
                        answer_text += f" SR: {candidate.safety_ratings}"
                elif response.prompt_feedback:
                    answer_text = f"No content. PF: {response.prompt_feedback}"
                else:
                    answer_text = "Empty response."
                break

        if num_function_calls >= MAX_FUNCTION_CALLS:
            answer_text = "Exceeded max function calls."

    except Exception as e_outer:
        answer_text = f"Unexpected error: {str(e_outer)}"
        st.exception(e_outer)

    return answer_text, generated_history_for_save, current_chat_data