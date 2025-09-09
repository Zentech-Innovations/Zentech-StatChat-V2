# models/openai_chatgpt.py
import openai
import time
import json
from app_modules import tool_declaration

ASSISTANT_NAME = "Financial_Assistant"

def get_or_create_assistant(client, system_instruction, model_id, available_tools): 
    assistant_fingerprint = f"{ASSISTANT_NAME}_{model_id}"
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

        assistant = client.beta.assistants.create(
            name=assistant_fingerprint,
            instructions=system_instruction,
            model=model_id,
            tools=available_tools, 
        )
        return assistant
    except Exception as e:
        return None

def get_openai_response(
    api_key: str,
    model_id: str,
    system_instruction: str,
    current_chat_messages: list,
    user_query: str,
    current_chat_data: dict,
    client_code_from_session: str,
    available_tools: list 
):
    final_text_response = "Error: Model processing failed."
    updated_chat_metadata = dict(current_chat_data)
    
    try:
        client = openai.OpenAI(api_key=api_key)
        assistant = get_or_create_assistant(client, system_instruction, model_id, available_tools) 
        if not assistant:
            return "Failed to initialize Assistant.", [], updated_chat_metadata

        thread_id = updated_chat_metadata.get("openai_thread_id")
        if not thread_id:
            thread = client.beta.threads.create()
            thread_id = thread.id
            updated_chat_metadata["openai_thread_id"] = thread_id
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_query,
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant.id,
            tools=available_tools 
        )

        while run.status in ["queued", "in_progress", "requires_action"]:
            time.sleep(1) 
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

            if run.status == "requires_action":
                tool_outputs = []
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    if tool_name in tool_declaration.TOOL_IMPLEMENTATIONS:
                        implementation = tool_declaration.TOOL_IMPLEMENTATIONS[tool_name]

                        if tool_name in ["get_personal_financial_trades", "get_cdsl_portfolio"]:
                            tool_args["client_code"] = client_code_from_session

                        try:
                            output = implementation(**tool_args)
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": json.dumps(output),
                            })
                        except Exception as e_tool_exec:
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": json.dumps({"error": f"Tool {tool_name} failed: {str(e_tool_exec)}"}),
                            })
                    else:
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps({"error": f"Tool {tool_name} not found."}),
                        })

                run = client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )

            time.sleep(1) 
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)


        if run.status == "completed":
            messages_page = client.beta.threads.messages.list(thread_id=thread_id, order="asc", limit=100)
            
            reconstructed_history = []
            for msg_obj in messages_page.data:
                if msg_obj.role == "user":
                    if msg_obj.content and msg_obj.content[0].type == "text":
                        reconstructed_history.append({"role": "user", "content": msg_obj.content[0].text.value})

                elif msg_obj.role == "assistant":
                    assistant_msg_dict = {"role": "assistant"}
                    
                    text_content = ""
                    if msg_obj.content:
                        for block in msg_obj.content:
                            if block.type == "text":
                                text_content += block.text.value
                    if text_content:
                        assistant_msg_dict["content"] = text_content

                    if hasattr(msg_obj, 'tool_calls') and msg_obj.tool_calls:
                        tool_calls_list = []
                        for tc in msg_obj.tool_calls:
                            tool_calls_list.append({
                                "id": tc.id,
                                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                                "type": tc.type
                            })
                        assistant_msg_dict["tool_calls"] = tool_calls_list
                    
                    reconstructed_history.append(assistant_msg_dict)

                elif msg_obj.role == "tool":
                    if msg_obj.content and msg_obj.content[0].type == "text":
                        reconstructed_history.append({
                            "role": "tool",
                            "tool_call_id": msg_obj.tool_call_id,
                            "content": msg_obj.content[0].text.value
                        })
            
            if reconstructed_history and reconstructed_history[-1]["role"] == "assistant":
                final_text_response = reconstructed_history[-1]["content"]
            else:
                final_text_response = "OpenAI response completed, but no final text message found."

            return final_text_response, reconstructed_history, updated_chat_metadata

        else:
            error_message = f"Assistant run finished with status: {run.status}"
            if run.last_error: error_message += f" - {run.last_error.message}"
            final_text_response = error_message
            return final_text_response, list(current_chat_messages), updated_chat_metadata

    except Exception as e:
        final_text_response = f"An unexpected error occurred: {str(e)}"
        return final_text_response, list(current_chat_messages), updated_chat_metadata