# Architecture and operations

This document describes `feat/three-role-frontend`. [Product overview](../readme.md) · [Development guide](DEVELOPMENT.md) · [API reference](API_REFERENCE.md)

## Service architecture

RydeResolve separates the browser experience, API transport, case workflow, model runtime, policy controls, and persistence.

| Layer | Responsibility | Source |
|---|---|---|
| Next.js portals | Rider, driver, reviewer, execution monitor, and inspection dashboard | [Frontend routes](../frontend/src/app) |
| Server-side proxy | Fixed backend destination, controlled headers, optional Cloud Run OIDC token, sanitized transport errors | [Proxy](../frontend/src/app/api/proxy/%5B...path%5D/route.js) |
| FastAPI | Case access, evidence, clarifications, appeals, processing, and reviewer decisions | [API](../backend/app/main.py) |
| Case workflow | State transitions, notifications, audit events, review packets, and reviewed guidance | [Services](../backend/app/services.py) |
| Google ADK / Gemini | Structured agent recommendations and image observations | [Agents](../backend/app/agents.py), [runtime](../backend/app/gemini_runtime.py) |
| Policy control | Independent candidate calculation and eligibility gates | [Policy engine](../backend/app/policy_engine.py) |
| Persistence | Firestore records and Cloud Storage evidence; memory/local-file adapters for development | [Repository](../backend/app/repository.py), [storage](../backend/app/storage.py) |

The two service images are defined in [backend/Dockerfile](../backend/Dockerfile) and [frontend/Dockerfile](../frontend/Dockerfile).

## Decision authority

The routing index identifies candidate rules. The application retrieves authoritative rules and relevant precedents before model calls. The Dispute Orchestrator runs first, four specialist agents run concurrently within runtime limits, and the Judge runs last with advocate outputs and policy analysis.

The policy engine derives its own candidate from evidence. Automatic resolution requires policy eligibility, valid agent outputs, and a matching Judge recommendation. Financial amounts must agree within the implemented consistency tolerance.

The current eligibility envelope includes a valid team policy signoff, trusted synthetic fixture facts, complete and consistent evidence, and category/value rules. Values of SGD 10 or more and all route-deviation cases require review in this configuration. Safety, appeals, and unclassified intake have explicit review paths. Direct user reports remain allegations and are not automatically eligible.

Safety cases may receive constrained advisory summaries, but the Judge is skipped. Reviewer decisions are an explicit human decision path; the automatic eligibility gate governs automated actions.

## Runtime resilience and observability

The Gemini runtime provides:

- Two concurrent model calls per event loop.
- A 25-second attempt timeout, up to two attempts per configured model, and a 115-second request budget after acquiring a slot.
- A separate 115-second slot-acquisition timeout and a 240-second overall agent workflow timeout.
- Retry handling for transient failures and schema-validation errors.
- An optional `GEMINI_FALLBACK_MODEL`, with the chosen model and fallback use recorded.
- Structured diagnostics, attempt counts, latency, and sanitized error categories.

These are execution budgets, not response-time service targets. The orchestration schedules four specialists together while the limiter controls active calls. Incomplete or invalid outputs prevent automatic finalization.

The monitor derives workflow state from persisted case outputs and replays recorded traces. In-app delivery means an update is available in a linked recipient's portal; it does not indicate that the recipient has read it.

## Persistence, evidence, and repeat-safe actions

Firestore stores cases, simulated actions, learning proposals, and approved precedent records. Fixture seeding uses create-only writes. Simulated actions use a deterministic key based on case, revision, disposition, and amount; repeated identical actions reuse the stored receipt.

Evidence objects use content hashes and create-only object uploads. PNG, JPEG, and PDF files are checked for type, signature, and size. Successful evidence records are deduplicated by content hash. Gemini image observations describe pixels; capture origin and trip attribution are separate evidence questions.

