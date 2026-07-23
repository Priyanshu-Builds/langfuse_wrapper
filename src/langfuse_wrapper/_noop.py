"""No-op stand-ins used when the wrapper is inactive (disabled or missing credentials).

These mirror the subset of the Langfuse v4 client/span API that langfuse_wrapper calls, so the
rest of the library — and user code — can treat an inactive wrapper exactly like an active one.
Every method is a safe no-op: context managers yield a dummy span, mutators return ``self`` so
call-chains work, and query methods return ``None``/``False``.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


class NoopSpan:
    """A do-nothing observation (span/generation/...) that supports the real span protocol."""

    id: None = None
    trace_id: None = None

    def update(self, **kwargs: Any) -> NoopSpan:
        return self

    def end(self, **kwargs: Any) -> NoopSpan:
        return self

    def update_trace(self, **kwargs: Any) -> NoopSpan:
        return self

    def set_trace_io(self, **kwargs: Any) -> NoopSpan:
        return self

    def create_event(self, **kwargs: Any) -> NoopSpan:
        return self

    def score(self, **kwargs: Any) -> None:
        return None

    def score_trace(self, **kwargs: Any) -> None:
        return None

    def start_observation(self, **kwargs: Any) -> NoopSpan:
        return NoopSpan()

    @contextmanager
    def start_as_current_observation(self, **kwargs: Any) -> Iterator[NoopSpan]:
        yield NoopSpan()

    def __enter__(self) -> NoopSpan:
        return self

    def __exit__(self, *exc: Any) -> None:
        return None


class NoopClient:
    """A do-nothing Langfuse client returned by ``get_client()`` when the wrapper is inactive."""

    @contextmanager
    def start_as_current_observation(self, **kwargs: Any) -> Iterator[NoopSpan]:
        yield NoopSpan()

    def start_observation(self, **kwargs: Any) -> NoopSpan:
        return NoopSpan()

    def create_score(self, **kwargs: Any) -> None:
        return None

    def score_current_trace(self, **kwargs: Any) -> None:
        return None

    def score_current_span(self, **kwargs: Any) -> None:
        return None

    def update_current_span(self, **kwargs: Any) -> None:
        return None

    def update_current_generation(self, **kwargs: Any) -> None:
        return None

    def get_current_trace_id(self) -> None:
        return None

    def get_current_observation_id(self) -> None:
        return None

    def get_trace_url(self, **kwargs: Any) -> None:
        return None

    def get_prompt(self, name: str, **kwargs: Any) -> None:
        return None

    def auth_check(self) -> bool:
        return False

    def flush(self) -> None:
        return None

    def shutdown(self) -> None:
        return None
