import json
import os

from openai import OpenAI

from app.agents.data_agent import (
    get_delayed_orders,
    get_open_support_tickets,
)


def ask_data_agent(message: str) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    tools = [
        {
            "type": "function",
            "name": "get_delayed_orders",
            "description": "Retrieve delayed customer orders from the database.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
            "strict": True,
        },
        {
            "type": "function",
            "name": "get_open_support_tickets",
            "description": "Retrieve open customer support tickets from the database.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
            "strict": True,
        },
    ]

    instructions = (
        "You are a business data assistant. "
        "Use the available database tools when answering questions "
        "about orders or support tickets. "
        "Never invent customer records or database information. "
        "Only make claims supported by the tool results. "
        "Be concise."
    )

    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=message,
        tools=tools,
    )

    max_rounds = 5

    for round_number in range(max_rounds):
        tool_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        if not tool_calls:
            return response.output_text or "No answer was generated."

        tool_results = []

        for call in tool_calls:
            print(f"AI selected tool: {call.name}")

            if call.name == "get_delayed_orders":
                result = get_delayed_orders()

            elif call.name == "get_open_support_tickets":
                result = get_open_support_tickets()

            else:
                raise ValueError(
                    f"Unknown tool requested: {call.name}"
                )

            tool_results.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result),
                }
            )

        response = client.responses.create(
            model=model,
            instructions=instructions,
            previous_response_id=response.id,
            input=tool_results,
            tools=tools,
        )

    raise RuntimeError(
        "Data Agent exceeded the maximum number of tool rounds"
    )