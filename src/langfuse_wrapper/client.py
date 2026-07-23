"""Client resolution with graceful degradation.

``get_client()`` returns either the real Langfuse client (when the wrapper is active) or a
:class:`~langfuse_wrapper._noop.NoopClient` (when disabled or missing credentials). The result
is cached as a process-wide singleton; :func:`configure` rebuilds settings and resets the cache.

The guarantee: if credentials are absent, ``LFWRAP_ENABLED`` is false, or the Langfuse client
fails to construct, the host application keeps running — every wrapper call becomes a no-op.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langfuse import Langfuse

from ._noop import NoopClient
from .config import Settings

if TYPE_CHECKING:
    LangfuseClient = Langfuse | NoopClient

logger = logging.getLogger("langfuse_wrapper")

_UNSET: Any = object()

_settings: Settings | None = None
_client: LangfuseClient | None = None


def get_settings() -> Settings:
    """Return the cached :class:`Settings`, loading from env/`.env` on first use."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def configure(
    *,
    public_key: str | None = _UNSET,
    secret_key: str | None = _UNSET,
    base_url: str | None = _UNSET,
    enabled: bool = _UNSET,
    scrub_pii: bool = _UNSET,
) -> Settings:
    """Override configuration programmatically and reset the cached client.

    Values default to the environment; any argument passed here takes precedence. Passing an
    explicit ``None`` is respected (e.g. to clear a key). Returns the new active settings.
    """
    global _settings, _client
    base = Settings()
    overrides = {
        "public_key": public_key,
        "secret_key": secret_key,
        "base_url": base_url,
        "enabled": enabled,
        "scrub_pii": scrub_pii,
    }
    applied = {k: v for k, v in overrides.items() if v is not _UNSET}
    _settings = base.model_copy(update=applied)
    _client = None
    return _settings


def is_enabled() -> bool:
    """True when the wrapper is active (enabled and credentialed)."""
    return get_settings().is_active


def get_client() -> LangfuseClient:
    """Return the cached Langfuse client, or a no-op client when the wrapper is inactive."""
    global _client
    if _client is not None:
        return _client

    settings = get_settings()
    if not settings.is_active:
        if settings.enabled and not settings.has_credentials:
            logger.info(
                "langfuse_wrapper: LANGFUSE_PUBLIC_KEY/SECRET_KEY not set — running in no-op mode."
            )
        _client = NoopClient()
        return _client

    try:
        _client = Langfuse(
            public_key=settings.public_key,
            secret_key=settings.secret_key,
            base_url=settings.base_url,
        )
    except Exception:  # defensive: keep the host app alive on any init failure
        logger.warning(
            "langfuse_wrapper: failed to initialize Langfuse client — falling back to no-op.",
            exc_info=True,
        )
        _client = NoopClient()
    return _client


def flush() -> None:
    """Flush buffered events to Langfuse. No-op when inactive. Safe for short-lived processes."""
    get_client().flush()


def reset() -> None:
    """Clear cached settings and client. Primarily for tests and re-configuration."""
    global _settings, _client
    _settings = None
    _client = None
