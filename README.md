# langfuse_wrapper

An **ergonomic, feature-additive Python wrapper** around the
[Langfuse](https://langfuse.com) observability SDK (v4).

The raw Langfuse SDK is powerful but verbose to instrument, and every app ends up
re-solving the same concerns: client setup, "what if the keys are missing / Langfuse
is down", cost tracking, prompt versioning, scoring, and PII redaction.
`langfuse_wrapper` packages those into a thin, opinionated layer.

## Why

- **One-line instrumentation** — decorators and context managers instead of Langfuse
  boilerplate.
- **Graceful degradation is a feature** — when `LANGFUSE_PUBLIC_KEY` is unset or the
  wrapper is disabled, every call becomes a safe no-op. Your app runs identically with
  or without Langfuse configured.
- **Configurable host** — works with Langfuse Cloud or a self-hosted instance via env.
- **Feature-additive helpers** — LLM cost tracking, prompt helpers, scoring utilities,
  and optional PII scrubbing on top of Langfuse.

## Status

Early development. Built incrementally in phases:

| Phase | Feature | Status |
|-------|---------|--------|
| 0 | Package scaffold + SDK confirmation | ✅ |
| 1 | Config + client + graceful degradation | ✅ |
| 2 | Tracing decorators / context managers | ✅ |
| 3 | LLM usage + cost tracking | ✅ |
| 4 | Prompt management helpers | ⏳ |
| 5 | Scoring / eval utilities | ⏳ |
| 6 | PII scrubbing | ⏳ |
| 7 | LangGraph / LangChain integration | ⏳ |
| 8 | Docs polish | ⏳ |

## Install (development)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Unix:     source .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and fill in your Langfuse credentials:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com   # or your self-hosted URL
```

## Planned API

```python
from langfuse_wrapper import trace, span, generation, track_llm, score, get_handler

@trace(name="research_agent")
def run_agent(query: str): ...

with generation(name="llm-call", model="claude-opus-4-8") as gen:
    resp = client.messages.create(...)
    track_llm(gen, resp)          # records usage + computed USD cost

score(name="relevance", value=0.9)
handler = get_handler(session_id=...)   # configured Langfuse CallbackHandler for LangGraph
```

If `LANGFUSE_PUBLIC_KEY` is unset, every call above is a safe no-op.

## Requirements

- Python ≥ 3.10
- `langfuse>=4,<5`

## License

Apache-2.0 — see [LICENSE](LICENSE).
