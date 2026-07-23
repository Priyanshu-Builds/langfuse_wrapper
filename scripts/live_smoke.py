"""Live, self-verifying smoke test against a real Langfuse instance.

Confirms the wrapper actually emits — and does so correctly even when a SECOND Langfuse client
also exists in the process (the multi-client case mocked tests cannot cover). It runs a small
traced workload, flushes, then fetches the trace back through the Langfuse API and asserts the
structure, trace attributes, and token usage.

Set real credentials in `.env` or the environment, then run from the repo root:

    LANGFUSE_PUBLIC_KEY=pk-lf-...
    LANGFUSE_SECRET_KEY=sk-lf-...
    LANGFUSE_BASE_URL=https://cloud.langfuse.com   # or your region / self-hosted URL

    python scripts/live_smoke.py
"""

from __future__ import annotations

import time

import langfuse_wrapper as lw


class _Usage:
    input_tokens = 1200
    output_tokens = 350


class _Response:
    usage = _Usage()


@lw.trace(name="live_smoke_agent")
def run_agent(question: str) -> str:
    with lw.span("retrieve", input={"question": question}) as retrieval:
        retrieval.update(output=f"context for {question!r}")

    model = "claude-opus-4-8"
    with lw.generation("llm-call", model=model) as gen:
        lw.track_llm(gen, _Response(), model=model, record_cost=True)

    lw.score("smoke_ok", True)  # scored inside the trace, where an observation is active
    return lw.get_client().get_current_trace_id() or ""


def _fetch_trace(trace_id: str, attempts: int = 12, delay: float = 2.0):
    """Poll for the trace until Langfuse has ingested it (ingestion is async)."""
    client = lw.get_client()
    for i in range(attempts):
        try:
            return client.api.trace.get(trace_id)
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(delay)
    return None


def main() -> None:
    if not lw.is_enabled():
        print(
            "Wrapper is INACTIVE — set LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY "
            "(and LANGFUSE_BASE_URL) in .env or the environment, then re-run."
        )
        return

    settings = lw.get_settings()
    host = settings.base_url or "https://cloud.langfuse.com"
    print(f"wrapper active — host: {host}")

    # Simulate a host app (like CHAMP) that ALSO constructs its own Langfuse client under a
    # different key. With two instances, langfuse's keyless resolution returns a DISABLED client;
    # the wrapper binds our configured key so @trace / trace_context still emit.
    import langfuse

    langfuse.Langfuse(
        public_key="pk-other-project",
        secret_key="sk-other-project",
        base_url="http://localhost:9",
        tracing_enabled=False,
    )
    print("second (foreign) Langfuse client constructed — simulating a multi-client process\n")

    with lw.trace_context(session_id="live-smoke", user_id="priyanshu", tags=["smoke", "poc"]):
        trace_id = run_agent("Does the wrapper emit under a foreign client?")

    lw.flush()
    print(f"emitted trace_id: {trace_id}\nfetching it back from Langfuse to verify...")

    trace = _fetch_trace(trace_id)
    observations = list(getattr(trace, "observations", []) or [])
    names = {getattr(o, "name", None) for o in observations}
    types = {getattr(o, "type", None) for o in observations}
    generation = next((o for o in observations if getattr(o, "type", "") == "GENERATION"), None)

    checks = [
        ("trace fetched", trace is not None),
        ("session_id attached", getattr(trace, "session_id", None) == "live-smoke"),
        ("user_id attached", getattr(trace, "user_id", None) == "priyanshu"),
        ("tags attached", set(getattr(trace, "tags", []) or []) >= {"smoke", "poc"}),
        ("retrieve span present", "retrieve" in names),
        ("generation present", "GENERATION" in types and "llm-call" in names),
        (
            "generation has usage",
            generation is not None and bool(getattr(generation, "usage_details", None)),
        ),
    ]

    print()
    all_ok = True
    for label, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        all_ok = all_ok and ok

    print(
        f"\n{'ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED'} — "
        f"{len(observations)} observations on the trace"
    )
    print(f"view: {host.rstrip('/')}  (Tracing -> session 'live-smoke')")


if __name__ == "__main__":
    main()
