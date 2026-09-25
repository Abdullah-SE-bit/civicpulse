# ADR 0004: What personal data leaves the machine, and why

Status: accepted for coursework with synthetic data; revisit before real citizen data

## Context
Citizens type free text. It can contain names, street addresses, phone numbers and descriptions of other people, even though the form never asks for them. The form also has a separate optional `reporter_contact` field. With `TRIAGE_PROVIDER=llm` the text is sent to a third-party hosted model. This ADR describes what the code actually does; it makes no claim about any provider's retention or training policy, which we have not verified, and it does not assert compliance with any law.

## Decision (what the code does)
- **Sent to a hosted LLM:** the complaint text and the location string, and nothing else (`build_user_prompt`, `providers/triage/base.py`; called with `(text, location)` only). `reporter_contact`, ids, timestamps and status are never passed to a provider.
- **Not redacted.** Text is sent as typed. If a citizen writes a phone number or a name inside the complaint body, it is transmitted to the provider.
- **Stays local:** everything is stored in our own PostgreSQL. The Redis triage cache stores only the model's result (category, priority, summary, confidence) under a SHA-256 key of the normalised text and location, not the raw text. The summary is model-written and can echo fragments of the input.
- **Logs:** request logs carry method, path, status, duration and request id. Triage fallback warnings carry complaint id, provider and error class. Complaint text, contact and the API key are never logged; `httpx` logging is set to WARNING so request URLs stay out of logs.
- **Local-only options:** `TRIAGE_PROVIDER=ollama` (model runs in our Compose stack) and `rules` send nothing off the machine. `simulated` is offline and only for tests.
- The API key comes from the environment / a Kubernetes Secret and is never in the repository.

## Alternatives considered
- **Regex redaction of phone numbers and emails before sending:** cheap, but it cannot find names or addresses, and would give a false sense of protection. Not implemented.
- **Send only part of the text or a hash:** defeats the purpose, since the model needs the content to classify it.
- **Hosted LLM only for text with no detected personal data:** detection has the same reliability problem as redaction.
- **Ollama or rules as the only provider:** the safest choice for personal data, at the cost of noticeably worse classification (rules) or slower CPU inference (Ollama).

## Consequences
- The default hosted path is acceptable only for synthetic or non-sensitive text such as this assignment's seed data. For real complaints the recommended configuration is `ollama` or `rules`, or a hosted provider whose data-handling terms have been reviewed and accepted.
- The exposure is documented, not mitigated: anyone reading this repository can see exactly which fields cross the boundary.
- Backup and retention of the PostgreSQL volume are outside this ADR and not designed here.
