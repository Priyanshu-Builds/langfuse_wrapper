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

## Install

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Unix:     source .venv/bin/activate

pip install -e ".[dev]"              # library + dev tooling (pytest, ruff, mypy)
pip install -e ".[dev,langchain]"    # also enable the LangChain/LangGraph integration
```

Requires Python ≥ 3.10 and `langfuse>=4,<5`.

## Configuration

Copy `.env.example` to `.env` and fill in your Langfuse credentials:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com   # or your self-hosted URL
```

- **Langfuse Cloud**: `https://cloud.langfuse.com` (EU) or `https://us.cloud.langfuse.com` (US).
- **Self-hosted**: set `LANGFUSE_BASE_URL` to your instance. `LANGFUSE_HOST` is accepted as a
  deprecated alias.
- **Wrapper toggles**: `LFWRAP_ENABLED` (default `true`) is a master switch; `LFWRAP_SCRUB_PII`
  (default `false`) redacts PII from data sent to Langfuse.

The wrapper is *active* only when it is enabled **and** both keys are present — otherwise every
call below is a safe no-op.

## Quickstart

```python
import langfuse_wrapper as lw

@lw.trace(name="research_agent")            # records the call as an observation (sync or async)
def run_agent(query: str) -> str:
    with lw.generation("llm-call", model="claude-opus-4-8") as gen:
        response = client.messages.create(...)      # your LLM call
        lw.track_llm(gen, response, model="claude-opus-4-8")   # records token usage
    return "..."

with lw.trace_context(session_id="s1", user_id="u1", tags=["prod"]):
    answer = run_agent("What is observability?")
    lw.score("relevance", 0.9)              # score the current trace

lw.flush()                                   # flush before a short-lived process exits
```

See runnable scripts in [`examples/`](examples/):
`01_basic_trace.py`, `02_llm_cost_tracking.py`, `03_langgraph_integration.py`.

## API reference

### Tracing
- `@trace(name=None, as_type="span", capture_input=None, capture_output=None)` — decorate a sync
  or async function to record it as an observation.
- `span(name, **kwargs)` / `generation(name, model=None, **kwargs)` — context managers for a
  span / an LLM generation; keyword args (`input`, `output`, `metadata`, ...) are forwarded to
  Langfuse.
- `trace_context(user_id=, session_id=, tags=, metadata=, version=, name=)` — context manager that
  sets trace-level attributes for everything created in its scope.

### LLM usage & cost
- `track_llm(observation, response=None, model=None, usage=None, input_tokens=None,
  output_tokens=None, record_cost=False)` — record token usage (and, with `record_cost=True`, a
  client-side USD estimate) onto a generation.
- `estimate_cost(model, input_tokens, output_tokens) -> CostResult | None` — standalone estimate.
- `register_model_price(model, input_per_1k, output_per_1k)` — add/override a model's price.
- `extract_usage(response) -> Usage | None` — pull usage from an Anthropic/OpenAI response.

### Prompts
- `get_prompt(name, version=, label=, type="text", fallback=, cache_ttl_seconds=)` — fetch a
  Langfuse prompt, falling back to a local template when unavailable.
- `render(name, variables=, fallback=, ...)` — fetch and compile a prompt in one call.

### Scoring
- `score(name, value, target="trace", data_type=, comment=, metadata=, config_id=)` — score the
  current trace or observation.
- `create_score(name, value, trace_id=, observation_id=, ...)` — score a specific trace/observation
  by id (e.g. a deferred eval).

### PII scrubbing (opt-in via `LFWRAP_SCRUB_PII`)
- `scrub(value)` — redact PII from a string or nested structure.
- `register_pattern(name, pattern, replacement="[REDACTED]")` — add a redaction rule.

### LangChain / LangGraph (requires the `langchain` extra)
- `get_handler(public_key=None, trace_context=None)` — a configured Langfuse `CallbackHandler`, or
  `None` when inactive. Pair with `trace_context()` for session/user/tags:

  ```python
  handler = lw.get_handler()
  with lw.trace_context(session_id="s1", user_id="u1"):
      graph.invoke(state, config={"callbacks": [handler] if handler else []})
  ```

### Configuration & lifecycle
- `configure(public_key=, secret_key=, base_url=, enabled=, scrub_pii=)` — override settings
  programmatically and reset the client.
- `is_enabled()`, `get_settings()`, `get_client()`, `flush()`, `reset()`.

## Development

```bash
pytest                       # run the test suite (no network required)
ruff check .                 # lint
mypy src/langfuse_wrapper    # type-check
```

CI runs all three on Python 3.10–3.12 via GitHub Actions.

## License

Apache-2.0 — see [LICENSE](LICENSE).
