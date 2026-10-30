import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from contextcrew_api.config import Member, SpikeConfig
from contextcrew_api.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client(spike_config):
    with TestClient(create_app(spike_config)) as client:
        yield client


def headers(token="a" * 40):
    return {"Authorization": f"Bearer {token}"}


def update(**changes):
    return {
        "request_id": str(uuid4()),
        "kind": "decision",
        "title": "Authentication",
        "summary": "Use session cookies.",
        "body": "Synthetic body omitted from briefings.",
        **changes,
    }


def test_cross_user_read_and_room_isolation(client):
    record = client.post("/api/updates", headers=headers(), json=update()).json()
    context = client.get("/api/context", headers=headers("b" * 40)).json()
    assert context["records"][0]["id"] == record["id"]
    assert context["records"][0]["author"] == "alice"
    assert "body" not in context["records"][0]
    assert client.get("/api/context", headers=headers("c" * 40)).json()["records"] == []


def test_authentication_and_identity_cannot_be_overridden(client):
    assert client.get("/api/context").status_code == 401
    assert client.post("/api/updates", headers=headers("wrong"), json=update()).status_code == 401
    assert (
        client.post("/api/updates", headers=headers(), json=update(author="bob")).status_code == 422
    )
    assert (
        client.post("/api/updates", headers=headers(), json=update(room="other")).status_code == 422
    )


def test_expired_credential():
    config = SpikeConfig(
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
        members=[
            Member(
                author="alice", room="project", token_sha256=hashlib.sha256(b"a" * 40).hexdigest()
            ),
        ],
    )
    with TestClient(create_app(config)) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/api/context", headers=headers()).status_code == 401


def test_concurrent_retry_is_one_record_and_changed_payload_conflicts(client):
    payload = update()
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(
            pool.map(
                lambda _: client.post("/api/updates", headers=headers(), json=payload),
                range(5),
            )
        )
    assert all(result.status_code == 200 for result in results)
    assert len({result.json()["id"] for result in results}) == 1
    payload["summary"] = "Changed"
    assert client.post("/api/updates", headers=headers(), json=payload).status_code == 409
    assert len(client.get("/api/context", headers=headers()).json()["records"]) == 1


def test_bounded_cursor_has_no_skips(client):
    for index in range(25):
        assert (
            client.post(
                "/api/updates",
                headers=headers(),
                json=update(
                    title=f"Record {index}",
                    summary="🧪" * 500,
                ),
            ).status_code
            == 200
        )
    cursor, seen = 0, []
    while True:
        response = client.get(f"/api/context?after={cursor}&limit=20", headers=headers())
        assert len(response.text) <= 12000
        page = response.json()
        seen.extend(record["sequence"] for record in page["records"])
        cursor = page["next_cursor"]
        if not page["has_more"]:
            break
    assert seen == list(range(1, 26))
    assert client.get("/api/context?after=26", headers=headers()).status_code == 409


@pytest.mark.parametrize(
    "changes",
    [
        {"summary": ""},
        {"summary": "x" * 501},
        {"body": "x" * 8001},
        {"title": " "},
        {"kind": "unknown"},
        {"request_id": "not-a-uuid"},
    ],
)
def test_invalid_records_rejected(client, changes):
    assert client.post("/api/updates", headers=headers(), json=update(**changes)).status_code == 422


def test_invalid_page_limits_rejected(client):
    for query in ("after=-1", "limit=0", "limit=21"):
        assert client.get(f"/api/context?{query}", headers=headers()).status_code == 422
