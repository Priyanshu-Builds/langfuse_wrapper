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

from __future__ import annotations

from .client import configure, flush, get_client, get_settings, is_enabled, reset
from .config import Settings
from .cost import estimate_cost, get_model_price, register_model_price
from .llm import extract_usage, track_llm
from .prompts import LocalPrompt, get_prompt, render
from .tracing import generation, span, trace, trace_context
from .types import CostResult, ModelPrice, Usage

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "CostResult",
    "LocalPrompt",
    "ModelPrice",
    "Settings",
    "Usage",
    "configure",
    "estimate_cost",
    "extract_usage",
    "flush",
    "generation",
    "get_client",
    "get_model_price",
    "get_prompt",
    "get_settings",
    "is_enabled",
    "register_model_price",
    "render",
    "reset",
    "span",
    "track_llm",
    "trace",
    "trace_context",
]
