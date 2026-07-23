"""Basic tracing: decorator, context managers, trace attributes, and scoring.

Run it with no Langfuse configured and everything is a safe no-op (nothing is sent, no errors).
Set LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL to send real traces.

    python examples/01_basic_trace.py
"""

from __future__ import annotations

import langfuse_wrapper as lw


@lw.trace(name="answer_question")
def answer_question(question: str) -> str:
    # A nested span groups a unit of work under the current trace.
    with lw.span("retrieve", input={"question": question}) as retrieval:
        context = f"context for: {question}"
        retrieval.update(output=context)

    return f"Answer to {question!r} using {context!r}"


def main() -> None:
    print(f"wrapper active: {lw.is_enabled()}")

    # trace_context sets trace-level attributes for everything created in its scope.
    with lw.trace_context(session_id="demo-session", user_id="priyanshu", tags=["example"]):
        result = answer_question("What is observability?")
        print(result)

        # Attach a score to the current trace.
        lw.score("helpfulness", 0.95, comment="looks good")

    # Flush buffered events (important for short-lived scripts).
    lw.flush()
    print("done")


if __name__ == "__main__":
    main()