Case events include the previous event hash and a SHA-256 hash of the current entry. This supports internal chain-consistency checks. An externally anchored immutable audit service is a separate deployment integration.

## Access model

The demonstration intentionally supports open role selection. The `X-Demo-Key` value resolves a demo identity; a missing or unrecognized value defaults to reviewer access. Role and case-ownership checks then control that selected identity's view. This mechanism supports demonstration navigation, rather than authenticating a real account.

Separately, `BACKEND_AUTH_MODE=cloud_run` enables service-to-service OIDC in the frontend proxy. Configure Cloud Run IAM so the frontend runtime service account can invoke the backend. Service identity and end-user identity serve different boundaries.

For an authenticated rollout, replace open role selection with verified user sessions and server-derived claims, and retain the existing ownership checks and filtered party responses.

## Cloud configuration

| Service | Setting | Purpose |
|---|---|---|
| Backend | `APP_MODE=firestore` | Durable case/action/precedent storage |
| Backend | `AI_MODE=adk` | Google ADK model execution |
| Backend | `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_GENAI_USE_VERTEXAI=TRUE` | Vertex AI project and location |
| Backend | `GEMINI_MODEL`, optional `GEMINI_FALLBACK_MODEL` | Primary and fallback model selection |
| Backend | `GCS_BUCKET` | Evidence bucket |
| Backend | `POLICY_SIGNOFF_PATH` | Approval record bound to the supplied policy contract |
| Backend | `ALLOWED_ORIGINS` | Allowed browser origins |
| Frontend | `BACKEND_URL` | Canonical backend URL |
| Frontend | `BACKEND_AUTH_MODE=cloud_run` | Google-signed backend identity token |
| Both | `PORT` | Container listening port |

Use runtime service identities with permissions for the configured resources. Keep credentials in deployment configuration. Select model and location values supported by the deployment project. A backend request timeout should accommodate the 240-second agent workflow budget; coordinate it with the frontend request path.

## Scaling roadmap

The service boundaries support independent evolution of the UI, workflow, and persistence. The following integration work defines the path from the shared demonstration to a larger operational rollout.

| Area | Current mechanism | Rollout work |
|---|---|---|
| Case retrieval | Collection reads with application-side filtering | Ownership/status indexes, bounded queries, cursor pagination, retention |
| Concurrent decisions | Whole-case writes; action-key deduplication | Versioned transitions or transactions spanning case state and action authorization |
| Model capacity | In-process limiter and bounded retries | Shared quota management, durable task queues, backpressure, cancellation and worker ownership |
| Records | Case documents include evidence metadata, traces, and events | Separate growing event streams, archival, document-size budgets, migrations |
| Identity | Open demo identity selector; optional service OIDC | Verified user identity, organization boundaries, reviewer permissions and access logging |
| Financial execution | Simulated ledger receipts | Authorized payment adapter, reconciliation, reversal/appeal semantics, external idempotency |
| Evidence | GCS objects and provenance metadata | Trusted source connectors, malware screening, capture attestation and retention policies |
| Notifications | Persisted in-app updates | External delivery adapters, retries, read acknowledgements and recipient preferences |
| Operations | Health contract, execution metadata and scenario reports | Load/capacity measurements, dashboards, alerting, queue targets and incident procedures |

These are implementation milestones. Throughput and latency targets should be set from workload measurements and the selected model quota.

## Policy and reviewed guidance

The supplied policy is version 2.1, indexed by 41 rule IDs. Team signoff is bound to its source hash and index version. [Policy review notes](POLICY_REVIEW_NOTES.md) record interpretations of challenge material; the approval scope is the synthetic demonstration.

After an eligible reviewer decision, the application stages a case-specific example, verifies its source decision, runs deterministic policy regression, and publishes it if the checks pass. This reuses reviewed context without modifying policy rules or model weights. Rollback removes guidance from active retrieval while retaining its history. Agent precedent lookup also excludes examples whose source case has been appealed.
