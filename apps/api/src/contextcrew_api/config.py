import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Member(BaseModel):
    model_config = ConfigDict(extra="forbid")
    author: str = Field(min_length=1)
    room: str = Field(min_length=1)
    token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class SpikeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expires_at: datetime
    members: list[Member] = Field(min_length=1)

    @classmethod
    def load(cls, path: Path) -> "SpikeConfig":
        config = cls.model_validate(json.loads(path.read_text()))
        if config.expires_at.tzinfo is None:
            raise ValueError("Config expiry must include a timezone")
        return config
