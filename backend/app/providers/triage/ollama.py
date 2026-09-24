import httpx

from .base import (
    SYSTEM_PROMPT,
    RetryableTriageError,
    TriageError,
    TriageResult,
    build_user_prompt,
    parse_triage_json,
)
from .llm import TIMEOUT_SECONDS, raise_for_status


class OllamaTriage:
    """Fully offline path: local Ollama container, same interface."""

    name = "llm:ollama"

    def __init__(self, base_url: str, model: str, client: httpx.Client | None = None) -> None:
        self._model = model
        self._url = base_url.rstrip("/") + "/api/chat"
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS)

    def triage(self, text: str, location: str) -> TriageResult:
        body = {
            "model": self._model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(text, location)},
            ],
        }
        try:
            resp = self._client.post(self._url, json=body)
        except httpx.TimeoutException as exc:
            raise RetryableTriageError("timeout") from exc
        except httpx.HTTPError as exc:
            raise TriageError(type(exc).__name__) from exc
        raise_for_status(resp)
        try:
            content = resp.json()["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise TriageError("unexpected response shape") from exc
        return parse_triage_json(content)
