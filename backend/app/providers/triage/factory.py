import logging
import os
from collections.abc import Mapping

from .base import TriageProvider
from .llm import LLMTriage
from .ollama import OllamaTriage
from .rules import RuleBasedTriage
from .simulated import SimulatedTriage

log = logging.getLogger("civicpulse.triage")

# Must match the CHECK constraint on complaints.triaged_by (alembic 0001): 'llm:<vendor>'.
LLM_VENDORS = ("groq", "gemini")


def _get(env: Mapping[str, str], key: str, default: str) -> str:
    """Compose and Kubernetes pass unset values as empty strings; empty means 'use the default'."""
    return env.get(key) or default


def build_provider(env: Mapping[str, str] | None = None) -> TriageProvider:
    """Select the provider from TRIAGE_PROVIDER; secrets come from the environment only."""
    env = os.environ if env is None else env
    kind = _get(env, "TRIAGE_PROVIDER", "simulated").lower()
    if kind == "simulated":
        return SimulatedTriage()
    if kind == "rules":
        return RuleBasedTriage()
    if kind == "ollama":
        return OllamaTriage(
            _get(env, "OLLAMA_BASE_URL", "http://ollama:11434"),
            _get(env, "OLLAMA_MODEL", "llama3.2:1b"),
        )
    if kind == "llm":
        if not env.get("LLM_API_KEY"):
            # A missing key must not crash-loop the pods (a placeholder Secret has an empty key): serve rules.
            log.warning("TRIAGE_PROVIDER=llm but LLM_API_KEY is empty; using rule-based triage")
            return RuleBasedTriage()
        vendor = _get(env, "LLM_VENDOR", "groq")
        if vendor not in LLM_VENDORS:
            raise ValueError(f"LLM_VENDOR must be one of {LLM_VENDORS}, got {vendor!r}")
        return LLMTriage(
            api_key=env["LLM_API_KEY"],
            base_url=_get(env, "LLM_BASE_URL", "https://api.groq.com/openai/v1"),
            model=_get(env, "LLM_MODEL", "llama-3.1-8b-instant"),
            vendor=vendor,
        )
    raise ValueError(f"unknown TRIAGE_PROVIDER: {kind!r}")
