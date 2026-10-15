# RydeResolve - Winning Hybrid Implementation Kit

**Status:** working offline policy/backend reference implementation; **live Google ADK, Firestore, GCS, Cloud Run, frontend npm build require your own environment and have not been verified here**. Synthetic data and mock refunds ONLY.

## Start here
Read `RydeResolve_Complete_Implementation_Guide.pdf` (delivered alongside the ZIP) or `docs/IMPLEMENTATION_GUIDE.md` within this kit. The guide gives every milestone's commands, checks, expected results, and recovery steps.

### 1. Local backend
```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=. python scripts/check_contract.py
PYTHONPATH=. pytest -q
PYTHONPATH=. python scripts/evaluate.py
# TEAM: review the eight source policy ambiguities before creating the approval file
PYTHONPATH=. python scripts/signoff_policy.py --reviewer TEAM --acknowledge I_REVIEWED_POLICY_AMBIGUITIES
uvicorn app.main:app --reload --port 8000
```

### 2. Seed synthetic demo cases (second terminal)
```bash
curl -X POST http://127.0.0.1:8000/cases/seed -H 'X-Demo-Key: change-reviewer-key'
curl -X POST http://127.0.0.1:8000/cases/DISP-003/process -H 'X-Demo-Key: change-rider-key'
```
**Expected:** DISP-003 recommends/refunds **SGD 4.50 simulated** if contract approval exists. DISP-001 (4.3 km deviation) escalates. DISP-002 (fraud flag) escalates.

### 3. Frontend (third terminal)
```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```
Open http://localhost:3000. Enter `change-reviewer-key` for LOCAL demonstration only; use secure random codes for cloud.

### 4. Run full offline test suite
```bash
bash scripts/verify_all_local.sh
```
The currently tested Python suite contains 24 tests plus 12 reference cases and 3 injection boundary scenarios. **These are not production safety or model accuracy measurements.**

### 5. Activate real Google ADK
```bash
cd backend
pip install -r requirements-cloud.txt
gcloud auth application-default login
# set GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION in backend/.env
# set AI_MODE=adk and APP_MODE=memory first
PYTHONPATH=. python scripts/live_eval.py
```
This performs real model calls. Do not label a mock run as a successful ADK integration.

## Architecture
Next.js UI -> FastAPI on Cloud Run -> Google ADK/Gemini agents + policy routing index -> deterministic Python safety and remedy gates -> mock financial ledger -> Firestore cases/precedents, GCS image evidence. Innovation A adds active evidence clarification. Innovation B adds reviewed correction, regression evaluation, approval and versioned precedent release.

## Policy contracts
- `backend/policy/04_rulebook.json`: candidate routing/search index, *not* authority to issue rulings.
- `backend/policy/02_policy_rules.json`: structured policy rules by exact IDs.
- `backend/policy/policy_v2.1.md`: original source policy (SHA-256 validated).
- `backend/policy/contract_approval.json`: generated only after explicit TEAM signoff; **not** Ryde's signature.

## Frontend implementation status
The supplied reviewer workbench includes a synthetic PNG/JPEG/PDF upload control and a reviewer-only precedent rollback button. These have not yet been verified by a Next.js build in the authoring environment; complete the frontend npm build and browser tests in the PDF before claiming them working.

## Safety and limitations
- No real Ryde telemetry/payment/notifications or accounts are connected.
- No live funds movement or account changes are implemented.
- User-submitted facts never qualify for automatic settlement merely because they are supplied.
- Safety cases cannot reach the Judge ruling step; reviewer receives the file.
- Canned image fixtures and EXIF do not prove trusted in-app camera origin.
- The demo passcode system is NOT production authentication.
- Firestore create-once mock actions provide action-key deduplication; concurrent case-state changes still need production transactions / locking.
- Model self-assessed confidence is NOT calibrated.

## Build and source-of-truth verification
The source policy is supplied as internal challenge material. The index is explicitly marked draft by its author. Document and team-approve policy ambiguities before the first auto-remedy. Public Ryde policies can differ; the supplied v2.1 challenge policy controls the synthetic prototype.

## Provenance
This code package was generated specifically for the Ryde track. See `docs/IMPLEMENTATION_GUIDE.md` for official Tencent handbook pages, Google docs URLs, testing evidence and exact release checklist.
