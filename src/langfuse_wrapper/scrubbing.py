"""Heuristic PII scrubbing for data sent to Langfuse.

When ``LFWRAP_SCRUB_PII`` is enabled, the wrapper installs :func:`make_mask` as the Langfuse
client's ``mask`` function, so input, output, and metadata on every observation are redacted
centrally (including data captured automatically by ``@trace``/``@observe``).

Detection is regex-based and therefore best-effort — it trades occasional false positives for
broad coverage of common identifiers (email, credit-card, SSN, IPv4, phone). Extend or override
the rules with :func:`register_pattern`. Scrubbing is **off by default**; nothing changes unless
you opt in.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

# Insertion order matters: higher-signal patterns (with separators/anchors) run before the
# looser phone pattern so their digits are redacted first and cannot be re-matched.
_PATTERNS: dict[str, tuple[re.Pattern[str], str]] = {
    "email": (
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        "[REDACTED_EMAIL]",
    ),
    "credit_card": (
        re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b"),
        "[REDACTED_CC]",
    ),
    "ssn": (
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "[REDACTED_SSN]",
    ),
    "ipv4": (
        re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"),
        "[REDACTED_IP]",
    ),
    "phone": (
        re.compile(r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"),
        "[REDACTED_PHONE]",
    ),
}


def register_pattern(name: str, pattern: str, replacement: str = "[REDACTED]") -> None:
    """Add or override a redaction rule (applied to strings during scrubbing)."""
    _PATTERNS[name] = (re.compile(pattern), replacement)


def scrub_text(text: str) -> str:
    """Apply all redaction rules to a single string."""
    for regex, replacement in _PATTERNS.values():
        text = regex.sub(replacement, text)
    return text


def scrub(value: Any) -> Any:
    """Return a copy of ``value`` with PII redacted in any nested strings.

    Recurses through dicts, lists, tuples, and sets; strings are redacted; other types are
    returned unchanged (so JSON-serializability is preserved).
    """
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, dict):
        return {key: scrub(val) for key, val in value.items()}
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, tuple):
        return tuple(scrub(item) for item in value)
    if isinstance(value, set):
        return {scrub(item) for item in value}
    return value


def make_mask() -> Callable[..., Any]:
    """Build a Langfuse ``mask`` callable that scrubs the given data."""

    def _mask(*, data: Any, **_kwargs: Any) -> Any:
        return scrub(data)

    return _mask
