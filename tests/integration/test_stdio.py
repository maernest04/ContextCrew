import json
import socket
import sys
import threading
import time
from pathlib import Path
from uuid import uuid4

import pytest
import uvicorn
from contextcrew_api.config import SpikeConfig
from contextcrew_api.main import create_app
from contextcrew_bridge.cli import initialize
from contextcrew_bridge.config import BridgeConfig
from fastapi.testclient import TestClient
from mcp import Client
from mcp.client.stdio import StdioServerParameters


@pytest.fixture
def backend(spike_config):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(spike_config),
            log_level="warning",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            if not thread.is_alive():
                pytest.fail("Spike API exited during startup")
            time.sleep(0.02)
        assert server.started
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()
        assert not thread.is_alive()


def bridge(tmp_path, backend, name, token):
    config = tmp_path / f"{name}.json"
    config.write_text(json.dumps({"api_url": backend, "token": token}))
    config.chmod(0o600)
    return Client(
        StdioServerParameters(
            command=str(Path(sys.executable).parent / "contextcrew"),
            args=["serve", "--config", str(config)],
        )
    )


async def test_two_independent_stdio_processes_share_context(tmp_path, backend):
    async with (
        bridge(tmp_path, backend, "alice", "a" * 40) as alice,
        bridge(tmp_path, backend, "bob", "b" * 40) as bob,
    ):
        tools = await alice.list_tools()
        assert {tool.name for tool in tools.tools} == {"get_context", "publish_update"}
        payload = {
            "request_id": str(uuid4()),
            "kind": "decision",
            "title": "Synthetic login API",
            "summary": "POST /login sets a session cookie.",
        }
        published = await alice.call_tool("publish_update", payload)
        assert not published.is_error
        assert published.structured_content["author"] == "alice"
        retry = await alice.call_tool("publish_update", payload)
        assert retry.structured_content["id"] == published.structured_content["id"]
        received = await bob.call_tool("get_context", {"after": 0})
        assert not received.is_error
        assert received.structured_content["records"][0]["id"] == published.structured_content["id"]
        assert not received.structured_content["has_more"]
        invalid = await bob.call_tool("publish_update", {**payload, "summary": "x" * 501})
        assert invalid.is_error


async def test_backend_error_has_no_credential_or_record_echo(tmp_path, backend):
    token = "invalid-token-that-must-never-appear-in-tool-output"
    async with bridge(tmp_path, backend, "invalid", token) as client:
        result = await client.call_tool("get_context")
        assert result.is_error
        assert token not in result.model_dump_json()
        assert "401" in result.model_dump_json()


def test_credential_setup_permissions_and_no_overwrite(tmp_path, capsys):
    directory = tmp_path / "credentials"
    initialize(directory, "http://127.0.0.1:8000")
    alice = BridgeConfig.load(directory / "alice.json")
    assert alice.token not in capsys.readouterr().out
    assert (directory.stat().st_mode & 0o777) == 0o700
    server_config = SpikeConfig.load(directory / "server.json")
    assert alice.token not in (directory / "server.json").read_text()
    with TestClient(create_app(server_config)) as client:
        response = client.get("/api/context", headers={"Authorization": f"Bearer {alice.token}"})
        assert response.status_code == 200
        assert response.json()["records"] == []
    with pytest.raises(FileExistsError):
        initialize(directory, "http://127.0.0.1:8000")
    (directory / "alice.json").chmod(0o644)
    with pytest.raises(ValueError):
        BridgeConfig.load(directory / "alice.json")


@pytest.mark.parametrize(
    "origin",
    [
        "http://example.com",
        "https://user:password@example.com",
        "https://example.com/private",
    ],
)
def test_unsafe_backend_origins_rejected(origin):
    with pytest.raises(ValueError):
        BridgeConfig(api_url=origin, token="a" * 40)
