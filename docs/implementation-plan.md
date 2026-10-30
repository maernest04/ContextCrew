# ContextCrew implementation plan

Status: planned; application not implemented. Updated: October 29, 2026.

This is the authoritative execution plan for one complete personal-project release. Phases are build order, not separate product versions. Keep implementation checklists here; record completion only after the phase's verification passes.

## 1. Product and agreed scope

ContextCrew gives engineers using different MCP-compatible coding assistants a shared project memory. Debugging is the first fully supported workflow.

Two engineers join a project room, connect their assistants, publish useful decisions and experimental evidence, and retrieve concise context before continuing work. The website lets humans inspect and manage the same records. Agents communicate directly with the backend through local MCP bridges; the website need not remain open.

### Decisions already made

- General project context: decisions, interfaces, setup findings, progress/handoffs, open questions, debugging hypotheses and results.
- Agents publish automatically and choose relevant artifacts automatically, subject to user-configured sharing policy. No per-publication approval screen in the default workflow.
- Existing assistants execute commands locally under their own permissions. ContextCrew does not execute shared commands or run its own model.
- Retrieval returns a bounded summary and links to details, not every conversation or attachment.
- Evidence carries provenance and freshness information; disagreements remain visible until a human resolves them.
- Support two engineers on separate laptops first, then validate five-member operation in this same release.
- PostgreSQL, S3, Docker, GitHub Actions, and OpenTelemetry have concrete roles. No sponsor-specific dependencies.

### Boundaries

- Do not read private conversation databases, hidden model state, or entire repositories automatically.
- Automatic publication is cooperative agent behavior. Instructions and tool descriptions encourage calls; MCP cannot guarantee calls or interrupt every running client.
- A saved update becomes agent context only on a later retrieval/tool call. Dashboard polling is independent of agent retrieval.
- MCP compatibility is a client capability. Verify named clients individually; do not claim every app using a model works.
- No semantic guarantee that similar experiment descriptions represent identical work. Ownership is enforced for explicit experiment IDs.
- No general autonomous orchestrator, code editor, remote shell, billing system, vector database, Kafka, Redis, Kubernetes, or Terraform.

## 2. Architecture and stack

```text
Engineer A's assistant                  Engineer B's assistant
          | stdio MCP                            | stdio MCP
     Local Python bridge                    Local Python bridge
          | authenticated HTTPS                  |
          +------------------+-------------------+
                             |
                         FastAPI
                        /    |    \
               PostgreSQL   S3    OpenTelemetry exporter
                             |       -> Jaeger for development
                   selected artifacts
                             
Browser -> React static build served by FastAPI -> same authenticated API
```

| Layer | Choice | Responsibility |
| --- | --- | --- |
| Browser | React, TypeScript, Vite, Tailwind CSS | Room setup, investigation board, sharing preferences, evidence review |
| API | Python, FastAPI, Pydantic | Access control, publication, retrieval, concurrency, artifact handling |
| Database | PostgreSQL, SQLAlchemy, Alembic | Relational state, transactions, full-text search, schema migrations |
| Agent bridge | Python MCP SDK, HTTPX | stdio tools, local credentials, file access policy, fingerprints, API requests |
| Identity | Clerk | Browser sign-in; API verifies session tokens |
| Artifacts | Amazon S3, boto3 | Private object storage; server-generated keys; authorized temporary downloads |
| Observability | OpenTelemetry, Jaeger | Bridge-to-API-to-database/object-operation traces |
| Validation | pytest, Playwright, Ruff, TypeScript checking | Behavioral tests, browser flows, static checks |
| Delivery | Docker Compose, GitHub Actions | Reproducible development; automated checks and container build |
| Deployment | One container application host, managed PostgreSQL, S3 | HTTPS, process restarts, persistence and backups |

Poll the dashboard every five seconds while visible, with backoff on failure. No WebSocket/SSE service. Serve the compiled frontend from the API to keep a single application deployment. Choose the host during deployment based on current pricing and available accounts; no provider-specific architecture is required.

