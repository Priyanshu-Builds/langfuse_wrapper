"""LangChain / LangGraph integration.

:func:`get_handler` returns a configured Langfuse ``CallbackHandler`` to drop into a LangChain or
LangGraph run's ``callbacks``. It is no-op-safe: when the wrapper is inactive it returns ``None``,
so the common pattern stays clean::

    handler = lw.get_handler()
    with lw.trace_context(session_id="s1", user_id="u1", tags=["prod"]):
        graph.invoke(state, config={"callbacks": [handler] if handler else []})

Trace-level attributes (session/user/tags/...) are set with :func:`~langfuse_wrapper.trace_context`
rather than on the handler, matching the Langfuse v4 model. ``langchain`` is imported lazily, so
the base package never requires it — install the ``langchain`` extra to use this.
"""

from __future__ import annotations

from typing import Any

from ..client import get_client, get_settings, is_enabled


def get_handler(*, public_key: str | None = None, trace_context: Any | None = None) -> Any:
    """Return a Langfuse ``CallbackHandler`` bound to the configured client, or ``None``.

    Returns ``None`` when the wrapper is inactive. ``public_key`` defaults to the configured key
    (so the handler binds to our client); ``trace_context`` optionally attaches to an existing
    trace. Raises a helpful error if the ``langchain`` extra is not installed.
    """
    if not is_enabled():
        return None

    get_client()  # ensure our client is registered for global resolution

    try:
        from langfuse.langchain import CallbackHandler
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "langfuse_wrapper: the LangChain integration requires the 'langchain' extra. "
            "Install with: pip install 'langfuse-wrapper[langchain]'"
        ) from exc

    kwargs: dict[str, Any] = {}
    resolved_key = public_key or get_settings().public_key
    if resolved_key is not None:
        kwargs["public_key"] = resolved_key
    if trace_context is not None:
        kwargs["trace_context"] = trace_context

    return CallbackHandler(**kwargs)
