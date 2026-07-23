"""LLM usage and cost tracking on a generation observation.

Shows recording token usage from a provider-style response, an opt-in client-side cost, a
standalone cost estimate for budgeting, and registering a price for a custom model.

    python examples/02_llm_cost_tracking.py
"""

from __future__ import annotations

import langfuse_wrapper as lw


class _Usage:
    """Stand-in for an Anthropic-style usage object (response.usage.input_tokens/output_tokens)."""

    input_tokens = 1200
    output_tokens = 350


class _Response:
    usage = _Usage()


def main() -> None:
    print(f"wrapper active: {lw.is_enabled()}")

    model = "claude-opus-4-8"
    with lw.generation("llm-call", model=model) as gen:
        response = _Response()  # in real code: client.messages.create(...)
        # record_cost=True also attaches a client-side USD estimate (opt-in; Langfuse otherwise
        # computes cost server-side from the usage we send).
        lw.track_llm(gen, response, model=model, record_cost=True)

    # Standalone estimate, e.g. for a runtime budget guardrail.
    estimate = lw.estimate_cost(model, input_tokens=1200, output_tokens=350)
    if estimate is not None:
        print(f"estimated cost for {model}: ${estimate.total_cost:.4f}")

    # Teach the wrapper about a model it does not know yet (USD per 1000 tokens).
    lw.register_model_price("my-org/custom-llm", input_per_1k=0.001, output_per_1k=0.004)
    custom = lw.estimate_cost("my-org/custom-llm", 5000, 2000)
    if custom is not None:
        print(f"custom model cost: ${custom.total_cost:.4f}")

    lw.flush()
    print("done")


if __name__ == "__main__":
    main()
