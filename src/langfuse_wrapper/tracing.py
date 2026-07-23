"""Ergonomic tracing primitives.

Thin wrappers over Langfuse's own instrumentation, so OpenTelemetry parent/child context
propagation is handled by the SDK and never re-implemented here:

* :func:`trace` — decorator over Langfuse's ``@observe`` (sync **and** async), gated at call time.
* :func:`span` / :func:`generation` — context managers over the client's
  ``start_as_current_observation``.
* :func:`trace_context` — sets trace-level attributes (user/session/tags/...) for everything in
  its scope, via Langfuse's ``propagate_attributes``.

All of them degrade to no-ops when the wrapper is inactive: decorated functions run unwrapped,
context managers yield a dummy span, and :func:`trace_context` becomes a null context.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from typing import Any, Literal, TypeVar

from langfuse import observe as _observe
from langfuse import propagate_attributes as _propagate_attributes

from .client import get_client, is_enabled

F = TypeVar("F", bound=Callable[..., Any])

# Observation types accepted by Langfuse's @observe / start_as_current_observation.
ObservationType = Literal[
    "span",
    "generation",
    "agent",
    "tool",
    "chain",
    "retriever",
    "evaluator",
    "guardrail",
    "embedding",
]


def trace(
    func: F | None = None,
    *,
    name: str | None = None,
    as_type: ObservationType = "span",
    capture_input: bool | None = None,
    capture_output: bool | None = None,
) -> Any:
    """Decorator that records a function call as a Langfuse observation.

    Usable bare (``@trace``) or parameterized (``@trace(name=..., as_type="generation")``).
    Works on sync and async functions. When the wrapper is inactive the function runs
    completely unwrapped — zero overhead, no Langfuse calls.
    """

    def decorator(fn: F) -> F:
        observed = _observe(
            name=name,
            as_type=as_type,
            capture_input=capture_input,
            capture_output=capture_output,
        )(fn)

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                if not is_enabled():
                    return await fn(*args, **kwargs)
                get_client()  # ensure our client is registered for global resolution
                return await observed(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not is_enabled():
                return fn(*args, **kwargs)
            get_client()
            return observed(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    if func is not None:
        return decorator(func)
    return decorator


def span(name: str, **kwargs: Any) -> AbstractContextManager[Any]:
    """Context manager creating a span observation as the current OTel context.

    Extra keyword arguments (``input``, ``output``, ``metadata``, ``level``, ...) are forwarded
    to Langfuse's ``start_as_current_observation``. No-op when the wrapper is inactive.
    """
    return get_client().start_as_current_observation(name=name, as_type="span", **kwargs)


def generation(
    name: str, *, model: str | None = None, **kwargs: Any
) -> AbstractContextManager[Any]:
    """Context manager creating a generation observation (an LLM call) as the current context.

    ``model`` is surfaced because it is near-universal for generations; other keyword arguments
    (``input``, ``output``, ``usage_details``, ``cost_details``, ``model_parameters``, ...) are
    forwarded to ``start_as_current_observation``. No-op when the wrapper is inactive.
    """
    return get_client().start_as_current_observation(
        name=name, as_type="generation", model=model, **kwargs
    )


def trace_context(
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    version: str | None = None,
    name: str | None = None,
) -> AbstractContextManager[Any]:
    """Set trace-level attributes for every observation created within this scope.

    Wraps Langfuse's ``propagate_attributes``. ``name`` maps to the trace name. Returns a null
    context (does nothing) when the wrapper is inactive.
    """
    if not is_enabled():
        return nullcontext()
    get_client()  # ensure our client is registered for global resolution
    return _propagate_attributes(
        user_id=user_id,
        session_id=session_id,
        tags=tags,
        metadata=metadata,
        version=version,
        trace_name=name,
    )
