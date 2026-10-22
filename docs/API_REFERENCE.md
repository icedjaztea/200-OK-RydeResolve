# Backend API reference

This reference describes `feat/three-role-frontend`. [Product overview](../readme.md) · [Development guide](DEVELOPMENT.md) · [Architecture](OPERATIONAL_LIMITS.md)

Use the FastAPI schema at `http://localhost:8000/docs` for request models. Browser clients use the Next.js `/api/proxy/` route; the paths below are backend paths.

## Demo identities and access

The demonstration uses open role selection. Send `X-Demo-Key: rider_a`, `rider_b`, `driver_a`, `driver_b`, or `reviewer`. Configured environment-key matches are also accepted. Missing or unrecognized values default to reviewer access. This selector is for the shared demonstration, not real-account authentication.

Reviewer-only endpoints check the resolved role. Rider and driver reads filter by case ownership, and party detail responses omit reviewer-only material. Inaccessible case IDs return 404. The frontend proxy can additionally authenticate itself to Cloud Run using service OIDC; this is separate from the selected demo identity.

## Endpoints

“Case access” means a reviewer or a party linked to that case.

| Method and path | Access | Purpose |
|---|---|---|
| GET `/health` | Public | Runtime mode, policy contract, and team signoff state |
| GET `/policy/rules?ids=FA-3.1,FA-3.2` | Reviewer | Authoritative rule details by exact ID |
| GET `/cases` | Any demo role | Case summaries filtered for the selected identity |
| POST `/cases` | Any demo role | Create a report; party ownership is assigned server-side |
| POST `/cases/seed` | Reviewer | Create missing fixture cases without replacing existing cases |
| GET `/cases/{id}` | Case access | Role-filtered case detail, including linked appeals |
| POST `/cases/{id}/process` | Reviewer | Run evidence checks, agents, policy gate, and eligible simulated action |
| POST `/cases/{id}/appeals` | Linked rider or driver | Create or return that party's appeal of a resolved decision |
| GET `/cases/{id}/review-packet` | Reviewer | Consolidated investigation packet |
| POST `/cases/{id}/clarifications` | Reviewer | Ask a linked rider or driver a question |
| POST `/cases/{id}/clarifications/{request_id}/reply` | Intended linked party or reviewer | Record a party account and notify the reviewer |
| POST `/cases/{id}/evidence` | Reviewer | Record a synthetic corroborating fact with provenance |
| POST `/cases/{id}/files` | Case access; open case | Upload a PNG/JPEG/PDF, up to 5 MB, with optional image analysis |
| GET `/cases/{id}/files/{ref}` | Case access | Read an attachment referenced by the case |
| POST `/cases/{id}/review` | Reviewer | Save the human decision, simulated receipt, and guidance checks |
| POST `/cases/{id}/reclassify` | Reviewer | Reclassify an “Other” case and preserve the original category |
| GET `/cases/{id}/verify-audit` | Case access | Verify internal event-chain consistency |
| GET `/monitor` | Reviewer | Case workflow summaries and configured AI mode |
| GET `/learning` | Reviewer | Learning proposals and released precedents |
| POST `/learning/{id}/evaluate` | Reviewer | Evaluate a staged guidance proposal |
| POST `/learning/{id}/approve` | Reviewer | Release an evaluated, unchanged proposal |
| POST `/learning/{id}/rollback` | Reviewer | Remove released guidance from active retrieval, preserving history |
| GET `/evaluation/reference` | Reviewer | Deterministic reference-scenario results |

## Representative requests

These examples use Bash and local backend URLs. Replace case and request IDs with values from your case.

### Process a case

```bash
curl -X POST http://127.0.0.1:8000/cases/DISP-003/process \
  -H 'X-Demo-Key: reviewer'
```

An eligible completed result includes:

```json
{
  "case_id": "DISP-003",
  "path": "AUTO_ELIGIBLE",
  "candidate": {
    "disposition": "refund",
    "amount": 4.5,
    "rule_ids": ["FA-3.1", "FA-3.2", "FA-3.3-B", "FA-3.4", "FA-3.5"]
  },
  "status": "RESOLVED",
  "mock_action": {
    "status": "COMPLETED_SIMULATED",
    "simulated": true
  }
}
```

The full response includes evidence, gate details, outputs, and trace metadata. In live mode, invalid outputs or Judge-policy disagreement route the case to review.

### Request and answer a clarification

```bash
curl -X POST http://127.0.0.1:8000/cases/DEMO-FARE-CLARIFY/clarifications \
  -H 'Content-Type: application/json' -H 'X-Demo-Key: reviewer' \
  -d '{"recipient":"rider","question":"What fare notification appeared before you continued the trip?"}'

curl -X POST http://127.0.0.1:8000/cases/DEMO-FARE-CLARIFY/clarifications/REQUEST_ID/reply \
  -H 'Content-Type: application/json' -H 'X-Demo-Key: rider_a' \
  -d '{"answer":"I did not see a revised fare notification before continuing."}'
```

Use an existing pending request if one already exists for that recipient. Replies remain party accounts. Corroborating facts are recorded separately through the evidence endpoint:

```bash
curl -X POST http://127.0.0.1:8000/cases/DEMO-FARE-CLARIFY/evidence \
  -H 'Content-Type: application/json' -H 'X-Demo-Key: reviewer' \
  -d '{"field":"rider_notified","value":false,"provenance":"SIMULATED complete notification-event export"}'
```

All required facts must be supported; one evidence field alone may not complete the case.

### Appeal a resolved decision

```bash
curl -X POST http://127.0.0.1:8000/cases/DISP-003/appeals \
  -H 'Content-Type: application/json' -H 'X-Demo-Key: rider_a' \
  -d '{"reason":"Please reconsider the decision using the additional trip evidence I can provide."}'
```

The returned appeal has a deterministic ID for that decision and party, original-case context, inherited evidence, and a counterparty request when linked. Appeals require human review.

## State and response semantics

- `candidate`: the deterministic evidence-based proposal.
- `agent_outputs.Judge`: the model's recommendation, compared with the candidate before automatic resolution.
- `gate`: eligibility, blocking rules, and review reasons.
- `agent_trace`: stored execution metadata and outputs for inspection and replay.
- `mock_action`: the simulated action and repeat-safe receipt.
- `notifications`: recipient-specific in-app updates; “delivered” means available in the portal.
- `appeal_of`: the decision being reconsidered.
- `learning`: publication/check status for case-specific reviewed guidance.

Resolved cases accept new evidence through the appeal workflow. A repeated process request on a resolved case returns the stored result. Completed attachment uploads are deduplicated by content hash. Human review requires `REVIEW_REQUIRED`; an appeal with a pending counterparty request cannot be finalized.

## Errors

| Status | Meaning |
|---|---|
| 400 | Invalid state transition, unsupported evidence, or inconsistent request |
| 403 | Insufficient selected role or wrong clarification recipient |
| 404 | Missing or inaccessible case, proposal, or attachment |
| 422 | Request-schema validation error |
| 503 | Image analysis unavailable; retry the attachment while retaining the saved case |
| Proxy 400/500 | Invalid path or backend configuration |
| Proxy 502 | Backend transport unavailable |
| Proxy 503 | Cloud Run identity token unavailable; request was not forwarded |

Missing demo keys do not produce 401 in the open-access implementation. [Deployment identity requirements](OPERATIONAL_LIMITS.md#access-model) describe the boundary for an authenticated rollout.
