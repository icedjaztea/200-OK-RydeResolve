# Development and validation

These instructions target `feat/three-role-frontend`. [Product overview](../readme.md) · [Architecture and operations](OPERATIONAL_LIMITS.md) · [API reference](API_REFERENCE.md)

## Prerequisites

- Python 3.11.
- Node.js 22 and npm.
- Git.
- A Google Cloud project and application-default credentials for live ADK or cloud storage modes.

Clone the current application branch:

```bash
git clone --branch feat/three-role-frontend --single-branch https://github.com/icedjaztea/200-OK-RydeResolve.git
cd 200-OK-RydeResolve
```

## Start the backend

### Bash

From the repository root:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

### PowerShell

From the repository root:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Copy the environment template on first setup; preserve existing settings when resuming a configured checkout.

The template selects `APP_MODE=memory` and `AI_MODE=mock`. This provides an offline workflow with labelled fixture agent outputs. Startup seeds missing cases automatically. Restarting a memory-mode backend creates a fresh in-memory case store; local uploaded files remain under `backend/uploads/`.

The branch includes a team approval record for the supplied policy. `GET /health` reports policy integrity and signoff status. If policy sources change, review [POLICY_REVIEW_NOTES.md](POLICY_REVIEW_NOTES.md) and record an updated signoff using `scripts/signoff_policy.py` after the review.

## Start the frontend

In a second terminal, from the repository root:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

For PowerShell, replace the copy command with `Copy-Item .env.example .env.local`.

Open [http://localhost:3000](http://localhost:3000). The frontend sends API requests through its server-side proxy. The template sets `BACKEND_URL=http://127.0.0.1:8000`; local proxy mode is the default. API schemas are available at [http://localhost:8000/docs](http://localhost:8000/docs).

Role selection uses open demo identities. Rider/driver case views apply ownership filters for the selected identity. Trip histories are browser-local; cases use the configured backend repository.

## Enable live Gemini analysis

From an activated backend environment:

```bash
pip install -r requirements-cloud.txt
gcloud auth application-default login
```

Set these values in `backend/.env`:

```dotenv
APP_MODE=memory
AI_MODE=adk
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=your-supported-location
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GEMINI_MODEL=your-supported-model
GEMINI_FALLBACK_MODEL=
```

Choose a model and location available to your project. Restart the backend after changing configuration. The optional fallback model is used within the runtime's bounded retry budget, and its use is recorded in output metadata.

For Firestore and Cloud Storage, set `APP_MODE=firestore` and `GCS_BUCKET`, install the cloud requirements, and configure the runtime identity's resource access. See [cloud configuration](OPERATIONAL_LIMITS.md#cloud-configuration) for the frontend OIDC settings and service boundaries.

## Validation

### Backend and policy checks

From the repository root, with the backend virtual environment activated:

```bash
bash scripts/verify_all_local.sh
```

The script runs policy-contract integrity, pytest, deterministic reference scenarios, and prompt-injection boundary scenarios.

PowerShell equivalent, from `backend/`:

```powershell
$env:PYTHONPATH = '.'
.\.venv\Scripts\python.exe scripts/check_contract.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/evaluate.py
.\.venv\Scripts\python.exe scripts/threat_eval.py
```

### Frontend

From `frontend/` after `npm ci`:

```bash
npm test
npm run build
```

### Live ADK scenarios

Use a separate process with `AI_MODE=adk` and `APP_MODE=memory`. From `backend/`:

```bash
PYTHONPATH=. python scripts/live_eval.py --cases DISP-003
```

PowerShell:

```powershell
$env:PYTHONPATH = '.'
$env:APP_MODE = 'memory'
$env:AI_MODE = 'adk'
.\.venv\Scripts\python.exe scripts/live_eval.py --cases DISP-003
```

Omit `--cases` to run the script's default scenario set. Live evaluation makes model calls and writes timestamped JSON/CSV reports under `backend/reports/`, including scenario paths, policy citations, latency, and sanitized diagnostics. Interpret each result within its scenario set and configured model/runtime.

## Repository map

| Path | Contents |
|---|---|
| `frontend/src/app/` | Portals, monitor, dashboard, server-side proxy |
| `frontend/src/lib/` | Shared API access, appeals, timelines, attachments, trips, labels |
| `backend/app/` | API, workflow, agents, evidence, policy, persistence |
| `backend/policy/` | Supplied policy, structured rules, routing index, approval record |
| `backend/fixtures/` | Case fixtures, original source records, evaluation expectations |
| `backend/tests/` | Backend regression coverage |
| `backend/scripts/` | Policy checks, evaluations, seeding, signoff |
| `docs/` | Judge walkthrough, architecture, setup, API, policy notes |

The original build-from-zero guide is retained in [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) as historical project context. Use this document for the current branch's setup.
