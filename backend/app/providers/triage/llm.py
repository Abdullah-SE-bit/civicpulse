import httpx

from .base import (
    SYSTEM_PROMPT,
    RetryableTriageError,
    TriageError,
    TriageResult,
    build_user_prompt,
    parse_triage_json,
)

TIMEOUT_SECONDS = 10.0


def raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code == 429 or resp.status_code >= 500:
        raise RetryableTriageError(f"upstream status {resp.status_code}")
    if resp.status_code >= 400:
        raise TriageError(f"upstream status {resp.status_code}")


class LLMTriage:
    """OpenAI-compatible chat endpoint (Groq, Gemini compat, OpenRouter...) in JSON mode."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        vendor: str = "groq",
        client: httpx.Client | None = None,
    ) -> None:
        self.name = f"llm:{vendor}"
        self._model = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS)

    def triage(self, text: str, location: str) -> TriageResult:
        body = {
            "model": self._model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(text, location)},
            ],
        }
        try:
            resp = self._client.post(self._url, json=body, headers=self._headers)
        except httpx.TimeoutException as exc:
            raise RetryableTriageError("timeout") from exc
        except httpx.HTTPError as exc:
            raise TriageError(type(exc).__name__) from exc
        raise_for_status(resp)
        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise TriageError("unexpected response shape") from exc
        return parse_triage_json(content)
