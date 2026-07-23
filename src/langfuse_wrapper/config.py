"""Configuration for langfuse_wrapper.

Settings are read from environment variables (and an optional `.env` file), matching the
names the Langfuse SDK itself uses, plus wrapper-specific `LFWRAP_*` toggles:

* ``LANGFUSE_PUBLIC_KEY`` / ``LANGFUSE_SECRET_KEY`` — credentials.
* ``LANGFUSE_BASE_URL`` — host of the Langfuse instance (Cloud or self-hosted).
  ``LANGFUSE_HOST`` is accepted as a deprecated alias.
* ``LFWRAP_ENABLED`` — master on/off switch for the wrapper (default ``True``).
* ``LFWRAP_SCRUB_PII`` — scrub input/output payloads before sending (default ``False``).

The wrapper is *active* only when it is enabled **and** credentials are present. Otherwise it
degrades to a no-op so the host application runs unchanged.
"""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Resolved wrapper configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    public_key: str | None = Field(
        default=None, validation_alias=AliasChoices("LANGFUSE_PUBLIC_KEY")
    )
    secret_key: str | None = Field(
        default=None, validation_alias=AliasChoices("LANGFUSE_SECRET_KEY")
    )
    # LANGFUSE_BASE_URL is the current name; LANGFUSE_HOST is a deprecated alias the SDK
    # still honors. BASE_URL wins when both are set.
    base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGFUSE_BASE_URL", "LANGFUSE_HOST"),
    )
    enabled: bool = Field(default=True, validation_alias=AliasChoices("LFWRAP_ENABLED"))
    scrub_pii: bool = Field(default=False, validation_alias=AliasChoices("LFWRAP_SCRUB_PII"))

    @property
    def has_credentials(self) -> bool:
        """True when both public and secret keys are present and non-empty."""
        return bool(self.public_key and self.secret_key)

    @property
    def is_active(self) -> bool:
        """True when the wrapper should send data to Langfuse (enabled + credentials)."""
        return self.enabled and self.has_credentials
