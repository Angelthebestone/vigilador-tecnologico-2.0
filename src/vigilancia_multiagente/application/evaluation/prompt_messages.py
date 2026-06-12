"""Helpers para construir listas de mensajes MiniMax con few-shot.

Cada prompt de evaluacion puede tener, junto a su archivo de instrucciones
`<name>.txt` (system), un par opcional de archivos
`<name>.example_user.txt` y `<name>.example_ai.txt` que se inyectan como
`sample_message_user` y `sample_message_ai`. Si alguno de los dos no
existe, el par se omite (el adapter sigue funcionando con solo system +
user).
"""

from __future__ import annotations

from vigilancia_multiagente.domain.ports.prompt_loader import PromptLoader
from vigilancia_multiagente.domain.system_base import MiniMaxMessage


def build_messages_with_fewshot(
    *,
    prompt_loader: PromptLoader,
    base_path: str,
    user_content: str,
) -> list[MiniMaxMessage]:
    """Arma la lista de mensajes para una llamada LLM con few-shot opcional.

    *base_path* es la ruta del system prompt sin sufijo, p. ej.
    "evaluation/assumption_detection.txt". El helper deriva los nombres
    de los archivos de ejemplo reemplazando el sufijo:
    `assumption_detection.example_user.txt` y
    `assumption_detection.example_ai.txt`.

    Lanza ``FileNotFoundError`` si el system prompt no existe; el caller
    debe atrapar la excepcion. Si los archivos de ejemplo no existen, el
    par se omite silenciosamente.
    """
    system_prompt = prompt_loader.load(base_path)

    if not base_path.endswith(".txt"):
        raise ValueError(f"base_path must end with .txt: {base_path}")
    stem = base_path[: -len(".txt")]
    example_user_path = f"{stem}.example_user.txt"
    example_ai_path = f"{stem}.example_ai.txt"

    example_user: str | None
    example_ai: str | None
    try:
        example_user = prompt_loader.load(example_user_path)
    except FileNotFoundError:
        example_user = None
    try:
        example_ai = prompt_loader.load(example_ai_path)
    except FileNotFoundError:
        example_ai = None

    messages: list[MiniMaxMessage] = [
        MiniMaxMessage(role="system", content=system_prompt),
    ]
    if example_user and example_ai:
        messages.append(MiniMaxMessage(role="sample_message_user", content=example_user))
        messages.append(MiniMaxMessage(role="sample_message_ai", content=example_ai))
    messages.append(MiniMaxMessage(role="user", content=user_content))
    return messages
