# ADR 0001: Triage behind a provider interface, with reliability outside the providers

Status: accepted

## Context
Triage is done today by keyword rules, tomorrow by a hosted model, later by something else. The system must not care which, and must not fail when the clever one is slow, rate-limited or wrong. Free hosted tiers allow only tens of requests per minute.

## Decision
- `TriageProvider` is a `typing.Protocol` (`name`, `triage(text, location) -> TriageResult`). Four implementations (rules, simulated, OpenAI-compatible LLM, Ollama) are selected by `TRIAGE_PROVIDER` in one factory.
- Reliability (cache, single jittered retry, fallback to rules, latency measurement) lives in `TriageService`, not in the providers. Providers only translate errors into `TriageError` / `RetryableTriageError`.
- The provider speaks the OpenAI chat-completions shape rather than a vendor SDK, so Groq, Gemini's compatibility endpoint and similar services differ only by base URL, model and key.
- The model's output is always validated against `TriageResult` (Pydantic) before it is used.

## Alternatives
- An abstract base class per provider: heavier than needed; a structural Protocol lets tests pass any object with `name` and `triage`.
- Retry and fallback inside each provider: duplicated per implementation, and the fallback would have to know about the rule provider.
- A vendor SDK (e.g. `openai`, `groq`): extra dependency for four HTTP lines, and it hides the timeout and status handling we need to control.
- An agent/LLM framework: far more surface than "classify one paragraph".

## Consequences
- Adding a provider is one class plus a factory branch; the service and API do not change.
- Tests need no network: `SimulatedTriage` for the API, `httpx.MockTransport` for the HTTP providers.
- `triaged_by` values are constrained in the database, so the factory must reject vendors the constraint would reject (`LLM_VENDORS`). A new vendor needs a migration.
- The fallback answer is lower quality than a working model, by design; it is recorded (`rules:fallback`) so it is visible, not hidden.