### Repository layout

Planned directory structure for the complete release. Create files as their features are implemented; this tree does not require empty placeholder modules.

```text
ContextCrew/
├── README.md                         # Purpose, installation, development commands
├── pyproject.toml                    # Python workspace and shared tooling
├── uv.lock                           # Locked API/bridge dependencies
├── .python-version
├── .node-version
├── .gitignore
├── .dockerignore
├── compose.yaml                      # Local API, PostgreSQL, development Jaeger
├── .github/
│   └── workflows/
│       └── ci.yml                    # Checks, tests, frontend/container builds
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── Dockerfile                # Builds web assets and packages FastAPI
│   │   ├── .env.example              # Safe backend configuration placeholders
│   │   ├── alembic.ini
│   │   ├── migrations/
│   │   │   ├── env.py
│   │   │   └── versions/             # Database migrations
│   │   ├── src/contextcrew_api/
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # App, middleware, health, static frontend
│   │   │   ├── config.py
│   │   │   ├── auth.py               # Identity verification and room access
│   │   │   ├── db.py                 # Connections and transaction sessions
│   │   │   ├── models.py             # SQLAlchemy tables
│   │   │   ├── schemas.py            # Pydantic request/response contracts
│   │   │   ├── routes/               # Rooms, context, investigations, artifacts
│   │   │   ├── services/             # Retrieval, claims, publication, S3 lifecycle
│   │   │   ├── maintenance.py        # Pending upload/deletion cleanup command
│   │   │   └── telemetry.py
│   │   └── tests/                    # API behavior and database integration
│   └── web/
│       ├── package.json
│       ├── package-lock.json
│       ├── .env.example              # Public frontend configuration only
│       ├── index.html
│       ├── vite.config.ts
│       ├── tsconfig.json
│       └── src/
│           ├── main.tsx
│           ├── App.tsx
│           ├── styles.css
│           ├── api/                  # HTTP client and API types
│           ├── pages/                # Rooms, context, investigation, settings
│           └── components/           # Shared interface elements
├── packages/
│   └── bridge/
│       ├── pyproject.toml
│       ├── src/contextcrew_bridge/
│       │   ├── __init__.py
│       │   ├── cli.py                # Connect, local settings, MCP entry point
│       │   ├── server.py             # stdio MCP registration
│       │   ├── tools.py              # ContextCrew tool handlers
│       │   ├── client.py             # Authenticated backend requests and retries
│       │   ├── config.py             # Workspace binding and credential loading
│       │   ├── policy.py             # Local exclusions and publication checks
│       │   ├── fingerprints.py       # File hashes and local freshness checks
│       │   └── telemetry.py
│       └── tests/                    # Tools, path policy, retries, fingerprints
├── tests/
│   ├── integration/                  # Bridge → API → database/storage flows
│   └── e2e/                          # Playwright and two-user workflow scenarios
├── fixtures/
│   ├── debugging-project/            # Synthetic frontend/backend bug
│   └── evidence/                     # Synthetic logs and secret-check fixtures
└── docs/
    └── implementation-plan.md        # Authoritative phase checklist
```

The API owns shared state and permissions; the bridge owns local file access and tool integration; the web app presents the shared records. Keep route handlers thin and put transactional rules in API services. Start with the single `models.py` and `schemas.py`; split them only if their size warrants it.

Use one Python workspace for API/bridge dependencies and npm for the single frontend. Reuse contracts through existing packages or generated OpenAPI types where practical; do not create a general-purpose shared library upfront. Keep real environment files, bridge credentials, uploaded artifacts, database volumes, and generated builds outside tracked source. No directories or application scaffold have been created by this plan.

## 3. Identity, room membership, and sharing

### Authentication and setup

