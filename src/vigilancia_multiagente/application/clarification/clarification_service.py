from dataclasses import dataclass
from uuid import UUID

from vigilancia_multiagente.domain.ports.llm_client import LLMClient
from vigilancia_multiagente.domain.ports.prompt_loader import PromptLoader
from vigilancia_multiagente.domain.system_base import MiniMaxMessage


@dataclass(slots=True, frozen=True)
class ClarificationQuestion:
    id: str
    text: str
    options: tuple[str, ...]


class ClarificationService:
    def __init__(self, prompt_loader: PromptLoader | None = None) -> None:
        self._prompt_loader = prompt_loader
        self._answers: dict[UUID, dict[str, str]] = {}

    async def generate_questions(
        self, user_query: str, llm: LLMClient | None = None
    ) -> list[ClarificationQuestion]:
        if llm is not None and self._prompt_loader is not None:
            import json

            try:
                prompt = self._prompt_loader.load("orchestration/clarify").format(
                    user_query=user_query
                )
                response = await llm.complete(
                    messages=[MiniMaxMessage(role="user", content=prompt)]
                )
                data = json.loads(response.content)
                return [
                    ClarificationQuestion(id=q["id"], text=q["text"], options=tuple(q["options"]))
                    for q in data.get("questions", [])
                ]
            except (json.JSONDecodeError, KeyError, TypeError, RuntimeError):
                pass
        return [
            ClarificationQuestion(
                id="scope-horizon",
                text="What horizon should be prioritized?",
                options=("short-term", "mid-term", "long-term"),
            ),
            ClarificationQuestion(
                id="scope-geo",
                text="What geographic scope should be prioritized?",
                options=("global", "latam", "country-specific"),
            ),
        ]

    def save_answers(self, session_id: UUID, answers: dict[str, str]) -> None:
        self._answers[session_id] = answers

    def get_answers(self, session_id: UUID) -> dict[str, str]:
        return self._answers.get(session_id, {})
