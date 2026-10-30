import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from contextcrew_api.config import Member, SpikeConfig


@pytest.fixture
def spike_config():
    return SpikeConfig(
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        members=[
            Member(
                author=author, room=room, token_sha256=hashlib.sha256(token.encode()).hexdigest()
            )
            for author, room, token in [
                ("alice", "project", "a" * 40),
                ("bob", "project", "b" * 40),
                ("outsider", "other", "c" * 40),
            ]
        ],
    )
