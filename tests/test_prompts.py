"""Tests for langfuse_wrapper.prompts (local fallback + get_prompt/render)."""

from __future__ import annotations

from typing import Any

import pytest

import langfuse_wrapper as lw
from langfuse_wrapper import client as client_mod
from langfuse_wrapper import prompts
from langfuse_wrapper.prompts import LocalPrompt

# --- LocalPrompt rendering (matches Langfuse's TemplateParser) ---------------


def test_local_prompt_text_substitutes_variables() -> None:
    p = LocalPrompt(name="greet", prompt="Hello {{ name }}, welcome to {{ place }}.")
    assert p.compile(name="Priya", place="CHAMP") == "Hello Priya, welcome to CHAMP."


def test_local_prompt_leaves_unknown_variables_intact() -> None:
    p = LocalPrompt(name="p", prompt="Hi {{ name }} / {{ missing }}")
    assert p.compile(name="X") == "Hi X / {{ missing }}"


def test_local_prompt_none_value_renders_empty() -> None:
    p = LocalPrompt(name="p", prompt="[{{ x }}]")
    assert p.compile(x=None) == "[]"


def test_local_prompt_variables_property() -> None:
    p = LocalPrompt(name="p", prompt="{{ a }} and {{ b }}")
    assert p.variables == ["a", "b"]


def test_local_prompt_chat_substitutes_each_message() -> None:
    p = LocalPrompt(
        name="chat",
        type="chat",
        prompt=[
            {"role": "system", "content": "You are {{ persona }}."},
            {"role": "user", "content": "Help with {{ topic }}."},
        ],
    )
    compiled = p.compile(persona="a helpful agent", topic="tracing")
    assert compiled == [
        {"role": "system", "content": "You are a helpful agent."},
        {"role": "user", "content": "Help with tracing."},
    ]


# --- get_prompt / render when inactive --------------------------------------


def test_get_prompt_inactive_with_fallback_returns_local_prompt() -> None:
    p = prompts.get_prompt("welcome", fallback="Hi {{ name }}")
    assert isinstance(p, LocalPrompt)
    assert p.compile(name="Sam") == "Hi Sam"


def test_get_prompt_inactive_without_fallback_returns_none() -> None:
    assert prompts.get_prompt("welcome") is None


def test_render_inactive_uses_fallback() -> None:
    out = prompts.render("welcome", variables={"name": "Sam"}, fallback="Hi {{ name }}")
    assert out == "Hi Sam"


def test_render_inactive_without_fallback_returns_none() -> None:
    assert prompts.render("welcome", variables={"name": "Sam"}) is None


# --- get_prompt / render when active ----------------------------------------


class FakePrompt:
    def __init__(self, template: str) -> None:
        self.template = template

    def compile(self, **variables: Any) -> str:
        return self.template.format(**variables)


def test_get_prompt_active_delegates_to_client(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeClient:
        def get_prompt(self, name: str, **kwargs: Any) -> FakePrompt:
            captured["name"] = name
            captured.update(kwargs)
            return FakePrompt("server template")

    monkeypatch.setattr(client_mod, "Langfuse", lambda **kwargs: FakeClient())
    lw.configure(public_key="pk", secret_key="sk")

    p = prompts.get_prompt("myprompt", version=3, label="prod", fallback="fb")
    assert isinstance(p, FakePrompt)
    assert captured["name"] == "myprompt"
    assert captured["version"] == 3
    assert captured["label"] == "prod"
    assert captured["fallback"] == "fb"
    assert captured["type"] == "text"


def test_get_prompt_active_but_client_unavailable_uses_local_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Enabled + credentials, but client construction fails -> NoopClient (get_prompt -> None).
    def boom(**kwargs: Any) -> None:
        raise RuntimeError("unreachable")

    monkeypatch.setattr(client_mod, "Langfuse", boom)
    lw.configure(public_key="pk", secret_key="sk")

    p = prompts.get_prompt("myprompt", fallback="local {{ v }}")
    assert isinstance(p, LocalPrompt)
    assert p.compile(v="ok") == "local ok"
