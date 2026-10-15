# RydeResolve Backend API Reference

All case data is synthetic. `GET /health` is public. Every other endpoint requires `X-Demo-Key` equal to a configured rider, driver or reviewer value. The caller's role derives from key matching, not an untrusted `role` header.

| Endpoint | Role | Purpose |
|---|---|---|
| GET `/health` | public | Runtime and policy contract state |
| POST `/cases/seed` | reviewer | Populate 12 curated synthetic cases |
| GET `/cases` | any keyed role | List cases |
| POST `/cases` | any keyed role | Submit synthetic allegations; automatically untrusted |
| GET `/cases/{id}` | any keyed role | Full case, evidence, traces, state |
| POST `/cases/{id}/process` | any keyed role | Run policy routing, investigation/ADK, gate and safe mock action |
| POST `/cases/{id}/clarifications/{request_id}/reply` | intended party or reviewer | Reply is an unverified allegation |
| POST `/cases/{id}/evidence` | reviewer | Import trusted synthetic system field, record provenance |
| POST `/cases/{id}/files` | reviewer | Multipart PNG/JPEG/PDF, maximum 5 MB, GCS/local storage and optional Gemini pixels only |
| POST `/cases/{id}/review` | reviewer | Human decision and idempotent mock action |
| GET `/cases/{id}/verify-audit` | reviewer | Verify internal SHA-256 event hash chain |
| GET `/learning` | reviewer | Staged correction and approved precedent lists |
| POST `/learning/{id}/evaluate` | reviewer | Run 12-case synthetic regression suite |
| POST `/learning/{id}/approve` | reviewer | Release corrected precedent after passing tests and manual rationale |
| POST `/learning/{id}/rollback` | reviewer | Roll back an approved precedent without deleting its historical record |
| GET `/evaluation/reference` | reviewer | Offline labeled reference evaluation (not model accuracy) |

### Example result, after signoff and processing DISP-003
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
  "mock_action": {"status": "COMPLETED_SIMULATED", "simulated": true}
}
```
The real response contains additional fields. Read `backend/app/models.py` and inspect FastAPI OpenAPI docs at `http://localhost:8000/docs` for generated request examples.

### Example clarification reply
```bash
curl -X POST "http://127.0.0.1:8000/cases/DEMO-FARE-CLARIFY/clarifications/REQUEST_UUID/reply" \
  -H 'Content-Type: application/json' -H 'X-Demo-Key: change-rider-key' \
  -d '{"answer":"I did not see an in-app surge notification"}'
```
This answer must not silently set `facts.rider_notified=false`. Reviewer must import corroborating synthetic source evidence separately.

### Example reviewer evidence import
```bash
curl -X POST 'http://127.0.0.1:8000/cases/DEMO-FARE-CLARIFY/evidence' \
  -H 'Content-Type: application/json' -H 'X-Demo-Key: change-reviewer-key' \
  -d '{"field":"rider_notified","value":false,"provenance":"SIMULATED complete notification event export"}'
```
Use a second call to verify `notification_log_complete=true`, then reprocess the case.

### API error handling
- 400: invalid state, malformed or inconsistent input, wrong file signature, missing signoff/unsafe action.
- 401: no/invalid key.
- 403: valid but insufficient role.
- 404: case/proposal not found.
- 502: frontend proxy cannot reach backend.
- 503: hosted-mode default demo passcode not changed.

### Response interpretation
- `agent_trace` is observable event/tool metadata. It is NOT a privileged model reasoning chain.
- `candidate` is the deterministic evidence-supported reference proposal; the Judge's text output is in `agent_outputs.Judge`.
- `gate` is the independent permission-to-auto-finalize decision; it can disagree with a Judge.
- `mock_action` is simulated; there is no payment API.
- `source_trust` is either curated synthetic system fixture or unverified user report.
