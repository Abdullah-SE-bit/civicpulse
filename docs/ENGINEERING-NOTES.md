# Engineering Notes

Answers to the eight questions in assignment §5.2, with file-and-line references. Filled in as the implementation lands; unanswered sections are marked TODO rather than guessed.

1. Laptop vs CI runner differences: TODO
2. CI/CD maturity rung: TODO
3. Build-once-deploy-many line: TODO
4. What "correct" means for a probabilistic LLM component; keeping CI deterministic: TODO
5. HPA lag (measured): TODO
6. Why VPA is in Off mode: TODO
7. `internal: true` network vs a hosted LLM call: the backend is the only service on both networks, so it keeps a route out via `edge` and calls the hosted LLM itself. Postgres and Redis stay internal-only. The alternative (a dedicated egress proxy service on both networks) adds a moving part with no gain here. Ollama sits on `edge` because it must download model weights. (compose.yaml)
8. The failure that cost more than an hour: TODO

## Index justifications (to complete with the schema)
- `(status, priority)`: TODO name the query
- `created_at`: TODO name the query

## Redis on a volume (AOF)
Redis here is also the distributed rate limiter, and the 24 h triage-result cache saves paid/limited LLM calls. Losing it on restart would zero every client's rate-limit window and re-spend the whole day's LLM quota on duplicate complaints, so we persist it with AOF on `redisdata`. Stats cache entries are worthless after a restart but harmless. (compose.yaml)