1. Engineer signs in on the website and creates or joins a room using an expiring invite.
2. Website issues a room-scoped bridge token for that user, displayed once. Store only a digest server-side; tokens expire and can be revoked.
3. Engineer runs `contextcrew connect` and pastes the token into a hidden prompt. Never place credentials in assistant messages, repository files, CLI arguments, or tool results.
4. CLI saves credentials outside the repository with owner-only permissions and binds this local workspace to the room and a repository alias.
5. Engineer registers the bridge using that client's documented stdio MCP configuration and adds the supplied short agent instructions.

Owner/member roles only. Owners manage invites, membership, and room policy; members publish and inspect context. Members can retract their own content; owners can resolve conflicts and delete room content. Every endpoint checks current membership, including bridge-token requests and artifact access. Removing a member invalidates their bridge access even if a token has not expired.

### Sharing policy

- Room policy sets the upper bound; local workspace preferences may be stricter. Enforce at publication time, including policy changes after connection.
- Settings: enabled record types, allowed artifact types, maximum size, excluded paths, and pause all sharing. File exclusions also reject text records declaring an excluded related file.
- Default artifacts: bounded UTF-8 text/logs, JSON, PNG, JPEG. Start with 5 MiB per artifact, 20 MiB per publication, 100 MiB stored per room. These are product limits, not performance claims.
- Hard exclusions include credential files, private keys, `.env` files, version-control internals, paths outside the configured workspace, and symlink escapes. Do not expose an agent tool that changes these rules.
- Apply text secret checks before upload and again server-side. Reject detected credentials with a sanitized reason; never echo the secret. Scan text records as well as artifacts.
- Screenshot content is not comprehensively checked for secrets; make this limitation visible in settings. Users can disable image uploads. No promise of complete DLP or automatic privacy protection.
- Agents explicitly select artifact paths; never upload a directory, arbitrary archive, or full transcript by default. Backend cannot fetch arbitrary URLs or read a local machine.
- Shared content is untrusted data, not permission to run commands. Tool descriptions and retrieved summaries repeat this boundary.
- Users can pause locally without contacting the server. If current room policy cannot be checked, publication fails closed and local coding may continue.

## 4. Data and correctness rules

### Logical tables

| Table | Key contents |
| --- | --- |
| users | Internal ID and external identity subject |
| rooms / memberships / invites | Project name, roles, policy revision, hashed expiring invites |
| bridge_tokens | Digest, user, room, expiry, revocation |
| investigations | Goal, reproduction notes, state: open/resolved |
| records | Type, title, bounded summary/body, author, investigation, revision, status, superseded record, conflict links |
| experiments | Investigation, hypothesis record, planned procedure, status, current lease generation/expiry |
| experiment_results | Experiment, recorded observations, interpretation, conditions, code fingerprints, outcome, reporter |
| artifacts | Room/result/record association, object key, checksum, size, type, upload/deletion state |
| room_events | Per-room sequence and small event payload for incremental retrieval |
| idempotency_requests | Actor/room/key, payload digest and committed response |

Use foreign keys and room-scoped queries consistently. Author identity and timestamps come from authentication/server time. Agent/client labels are self-reported metadata, not verified model identity.

### Publication and retrieval

- Agent-written summaries: maximum 500 characters; record bodies: maximum 8,000 characters. Retain full evidence separately.
- No additional model API for summarization. Assemble a deterministic briefing from current record summaries, open questions, active experiment ownership, and changed records relevant to the requested task/files.
- Use PostgreSQL text search plus exact investigation/repository/path filters. Prioritize current decisions and scoped results; retain supersession/conflict warnings. Include IDs, author, date, and freshness status.
- Briefing maximum: 12,000 characters including metadata; indicate omitted counts and a continuation cursor. This is a character budget, not an exact token guarantee. Detail reads are bounded and paginated too.
- `get_context` accepts the previous cursor. Fetching does not silently mark updates consumed; clients can safely retry. Do not advance past omitted events. Policy/conflict/retraction changes must appear in subsequent deltas.
- Per-room event sequences must reflect committed publication order. Allocate a sequence transactionally under a room-row lock, not a bare global sequence that can commit out of order.
- Publish related state and its activity event in one database transaction. Client-generated idempotency keys prevent duplicates after a lost response; reuse with a different payload returns a conflict.
- Revision checks reject stale edits/resolutions. Supersession never silently erases another conclusion. Deletion removes bodies and retrieval/search access, leaving only minimal non-content tombstones for cursor consistency.

