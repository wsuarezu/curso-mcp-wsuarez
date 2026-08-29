"""In-memory conversation history — the model 'remembers' because we resend it."""

import logging
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

# El SDK sugiere Chat.send_message; aqui construimos el historial a mano a proposito.
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODEL = "gemini-3.5-flash-lite"
RATE_LIMIT_MODEL = "gemini-3.5-flash"  # free tier: solo 20 requests/dia
SYSTEM_INSTRUCTION = "Eres un asistente breve. Respondes en español."
TEMPERATURE = 0.7
MAX_OUTPUT_TOKENS = 500

# List of plain dicts, same shape as `contents` — nothing hidden here.
history: list[dict] = []


MAX_TURNS = 10  # keeps the last 10 user/model exchanges (20 entries)


def trim_history() -> None:
    max_entries = MAX_TURNS * 2
    if len(history) > max_entries:
        del history[:-max_entries]


def send(message: str, _retries: int = 0) -> str:
    trim_history()
    history.append({"role": "user", "parts": [{"text": message}]})

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=TEMPERATURE,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            ),
        )
    except errors.ClientError as exc:
        if exc.code == 429 and _retries < 3:
            wait = 2 ** _retries
            print(f"[429 {exc.status}] Límite de RPM alcanzado. Reintentando en {wait}s...")
            time.sleep(wait)
            history.pop()  # avoid duplicating the same user turn
            return send(message, _retries=_retries + 1)
        history.pop()
        return f"Error del cliente ({exc.code}): {exc.message}. No se reintenta."
    except errors.ServerError as exc:
        if _retries < 3:
            wait = 2 ** _retries
            print(f"[{exc.code}] Error del servidor. Reintentando en {wait}s...")
            time.sleep(wait)
            history.pop()
            return send(message, _retries=_retries + 1)
        history.pop()
        return f"El servicio no respondió tras varios intentos ({exc.code})."

    usage = response.usage_metadata
    print(
        f"[tokens] total={usage.total_token_count} "
        f"(prompt={usage.prompt_token_count}, respuesta={usage.candidates_token_count})"
    )

    finish_reason = str(response.candidates[0].finish_reason)
    if "MAX_TOKENS" in finish_reason:
        print("[warning] Respuesta truncada por max_output_tokens.")

    history.append({"role": "model", "parts": [{"text": response.text}]})
    return response.text


def main() -> None:
    # 8 turns: the fact goes in turn 1, and gets asked back at turn 8.
    turns = [
        "Me llamo Alex y mi color favorito es el verde.",
        "¿Qué framework de Python vimos en la Clase 1?",
        "Dame un ejemplo de dato que no cabe en un int.",
        "¿Qué hace el comando uv init?",
        "Explica en una frase qué es un token.",
        "¿Qué significa que una API sea stateless?",
        "¿Para qué sirve un archivo .env?",
        "¿Cómo me llamo y cuál es mi color favorito?",
    ]
    for n, question in enumerate(turns, start=1):
        print(f"===== TURNO {n} de {len(turns)} =====")
        print(f"USUARIO: {question}")
        print(f"BOT    : {send(question)}")
        print(f"[history: {len(history)} entradas]\n")


def trigger_rate_limit() -> None:
    """Sends several requests back to back to hit the free tier's requests-per-minute cap."""
    global history, MODEL
    history = []
    original_model = MODEL
    MODEL = RATE_LIMIT_MODEL  # cuota mas baja: el 429 llega antes
    try:
        for i in range(1, 21):
            print(f"Request {i}: {send(f'Cuenta hasta {i}.')}")
    finally:
        MODEL = original_model
        history = []


if __name__ == "__main__":
    main()
