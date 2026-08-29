"""Calls Gemini with a system instruction and explicit generation parameters."""

import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# El SDK sugiere Chat.send_message; aqui construimos el historial a mano a proposito.
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODEL = "gemini-3.5-flash"
CONTEXT_WINDOW_LIMIT = 1_048_576  # tokens de entrada de gemini-3.5-flash

SYSTEM_INSTRUCTION = (
    "Eres un instructor de programación para principiantes. "
    "Respondes en español, máximo 3 frases. "
    "Sin jerga sin explicar, sin inventar funciones."
)


def print_budget(contents: list[dict]) -> None:
    tokens = client.models.count_tokens(model=MODEL, contents=contents)
    used_ratio = tokens.total_tokens / CONTEXT_WINDOW_LIMIT
    print(f"Historial: {tokens.total_tokens} tokens ({used_ratio:.4%} de la ventana)")


def ask(prompt: str, temperature: float = 1.7) -> tuple[str, str]:
    """Returns (text, finish_reason)."""
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    print_budget(contents)
    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=temperature,
            max_output_tokens=3000,
        ),
    )
    finish_reason = str(response.candidates[0].finish_reason)
    if "MAX_TOKENS" in finish_reason:
        print("[warning] La respuesta viene truncada por max_output_tokens.")
    return response.text, finish_reason


def main() -> None:
    r1_text, _ = ask("Hola, me llamo Valeria.")
    print("BOT:", r1_text)

    r2_text, _ = ask("¿Cómo me llamo?")
    print("BOT:", r2_text)


if __name__ == "__main__":
    main()
