import os

from openai import OpenAI


def generate_ai_response(message: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OpenAI API key is not configured")

    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        input=message,
    )

    if not response.output_text:
        raise RuntimeError("OpenAI returned an empty response")

    return response.output_text