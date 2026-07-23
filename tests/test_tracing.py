"""Tests for langfuse_wrapper.tracing (decorators + context managers)."""

from __future__ import annotations

import asyncio
import functools
from contextlib import nullcontext
from typing import Any

import pytest

import langfuse_wrapper as lw
from langfuse_wrapper import client as client_mod
from langfuse_wrapper import tracing
from langfuse_wrapper._noop import NoopSpan


def _counting_observe(counter: dict[str, int]):
    """A stand-in for langfuse.observe that counts wrapper invocations (not decoration).

    Mirrors the real observe by popping the ``langfuse_public_key`` call-time kwarg so it never
    leaks to the wrapped function.
    """

    def observe(**_kwargs: Any):
        def decorator(fn):
            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any):
                counter["calls"] += 1
                counter["public_key"] = kwargs.pop("langfuse_public_key", None)
                return fn(*args, **kwargs)

            return wrapper

        return decorator

    return observe


# --- @trace -----------------------------------------------------------------


def test_trace_runs_unwrapped_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = {"calls": 0}
    monkeypatch.setattr(tracing, "_observe", _counting_observe(counter))

    @tracing.trace(name="add")
    def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5
    assert counter["calls"] == 0  # observe wrapper never invoked when inactive


def test_trace_uses_observe_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = {"calls": 0}
    monkeypatch.setattr(tracing, "_observe", _counting_observe(counter))
    monkeypatch.setattr(client_mod, "Langfuse", lambda **kwargs: object())
    lw.configure(public_key="pk", secret_key="sk")

    @tracing.trace(name="mul")
    def mul(a: int, b: int) -> int:
        return a * b

    assert mul(2, 4) == 8
    assert counter["calls"] == 1
    # our configured key is forwarded so resolution binds our client (multi-client safety)
    assert counter["public_key"] == "pk"


def test_trace_bare_usage_without_parentheses() -> None:
    @tracing.trace
    def greet(name: str) -> str:
        return f"hi {name}"

    assert greet("x") == "hi x"


def test_trace_async_disabled() -> None:
    @tracing.trace()
    async def afn(x: int) -> int:
        return x + 1

    assert asyncio.run(afn(4)) == 5


def test_trace_async_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = {"calls": 0}
    monkeypatch.setattr(tracing, "_observe", _counting_observe(counter))
    monkeypatch.setattr(client_mod, "Langfuse", lambda **kwargs: object())
    lw.configure(public_key="pk", secret_key="sk")

    @tracing.trace(name="afn")
    async def afn(x: int) -> int:
        return x * 3

    assert asyncio.run(afn(3)) == 9
    assert counter["calls"] == 1


# --- span() / generation() --------------------------------------------------


def test_span_and_generation_yield_noop_when_disabled() -> None:
    with tracing.span("s") as s:
        assert isinstance(s, NoopSpan)
    with tracing.generation("g", model="claude-opus-4-8") as g:
        assert isinstance(g, NoopSpan)


def test_span_forwards_to_client_with_span_type(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeCM:
        def __enter__(self) -> str:
            return "SPAN"

        def __exit__(self, *exc: Any) -> bool:
            return False

    class FakeClient:
        def start_as_current_observation(self, **kwargs: Any) -> FakeCM:
            captured.update(kwargs)
            return FakeCM()

    monkeypatch.setattr(client_mod, "Langfuse", lambda **kwargs: FakeClient())
    lw.configure(public_key="pk", secret_key="sk")

    with tracing.span("myspan", input={"a": 1}) as s:
        assert s == "SPAN"
    assert captured["name"] == "myspan"
    assert captured["as_type"] == "span"
    assert captured["input"] == {"a": 1}


def test_generation_forwards_model_and_generation_type(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeCM:
        def __enter__(self) -> str:
            return "GEN"

        def __exit__(self, *exc: Any) -> bool:
            return False

    class FakeClient:
        def start_as_current_observation(self, **kwargs: Any) -> FakeCM:
            captured.update(kwargs)
            return FakeCM()

    monkeypatch.setattr(client_mod, "Langfuse", lambda **kwargs: FakeClient())
    lw.configure(public_key="pk", secret_key="sk")

    with tracing.generation("llm", model="claude-opus-4-8"):
        pass
    assert captured["as_type"] == "generation"
    assert captured["model"] == "claude-opus-4-8"


# --- trace_context() --------------------------------------------------------


def test_trace_context_is_noop_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"propagate": False}

    def fake_propagate(**kwargs: Any):
        called["propagate"] = True
        return nullcontext()

    monkeypatch.setattr(tracing, "_propagate_attributes", fake_propagate)
    with tracing.trace_context(user_id="u"):
        pass  # no error
    assert called["propagate"] is False  # never touches Langfuse when inactive


def test_trace_context_calls_propagate_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_propagate(**kwargs: Any):
        captured.update(kwargs)
        return nullcontext()

    monkeypatch.setattr(tracing, "_propagate_attributes", fake_propagate)
    monkeypatch.setattr(client_mod, "Langfuse", lambda **kwargs: object())
    lw.configure(public_key="pk", secret_key="sk")

    with tracing.trace_context(user_id="u1", session_id="s1", tags=["t"], name="flow"):
        pass

    assert captured["user_id"] == "u1"
    assert captured["session_id"] == "s1"
    assert captured["tags"] == ["t"]
    assert captured["trace_name"] == "flow"  # name maps to trace_name


def test_trace_context_binds_configured_public_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from langfuse._client.get_client import _current_public_key

    seen: dict[str, Any] = {}

    def fake_propagate(**kwargs: Any):
        seen["key_inside"] = _current_public_key.get(None)
        return nullcontext()

    monkeypatch.setattr(tracing, "_propagate_attributes", fake_propagate)
    monkeypatch.setattr(client_mod, "Langfuse", lambda **kwargs: object())
    lw.configure(public_key="pk-project-a", secret_key="sk")

    with tracing.trace_context(user_id="u1"):
        pass

    # our key is bound so keyless resolution inside the scope picks our client
    assert seen["key_inside"] == "pk-project-a"
    assert _current_public_key.get(None) is None  # restored after the scope
