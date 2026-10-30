# ContextCrew

Shared project context for engineers and their coding agents.

ContextCrew is designed to connect teammates using different MCP-compatible coding assistants to one project room. Agents share decisions, interface changes, handoffs, and debugging evidence so the next agent can build on what the team already knows.

**Status:** Planning. The repository currently contains documentation; the application and client integrations are not implemented or verified yet. See the [implementation plan](docs/implementation-plan.md) for the architecture, directory structure, and build phases.

## How it works

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

Start with the [implementation plan](docs/implementation-plan.md). It contains the authoritative checklist and acceptance gates, beginning with a two-client, two-laptop context-sharing test and extending to five-member operation.

Installation and startup commands will be added when the scaffold exists and those commands have been tested.
