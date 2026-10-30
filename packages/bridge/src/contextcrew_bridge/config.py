import json
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BridgeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_url: str
    token: str = Field(min_length=32, repr=False)

    @field_validator("api_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        url = urlparse(value)
        if url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
            raise ValueError("Use a backend origin without credentials, path, query, or fragment")
        if url.scheme != "https" and not (
            url.scheme == "http" and url.hostname in ("127.0.0.1", "localhost", "::1")
        ):
            raise ValueError("HTTP is permitted only on loopback; use HTTPS elsewhere")
        if not url.hostname:
            raise ValueError("Backend hostname is required")
        return value.rstrip("/")

    @classmethod
    def load(cls, path: Path) -> "BridgeConfig":
        if path.stat().st_mode & 0o077:
            raise ValueError("Bridge credential file must be owner-only (chmod 600)")
        return cls.model_validate(json.loads(path.read_text()))
