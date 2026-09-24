import os
from collections.abc import Mapping

from .base import TriageProvider
from .llm import LLMTriage
from .ollama import OllamaTriage
from .rules import RuleBasedTriage
from .simulated import SimulatedTriage


def build_provider(env: Mapping[str, str] | None = None) -> TriageProvider:
    """Select the provider from TRIAGE_PROVIDER; secrets come from the environment only."""
    env = os.environ if env is None else env
    kind = env.get("TRIAGE_PROVIDER", "simulated").lower()
    if kind == "simulated":
        return SimulatedTriage()
    if kind == "rules":
        return RuleBasedTriage()
    if kind == "ollama":
        return OllamaTriage(
            env.get("OLLAMA_BASE_URL", "http://ollama:11434"),
            env.get("OLLAMA_MODEL", "llama3.2:1b"),
        )
    if kind == "llm":
        if not env.get("LLM_API_KEY"):
            raise ValueError("TRIAGE_PROVIDER=llm requires LLM_API_KEY")
        return LLMTriage(
            api_key=env["LLM_API_KEY"],
            base_url=env.get("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
            model=env.get("LLM_MODEL", "llama-3.1-8b-instant"),
            vendor=env.get("LLM_VENDOR", "groq"),
        )
    raise ValueError(f"unknown TRIAGE_PROVIDER: {kind!r}")
