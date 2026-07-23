"""Prompt management helpers over Langfuse's prompt registry.

Wraps the client's ``get_prompt`` (which already handles version/label selection, caching, and a
built-in ``fallback``) and adds a one-call :func:`render` plus a graceful **local fallback**: when
the wrapper is inactive (or the client cannot be reached) and a ``fallback`` template is supplied,
prompts still resolve and compile locally so the host app keeps working offline.

Local rendering reuses Langfuse's own ``TemplateParser``, so ``{{ variable }}`` substitution is
identical to server-fetched prompts (whitespace-trimmed names, unknown variables left intact,
``None`` values rendered as empty strings).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from langfuse.model import TemplateParser

from .client import get_client, is_enabled


@dataclass
class LocalPrompt:
    """A prompt resolved from a local fallback template, mirroring the SDK prompt-client API."""

    name: str
    prompt: str | list[dict[str, Any]]
    type: str = "text"
    version: int | None = None

    @property
    def variables(self) -> list[str]:
        """Names of ``{{ variable }}`` placeholders in the template."""
        if self.type == "chat":
            names: list[str] = []
            for message in cast("list[dict[str, Any]]", self.prompt):
                names.extend(TemplateParser.find_variable_names(str(message.get("content", ""))))
            return names
        return TemplateParser.find_variable_names(str(self.prompt))

    def compile(self, **variables: Any) -> str | list[dict[str, Any]]:
        """Render the template with the given variables (str for text, messages for chat)."""
        if self.type == "chat":
            return [
                {
                    **message,
                    "content": TemplateParser.compile_template(
                        str(message.get("content", "")), variables
                    ),
                }
                for message in cast("list[dict[str, Any]]", self.prompt)
            ]
        return TemplateParser.compile_template(str(self.prompt), variables)


def get_prompt(
    name: str,
    *,
    version: int | None = None,
    label: str | None = None,
    type: str = "text",
    fallback: str | list[dict[str, Any]] | None = None,
    cache_ttl_seconds: int | None = None,
) -> Any:
    """Fetch a prompt from Langfuse, falling back to a local template when unavailable.

    Returns an SDK prompt client when active and reachable (``fallback`` is forwarded to the SDK
    so its own offline handling applies), a :class:`LocalPrompt` when the wrapper is inactive but a
    ``fallback`` is provided, or ``None`` when no prompt can be resolved.
    """
    if is_enabled():
        kwargs: dict[str, Any] = {"type": type}
        if version is not None:
            kwargs["version"] = version
        if label is not None:
            kwargs["label"] = label
        if fallback is not None:
            kwargs["fallback"] = fallback
        if cache_ttl_seconds is not None:
            kwargs["cache_ttl_seconds"] = cache_ttl_seconds
        result = get_client().get_prompt(name, **kwargs)
        if result is not None:
            return result
        # Active but client unavailable (e.g. init failed -> NoopClient): use local fallback below.

    if fallback is not None:
        return LocalPrompt(name=name, prompt=fallback, type=type)
    return None


def render(
    name: str,
    *,
    variables: dict[str, Any] | None = None,
    version: int | None = None,
    label: str | None = None,
    type: str = "text",
    fallback: str | list[dict[str, Any]] | None = None,
    cache_ttl_seconds: int | None = None,
) -> Any:
    """Fetch and compile a prompt in one call. Returns the rendered prompt, or ``None``.

    Text prompts render to ``str``; chat prompts render to a list of messages.
    """
    prompt = get_prompt(
        name,
        version=version,
        label=label,
        type=type,
        fallback=fallback,
        cache_ttl_seconds=cache_ttl_seconds,
    )
    if prompt is None:
        return None
    return prompt.compile(**(variables or {}))
