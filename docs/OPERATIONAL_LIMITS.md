# Prototype limitations and next-production integration steps

| Area | This implementation | Production integration still needed |
|---|---|---|
| Data | 12 curated synthetic cases; original DISP-001/2/3 source fixtures stored separately | Ryde connectors, permissioning, retention, source reconciliation |
| Agent reasoning | Google ADK LlmAgent source code; offline `AI_MODE=mock` runnable | Live Gemini/ADK smoke tests, latency and model validation |
| Storage | Firestore adapter, local memory fallback | Firestore indexes, transactions for all concurrent case transitions, migrations |
| Images | Private GCS/local file store, signature/size validation; optional Gemini pixel description | Trusted in-app camera capture attestation, malware scan, privacy policy |
| Payment | Idempotent MOCK ledger action | External financial ledger integration with authorization and reconciliation |
| Auth | Separate demo passcodes by role | Firebase Auth/Identity Platform, true per-user claims and fine-grained IAM |
| Trace | Hash-linked event list stored with case | External immutable/tamper-evident audit sink and trusted clock |
| Notifications | Status and simulated outbox records | Secure in-app/webhook delivery, retry, timeout, opt-in contact rules |
| Learning | Human correction -> 12-case regression -> approved precedent record | Signed PR/release, independent domain review, rollback, monitoring |
| Policy | Supplied v2.1 and 41-ID draft routing index with team signoff | Ryde formal validation of ambiguous thresholds and confidence calibration |
| Safety | Conservative mandatory escalation | Dedicated 24/7 human safety operating procedure and actual access controls |
| SLA | Safety/high-value priority classes, no numeric SLA invented | Operationally approved service targets and queue management |

No user data, keys, signatures or private interviewer messages should be published in a public repository or demo without permission. Source policy is challenge-specific reference; do not claim that it is Ryde's live production policy.
