"""Ephemeral interoperability spike. No production identity or persistence."""

import argparse
import hashlib
import secrets
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Annotated
from uuid import uuid4

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from contextcrew_api.config import Member, SpikeConfig
from contextcrew_api.schemas import ContextResponse, RecordSummary, UpdateInput


def create_app(config: SpikeConfig) -> FastAPI:
    app = FastAPI(title="ContextCrew Phase 0 spike", version="0.0.1")
    bearer = HTTPBearer(auto_error=False)
    lock = Lock()
    # Phase 0 only: all state belongs to this app instance and disappears on restart.
    records: dict[str, list[RecordSummary]] = {}
    requests: dict[tuple[str, str, str], tuple[UpdateInput, RecordSummary]] = {}

    def authenticate(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> Member:
        if credentials is None or datetime.now(UTC) >= config.expires_at:
            raise HTTPException(401, "Missing, invalid, or expired spike credential")
        digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
        for member in config.members:
            if secrets.compare_digest(digest, member.token_sha256):
                return member
        raise HTTPException(401, "Missing, invalid, or expired spike credential")

    @app.get("/healthz")
    def health() -> dict:
        return {"status": "ok", "mode": "ephemeral-spike"}

    @app.post("/api/updates", response_model=RecordSummary)
    def publish(update: UpdateInput, member: Annotated[Member, Depends(authenticate)]):
        key = (member.room, member.author, str(update.request_id))
        with lock:
            if previous := requests.get(key):
                if previous[0] != update:
                    raise HTTPException(409, "Request ID already used with different content")
                return previous[1]
            room_records = records.setdefault(member.room, [])
            if len(room_records) >= 1000:
                raise HTTPException(
                    409, "Spike room limit reached; restart to reset synthetic data"
                )
            record = RecordSummary(
                id=uuid4(),
                sequence=len(room_records) + 1,
                kind=update.kind,
                title=update.title,
                summary=update.summary,
                author=member.author,
                created_at=datetime.now(UTC),
            )
            # Body is validated but not exposed by the summary-only spike.
            requests[key] = (update, record)
            room_records.append(record)
            return record

    @app.get("/api/context", response_model=ContextResponse)
    def get_context(
        member: Annotated[Member, Depends(authenticate)],
        after: int = Query(default=0, ge=0),
        limit: int = Query(default=10, ge=1, le=20),
    ):
        with lock:
            room_records = records.get(member.room, [])
            if after > len(room_records):
                raise HTTPException(409, "Cursor is ahead of this room; restart retrieval at zero")
            selected: list[RecordSummary] = []
            for record in room_records[after : after + limit]:
                candidate = ContextResponse(
                    records=[*selected, record],
                    next_cursor=record.sequence,
                    has_more=record.sequence < len(room_records),
                )
                if len(candidate.model_dump_json()) > 12000:
                    break
                selected.append(record)
            cursor = selected[-1].sequence if selected else after
            return ContextResponse(
                records=selected,
                next_cursor=cursor,
                has_more=cursor < len(room_records),
            )

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    config = SpikeConfig.load(args.config)
    # The spike is deliberately loopback-only; use an SSH tunnel for another laptop.
    uvicorn.run(create_app(config), host="127.0.0.1", port=args.port, access_log=False)
