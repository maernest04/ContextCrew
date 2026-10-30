"""Phase 0 setup and local stdio bridge. Use only synthetic records."""

import argparse
import hashlib
import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

from contextcrew_bridge.config import BridgeConfig


def initialize(directory: Path, api_url: str):
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    members = []
    for author in ("alice", "bob"):
        token = secrets.token_urlsafe(32)
        config = BridgeConfig(api_url=api_url, token=token)
        path = directory / f"{author}.json"
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
            stream.write(config.model_dump_json(indent=2))
        members.append(
            {
                "author": author,
                "room": "synthetic-project",
                "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
            }
        )
    server = {
        "expires_at": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
        "members": members,
    }
    (directory / "server.json").write_text(json.dumps(server, indent=2))
    print(f"Created 24-hour synthetic credentials in {directory.resolve()}; values not displayed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser(
        "spike-init", help="Create a NEW private synthetic credential directory"
    )
    init.add_argument("--directory", type=Path, required=True)
    init.add_argument("--api-url", default="http://127.0.0.1:8000")
    serve = commands.add_parser("serve", help="Run stdio MCP; does not execute local commands")
    serve.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "spike-init":
            initialize(args.directory, args.api_url)
        else:
            from contextcrew_bridge.server import create_server

            create_server(BridgeConfig.load(args.config)).run(transport="stdio")
    except (OSError, ValueError):
        # Validation errors can contain raw credential input; do not render them.
        parser.exit(
            1, "Configuration failed; check file permissions, origin, and required fields.\n"
        )