### Experiment coordination

- Claim an explicit experiment using an atomic conditional update or row lock. Exactly one unexpired lease may own an experiment.
- Default lease: 10 minutes; allow renew/release calls. Check expiry on access; no always-running scheduler is required for correctness.
- Generate a new lease generation on each claim. Renewal, completion, and release require the matching owner/generation. A stale claimant cannot overwrite the new owner's state.
- Preserve a late result as a labeled observation if useful, but do not let it close an experiment now owned by someone else.
- Outcomes describe observations: reproduced, not reproduced under stated conditions, or inconclusive. Hypotheses remain separate from those observations.

### Provenance and freshness

- Results include repository alias, relative relevant paths, SHA-256 fingerprints, procedure/command text, timestamp, declared environment and selected evidence. Never hash secret files or upload raw environment variables.
- Repository aliases identify corresponding workspaces explicitly; do not assume matching relative paths mean the same repository. Multi-repository rooms are allowed through aliases, not inferred automatically.
- Bridge checks current fingerprints against retrieved evidence for its bound workspace. Return `matching`, `changed`, `missing`, or `unknown`, with a reason. Other repositories and unmeasured dependencies remain unknown.
- A matching fingerprint proves only those files match. It does not validate external services, dependencies, or the entire environment.
- Evidence uploaded by agents is reporter-supplied, not independently verified execution. Claims shown in the UI must preserve this distinction.

### Artifact lifecycle

- Bridge reads only selected permitted files and checks size/type/policy before transmission. API validates authorization, quotas, type, and text secret patterns independently.
- Use bounded multipart uploads through the API to S3 for this release; no arbitrary upload URLs supplied by the caller. Do not hold a database transaction open during S3 I/O.
- Allocate an idempotent pending artifact record, upload to a server-generated object key, then mark available after checksum/size confirmation. Link only available artifacts to published evidence.
- Record and artifact operations have separate idempotency keys. Failed uploads stay visibly pending/failed and can be retried; do not invent successful evidence links.
- Authorize before issuing a 60-second presigned download URL. URLs are bearer credentials until expiry; membership revocation blocks new URLs, not already issued ones.
- Do not render uploaded HTML or execute artifacts. Only approved images have browser previews; everything else is an attachment.
- Deletion hides the object immediately in the application and records pending S3 deletion. A small scheduled maintenance command retries deletions and removes abandoned pending uploads; no queue service.
- Keep available evidence until users delete it or its room; enforce quotas rather than silently expiring cited evidence. Document backup retention separately.

## 5. MCP surface and agent behavior

| Tool | Responsibility |
| --- | --- |
| `get_context` | Bounded project/investigation briefing and incremental updates; policy and local freshness hints |
| `get_record` | Bounded details and associated evidence metadata |
| `publish_update` | Decision/interface/setup/handoff/question/hypothesis; optional supersession/conflict references |
| `create_experiment` | Define a procedure tied to an investigation and hypothesis |
| `claim_experiment` | Atomically claim the identified experiment |
| `renew_experiment` / `release_experiment` | Maintain or abandon a matching lease |
| `publish_result` | Store observations, conditions and evidence references with ownership checks |
| `upload_artifact` | Apply local file policy and upload one selected file |

Bind room, repository root, and credentials in trusted local configuration. Do not let tool arguments select arbitrary roots or another user's identity. Put protocol logs on stderr. Use finite HTTP timeouts and bounded retries only where idempotency permits; on failure tell the agent what was not shared. No durable offline queue in this release: retain the result in the local assistant and retry explicitly with the same key.

