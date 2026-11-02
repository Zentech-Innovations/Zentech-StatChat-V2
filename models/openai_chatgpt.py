
# models/openai_chatgpt.py

import json
import openai

from app_modules import tool_declaration


MAX_TOOL_CALL_ROUNDS = 8

SESSION_SPECIFIC_TOOLS = {
    "get_personal_financial_trades",
    "get_nsdl_portfolio",
}


def convert_tools_to_responses_format(available_tools: list) -> list:
    """
    Convert existing OpenAI function declarations
    into Responses API function declarations.
    """
    responses_tools = []

    for tool in available_tools:
        if tool.get("type") != "function":
            continue

        function = tool["function"]

        responses_tool = {
            "type": "function",
            "name": function["name"],
            "parameters": function.get("parameters", {}),
        }

        if function.get("description"):
            responses_tool["description"] = function["description"]

        if "strict" in function:
            responses_tool["strict"] = function["strict"]

        responses_tools.append(responses_tool)

    return responses_tools


def get_or_create_conversation(client, chat_metadata: dict) -> str:
    """
    Retrieve an existing conversation ID or create a new conversation.
    """
    conversation_id = chat_metadata.get("openai_conversation_id")

    if not conversation_id:
        conversation = client.conversations.create()
        conversation_id = conversation.id
        chat_metadata["openai_conversation_id"] = conversation_id

    return conversation_id


def execute_tool_call(tool_call, client_code_from_session: str) -> str:
    """
    Execute a requested function and return its output.
    """
    tool_name = tool_call.name

    try:
        tool_args = json.loads(tool_call.arguments)

        if not isinstance(tool_args, dict):
            raise ValueError("Tool arguments must be a JSON object.")

        implementation = tool_declaration.TOOL_IMPLEMENTATIONS.get(
            tool_name
        )

        if implementation is None:
            raise ValueError(f"Tool {tool_name} not found.")

        if tool_name in SESSION_SPECIFIC_TOOLS:
            tool_args["client_code"] = client_code_from_session

        output = implementation(**tool_args)

        if isinstance(output, str):
            return output

        return json.dumps(output, default=str)

    except Exception as e:
        return json.dumps({
            "error": f"Tool {tool_name} failed: {str(e)}"
        })


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
    reconstructed_history = list(current_chat_messages)

    try:
        client = openai.OpenAI(api_key=api_key)

        # Convert existing function declarations.
        responses_tools = convert_tools_to_responses_format(
            available_tools
        )

        # Retrieve or create a persistent conversation.
        conversation_id = get_or_create_conversation(
            client,
            updated_chat_metadata
        )

        # Remove the obsolete Assistants API metadata.
        updated_chat_metadata.pop("openai_thread_id", None)

        # Add the current user message to local history.
        reconstructed_history.append({
            "role": "user",
            "content": user_query
        })

        # Initial Responses API request.
        response = client.responses.create(
            model=model_id,
            instructions=system_instruction,
            conversation=conversation_id,
            input=user_query,
            tools=responses_tools,
        )

        tool_call_rounds = 0

        while True:

            # Check response status.
            if response.status != "completed":
                error_details = (
                    response.error
                    or response.incomplete_details
                    or "No additional error details."
                )

                raise RuntimeError(
                    f"Response finished with status "
                    f"'{response.status}': {error_details}"
                )

            # Extract function calls.
            function_calls = [
                item
                for item in response.output
                if item.type == "function_call"
            ]

            # No more function calls: final response received.
            if not function_calls:
                break

            if tool_call_rounds >= MAX_TOOL_CALL_ROUNDS:
                raise RuntimeError(
                    "Maximum function-call rounds exceeded."
                )

            tool_call_rounds += 1

            tool_outputs = []
            assistant_tool_calls = []

            # Execute all requested functions.
            for tool_call in function_calls:

                assistant_tool_calls.append({
                    "id": tool_call.call_id,
                    "type": "function",
                    "function": {
                        "name": tool_call.name,
                        "arguments": tool_call.arguments,
                    }
                })

                tool_output = execute_tool_call(
                    tool_call,
                    client_code_from_session
                )

                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": tool_output,
                })

            # Preserve assistant function-call history.
            assistant_message = {
                "role": "assistant",
                "tool_calls": assistant_tool_calls,
            }

            if response.output_text:
                assistant_message["content"] = response.output_text

            reconstructed_history.append(assistant_message)

            # Preserve individual tool outputs.
            for tool_output in tool_outputs:
                reconstructed_history.append({
                    "role": "tool",
                    "tool_call_id": tool_output["call_id"],
                    "content": tool_output["output"],
                })

            # Submit function outputs to the Responses API.
            response = client.responses.create(
                model=model_id,
                instructions=system_instruction,
                conversation=conversation_id,
                input=tool_outputs,
                tools=responses_tools,
            )

        # Extract the final assistant response.
        final_text_response = response.output_text

        if not final_text_response:
            final_text_response = (
                "OpenAI response completed, "
                "but no final text message was found."
            )

        reconstructed_history.append({
            "role": "assistant",
            "content": final_text_response,
        })

        return (
            final_text_response,
            reconstructed_history,
            updated_chat_metadata,
        )

    except Exception as e:
        final_text_response = (
            f"An unexpected error occurred: {str(e)}"
        )

        return (
            final_text_response,
            reconstructed_history,
            updated_chat_metadata,
        )
