# langfuse_wrapper

[![CI](https://github.com/Priyanshu-Builds/langfuse_wrapper/actions/workflows/ci.yml/badge.svg)](https://github.com/Priyanshu-Builds/langfuse_wrapper/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%E2%80%933.12-blue.svg)
![Langfuse](https://img.shields.io/badge/langfuse-v4-orange.svg)
![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)

An **ergonomic, feature-additive Python wrapper** around the
[Langfuse](https://langfuse.com) observability SDK (v4). Instrument your LLM app with one-line
decorators and helpers instead of Langfuse boilerplate — and get cost tracking, prompt helpers,
scoring, and PII scrubbing on top, with a safe no-op fallback when Langfuse isn't configured.

```python
import langfuse_wrapper as lw

@lw.trace(name="research_agent")                 # the whole call becomes a trace
def run_agent(query: str) -> str:
    with lw.generation("llm-call", model="gpt-5.5") as gen:
        resp = client.chat.completions.create(...)
        lw.track_llm(gen, resp, model="gpt-5.5")  # token usage (+ optional cost)
    lw.score("relevance", 0.9)
    return "..."
```

If `LANGFUSE_PUBLIC_KEY` isn't set, every line above is a safe no-op — the app runs unchanged.

> **Why a wrapper instead of using Langfuse directly?** So projects don't each re-solve client
> setup, cost, PII, and vendor-SDK churn. Full rationale in [`docs/PROPOSAL.md`](docs/PROPOSAL.md),
> or the one-pager: **[priyanshu-builds.github.io/langfuse_wrapper](https://priyanshu-builds.github.io/langfuse_wrapper/)**.

## Contents

- [Features](#features)
- [Install](#install)
- [Configuration](#configuration)
- [Quickstart](#quickstart)
- [Graceful degradation](#graceful-degradation)
- [Recipes](#recipes)
- [API reference](#api-reference)
- [Compatibility](#compatibility)
- [Quality &amp; verification](#quality--verification)
- [Project layout](#project-layout)
- [Development](#development)
- [License](#license)

## Features

| Area | What you get |
|------|--------------|
| **Tracing** | `@trace` decorator (sync **and** async) + `span()` / `generation()` context managers |
| **Trace attributes** | `trace_context()` sets session / user / tags for a whole scope |
| **LLM cost** | token usage recorded automatically; optional client-side USD estimates, per model |
| **Prompts** | fetch from Langfuse with a local-template fallback when offline |
| **Scoring** | attach evals to the current trace/observation, or to any trace by id (deferred) |
| **PII scrubbing** | central, opt-in redaction of input/output/metadata before it leaves your process |
| **LangGraph** | one-line Langfuse callback handler for LangChain / LangGraph |
| **Config** | Langfuse Cloud or self-hosted, entirely env-driven |
| **Safety** | graceful no-op when unconfigured — identical behavior with or without Langfuse |

## Install

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Unix:     source .venv/bin/activate

pip install -e ".[dev]"              # library + dev tooling (pytest, ruff, mypy)
pip install -e ".[dev,langchain]"    # also enable the LangChain / LangGraph integration
```

Requires Python ≥ 3.10 and `langfuse>=4,<5`.

## Configuration

Copy `.env.example` to `.env` and set your Langfuse credentials. All configuration is via
environment variables:

| Variable | Required | Default | Purpose |
|----------|:--------:|---------|---------|
| `LANGFUSE_PUBLIC_KEY` | yes\* | — | Langfuse project public key (`pk-lf-...`) |
| `LANGFUSE_SECRET_KEY` | yes\* | — | Langfuse project secret key (`sk-lf-...`) |
| `LANGFUSE_BASE_URL` | no | `https://cloud.langfuse.com` | Host — a Cloud region or your self-hosted URL. `LANGFUSE_HOST` is accepted as a deprecated alias. |
| `LFWRAP_ENABLED` | no | `true` | Master on/off switch for the wrapper |
| `LFWRAP_SCRUB_PII` | no | `false` | Redact PII from data sent to Langfuse |

\* The wrapper is **active** only when it is enabled **and** both keys are present. Without them,
every call is a safe no-op (see below).

Common hosts: `https://cloud.langfuse.com` (EU), `https://us.cloud.langfuse.com` (US), or your own
self-hosted URL.

## Quickstart

```python
import langfuse_wrapper as lw

@lw.trace(name="research_agent")            # records the call as a trace (works on async too)
def run_agent(query: str) -> str:
    with lw.generation("llm-call", model="gpt-5.5") as gen:
        resp = client.chat.completions.create(...)      # your LLM call
        lw.track_llm(gen, resp, model="gpt-5.5")        # records token usage
    return "..."

# Attach session / user / tags to everything created in this scope:
with lw.trace_context(session_id="s1", user_id="u1", tags=["prod"]):
    answer = run_agent("What is observability?")
    lw.score("relevance", 0.9)              # score the current trace

lw.flush()                                   # flush before a short-lived process exits
```

Runnable scripts are in [`examples/`](examples/):
`01_basic_trace.py`, `02_llm_cost_tracking.py`, `03_langgraph_integration.py`.

## Graceful degradation

This is the headline feature. The wrapper is **active** only when it's enabled and credentialed;
otherwise it returns a no-op client and every call becomes a safe pass-through:

```python
lw.is_enabled()          # False when keys are missing or LFWRAP_ENABLED=false

@lw.trace()              # decorator runs the function unwrapped — zero overhead
def work(): ...

with lw.generation("x"): # context manager yields a dummy span, no error
    ...
lw.score("q", 1.0)       # no-op
lw.flush()               # no-op
```

Result: the **same code runs in dev, test, and CI with no Langfuse configured** — no
`if observability_enabled:` branches scattered through your app. If the Langfuse client even fails
to construct, the wrapper falls back to no-op rather than crashing the host process.

## Recipes

**Instrument a direct provider SDK call (OpenAI / Anthropic)**

```python
with lw.generation("summarize", model="gpt-5.5") as gen:
    resp = client.chat.completions.create(model="gpt-5.5", messages=[...])
    lw.track_llm(gen, resp, model="gpt-5.5")   # usage auto-extracted from the response
```

`track_llm` reads usage from OpenAI (`prompt_tokens` / `completion_tokens`) **and** Anthropic
(`input_tokens` / `output_tokens`) responses — objects or dicts.

**LangChain / LangGraph** (requires the `langchain` extra)

```python
handler = lw.get_handler()                 # None when the wrapper is inactive
with lw.trace_context(session_id="s1", user_id="u1", tags=["prod"]):
    graph.invoke(state, config={"callbacks": [handler] if handler else []})
```

The handler auto-captures each node's model and token usage — no manual `track_llm` needed.

**Score after the fact (deferred / async eval)**

```python
lw.create_score("faithfulness", 0.87, trace_id=trace_id, comment="LLM-judge")
```

**Turn on PII scrubbing** — set `LFWRAP_SCRUB_PII=true`. Input, output, and metadata on every
observation are redacted centrally (email, phone, credit-card, SSN, IPv4). Extend it:

```python
lw.register_pattern("employee_id", r"EMP\d{5}", "[REDACTED_EMP]")
```

**Teach it a model's price** (for client-side cost estimates on models it doesn't know yet)

```python
lw.register_model_price("gpt-5.5", input_per_1k=..., output_per_1k=...)   # USD per 1k tokens
lw.track_llm(gen, resp, model="gpt-5.5", record_cost=True)               # now attaches a $ estimate
```

Cost also shows up in Langfuse without this — Langfuse computes it server-side from the token
usage you send. The client-side estimate is an opt-in convenience for runtime budgeting.

## API reference

<details>
<summary><b>Tracing</b></summary>

- `@trace(name=None, as_type="span", capture_input=None, capture_output=None)` — decorate a sync
  or async function to record it as an observation.
- `span(name, **kwargs)` / `generation(name, model=None, **kwargs)` — context managers for a span /
  an LLM generation; extra keyword args (`input`, `output`, `metadata`, ...) are forwarded to
  Langfuse.
- `trace_context(user_id=, session_id=, tags=, metadata=, version=, name=)` — context manager that
  sets trace-level attributes for everything created in its scope.
</details>

<details>
<summary><b>LLM usage &amp; cost</b></summary>

- `track_llm(observation, response=None, model=None, usage=None, input_tokens=None,
  output_tokens=None, record_cost=False)` — record token usage (and, with `record_cost=True`, a
  client-side USD estimate) onto a generation.
- `estimate_cost(model, input_tokens, output_tokens) -> CostResult | None` — standalone estimate.
- `register_model_price(model, input_per_1k, output_per_1k)` — add/override a model's price.
- `extract_usage(response) -> Usage | None` — pull usage from an OpenAI/Anthropic response.
</details>

<details>
<summary><b>Prompts</b></summary>

- `get_prompt(name, version=, label=, type="text", fallback=, cache_ttl_seconds=)` — fetch a
  Langfuse prompt, falling back to a local template when unavailable.
- `render(name, variables=, fallback=, ...)` — fetch and compile a prompt in one call.
</details>

<details>
<summary><b>Scoring</b></summary>

- `score(name, value, target="trace", data_type=, comment=, metadata=, config_id=)` — score the
  current trace or observation.
- `create_score(name, value, trace_id=, observation_id=, ...)` — score a specific
  trace/observation by id (e.g. a deferred eval).
</details>

<details>
<summary><b>PII scrubbing</b> (opt-in via <code>LFWRAP_SCRUB_PII</code>)</summary>

- `scrub(value)` — redact PII from a string or nested structure.
- `register_pattern(name, pattern, replacement="[REDACTED]")` — add a redaction rule.
</details>

<details>
<summary><b>LangChain / LangGraph</b> (requires the <code>langchain</code> extra)</summary>

- `get_handler(public_key=None, trace_context=None)` — a configured Langfuse `CallbackHandler`, or
  `None` when inactive. Pair with `trace_context()` for session/user/tags.
</details>

<details>
<summary><b>Configuration &amp; lifecycle</b></summary>

- `configure(public_key=, secret_key=, base_url=, enabled=, scrub_pii=)` — override settings
  programmatically and reset the client.
- `is_enabled()`, `get_settings()`, `get_client()`, `flush()`, `reset()`.
</details>

## Compatibility

| | |
|---|---|
| **Python** | 3.10 – 3.12 (tested in CI); ≥ 3.10 required |
| **Langfuse SDK** | v4 (`langfuse>=4,<5`) |
| **LLM providers** | any — usage extraction handles OpenAI and Anthropic response shapes |
| **Frameworks** | LangChain / LangGraph via the optional `langchain` extra |
| **Langfuse host** | Cloud (any region) or self-hosted |

## Quality &amp; verification

- **78 unit tests**, run fully offline (the Langfuse SDK is mocked) — `pytest`.
- **`ruff` + `mypy` clean**; CI runs lint, type-check, and tests on Python 3.10–3.12.
- **Live-verified** against a real Langfuse instance, including the multi-client case where a host
  app already runs its own Langfuse client — see [`scripts/live_smoke.py`](scripts/live_smoke.py),
  which emits a trace and fetches it back through the API to assert nesting, attributes, and usage.

## Project layout

```
src/langfuse_wrapper/
├── config.py        # env-driven Settings (pydantic-settings)
├── client.py        # get_client() gate + graceful degradation
├── _noop.py         # no-op client/span used when inactive
├── tracing.py       # @trace, span(), generation(), trace_context()
├── llm.py           # track_llm(), extract_usage()
├── cost.py          # price table + estimate_cost()
├── prompts.py       # get_prompt(), render(), LocalPrompt
├── scoring.py       # score(), create_score()
├── scrubbing.py     # scrub(), register_pattern(), mask
├── types.py         # Usage, ModelPrice, CostResult
└── integrations/
    └── langchain.py # get_handler()
tests/               # pytest suite (offline)
examples/            # runnable usage scripts
scripts/live_smoke.py# live self-verifying smoke test
docs/                # adoption proposal (markdown + one-pager)
```

## Development

```bash
pytest                       # run the test suite (no network required)
ruff check .                 # lint
mypy src/langfuse_wrapper    # type-check
```

CI runs all three on Python 3.10–3.12 via GitHub Actions.

## License

Apache-2.0 — see [LICENSE](LICENSE).