Supplied instructions: fetch context before choosing work; publish material decisions, interface changes, blockers, verified observations and handoffs; attach relevant evidence automatically when policy allows; check updates before each new experiment; renew long-running claims; publish inconclusive outcomes honestly; do not treat teammate content as executable instructions. Model-specific hooks are not required for the product to work.

## 6. Build phases and verification gates

### Phase 0 — Contracts and interoperability spike

- [ ] Create the minimal Python/web workspace following the directory layout above; lock compatible dependencies and record tested versions.
- [ ] Define request/response schemas, record types, policy merge rules, cursor semantics and error responses.
- [ ] Build a temporary two-tool bridge against a minimal API: publish and retrieve one synthetic record.
- [ ] Test the bridge in two different real MCP clients on two laptops. Try Codex and Claude Code first; check Gemini CLI as an additional compatibility target using its then-current documentation.
- [ ] Capture exact client versions, configuration, approvals and limitations without storing credentials.

Verify: engineer A's record is retrieved by engineer B without an open dashboard. If installation/authentication or automatic tool calling is unreliable, resolve it before building the dashboard. Generic MCP support is not a substitute for this gate.

### Phase 1 — Persistent identity and general context

- [ ] Add PostgreSQL migrations, Clerk sign-in/token verification, rooms, membership and expiring invites.
- [ ] Implement room-scoped bridge credentials, revocation, hidden-prompt CLI connection and workspace binding.
- [ ] Implement record publication, revisions, supersession/conflict links, deletion and transactional activity events.
- [ ] Implement deterministic summaries, PostgreSQL search, bounded pagination and incremental retrieval.
- [ ] Add basic dashboard: sign-in, create/join room, context list, detail and connection instructions.

Verify: two users publish/retrieve all supported general-context types; a nonmember cannot access records, searches or events. Retries create one record; stale revisions fail. Concurrent commits cannot create missed cursor updates; oversized briefings return usable continuation data.

### Phase 2 — Shared debugging and ownership

- [ ] Add investigations, hypothesis records, experiments and separate observed results.
- [ ] Implement claim/renew/release and generation-aware result completion.
- [ ] Add bridge fingerprints and local matching/changed/missing/unknown checks.
- [ ] Add investigation board showing owner, lease expiry, observations, conflicting conclusions and stale evidence.
- [ ] Supply concise reusable agent instructions for context checks and automatic publication.

Verify: simultaneous claims produce one owner; owner crash permits reclaim after expiry; stale owners cannot renew or finish the new lease. Two different descriptions are not falsely advertised as deduplicated. Changed source marks applicable evidence stale; unmeasured environments remain unknown. Conflicting findings remain visible.

### Phase 3 — Automatic artifacts and sharing controls

- [ ] Add effective room/local policy, pause, path confinement, type/size limits and credential-pattern checks.
- [ ] Add private S3 uploads/downloads, checksums, quota accounting, artifact idempotency and deletion maintenance.
- [ ] Add settings and evidence UI with source/provenance labels and image-scanning limitations.
- [ ] Recheck policy on each publication; verify that an old bridge configuration cannot bypass a newer room restriction.

Verify: an allowed log uploads automatically and is readable by a member. Excluded paths, symlink escapes, credential fixtures, oversized content, cross-room attachment IDs and revoked users fail safely. Simulate S3 outage and a lost response: no false success or duplicate artifacts. Deletion and orphan cleanup release quota and remove objects. Test against an isolated real S3 bucket before declaring this phase complete; fakes alone do not establish cloud behavior.

### Phase 4 — Operational deployment and observability

