# Triage

How a complaint becomes `category`, `priority` and a one-line summary. Code references are to `backend/app/`.

## Interface and selection
`TriageProvider` is a `Protocol` (`providers/triage/base.py`) with a `name` and `triage(text, location) -> TriageResult`. `TriageResult` is a Pydantic v2 model: `category` and `priority` are enums, `summary` is at most 140 characters, `confidence` is 0..1. `build_provider()` (`providers/triage/factory.py`) picks the implementation from `TRIAGE_PROVIDER`:

| Value | Class | `name` (stored as `triaged_by`) | Use |
|---|---|---|---|
| `llm` | `LLMTriage` | `llm:groq` or `llm:gemini` (`LLM_VENDOR`) | hosted OpenAI-compatible chat API, JSON mode |
| `ollama` | `OllamaTriage` | `llm:ollama` | offline, container in Compose (`--profile ollama`) |
| `rules` | `RuleBasedTriage` | `rules` | deterministic keyword rules |
| `simulated` (default) | `SimulatedTriage` | `simulated` | deterministic fake for CI, with failure injection |

The database CHECK constraint on `triaged_by` (migration 0001) allows exactly these values plus `rules:fallback`, so `LLM_VENDOR` is validated in the factory (an unknown vendor would otherwise fail every insert). Empty environment values (which Compose and Kubernetes pass for unset variables) mean "use the default". `TRIAGE_PROVIDER=llm` with an empty `LLM_API_KEY` logs a warning and serves `rules` rather than crash-looping the pods.

## Reliability pipeline (`services/triage_service.py`)
1. **Cache**: key is `sha256` of the provider's `cache_scope` (its name, plus the model for LLM and Ollama: `llm:groq:<model>`) and the whitespace/case-normalised text and location (`content_key`), so switching provider or model never serves the old one's results; value is the provider name plus the result JSON, TTL 24 h (`CACHE_TTL_SECONDS`). A hit skips the provider entirely. Fallback results are never cached.
2. **Call** the provider. **Timeout**: `httpx` timeout of 10 s (`providers/triage/llm.py`, `TIMEOUT_SECONDS`).
3. **Retry once**, with 0.1 to 0.5 s of random jitter, only for `RetryableTriageError` (timeout, HTTP 429, 5xx: `raise_for_status` in `llm.py`). A 4xx, a malformed body or a schema violation is a plain `TriageError` and is never retried.
4. **Validate**: the model's text is parsed and validated against `TriageResult` (`parse_triage_json`). Prose, a code fence, an unknown category or a 400-character summary are rejected.
5. **Fall back**: on any exception the service runs `RuleBasedTriage` and records `triaged_by = "rules:fallback"`. It logs one WARNING with `complaint_id`, `provider` and `error_class` (never the key or the complaint text). The request therefore still returns 201.

Known limits, stated plainly: the timeout is `httpx`'s per-phase timeout, not a wall-clock cap, so a server that trickles bytes could exceed 10 s; and the worst case for a failing provider is two attempts plus jitter, roughly 20 s, before the fallback answers.

## Prompt injection
Complaint text is untrusted. It is placed between `<complaint>` tags and any `</complaint>` inside it is stripped (`build_user_prompt`); the system prompt tells the model not to follow instructions inside the tags. That reduces the risk but is not the guarantee. The guarantee is structural: the output is validated against the schema, so injected text can at worst change *which valid label* is chosen, never produce an out-of-enum value or reach SQL (persistence uses SQLAlchemy parameters; model output is never concatenated into a query). Tests: `test_triage.py::test_prompt_injection_cannot_escape_the_schema`, `test_api.py::test_injection_attempt_cannot_change_the_schema_decided_category`.

## Observability
`triage_latency_ms` is stored on each row. `GET /api/meta/providers` returns the active provider, the last 20 outcomes (`provider`, `latency_ms`, `fallback`) and this process's cache hit/miss tally. Prometheus: `triage_latency_seconds{provider}`, `triage_fallback_total{provider}`, `triage_cache_total{result}`. The hit rate is **per process since start**. There is no production traffic to measure; the measured behaviour on a synthetic burst workload (38 requests, 12 distinct incidents: 12 misses, 26 hits, 68.4 % by construction, a hit about 7x faster than a miss) is in `docs/evidence/triage-cache-measured.md`, and the test `test_duplicate_complaints_cost_one_inference` shows that a duplicate costs one provider call.

## CI
CI sets `TRIAGE_PROVIDER=simulated`. LLM and Ollama providers are exercised through `httpx.MockTransport`, so no test calls a network. `SimulatedTriage(failure=...)` supports `raise`, `retryable` and `malformed` for fallback tests.
