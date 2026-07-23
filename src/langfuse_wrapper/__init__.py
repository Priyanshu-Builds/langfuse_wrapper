"""langfuse_wrapper: an ergonomic, feature-additive wrapper around the Langfuse SDK.

This package is a thin, opinionated layer over `langfuse` (v4). It provides:

* Ergonomic instrumentation — decorators / context managers that reduce Langfuse
  boilerplate, with graceful degradation: when credentials are absent or the
  wrapper is disabled, every call becomes a safe no-op and the host app is unaffected.
* Feature-additive helpers — LLM cost tracking, prompt helpers, scoring utilities,
  and optional PII scrubbing.

The public API is populated incrementally across implementation phases; this module
re-exports the curated surface. See README.md for the roadmap.
"""

__version__ = "0.1.0"

__all__: list[str] = [
    "__version__",
]