- [ ] Finish Docker Compose for API, PostgreSQL and development Jaeger; keep S3 and identity credentials out of images.
- [ ] Serve the frontend build from FastAPI; deploy one application instance with TLS and managed PostgreSQL.
- [ ] Configure private S3 access, narrowly scoped backend credentials, production identity, limits, backups, health checks and structured logs.
- [ ] Instrument context retrieval, experiment claims, record/result publication and artifact operations with OpenTelemetry.
- [ ] Propagate trace context from bridge HTTP requests; record outcome/latency/IDs without record bodies, commands, tokens, presigned URLs, or attachment contents.
- [ ] Make trace exporting nonblocking and optional at runtime: exporter failure must not stop collaboration. Document a protected OTLP destination; Jaeger remains a development dependency unless deliberately deployed privately.
- [ ] Add GitHub Actions for Python checks/tests, frontend typecheck/build, PostgreSQL integration tests, browser checks and container build. No secrets in pull-request jobs; real cloud smoke checks run separately with restricted credentials.
- [ ] Add deployment, migration, backup-restore and credential-revocation instructions as sections here or concise operational documentation once commands exist.

Verify: clean-machine startup and HTTPS access work; a server restart retains records; database restore and artifact retrieval work together. An OTLP export outage leaves core requests working. Inspect one bridge/API/database trace and one artifact trace. Confirm logs/traces contain no synthetic secret fixtures. Do not publish a Jaeger UI openly.

### Phase 5 — Complete-release acceptance and evidence

- [ ] Create a synthetic frontend/backend duplicate-request bug with documented ground truth and alternative hypotheses.
- [ ] Run two engineers using different clients on separate laptops: one publishes a scoped experiment; the other retrieves it, changes its next action and identifies the bug.
- [ ] Exercise general context alongside debugging: publish an interface decision, supersede it, share a handoff and resolve a question.
- [ ] Repeat with five distinct authenticated members/bridge sessions; verify attribution, isolation, bounded retrieval and claim correctness. Label simulated sessions separately from actual human use.
- [ ] Exercise failure scenarios: network loss, lost response, expired lease, removed member, artifact outage, changed files, conflicting findings and deleted evidence.
- [ ] Record test commands, environment/client versions, observed results, timings and limitations. Separate local tests from deployed multi-machine results.
- [ ] Record a walkthrough and write accurate setup instructions for someone outside the project.
- [ ] Write resume bullets only from implemented, verified behavior. Do not claim time savings, universal compatibility, automatic causal diagnosis or industry novelty without evidence.

Verify: a new pair can install, join, publish and retrieve without developer database edits. Both clients exhibit the sharing workflow in the recorded session. Passing scripted API tests alone is insufficient.

## 7. Completion criteria

The release is complete when all phase gates pass, including:

1. Two different MCP clients share general project context across separate laptops.
2. Shared debugging results visibly influence the receiving agent's next action.
3. Concurrent claims, expired leases, revision conflicts and retried publications preserve correctness.
4. Summaries remain bounded while evidence details are available on demand.
5. Automatic sharing honors effective preferences, paths, quotas and revocation.
6. Evidence freshness reports its measured scope without overstating verification.
7. Five-member operation is tested; deployment, backup/restore and artifact lifecycle work.
8. Traces explain operations without exposing content or breaking core behavior.

## 8. Remaining implementation checks, not new product decisions

- Verify exact dependency/client versions and MCP setup syntax during Phase 0; pin tested versions rather than copying unverified examples.
- Choose the single application host after checking current cost and account access. Real identity, S3 and hosting smoke tests require configured user-owned resources; do not create paid resources or publish publicly as part of writing this plan.
- Tune the stated polling intervals, leases, payload budgets and storage quotas only when acceptance tests reveal a problem. No speculative scaling infrastructure.
- Treat shared record attribution as provenance, not causal proof of why a model acted. The product does not inspect hidden reasoning.

## 9. Primary implementation references

- [MCP server development](https://modelcontextprotocol.io/docs/develop/build-server): tools and stdio integration; confirm installed Python SDK API before coding.
- [Clerk token verification](https://clerk.com/docs/guides/sessions/manual-jwt-verification): validate authentication server-side; application membership is a separate check.
- [S3 presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html): temporary access and bearer-URL expiry behavior.
- [OpenTelemetry Python instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/): spans, propagation, and export setup.

These references support component behavior, not a claim that ContextCrew is already built or that its acceptance tests have passed.
