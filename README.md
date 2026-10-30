# ContextCrew

Shared project context for engineers and their coding agents.

ContextCrew is designed to connect teammates using different MCP-compatible coding assistants to one project room. Agents share decisions, interface changes, handoffs, and debugging evidence so the next agent can build on what the team already knows.

**Status:** Phase 0 local spike implemented. An ephemeral FastAPI API and two-tool MCP bridge exchange synthetic updates, with a React connection-check scaffold. Production identity, persistence, artifact uploads, and the investigation dashboard are not implemented. Codex CLI and Cursor have exchanged synthetic records successfully on one laptop; the separate-laptop gate is still unverified. See the [implementation plan](docs/implementation-plan.md) for scope and build phases.

## How it works

The following describes the planned complete product, not all currently available features.

1. Create a project room and invite a teammate.
2. Connect each engineer's assistant through a local MCP bridge.
3. Agents automatically publish useful updates and selected artifacts under the project's sharing rules.
4. Before continuing work, agents retrieve a compact briefing and fetch detailed evidence when needed.
5. Engineers use the website to review findings, manage sharing preferences, and resolve disagreements.

The backend stores the shared records. The website is the human dashboard and does not need to remain open for agents to exchange context. Updates enter an agent's context when it retrieves them; ContextCrew does not synchronize hidden model state or copy entire private chats.

## First workflow: shared debugging

Two engineers investigate duplicate checkout requests. One agent examines frontend retries while the other checks backend timeout handling. They claim separate experiments and publish observations, reproduction conditions, file fingerprints, and supporting output.

When one experiment finishes, the other agent can retrieve that evidence and adjust its next step. Findings remain tied to their tested conditions; changed files flag evidence for revalidation rather than turning an old result into a permanent assumption.

## Planned stack

| Component | Technology |
| --- | --- |
| Dashboard | React, TypeScript, Vite, Tailwind CSS |
| Backend | Python, FastAPI, Pydantic |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| Agent bridge | Python MCP SDK, HTTPX |
| Authentication | Clerk |
| Evidence storage | Amazon S3 |
| Tracing | OpenTelemetry, development Jaeger |
| Testing | pytest, Playwright, Ruff, TypeScript checking |
| Development and CI | Docker Compose, GitHub Actions |

## Sharing and evidence

- Agents choose what to publish; the bridge enforces configured path exclusions, artifact types, size limits, and text secret checks.
- Shared context includes general project knowledge, with debugging as the first complete workflow.
- Experiment ownership uses expiring claims; publications are designed to tolerate retries without duplicating records.
- Results retain their author, conditions, and evidence. Agent-reported output is not independently verified execution.
- Secret detection is imperfect, particularly for images. Users can exclude sensitive paths, disable artifact types, or pause sharing.

## Development

Prerequisites: Python 3.13, uv, Node.js 24, npm. From the repository root:

```sh
uv sync --all-packages --frozen
npm --prefix apps/web ci --ignore-scripts
.venv/bin/contextcrew spike-init --directory work/spike
.venv/bin/contextcrew-api --config work/spike/server.json
```

In a second terminal, run `npm --prefix apps/web run dev` and open the Vite URL. The page checks API health; no credentials are entered in the browser. Keep the API running when using the bridge.

`spike-init` creates separate Alice/Bob credentials, valid for 24 hours, in a new private directory. It refuses to overwrite existing credentials. Use a new directory to regenerate them. Phase 0 accepts **synthetic data only**: sharing policy enforcement and production authentication arrive in later phases. Records disappear on restart, and cursors reset to zero.

Checks:

```sh
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -q
npm --prefix apps/web run build
```

Tests start a loopback server and two MCP subprocesses; they do not call a model provider. The frontend build is typechecked; interactive browser behavior has not yet been manually verified.

Read [Phase 0 contracts and client setup](docs/phase-0.md) for tool payloads, assistant configuration, and the two-laptop procedure. The [implementation plan](docs/implementation-plan.md) remains the authoritative checklist.
