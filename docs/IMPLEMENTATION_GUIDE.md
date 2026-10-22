# Historical build-from-zero implementation guide

> **Historical reference — 14 October 2026.** This document preserves the original implementation plan and its status at that time. For the current `feat/three-role-frontend` application, use the [development guide](DEVELOPMENT.md), [architecture and operations](OPERATIONAL_LIMITS.md), and [API reference](API_REFERENCE.md). Judges can start with the [product overview](../readme.md) or [guided walkthrough](JUDGE_WALKTHROUGH.md).

**Google ADK + Gemini + Firestore + Google Cloud Storage + Cloud Run + FastAPI + Next.js**  
**Covers:** all 3 mandatory agents, 7 Ryde stretch capabilities, Innovation A (active investigation), Innovation B (governed learning), evaluation, cloud deployment and submission.  
**Prepared:** 14 October 2026 (Singapore time). **Challenge submission:** 16 October 2026 at 23:59 SGT, per organizer WhatsApp post dated 9 October.  
**Audience:** engineers starting with an almost-empty repository. **No task owner names.**

> **Read first:** This is a two-part implementation deliverable: (1) this illustrated, printable guide and (2) the accompanying `RydeResolve_Implementation_Kit.zip`. The ZIP contains executable reference files for the complete synthetic prototype; live Google integrations still require the listed verification gates. Never retype 1,000 lines of code from a PDF: unzip and follow these commands instead. The companion package contains the named source files and core APIs; cloud resources, project-specific credentials and services must be created as described, and command placeholders replaced. The guide is your operating manual; the package is the code you deploy.

> **Verification status:** I verified the policy conversion/source hash, 41 policy IDs ↔ 41 routing index IDs, backend startup, real HTTP health/seed/process behavior, 24 local Python tests, the separate 12-case deterministic reference evaluation and 3 synthetic policy-injection checks. **Not yet verified:** a live ADK/Gemini call, Firestore/GCS cloud credentials, frontend Next.js build, or Cloud Run deployment. You must run the explicit verification gates below. Do not call an untested integration working.

## 0. Read this first - how to follow the manual

**Rule 1: Do not skip PASS gates.** Complete each step in order unless marked *independent*; capture terminal results/screenshot as evidence. If a test fails, follow its fix procedure before proceeding. Use the `PASS/FAIL` ledger in Appendix E to track status.

**Rule 2: This is a synthetic prototype, not a Ryde production integration.** Trip, route, traffic, fare, message, image and payment data are synthetic or local mock adapters. The mock financial ledger never contacts a bank. Model output never authorizes a payment or account action.

**Rule 3: Policy authority is hierarchical.** `04_rulebook.json` is an INDEX to discover candidate rules; `02_policy_rules.json` is the structured rule source and contains full sections copied from `policy_v2.1.md`; a separate Python policy gate makes the final permission decision. Similar-case precedent never overrides mandatory safety or human review.

**Rule 4: Keep Git history usable.** Commit after each completed stage, avoid introducing services that have no demo payoff, and reserve final time for end-to-end integration, evaluation and submission.

**Rule 5: Distinguish three run modes.** (A) `APP_MODE=memory, AI_MODE=mock` = deterministic offline test and UI scaffolding; (B) `APP_MODE=memory, AI_MODE=adk` = live Google model agent integration without cloud storage; (C) `APP_MODE=firestore, AI_MODE=adk` = Google Cloud full stack. A mock trace is clearly marked `MOCK_NOT_MODEL_OUTPUT`.

### 0.1 Final architecture at a glance

```text
NEXT.JS USER INTERFACE (Rider / Driver / Reviewer / Trace)
               |
        NEXT.JS SERVER PROXY  (no browser-to-backend CORS dependency)
               |
          FASTAPI ON CLOUD RUN  -- demo role passcodes, case APIs, events
               |
       DISPUTE MANAGER / PYTHON ORCHESTRATOR
          |              |             |
   04_rulebook.json   Safety Screen   Priority Router
   (candidate IDs)       |             |
          |          mandatory     P0 safety / P1 / P2
   02_policy_rules   human gate
    (full rule IDs)
          |
   EVIDENCE COLLECTION / PROVENANCE / FIRESTORE / GCS
          |
   PARALLEL GOOGLE ADK AGENTS: Rider, Driver, Policy/Precedent, Fraud
          |
   JUDGE ADK AGENT reads same rulebook + policy tools
          |
  INNOVATION A: missing/conflicting evidence -> specific question
                -> persisted pending state -> reply/evidence -> rerun
          |
 DETERMINISTIC PYTHON POLICY VALIDATOR (independent of Judge)
         / \
       AUTO     REVIEWER WORKBENCH (safety, high-value, fraud flag,
       |          uncalibrated confidence, disputed damage, uncertainty)
       \          /
      IDEMPOTENT SIMULATED REMEDY + RECEIPT + AUDIT TRAIL
                   |
   INNOVATION B: review correction -> staged precedent -> regression
                 tests -> explicit approval -> versioned publication
                   |
       FIRESTORE CASES / ACTIONS / APPROVED PRECEDENTS
       GOOGLE CLOUD STORAGE FOR PRIVATE IMAGE DOCUMENTS
       GITHUB ACTIONS / PYTEST / CODEBUDDY DEVELOPMENT PROOF
```

### 0.2 Why this approach is appropriate to the rubric

Tencent's handbook (general handbook pp. 21-25, 35-39; Ryde-specific pp. 4-8, 9-13) requires Rider Advocate, Driver Advocate, Judge, at least two complete categories, observable agent interaction, a prototype/demo and GitHub source. Seven bonus capabilities are evidence collection, parallel fraud detection, policy/precedent, image analysis, escalation, learning feedback and SLA/routing. Submission eligibility requires genuine CodeBuddy OR WorkBuddy usage with at least 3 development conversation-history screenshots. ADK is allowed; ADP is **not mandatory**. The separate 10 × 10 published rubric is only a general guide; a detailed track-specific preliminary rubric was not supplied.

### 0.3 What is supplied and what must be created

| Source | Path in kit | Authority / limitations |
|---|---|---|
| RydeResolve Policy v2.1 | `backend/policy/policy_v2.1.md` | Supplied challenge policy, effective 1 Jan 2026. Not identical to all public terms. |
| Structured rules | `backend/policy/02_policy_rules.json` | 41 rules, `runtime_approval_status=PROPOSED_UNTIL_TEAM_CONTRACT_SIGNOFF`. |
| Rule routing index | `backend/policy/04_rulebook.json` | 41 matching IDs, `status=DRAFT_TEAM_CONTRACT_REVIEW`, candidate lookup only. |
| Original synthetic examples | `backend/fixtures/source/DISP-001.json`, `DISP-002.json`, `DISP-003.json` | Source examples may contain `recommended_ruling`, which must NOT be passed to an agent. |
| Clean normalized demo records | `backend/fixtures/cases/*.json` | 12 evidence-driven, synthetic operational cases. The source is disclosed as a simulated verified feed for these curated cases only. |
| Test answers | `backend/fixtures/evaluation/gold.json` | Evaluation-only. NEVER provide this file or its target labels to ADK. |
| Python backend and ADK integration | `backend/app/*.py` | Locally tested in mock mode; live integration requires Google credentials. |
| Next.js app | `frontend/src/app/...` | Source supplied; npm installation/build remains for your Mac to verify. |

### 0.4 Must-not-ship failures

- Any safety indicator routed through an AI ruling or account suspension tool.
- A route deviation greater than 2 km auto-finalized because the refund is small.
- A flagged rider case auto-finalized using a model's uncalibrated “95% confidence”.
- A disputed damage claim auto-finalized despite policy §4.4.
- A refund executed twice after duplicate API calls, or a supposed refund without a simulated receipt/status.
- A missing chat/call/notification record treated as a proven negative without source-completeness check.
- Any system claiming live ADK/GCS/Firestore success when only mock mode was tested.
- A missing CodeBuddy/WorkBuddy development record: organizers say projects without proof do not proceed to scoring.

### 0.5 Target development environments

- macOS laptop, Terminal/zsh, Git, CodeBuddy desktop IDE, Python 3.11 (recommended), Node.js 22, npm, Google Cloud CLI, a Google Cloud project with billing, permission to enable services, and supported Vertex AI model access.
- For local mode, no Google API key, credit card, cloud bucket or Firestore instance is needed.
- For hosted mode, create and set your own billing-budget alert. Never commit `.env`, secrets or real rider/driver data.

---

# Phase A - Repository and local development environment

## A.0 Gate: Read prior source warnings

Before writing code, agree that the policy v2.1 is the **challenge prototype authority**, the converted JSON/index are DRAFT until team review, all Google integrations must be explicitly tested, the demo uses *only* synthetic data, and you need screenshots of CodeBuddy development. Do not claim actual Ryde payment API access.

## Step 01 - Clone and inspect the actual repository (P0)

**Dependency:** Independent. **Goal:** begin from the confirmed repository rather than assumptions about missing code.

1. Open Terminal. Run `pwd`; choose your regular projects folder. Do NOT work inside a temporary Downloads ZIP folder after unzipping.
2. `git clone` the shared project; enter it. Do not create another remote repository.
3. Run `git status`, `git branch --show-current`, and `find . -maxdepth 2 -type f | sort | head -80`.
4. Open the folder with CodeBuddy. Confirm CodeBuddy can show the Git repository. Keep the editor chat visible when implementing so you can capture authentic product-usage evidence.
5. If the remote has advanced after this guide was generated, compare the new files with the kit; do NOT blindly overwrite work. For the initial inspected default branch, the repository contained only a 13-byte `readme.md`.

```bash
mkdir -p ~/Projects && cd ~/Projects
git clone https://github.com/icedjaztea/200-OK-RydeResolve.git
cd 200-OK-RydeResolve
git status
git branch --show-current
find . -maxdepth 2 -type f | sort | head -80
```

**PASS:** current branch and `git status` display without errors; all current files are understood. **If it fails:** check GitHub permissions, login, correct URL and network. **Evidence:** capture terminal inventory, Git remote and screenshot showing the CodeBuddy project.

## Step 02 - Copy the complete implementation kit into the repo (P0)

**Dependency:** Step 01. **Goal:** avoid typing hundreds of source lines and broken imports.

1. Download `RydeResolve_Implementation_Kit.zip` from the accompanying link and unzip it in Finder, or use `unzip`.
2. Copy **the contents** of `RydeResolve_Implementation_Kit` into the cloned `200-OK-RydeResolve` directory (do not accidentally create `200-OK-RydeResolve/RydeResolve_Implementation_Kit/backend`).
3. Check that `backend/app/main.py`, `backend/policy/04_rulebook.json`, `frontend/src/app/page.jsx`, `.github/workflows/ci.yml`, `scripts/verify_all_local.sh` exist at those exact paths.
4. Do not copy your actual `.env` into source control; no `.env` is supplied, only `.env.example`.
5. Read `README.md` and check this guide is present under `docs/IMPLEMENTATION_GUIDE.md`.

```bash
# Example after extracting the ZIP at ~/Downloads/RydeResolve_Implementation_Kit
rsync -av ~/Downloads/RydeResolve_Implementation_Kit/ ./
find backend/app -maxdepth 1 -type f | sort
find frontend/src/app -maxdepth 4 -type f | sort
git status --short
```

**PASS:** required files exist in the correct relative locations. **If it fails:** inspect whether an extra nested directory was introduced; fix paths before running code. **Evidence:** tree screenshot and `git status`.

## Step 03 - Check and install macOS tooling (P0)

**Dependency:** Independent (parallel with Step 01). **Goal:** eliminate PATH and Python version errors early.

1. Run version checks; prefer Python 3.11 instead of your Mac system Python 3.13 when starting a new ADK project, because dependency ranges can behave differently.
2. Install the missing tools from their official providers: Homebrew, Python 3.11, Node 22, Google Cloud CLI, Git and Docker Desktop (Docker optional for local tests but useful for deployment parity).
3. Restart Terminal after installing. `which python3.11`, `which node`, `which gcloud`, `which git` must resolve.
4. Ensure `python3.11 -m pip --version` uses the same interpreter as `python3.11`.
5. Check disk space (`df -h .`) and Internet access (`git ls-remote` against the repo). Large model/cloud dependencies may need several GB.

```bash
python3.11 --version
node --version
npm --version
git --version
gcloud --version
which python3.11 node npm git gcloud
```

**PASS:** Python 3.11, Node, npm, Git and gcloud are installed; versions are printed. **If it fails:** on macOS install the missing commands via Homebrew / official installers, reopen terminal, confirm PATH. **Evidence:** environment-versions transcript.

## Step 04 - Create isolated Python environment (P0)

**Dependency:** Steps 02-03. **Goal:** reproducible Python installation without changing global packages.

1. `cd backend`; create `.venv` with Python 3.11 and activate it in this terminal session.
2. Confirm `python --version` and `which python` point to `.venv/bin/python`.
3. Upgrade `pip` and install `requirements.txt` for **offline** mode. Do **not** install cloud/ADK packages until the offline behavior works.
4. Copy `.env.example` to `.env`. Read it: the default starts `APP_MODE=memory`, `AI_MODE=mock`, `ALLOWED_ORIGINS=http://localhost:3000`.
5. Close and reopen a terminal to confirm you remember to reactivate `.venv` each time.

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
python --version
python -c 'import fastapi, pydantic, pytest; print("basic imports OK")'
```

**PASS:** `basic imports OK`; `.env` exists locally; `.gitignore` prevents committing it. **If it fails:** delete and recreate `.venv` using Python 3.11; check certificate/proxy issue if pip cannot reach package index. **Evidence:** pip output and import line.

## Step 05 - Inspect root configuration and conventions (P0)

**Dependency:** Step 04. **Goal:** understand files before making modifications.

1. Read `backend/app/config.py` to see how root paths, mock/cloud modes and signoff are selected.
2. Read `backend/app/models.py` to understand `CaseCreate`, `ClarificationReply`, `EvidenceUpload`, `ReviewerDecision` and `LearningApproval`.
3. Read `backend/app/repository.py`: memory adapter supports offline tests, Firestore adapter persists cases, actions, learning proposals and precedents.
4. Read `backend/app/main.py`: the HTTP routes and their authorization gates.
5. Read `frontend/src/app/api/proxy/[...path]/route.js`: same-origin browser requests are relayed to FastAPI; frontend alone does not authorize case review.
6. Do not rename files arbitrarily. The guide uses these paths to explain exact commands and expected imports.

```bash
cd backend
find app -maxdepth 1 -type f | sort
python -m compileall -q app scripts
```

**PASS:** `compileall` exits successfully; you can point to policy, storage, agents, service, evaluation and API modules. **If it fails:** restore the exact file tree from the ZIP and rerun from `backend` with `PYTHONPATH=.`. **Evidence:** source tree and import pass.

## Step 06 - Check policy provenance and 41-rule index mapping (P0)

**Dependency:** Step 04. **Goal:** prove that the files just uploaded are actually identical in authority and lookup coverage.

1. Open `backend/policy/policy_v2.1.md`. This is the supplied source policy. The challenge edition is effective 1 January 2026.
2. Inspect `02_policy_rules.json`: `structured_rules` have exact rule IDs, conditions/effects, source sections and implementation ambiguities.
3. Inspect `04_rulebook.json`: `rule_entries` provide descriptions, search phrases, candidate conditions, evidence names and `read_full_rule_from=02_policy_rules.json`.
4. Run contract validator, which recomputes SHA-256 of the source Markdown, checks uniqueness, exact 41↔41 ID equality, version, and source reference.
5. Explain the contract aloud: `04_rulebook` selects *candidates*; `02_policy_rules` returns the full selected objects; Python decides whether observed evidence proves a rule condition. No JSON `condition` string is evaluated with Python `eval()`.

```bash
cd backend
PYTHONPATH=. python scripts/check_contract.py
python - <<'PY'
from app.policy import contract_report,load_rulebook,full_rules
r=contract_report();print(r)
print('Sample candidates:',full_rules(['FA-3.3-B','TH-6.3']))
assert r['valid'] and r['rule_count']==41
PY
```

**PASS:** `valid:true`, 41 rules in each file, matching `source_sha256=827c4d2cab2d4db9e176521000b079632bbe80c20f69c3ffd0addecc8cbc8699`. A missing signoff is *expected* at this stage. **If it fails:** do not suppress mismatch; compare sources, restore the supplied versions and investigate. **Evidence:** validator output.

## Step 07 - Review the policy's eight documented ambiguities (P0)

**Dependency:** Step 06. **Goal:** agree what the prototype may safely automate, without silently inventing policy.

1. Open `02_policy_rules.json` → `implementation_ambiguities` and `04_rulebook.json` → `source_ambiguities`. Both list AMB-01 through AMB-08.
2. Create `docs/POLICY_REVIEW_NOTES.md` and copy the IDs, actual issue, chosen handling and any unresolved questions. Do not edit the authoritative source policy to force a desired outcome.
3. Check AMB-01: DISP-002 mentions an eight-minute event but the policy counts five free minutes from **scheduled pickup**; use the policy anchor and treat the eight-minute app event as dataset-specific.
4. Check AMB-02: a rider-disputed damage case requires review under §4.4 despite the cleaning eligibility table in §6.2.
5. Check AMB-03/08: fixed SGD 5 no-show and under-$10 rules coexist with fraud flag ≥1 requiring 95%; there is no calibrated confidence model supplied. Escalate flagged cases rather than trusting an LLM's number.
6. Check AMB-04: no per-km fare tariff is supplied, so use a verified fare breakdown only.
7. Check AMB-05: before no-show cancellation require **both** one chat message and one in-app call.
8. Check AMB-06/07: no account action without authorized human review, and unknown dispute-value basis goes to review.
9. Confirm which outcomes are auto-eligible for our **synthetic** tests: DISP-003's documented SGD 4.50 unnotified surge refund is eligible, while DISP-001 is >2 km and DISP-002 has fraud flag 1 so both require human review.

**PASS:** all eight IDs have a written safe interpretation; no open ambiguity can bypass mandatory review. **If it fails:** select the conservative human-review path and mark the policy interpretation unresolved. **Evidence:** `docs/POLICY_REVIEW_NOTES.md` committed.

## Step 08 - Explicitly sign off the draft conversion contract (P0)

**Dependency:** Steps 06-07. **Goal:** enable only team-reviewed prototype auto-decisions.

1. Run the signing script only after completing the ambiguity review. Choose a non-personal reviewer label such as `TEAM_REVIEWED`.
2. The script creates `backend/policy/contract_approval.json` containing policy source hash, version, rulebook version, timestamp and team-review acknowledgment. This is **NOT** official Ryde approval.
3. Rerun `scripts/check_contract.py`. Its `team_signoff_valid` field should now be true.
4. Do not manually set `runtime_approval_status` in the supplied JSON to `APPROVED`; its historical draft status is useful provenance. The separate approval file is your controlled implementation decision.
5. Commit the nonsensitive contract record with the code so Cloud Run can verify the exact same version. A change to either policy source hash or routing-index version must invalidate the approval.

```bash
cd backend
PYTHONPATH=. python scripts/signoff_policy.py \
  --reviewer TEAM_REVIEWED \
  --acknowledge I_REVIEWED_POLICY_AMBIGUITIES
PYTHONPATH=. python scripts/check_contract.py
cat policy/contract_approval.json
```

**PASS:** `team_signoff_valid:true`, no mismatched source hash, signoff file committed to the repo. **If it fails:** re-run source validator and review again; do not hardcode “approval=true” in service code. **Evidence:** contract JSON and validator screenshot.

## Step 09 - Run the local backend's offline test gate before adding AI (P0)

**Dependency:** Steps 04-06; Step 08 is not required for unit tests because tests use an isolated test-only signoff fixture.

1. Run `bash scripts/verify_all_local.sh` from the project root.
2. Observe four phases: contract integrity, pytest, 12-case reference evaluation, and adversarial-string boundary checks.
3. Inspect test source in `backend/tests/test_policy.py` and `test_api.py`; never remove a failing safety case simply to get green CI.
4. If a test fails, read its failing assertion and identify whether the underlying policy/routing data changed, the input fixture was malformed, or application behavior regressed.
5. Capture the terminal output and an authentic CodeBuddy chat screenshot from any real editing/debugging assistance.

```bash
cd 200-OK-RydeResolve    # if not already at repo root
bash scripts/verify_all_local.sh
```

**PASS:** `pytest` passes, the independent 12-case suite reports `all_passed:true`, and all three synthetic prompt-injection checks print PASS. **If it fails:** see Appendix D troubleshooting and run the failing script individually from `backend` with `PYTHONPATH=.`. **Evidence:** saved terminal transcript and CI screenshot later.

---

# Phase B - Data contracts, Firestore model, and evidence storage

## Step 10 - Inspect original Ryde sample fixtures without leaking their answers (P0)

**Dependency:** Step 02. **Goal:** use sample data as evidence, not as instructions to agents.

1. Open `backend/fixtures/source/DISP-001.json` and identify rider allegation, driver route, traffic incidents, chat and fare decomposition.
2. Open `DISP-002.json`: identify scheduled pickup 08:45, driver arrived 08:43, cancellation 08:51, four messages, one call, and one historical fraud flag. The eight-minute platform event is a sample observation, not a new policy rule.
3. Open `DISP-003.json`: quote SGD 12, actual SGD 16.50, new surge 1.5×, `rider_notified:false`, difference SGD 4.50. Confirm the fare difference is solely surge-related for this example.
4. Do **NOT** include the original `recommended_ruling`, `ruling_rationale`, `expected_ruling` or known `recommended_refund_amount` fields in ADK prompts. They are used only to form separate evaluation labels.
5. Inspect `backend/fixtures/cases/`: 12 curated normalized records are what the actual demo API seeds. `backend/fixtures/evaluation/gold.json` must never be passed as `case` input to any agent.
6. Note the distinction between evidence reported in original synthetic examples and evidence that would need genuine Ryde verification in production.

```bash
cd backend
python - <<'PY'
import json
from pathlib import Path
for p in sorted(Path('fixtures/cases').glob('*.json')):
 d=json.loads(p.read_text());print(d['case_id'], d['category'], d['dispute_amount'], d['source_trust'])
PY
```

**PASS:** 12 distinct synthetic case IDs and the separate answer file; no agent code imports `fixtures/evaluation/gold.json`. **If it fails:** restore fixtures from ZIP, search agent code for `gold`/`expected_ruling`, and remove leakage. **Evidence:** fixture inventory screenshot.

## Step 11 - Understand the case JSON schema and state machine (P0)

**Dependency:** Step 10. **Goal:** make new APIs and UI use one source-of-truth schema.

1. Read `app/models.py`, `app/services.py` and a normalized fixture such as `DISP-003.json`.
2. Case top-level fields: `case_id`, `trip_id`, `category`, `filed_by`, `description`, `dispute_amount`, `dispute_value_basis`, `facts`, `fraud_flags`, `source_trust`, `evidence`, `status`, `revision`, `events`, `clarifications`.
3. `source_trust=SIMULATED_VERIFIED_SYSTEM_FIXTURE` applies **only** to the curated synthetic demo source adapters. `POST /cases` supplied by a rider is forced to `UNVERIFIED_USER_REPORT`, regardless of caller-provided facts.
4. Status transitions: `NEW -> AWAITING_CLARIFICATION -> NEW/REVIEW_REQUIRED`; `NEW -> REVIEW_REQUIRED -> REVIEWED_AND_RESOLVED`; `NEW -> RESOLVED` for eligible routine simulated outcomes. Replaying a resolved case returns the saved outcome.
5. `routing` contains candidate IDs; `candidate` contains deterministic supported action suggestion; `agent_outputs` contains ADK or mock agent text; `gate` contains independent permission decision; `mock_action` contains payment simulation receipt.
6. Keep financial values numeric and round via `Decimal` in `policy_engine.py`, not raw float arithmetic for production money. The demo currently stores SGD floats in JSON, so avoid expanding it into a real ledger.

```json
{
  "case_id":"DISP-003", "category":"fare_dispute", "dispute_amount":4.50,
  "dispute_value_basis":"amount_in_dispute",
  "facts":{"upfront_quote":12.0,"actual_fare":16.5,"surge_before":1.0,
  "surge_after":1.5,"rider_notified":false,"notification_log_complete":true,
  "difference_solely_surge":true},
  "source_trust":"SIMULATED_VERIFIED_SYSTEM_FIXTURE"
}
```

**PASS:** API, repository and UI agree on field names and state transitions; a new user allegation cannot become auto-authorized. **If it fails:** debug `app/models.py` validation and `app/policy_engine.py` trust gate, not by editing fixture gold labels. **Evidence:** normalized schema diagram or fields table in README.

## Step 12 - Run in-memory repository before Firestore (P0)

**Dependency:** Steps 04, 11. **Goal:** prove complete backend flow without cloud accounts.

1. Keep `.env` as `APP_MODE=memory, AI_MODE=mock`, and ensure the team policy signoff file exists if testing autonomous finalization.
2. From `backend`, run `uvicorn app.main:app --reload --port 8000`. Leave this terminal running.
3. In a second terminal, run the health command and confirm `policy_contract.valid=true`, `team_signoff_valid=true`, `storage_mode=memory`, `ai_mode=mock`.
4. Seed the 12 demo cases by HTTP, **not** by running a separate `python scripts/seed.py` process; an in-memory store in a separate process cannot seed the running Uvicorn process.
5. List the cases, process DISP-003, and compare the returned `candidate`, `gate`, `path`, `mock_action`.
6. Run the same process request again and verify the same `MOCK-` receipt appears rather than a new financial event.

```bash
# Terminal 1: from backend, with .venv activated
uvicorn app.main:app --reload --port 8000
# Terminal 2
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
curl -s -X POST -H 'X-Demo-Key: change-reviewer-key' http://127.0.0.1:8000/cases/seed
curl -s -H 'X-Demo-Key: change-rider-key' http://127.0.0.1:8000/cases
curl -s -X POST -H 'X-Demo-Key: change-rider-key' http://127.0.0.1:8000/cases/DISP-003/process | python3 -m json.tool
```

**PASS:** health responds 200, seed returns `created:12` on the first run, DISP-003 returns `AUTO_ELIGIBLE` + a `COMPLETED_SIMULATED` SGD 4.50 refund if signed off. **If it fails:** default role key mismatch → inspect `.env`; port conflict → choose 8001 and update proxy; missing policy approval → Step 08; cloud imports requested unexpectedly → verify `APP_MODE=memory`. **Evidence:** HTTP requests and response screenshot.

## Step 13 - Create and protect Google Cloud project and billing (P0 for hosting, parallelizable)

**Dependency:** Independent after local development begins. **Goal:** unlock Firestore, GCS, Cloud Run and Vertex AI before deployment day.

1. In Google Cloud Console select an existing approved project or create a project dedicated to the hackathon. Record its **project ID** (not display name).
2. Confirm a billing account is linked. Set a budget alert with a low amount appropriate for the team. Do not assume free tiers or free credits apply in every region/account.
3. `gcloud auth login` using authorized Google account; set the selected project and confirm output.
4. Enable Firestore, Cloud Storage, Vertex AI, Cloud Run, Cloud Build, Artifact Registry and Secret Manager APIs. Some organizations require an admin to grant permissions.
5. Pick Singapore for Cloud Run/Firestore/storage when supported (`asia-southeast1`) and choose a model-supported Vertex AI location (often `us-central1`; verify access). Cross-region model calls can affect latency/privacy; disclose the setup.
6. No service-account JSON file should go into GitHub. Use Application Default Credentials locally and a Cloud Run service identity when deployed.

```bash
export PROJECT_ID='REPLACE_WITH_YOUR_GCP_PROJECT_ID'
gcloud auth login
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com firestore.googleapis.com \
  storage.googleapis.com aiplatform.googleapis.com \
  secretmanager.googleapis.com

gcloud config get-value project
```

**PASS:** the expected project ID prints; API enable commands succeed; billing is confirmed in console. **If it fails:** diagnose account permissions, billing/project restrictions, region/model access, or quota. **Evidence:** console project info, gcloud project output and budget alert screenshot (no billing card details).

## Step 14 - Create Firestore Native database and connect locally (P0 for Google Cloud mode)

**Dependency:** Step 13. **Goal:** move from temporary memory to durable case state.

1. In Google Cloud Console, open Firestore → Databases. Select **Native mode**. Use `(default)` database if it does not already exist.
2. Create a regional database in a supported location (example: `asia-southeast1`). A project can already contain a default database; don't recreate it if it exists.
3. Run `gcloud auth application-default login` locally to give Python client libraries approved user-scoped credentials. Confirm `GOOGLE_CLOUD_PROJECT` is your correct project ID.
4. Install cloud requirements (includes `google-cloud-firestore`, GCS, ADK). Set `APP_MODE=firestore` in `.env` **only after** credentials and GCS bucket are configured; `APP_MODE` also selects GCS storage for file uploads.
5. Inspect `app/repository.py`: Firestore uses collections `cases`, `actions`, `learning_proposals`, `approved_precedents`. `actions/{idempotency-key}.create(...)` is the at-most-once receipt record; all case transitions are still a prototype and do not have production distributed locking.
6. Run a simple Firestore connectivity probe before starting the API; use a synthetic document with a disposable ID, then delete it.

```bash
cd backend
python -m pip install -r requirements-cloud.txt
export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
gcloud auth application-default login
gcloud firestore databases list
# Run only if the (default) Firestore database does not yet exist:
gcloud firestore databases create --location=asia-southeast1 --type=firestore-native
python - <<'PY'
from google.cloud import firestore
client=firestore.Client()
ref=client.collection('connection_tests').document('demo-smoke')
ref.set({'synthetic':True,'purpose':'temporary connection test'})
print(ref.get().to_dict())
ref.delete()
PY
```

**PASS:** Firestore returns the exact synthetic dictionary and delete succeeds; no credential or database error. **If it fails:** check ADC, `GOOGLE_CLOUD_PROJECT`, enabled API and IAM. **Evidence:** terminal probe and Firestore console.

## Step 15 - Optional Firestore emulator for safe development (P1)

**Dependency:** Step 03. **Goal:** test Firestore client calls without cloud charges or production database changes.

1. In a separate terminal run Firestore emulator on port 8081; leave it running.
2. In your backend terminal export `FIRESTORE_EMULATOR_HOST=127.0.0.1:8081` and `GOOGLE_CLOUD_PROJECT=ryderesolve-local` (a dummy local project name is sufficient for emulator).
3. Set `APP_MODE=firestore`; the Python Firestore client automatically discovers the emulator host.
4. Do not use this mode for GCS file uploads unless you have a real GCS bucket; GCS is not emulated by Firestore.
5. Probe a simple Firestore document, then kill the emulator after the test. Remember emulator data may be ephemeral.

```bash
# Terminal A
gcloud emulators firestore start --host-port=127.0.0.1:8081
# Terminal B (with .venv)
export FIRESTORE_EMULATOR_HOST=127.0.0.1:8081
export GOOGLE_CLOUD_PROJECT=ryderesolve-local
python - <<'PY'
from google.cloud import firestore
c=firestore.Client();r=c.collection('test').document('x');r.set({'ok':1});print(r.get().to_dict())
PY
```

**PASS:** `{'ok': 1}` and no real production project changed. **If it fails:** ensure gcloud emulator component is installed, port 8081 is unused, env var is set in the **same** terminal as Python. **Evidence:** emulator-probe screenshot.

## Step 16 - Create private Cloud Storage evidence bucket (P1, mandatory for hosted photo stretch)

**Dependency:** Step 13. **Goal:** store evidence securely without public URLs.

1. Choose a globally unique bucket name, e.g. `YOUR_PROJECT_ID-ryde-evidence`.
2. Create a regional bucket, enable uniform bucket-level access, and turn on public-access prevention. Keep images private; do not grant `allUsers` bucket access.
3. Record bucket name in `backend/.env` as `GCS_BUCKET=...` for cloud mode. Authenticate with ADC locally.
4. Inspect `app/storage.py`: validates content type/size/file signature, hashes file bytes and writes `cases/{case_id}/{sha24}.png/.jpg/.pdf`. Firestore gets only object reference and metadata, not image binary.
5. The uploader deliberately reports `origin_verified:false` and `authenticity_verified:false`; uploading a JPG, receiving EXIF or using Gemini image pixels is not proof it came from Ryde's in-app camera.
6. Test with a small **synthetic** PNG/JPEG created or provided with permission. Do not upload an interview screenshot or real plate/face.

```bash
export BUCKET="${PROJECT_ID}-ryde-evidence"
gcloud storage buckets create "gs://${BUCKET}" \
  --location=asia-southeast1 \
  --uniform-bucket-level-access \
  --public-access-prevention
gcloud storage buckets describe "gs://${BUCKET}"
```

**PASS:** bucket exists, is private, and `GCS_BUCKET` is set for the backend. **If it fails:** bucket name globally taken, wrong location, insufficient `storage.buckets.create`, or project billing. **Evidence:** bucket privacy settings (hide any sensitive detail).

## Step 17 - Understand evidence provenance, timestamps and missingness (P0)

**Dependency:** Steps 10-11. **Goal:** avoid unfairly treating allegations or weak telemetry as incontrovertible fact.

1. Read `app/evidence.py`: `safety_screen`, `gaps`, `conflicts`, `clarification_for`, `record_fact`, `hash_snapshot`.
2. `gaps` checks required facts per dispute type. Missing means missing/unknown, **not** false. `conflicts` flags contradictory party accounts or incomplete notification-source records.
3. Each evidence import records `field`, `value`, `provenance`, `captured_at`, `source` and a **synthetic** verification label. In real deployment this must be derived from authenticated upstream systems, not free text.
4. Reviewer-only `POST /cases/{id}/evidence` is the demo's simulated “trusted system export”. A rider's clarification response remains `UNVERIFIED_PARTY_ACCOUNT`, even if it sounds convincing.
5. Compare a route's actual/recommended distance using trip-provided metrics, not straight-line distance between GPS waypoints unless the tariff/policy defines that method. Check trip-time historical traffic provenance and notification method.
6. GPS presence, ratings and history are signals; location precision and failure modes must be visible in case summaries.

```bash
cd backend
PYTHONPATH=. python - <<'PY'
import json
from pathlib import Path
from app.evidence import gaps,conflicts,safety_screen
for name in ('DEMO-FARE-CLARIFY','DEMO-FARE-CONFLICT','DEMO-SAFETY-IN-FARE'):
 d=json.loads((Path('fixtures/cases')/(name+'.json')).read_text())
 print(name, 'gaps:',gaps(d),'conflicts:',conflicts(d),'safety:',safety_screen(d))
PY
```

**PASS:** clarification case has missing notification fields; conflict case reports evidence contradiction; disguised safety-fare case is flagged. **If it fails:** check field names and source normalization; never patch cases to force a desired answer. **Evidence:** printed tri-state findings.

---

# Phase C - Routing index and Google ADK multi-agent implementation

## Step 18 - Verify read-only routing and policy lookup functions (P0)

**Dependency:** Steps 06-08. **Goal:** both Orchestrator and Judge query the supplied actual 41-ID rulebook instead of memorizing policy.

1. Open `app/policy.py`. `select_candidates(category, narrative, fraud_flags, safety)` reads **only** `04_rulebook.json` entries, collecting category rules plus cross-cutting safety/value gates.
2. `full_rules(rule_ids)` reads **only** `02_policy_rules.json` by exact rule ID. An unrecognized ID cannot invent a rule. `lookup_precedents(category)` reads policy §7 examples.
3. Open `app/agents.py`. Three ADK callable functions wrap the lookup: `get_rulebook_candidates`, `get_full_policy_rules` and `get_relevant_precedents`. These are read-only functions; they have no Firestore writer or mock-ledger access.
4. Validate a fare dispute produces FA-3.1 etc, `TH-6.1-LOW/MID/HIGH`, `SF-5.1/SF-5.2`, `PR-7`; flagged case adds `TH-6.3`.
5. Verify full rule `FA-3.3-B` contains its true source clause and conditional refund effect. The index description is not accepted as independent evidence.

```bash
cd backend
PYTHONPATH=. python - <<'PY'
from app.policy import select_candidates,full_rules
route=select_candidates('fare_dispute','unnotified surge',0,False)
assert 'FA-3.3-B' in route['candidate_rule_ids']
print('Candidate count:',len(route['candidate_rule_ids']))
print('Full rule:',full_rules(['FA-3.3-B'])[0])
PY
```

**PASS:** candidate IDs exactly match the supplied index and resolve against source JSON. **If it fails:** run Step 06 contract check before looking at prompts; do not hardcode replacement IDs. **Evidence:** tool result screenshot.

## Step 19 - Understand ADK agent objects and model credentials (P0)

**Dependency:** Steps 03, 13 for live model; independent if reading code. **Goal:** replace mock summaries with actual Gemini reasoning.

1. Inspect `app/agents.py` → `call_adk(role, payload)`. It imports `LlmAgent`, `Runner`, `InMemorySessionService` and `google.genai.types`.
2. Each ADK agent is initialized with `name`, `model`, `description`, system `instruction` and the **same** approved read-only policy tools. It creates an isolated session and invokes `runner.run_async` to collect a final response and event/tool-call metadata.
3. Do not use `output_schema` plus Python tools until you have validated your specific model/ADK version. The supplied live adapter asks for JSON in natural language and parses it. A malformed response is marked `parse_failed`; it does not authorize actions.
4. To run locally against Vertex AI, `gcloud auth application-default login`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` and `GOOGLE_GENAI_USE_VERTEXAI=TRUE` must be configured. Pick a **model name actually available** in that account/region, initially `gemini-2.5-flash` if supported.
5. First run with `APP_MODE=memory` and `AI_MODE=adk`, isolating agent issues from Firestore/GCS problems.
6. NEVER paste service-account keys or API keys into CodeBuddy prompts or screenshots.

```bash
cd backend
python -m pip install -r requirements-cloud.txt
python - <<'PY'
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
print('Google ADK Python SDK import OK')
PY
# In .env:
# AI_MODE=adk
# APP_MODE=memory
# GOOGLE_GENAI_USE_VERTEXAI=TRUE
# GOOGLE_CLOUD_PROJECT=your-project-id
# GOOGLE_CLOUD_LOCATION=us-central1
# GEMINI_MODEL=gemini-2.5-flash
```

**PASS:** ADK imports without errors, ADC account and Vertex project confirmed, no production data connected. **If it fails:** install cloud requirements in active `.venv`; inspect Google ADK version and official docs; check model availability and `aiplatform.googleapis.com` IAM. **Evidence:** import success, sanitized config screenshot.

## Step 20 - Implement Dispute Orchestrator as policy-aware coordinator (P0)

**Dependency:** Steps 17-19. **Goal:** orchestrate the case, not let an LLM bypass business state.

1. Read `app/services.py` → `process_case(case_id)`, which is the deterministic orchestration supervisor. It loads case state, screens for safety, invokes routing index, checks unknown/contradictory evidence, then calls ADK agents and safety/remedy gates.
2. Read `app/agents.py` → `DisputeOrchestrator` agent role. It is an ADK policy-routing analyst, not the executable authorizer. The Python coordinator controls when and whether agents run.
3. Ensure the ADK routing agent has the `get_rulebook_candidates` tool and `get_full_policy_rules` tool, plus prompt restrictions that unknown assertions must not be assumed false.
4. Store a visible `routing` object in the case: `candidate_rule_ids`, `evidence_to_fetch`, `safety_screen`, `policy_version`, `matched_phrase_rule_ids`.
5. Add a trace event `routing_index_read` with candidate count and matched IDs, so the judge/demo can inspect real routing behavior.
6. When new evidence arrives, call `process_case` again; derive fresh rule applicability rather than caching an obsolete decision.
7. Do not let the Orchestrator directly call the mock payment executor or modify a user's fraud/account status.

**PASS:** processing DISP-003 exposes a routing object containing `FA-3.3-B`, the case event log records the lookup and the Judge has policy tools independently. **If it fails:** debug `select_candidates`/`get_full_policy_rules` and case event append. **Evidence:** screenshot of policy candidates in UI/API.

## Step 21 - Implement Rider Advocate and Driver Advocate (P0)

**Dependency:** Steps 18-20. **Goal:** get two traceable, materially different, evidence-grounded perspectives.

1. Inspect `agent_instructions('RiderAdvocate')` and `agent_instructions('DriverAdvocate')` in `app/agents.py`.
2. Rider prompt: construct rider-favorable case *based on evidence and policy*, but explicitly surface evidence that weakens the rider case.
3. Driver prompt: construct driver-favorable case without treating driver reputation as conclusive; surface weaknesses and contradictions.
4. Each agent sees identical sanitized case facts and routing index context, can independently retrieve exact policy by rule IDs, and returns summary/supporting/opposing evidence/uncertainty and policy IDs.
5. The adapter calls Rider, Driver, PolicyPrecedent and FraudBadFaith concurrently with `asyncio.gather`; the Python coordinator waits for all before constructing the Judge's input. ADK `ParallelAgent` is an optional future refactor, not required for concurrency.
6. In mock mode, each role returns `MOCK_NOT_MODEL_OUTPUT` so you can design/test UI without pretending an LLM ran.
7. Expose actual agent event/tool metadata, but never expose hidden chain-of-thought or claim a chat-style staged debate occurred if the code didn't do it.

**PASS:** one case shows two separately named advocates with different perspectives, both grounded in recognizable fields and real policy IDs. **If it fails:** inspect `agent_outputs`, confirm `AI_MODE=adk`, look at Gemini quota and tool function schemas; invalid agent JSON must fail closed to review. **Evidence:** real ADK trace screenshots after live verification.

## Step 22 - Implement Policy/Precedent and Fraud/Bad-Faith agents (P1)

**Dependency:** Steps 18-21. **Goal:** implement two substantive stretch goals without unsound accusations.

1. `PolicyPrecedent` reads v2.1 precedent entries from `get_relevant_precedents(category)`, compares material facts (not just case IDs), and cites exact clauses. It can also fetch approved new precedents from Firestore after Innovation B approval.
2. `FraudBadFaith` examines documented risk history independently and in parallel. Its role is to raise review signals (e.g., repeated disputed no-shows), not label a party a fraudster from average rating, nationality or account age.
3. Ensure fraud flag ≥1 maps to the 95% threshold from `TH-6.3` and triggers a conservative reviewer path in our prototype because calibrated confidence has not been established.
4. A precedent does not override present evidence or a mandatory human review. `PR-7` is candidate-retrieval guidance, not financial authorization.
5. Test DISP-002's historical fraud flag routes to review while the actual GPS/contact facts are still weighed. Test DISP-003 has no historic flag and a clear policy fact pattern.

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_policy.py -k fraud_flag
PYTHONPATH=. python - <<'PY'
from app.agents import get_relevant_precedents
print(get_relevant_precedents('fare_dispute'))
PY
```

**PASS:** policy precedent is cited by facts and fraud only influences escalation, not a predetermined guilty verdict. **If it fails:** compare output against original policy §6.3 and §7; remove any reasoning based on unverified stereotypes. **Evidence:** annotated case trace.

## Step 23 - Implement Judge proposal with an independent final policy gate (P0)

**Dependency:** Steps 19-22. **Goal:** preserve the challenge's impartial Judge while preventing model-only settlement.

1. Read `agent_instructions('Judge')`: both advocates' outputs, case facts and the policy routing context are passed to Judge after advocate execution; Judge also has direct read-only rulebook and full-policy lookup tools.
2. Judge proposes a structured disposition/amount and cites rule IDs. Its output is stored under `agent_outputs.Judge` with visible trace.
3. **Independent** `policy_engine.recommend(case)` derives an auditable reference action from confirmed synthetic facts; `policy_engine.gate(...)` decides whether human review is mandatory.
4. `judge_consistency(...)` compares the live Judge's recommendation/amount to the independently validated candidate. A mismatch, malformed JSON, timeout or unsupported amount **blocks automation**; it does not get “repaired” by inventing a higher confidence score.
5. Safety cases **skip Judge entirely** and have candidate `undetermined`. Human reviewers, not agents, decide fault/resolution.
6. Confirm no model has direct financial, account suspension, or database policy mutation tools.

**PASS:** DISP-003 proposes the SGD 4.50 surge differential, and the separate gate can authorize a mock action only after signoff/source completeness; DISP-001 (>2 km) and safety cases cannot bypass mandatory review. **If it fails:** inspect `candidate`, `agent_outputs.Judge`, `judge_consistency`, and gate reasons. **Evidence:** separate Judge proposal vs policy gate in UI.

## Step 24 - Capture observable agent interactions and failures (P0)

**Dependency:** Steps 20-23. **Goal:** satisfy Ryde's observable inter-agent communication criterion.

1. The live adapter records `agent_trace`: which ADK agent ran, which tool names were invoked, which event ended and whether the agent produced a final response.
2. The case stores `agent_outputs` separately. Show Orchestrator, Rider, Driver, Policy, Fraud, Judge and any image branch in the UI.
3. Confirm a Judge starts only **after** Rider/Driver results are available. Parallel outputs can arrive in varying order; don't assume timing proves precedence.
4. Log tool failures and parse failures; do not silently replace a broken ADK call with mock results when `AI_MODE=adk`. The code raises an error and leaves the case unfinalized.
5. Review logs for sensitive values. Demo-only synthetic IDs are acceptable; private interview excerpts and secrets are not.
6. For the pitch, show a concise event timeline—not an invented hidden reasoning trace.

**PASS:** with `AI_MODE=adk`, the trace contains ADK event metadata and each named role's final output; with `AI_MODE=mock`, every role is explicitly labeled mock. **If it fails:** check `app/agents.py` event collection and `agent_outputs`; fail closed. **Evidence:** sanitized real ADK trace recording.

## Step 25 - First controlled live Gemini/ADK smoke test (P0 before cloud deployment)

**Dependency:** Steps 08, 19-24 and approved model credentials. **Goal:** prove ADK is actually invoked.

1. Stop Uvicorn. In `backend/.env` keep `APP_MODE=memory` and set `AI_MODE=adk` plus Vertex environment details. Reopen/restart the API process so settings reload.
2. Start backend and seed 12 synthetic cases. Process **only DISP-003** first to conserve tokens, then inspect case `agent_trace` for tool-call events and all advocate/Judge outputs. It must no longer contain `MOCK_NOT_MODEL_OUTPUT`.
3. Use `backend/scripts/live_eval.py --cases DISP-003` in a *separate* evaluation process for an independently captured trace and latency file. The evaluator refuses to run in mock mode.
4. If a tool schema, model name or Vertex permission causes an exception, do not change the policy engine. Fix the actual SDK integration and rerun.
5. Record end-to-end latency, model name, region and invocation errors honestly. Live model calls can cost money; check quota.
6. Only after this gate passes, expand live evaluation to DISP-001, DISP-002, no-show variants, safety and damage cases.

```bash
# backend/.env must contain AI_MODE=adk, APP_MODE=memory, GOOGLE_CLOUD_PROJECT, etc.
cd backend
uvicorn app.main:app --reload --port 8000
# second terminal, backend root with venv and same .env
PYTHONPATH=. python scripts/live_eval.py --cases DISP-003
```

**PASS:** `live_execution_verified:true`, ADK events and actual Gemini responses are present; separate deterministic outcome is still correct. **If it fails:** most common causes are unavailable model/region, ADC permissions, missing ADK package, exhausted quotas, tool validation errors or malformed JSON output. Refer to Appendix D. **Evidence:** actual model trace and timestamped `backend/reports/live-*.json`.

---

# Phase D - Deterministic safety gates, actions, authentication and APIs

## Step 26 - Make safety detection the first decision gate (P0)

**Dependency:** Steps 11, 17. **Goal:** a safety allegation never reaches AI fault/ruling or automatic suspension.

1. Read `app/evidence.py` → `safety_screen(case)`, including the selected category and all text evidence checked against relevant risk language.
2. Read `app/services.py` → `process_case`. Safety screening happens before Judge. The system can still gather/summarize accounts; it must **not** propose a remedy or determine fault (Policy §5.1-5.2).
3. The service stores `path=IMMEDIATE_HUMAN_REVIEW`, `status=REVIEW_REQUIRED`, and a reviewer alert in a **simulated** notification outbox. No account action is executed.
4. Test a case labeled `fare_dispute` whose description includes “driver threatened me”. It must be treated as safety despite wrong category.
5. Stress test spelling/wording with variants. The current prototype's keyword detector is conservative but not exhaustive; real deployment requires supervised safety evaluation, escalation QA, potentially a separate classifier and monitored recall. Never claim keyword rules catch every safety incident.
6. Do not put model self-confidence ahead of a mandatory safety flag.

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_api.py -k safety
PYTHONPATH=. python scripts/threat_eval.py
```

**PASS:** safety case never contains `agent_outputs.Judge` or `mock_action`; `sla_routing.priority=P0_SAFETY`, no numeric SLA is invented. **If it fails:** inspect when safety is screened relative to agent calls, and stop auto-finalization until corrected. **Evidence:** safety case UI and test output.

## Step 27 - Implement monetary, category and fraud-flag precedence (P0)

**Dependency:** Steps 07-08, 26. **Goal:** one deterministic implementation of v2.1's overlapping rules.

1. Read `app/policy_engine.py` → `gate`. Check that category and safety/human gates apply even if the monetary band would otherwise allow AI finalization.
2. Monetary bands under §6.1: under SGD 10, SGD 10 through SGD 50, and above SGD 50. The boundary at exactly 10/50 belongs to the middle band; above 50 always review.
3. Route deviation §6.2: if actual-recommended exceeds 2 km, always human. If ≤2 km, ≥80% *validated* confidence is required. This prototype has no calibrated confidence, so it deliberately sends all route decisions to human review while still constructing the case and proposed refund.
4. Fraud flag ≥1 triggers a 95% confidence requirement under §6.3; because no calibrated model is supplied, flagged cases route to a reviewer. A flag is not proof of wrongdoing.
5. Rider-disputed damage claims always human under §4.4. Repair and poorly sourced photo cases are also conservative review paths.
6. Missing dispute amount/basis, missing evidence, and inconsistent Judge recommendation block automatic execution.
7. Reject any attempt to “override” the gate using a high model score or an instruction inside an evidence record.

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_policy.py -k thresholds
PYTHONPATH=. pytest -q tests/test_policy.py -k route
PYTHONPATH=. pytest -q tests/test_policy.py -k fraud
```

**PASS:** under-$10 fare/no-show examples can auto-resolve when complete and unflagged; route >2 km, fraud flag, safety, damage and >$50 always escalate. **If it fails:** compare actual rule IDs to source §6 and run the full 12-case suite; do not edit gold answers to match a bug. **Evidence:** boundary matrix test results.

## Step 28 - Implement exact dispute category evaluation (P0)

**Dependency:** Steps 17-27. **Goal:** make evidence materially change remedies, not merely explain preloaded answers.

1. **Fare/surge:** Policy §3.1-3.5. Read `recommend(case)`. Verify upfront quote, new surge, complete notification event source, whether notification occurred, and difference solely attributable to surge. Compute *only* verified difference; booking fee is surge-exempt.
2. **No-show:** Policy §2.1-2.4. Parse timezone-aware scheduled pickup and cancel times. Require 5 minutes from **scheduled pickup**, verified driver arrival/presence, one chat AND one in-app call attempted before cancellation. If a required contact type missing, void fee. Don't equate rider silence with guilt.
3. **Route:** Policy §1.1-1.4. Compare distance, historical traffic reason, timely notification and excess-distance component. Example DISP-001 can have an SGD 3.44 proposed excess-distance refund, but remains reviewer-only because 4.3 km exceeds 2 km.
4. **Damage:** Policy §4.2-4.4. Check photo timestamp, 24-hour submission, trip link, genuine *trusted* camera origin and whether rider disputes. A pixel model cannot authenticate origin. Disputed claims always review.
5. **Safety:** stop at reviewer case-file preparation; no AI fault/resolution proposal.
6. Edit `recommend` only with a policy-cited reason and new regression tests for each branch. Keep money/driver compensation/account action distinct.

```bash
cd backend
PYTHONPATH=. python scripts/evaluate.py
PYTHONPATH=. pytest -q tests/test_policy.py
```

**PASS:** all 12 golden paths match, with independent evidence-backed candidate values; no `recommended_ruling` labels enter the decision pipeline. **If it fails:** inspect source `facts` vs rule `condition`; never invent a tariff or missing notification. **Evidence:** 12-row evaluation result.

## Step 29 - Implement mock financial action executor and idempotency (P0)

**Dependency:** Steps 27-28. **Goal:** show a completed and safe *simulated* remedy, not just text advice.

1. Read `app/actions.py` → `execute_mock(repo, case, disposition, amount)`.
2. Only allowed dispositions: `refund`, `credit`, `no_action`, `reject_claim`. It does not use Stripe, a payment provider, or a real Ryde ledger.
3. The action key combines case ID, revision, disposition and amount. `repo.create_action(...)` returns prior record for retries; Firestore's document `create()` enforces existence preconditions.
4. The receipt starts `MOCK-` and has `status=COMPLETED_SIMULATED`, `simulated:true`, `currency:SGD`.
5. For auto-eligible cases, the validated service calls executor once and saves receipt. For reviewer cases, only an authorized review decision causes a mock action.
6. Retry `POST /cases/DISP-003/process` twice. The same receipt must appear and the action repository must not grow.
7. Know the limitation: while action document creation is atomic, complete Firestore case transitions would still need transactions/locks for production concurrency and race recovery.

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_api.py -k duplicate
PYTHONPATH=. pytest -q tests/test_api.py -k auto_fare
```

**PASS:** one completed simulated action per case/revision/disposition/amount, no real money movement, receipt visible. **If it fails:** audit action key and Firestore `create()` precondition; never fix by removing retry safety. **Evidence:** matching receipt screenshot from two requests.

## Step 30 - Implement review workbench access control (P0)

**Dependency:** Steps 11, 29. **Goal:** protect reviewer actions in a public synthetic demo.

1. Read `app/main.py` → `demo_role`, `reviewer`, `actor`. They map **three distinct passcodes** (`DEMO_REVIEWER_KEY`, `DEMO_RIDER_KEY`, `DEMO_DRIVER_KEY`) to roles by constant-time comparison.
2. Backend rejects requests without a passcode, and reviewer-only routes are unavailable to rider/driver keys. A caller sending `X-Demo-Role: reviewer` cannot bypass it.
3. `POST /cases/{id}/review` validates disposition, amount ≥0, written reason at least 10 characters and `status=REVIEW_REQUIRED`.
4. For hosted mode, **replace** all `change-...` default keys with random secrets. The code refuses hosted API auth when defaults remain. Do not expose reviewer code in frontend source or public screenshots.
5. This is demo passcode authorization only. Real integration would use Firebase Auth / Identity Platform + auditable per-user role claims + IAM and rate limits.
6. Test unauthenticated 401, rider key on reviewer endpoint 403, reviewer key success, duplicate review rejection.

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_api.py -k reviewer_only
curl -s -o /dev/null -w '%{http_code}\n' -H 'X-Demo-Key: wrong' http://127.0.0.1:8000/cases
```

**PASS:** wrong/absent key returns 401, rider forbidden returns 403, reviewer works; hosted defaults refused. **If it fails:** disable hosted access until fixed, inspect `.env` role keys; don't trust user-supplied role or expose secrets. **Evidence:** three status-code tests.

## Step 31 - Implement append-only-style audit events and tamper detection (P1)

**Dependency:** Steps 11, 29-30. **Goal:** reconstruct the case and make casual tampering detectable.

1. Read `app/services.py` → `event(case, kind, details)` and `verify_event_chain(case)`. Each event records `kind`, timestamp, details, prior hash, and SHA-256 of current event.
2. Events are appended at creation, rule index lookup, clarification requests/replies, safety review, gate evaluation, simulated remedy and reviewer learning.
3. The event record is saved inside the case document in memory/Firestore. This is a useful hackathon audit design but **not** an externally immutable audit system; an administrator who rewrites the full chain can defeat it.
4. Call `/cases/{id}/verify-audit` as reviewer. Mutate an event in an isolated unit test and confirm verification fails.
5. Display linked evidence IDs, source policy version, candidate ID list, action receipt and reviewer reason in the UI for transparency.
6. Avoid logging raw private emails, uploaded secrets or real interview transcripts in Cloud Logging.

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_api.py -k audit
curl -s -H 'X-Demo-Key: change-reviewer-key' http://127.0.0.1:8000/cases/DISP-003/verify-audit
```

**PASS:** original chain verifies true; mutation test returns false; case timeline is inspectable. **If it fails:** audit the event serialization/hash, timestamp format and whether someone mutated events after hash creation. **Evidence:** audit result.

## Step 32 - Verify FastAPI/OpenAPI contracts and error handling (P0)

**Dependency:** Steps 29-31. **Goal:** make UI integration predictable.

1. Start Uvicorn and open `http://127.0.0.1:8000/docs`. FastAPI automatically renders the API's request schemas and endpoints.
2. Review the full `docs/API_REFERENCE.md` table, including each role's permissions and expected request body.
3. Test `GET /health` (200), `POST /cases/seed` with reviewer key, `GET /cases`, `GET /cases/DISP-003`, `POST /cases/DISP-003/process`.
4. Test deliberately invalid case ID (404), missing passcode (401), non-reviewer file upload (403), invalid evidence field (400), repeated clarification response (400).
5. Ensure frontend displays error `detail` rather than silently retrying unauthorized financial actions.
6. For deployment, make `/health` a load balancer/smoke test. Be aware it is unauthenticated and should not expose secrets.

```bash
curl -s http://127.0.0.1:8000/openapi.json | python3 -m json.tool | head -50
curl -s -o /dev/null -w '%{http_code}\n' -H 'X-Demo-Key: change-rider-key' http://127.0.0.1:8000/cases/NOT-EXIST
```

**PASS:** FastAPI docs show the contracts, expected success/error codes match source. **If it fails:** inspect Uvicorn logs and the function in `app/main.py` owning that route. **Evidence:** OpenAPI screenshot and HTTP status matrix.

---

# Phase E - Innovation A: decision-changing active investigation

## Step 33 - Define an investigation-worthy evidence gap (P1)

**Dependency:** Steps 17, 28. **Goal:** ask a question only if the answer could change evidence or routing.

1. Read `app/evidence.py` → `gaps(case)`, `conflicts(case)`, `clarification_for(case)`.
2. Per category, identify decision-critical keys: fare surge before/after, quote/final, notice and notification-log completeness; no-show schedule/cancel, arrival, rider presence, chat/call; route distance, traffic, notification, excess fare; damage trip link and photo metadata.
3. Make a tri-state distinction: verified yes, verified no, and unknown. Missing source records are not proof a required event never occurred.
4. Detect explicit contradictory statements: e.g., driver claims in-app notice occurred while rider denies, or GPS system reports arrival while rider says the vehicle was at a different entrance.
5. Prioritize **one question** that could resolve the earliest causal uncertainty. The initial kit uses deterministic templates, not a speculative always-on questioning agent; if needed, ADK can improve the wording once the loop works.
6. Avoid asking a driver to check/respond to email while driving; represent delivery as in-app notification and let the driver respond when safe.
7. Store the required corroboration fields alongside the request so the system knows what *source evidence* is needed to close it.

```bash
cd backend
PYTHONPATH=. python - <<'PY'
import json
from app.config import ROOT
from app.evidence import gaps,conflicts,clarification_for
p=ROOT/'fixtures/cases/DEMO-FARE-CLARIFY.json';c=json.loads(p.read_text())
print(gaps(c));print(conflicts(c));print(clarification_for(c))
PY
```

**PASS:** fare-clarify case asks specifically about the revised surge notification and expects `notification_log_complete` and `rider_notified` as corroboration. **If it fails:** restore required-fact list and avoid generic “explain everything again” questions. **Evidence:** one real request object in API/UI.

## Step 34 - Persist clarification state and simulated notification (P1)

**Dependency:** Step 33. **Goal:** suspend asynchronous cases safely, with no forced ruling.

1. Read `services.process_case` branch handling `missing or inconsistent`.
2. Create `clarifications` entry containing `request_id` (UUID), recipient role, neutral question, required verified fields, created timestamp, status `PENDING`.
3. Set case state `AWAITING_CLARIFICATION`, `path=CLARIFICATION`, log event `clarification_requested`.
4. Append `notifications` record `SIMULATED_OUTBOX_NOT_DELIVERED`. No real email, SMS, TRTC call, or webhook is sent in this prototype. This is deliberate: the demonstration must not contact real drivers/riders.
5. Repeated process requests while a clarification is still pending must return the same pending request, not generate hundreds of questions.
6. For a production extension, specify a queue job, delivery retry, safe-response timing, and timeout policy with approved values; do not invent Ryde SLA minutes.

```bash
curl -s -X POST -H 'X-Demo-Key: change-rider-key' \
 http://127.0.0.1:8000/cases/DEMO-FARE-CLARIFY/process | python3 -m json.tool
```

**PASS:** state is `AWAITING_CLARIFICATION`, notification outbox labels are simulated and request UUID persists across reads. **If it fails:** inspect `process_case` and `repo.save_case`; confirm the case has a missing/contradictory critical fact. **Evidence:** two consecutive API responses showing stable request ID.

## Step 35 - Capture rider/driver response without turning claims into proof (P1)

**Dependency:** Step 34. **Goal:** give both parties a voice without dangerous inference.

1. Open the case UI while using the intended recipient's role/passcode; copy the pending `request_id` from the case response if calling the API directly.
2. Reply via `POST /cases/{case_id}/clarifications/{request_id}/reply` with a short factual answer. Service verifies only intended recipient or reviewer key can post.
3. The reply is marked `UNVERIFIED_PARTY_ACCOUNT`. It is stored with a timestamp and event record. It does **not** set `facts.rider_notified=false` or any trusted source variable.
4. Reprocess immediately: with no corroborating system record, the case must move to `REVIEW_REQUIRED` because the response alone cannot resolve the disputed source fact.
5. Show the result to user: “additional evidence needed / human review”, not “you failed to reply, so you are guilty”.
6. Duplicate reply to same request must be rejected; a reply by the wrong party must be rejected.

```bash
# Replace REQUEST_ID with the UUID returned by /cases/DEMO-FARE-CLARIFY/process
curl -X POST 'http://127.0.0.1:8000/cases/DEMO-FARE-CLARIFY/clarifications/REQUEST_ID/reply' \
 -H 'Content-Type: application/json' -H 'X-Demo-Key: change-rider-key' \
 -d '{"answer":"I did not receive a revised fare notification before pickup."}'
```

**PASS:** reply stored as unverified and without auto-remedy; second reply returns 400. **If it fails:** inspect status/role checks in `reply_to_clarification`; don't grant the party permission to write privileged `facts`. **Evidence:** before/after state comparison.

## Step 36 - Import verified synthetic source evidence and prove decision change (P1; Innovation A showcase)

**Dependency:** Steps 33-35; policy contract signed off. **Goal:** demonstrate a NEW piece of evidence changes a previously unresolved outcome.

1. Use reviewer role to import two **synthetic complete system event log facts** for `DEMO-FARE-CLARIFY`: `rider_notified=false` and `notification_log_complete=true`. In a real system these would be authenticated notification-service logs, not an individual's free-text claim.
2. Each `POST /cases/{id}/evidence` must record provenance and the new value, increment case revision and update `evidence_snapshot_hash`.
3. Reprocess. `gaps` should now be empty, and the deterministic policy evaluator can establish an unnotified surge increase. If no other blockers exist, path changes from CLARIFICATION/REVIEW to `AUTO_ELIGIBLE` with simulated SGD 4.50 refund.
4. Show the reviewer a comparison: before evidence: undetermined; after complete source record: rule `FA-3.3-B`, refund amount SGD 4.50, mock action receipt.
5. Test the *opposite* scenario: if the complete system log proves a valid in-app notification and rider proceeded, the supported disposition should be `no_action` rather than refund (with evidence `rider_proceeded=true`).
6. Document that the phrase “verified” means *synthetic trusted fixture in this demo*; no real Ryde notification service exists.

```bash
curl -X POST http://127.0.0.1:8000/cases/DEMO-FARE-CLARIFY/evidence \
 -H 'X-Demo-Key: change-reviewer-key' -H 'Content-Type: application/json' \
 -d '{"field":"rider_notified","value":false,"provenance":"SYNTHETIC complete system notification export"}'
curl -X POST http://127.0.0.1:8000/cases/DEMO-FARE-CLARIFY/evidence \
 -H 'X-Demo-Key: change-reviewer-key' -H 'Content-Type: application/json' \
 -d '{"field":"notification_log_complete","value":true,"provenance":"SYNTHETIC complete system notification export"}'
curl -s -X POST -H 'X-Demo-Key: change-reviewer-key' \
 http://127.0.0.1:8000/cases/DEMO-FARE-CLARIFY/process | python3 -m json.tool
```

**PASS:** previously unresolved case becomes evidence-supported and the **same case ID** gets a new policy-grounded result. **If it fails:** check signoff, gaps and case source trust; don't force “no evidence” to mean “no notification”. **Evidence:** before/after screenshots with policy citations and final mock receipt.

## Step 37 - Add explicit investigation failure, repeated response and pause/resume tests (P1)

**Dependency:** Steps 33-36. **Goal:** avoid theatrical clarification that never affects a decision.

1. Run `pytest -k innovation_a`. It checks request persistence, unverified reply, escalation and verified source fact import.
2. Create additional synthetic variants: no response by deadline, response with no corroboration, contradictory new system record, malformed evidence payload, two almost-simultaneous replies, and no-show source logs arriving late.
3. Decide safe behavior: no unauthorized finalization; explicit pending/review state; review packet shows what was sought and what remains unknown.
4. Set **target evaluation** before testing: all genuinely mandatory escalations correct; zero unsupported claim promotions; zero duplicate mock refunds. Do not report performance as measured until you have logs.
5. For production, add a durable job scheduler and optimistic revision checks. The starter kit has persisted case data and retry-safe mock action IDs but not full distributed workflow orchestration.

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_api.py -k innovation_a
```

**PASS:** decision cannot be changed by unverified text alone; addition of verified synthetic system fact changes policy result. **If it fails:** inspect `record_fact`, `source_trust`, `gaps`, `conflicts`, request status, and `gate`. **Evidence:** regression transcript.

---

# Phase F - Remaining Ryde stretch capabilities: image, escalation, routing

## Step 38 - Implement image evidence storage and multimodal interpretation (P1)

**Dependency:** Steps 16, 17, 19. **Goal:** demonstrate real pixels analyzed by an LLM while keeping photo authenticity claims honest.

1. Read `app/storage.py`: accepts PNG/JPEG/PDF up to 5 MB, rejects mismatched magic bytes, stores bytes under a content-hashed private object ref. Local memory mode writes into `backend/uploads`, hosted mode writes to GCS.
2. Read `app/image_analysis.py`: in `AI_MODE=adk`, an `LlmAgent` receives the actual image bytes via `types.Part.from_bytes` and is asked to describe **visible** damage/soiling and uncertainty, not determine authenticity or rider fault.
3. In `AI_MODE=mock`, image result must say `MOCK_NOT_MODEL_OUTPUT` and contain no asserted visual classification.
4. Upload a genuinely synthetic/permission-cleared vehicle interior photo via `POST /cases/DEMO-DAMAGE-DISPUTED/files` using reviewer key; verify the result is stored under `evidence` with metadata and `authenticity_verdict=UNKNOWN`.
5. Check image timestamp, trip association and in-app-camera attestation separately. A time-stamped external photo is **not** verifiable under Policy §4.2 merely because an LLM says it looks real. Our demo lacks a real Ryde in-app camera attestation source.
6. The rider **disputes** this cleaning claim; §4.4 requires human review even if the pixels clearly depict a stain and the claim is ≤SGD 50.
7. For actual stretch proof, run live ADK with a real synthetic photo, capture the image analyst response and show that it does not override mandatory review.

```bash
# Supply a synthetic JPEG path (no private people/real plate numbers):
curl -X POST 'http://127.0.0.1:8000/cases/DEMO-DAMAGE-DISPUTED/files' \
 -H 'X-Demo-Key: change-reviewer-key' \
 -F 'file=@./path/to/synthetic-seat-stain.jpg;type=image/jpeg'
```

**PASS:** GCS/local upload succeeds, file hash/storage ref and image analysis mode are visible, authenticity remains UNKNOWN, disputed damage goes human. **If it fails:** verify JPG signature, file size, GCS credentials, bucket permissions and Gemini modality support. **Evidence:** sanitized upload result and photo-evidence screen.

## Step 39 - Implement escalation and reviewer packet (P0)

**Dependency:** Steps 26-28, 33. **Goal:** turn mandatory review into useful human action.

1. Cases with `path=HUMAN_REVIEW` or `IMMEDIATE_HUMAN_REVIEW` must show `candidate` (if not safety), `gate.reasons`, applicable rule IDs and trace, `facts`, evidence gaps, contradictions and any clarification history.
2. Open Next.js Reviewer Workbench panel or fetch `GET /cases/{id}` as reviewer; review evidence provenance and policy references before deciding.
3. For safety, no AI fault/remedy recommendation may appear; the reviewer makes the decision independently.
4. For ordinary high-value/uncertain disputes, show the reference candidate separately from the legally authorized final reviewer decision.
5. Reviewer enters `disposition`, `amount`, `reason`, optional `proposed_precedent`, then the demo ledger generates a receipt. Store review timestamp/event.
6. Test DISP-001: proposed excess distance refund 3.44, but 4.3 km >2 forces human. Test DISP-002: no-show facts support driver but the historical flag prevents uncalibrated autonomous finalization.

**PASS:** reviewer can reconstruct the case without raw backend logs; a safety case has no AI fault recommendation, and reviewing it creates only a simulated action. **If it fails:** inspect reviewer role check, gate reasons, and `candidate` separation. **Evidence:** reviewer packet screenshot for both DISP-001 and safety.

## Step 40 - Implement SLA and routing without inventing SLA numbers (P1)

**Dependency:** Step 26. **Goal:** prioritize safety and high-value disputes as a stretch capability.

1. Read `app/sla.py` → `route_priority(case)`.
2. Safety is `P0_SAFETY` to `SAFETY_REVIEW`; financial value above 50 is `P1_HIGH_VALUE` to `FINANCIAL_REVIEW`; flagged cases are `P1_RISK_REVIEW`; routine disputes are `P2_STANDARD`.
3. The code returns `target_minutes:null` because the supplied hackathon policy does not publish operational SLA response targets. Do not invent “10-minute SLA”.
4. Inspect case's `sla_routing` object after processing and ensure reviewer queue can sort by priority.
5. Extend to backlog dispatch/aging metrics only if actual operational targets and reliable timestamps are available.
6. Test that a case filed as fare but containing a safety term still goes to P0.

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_api.py -k sla_safety_priority
```

**PASS:** safety always prioritized, no fabricated numeric SLA or priority guarantee. **If it fails:** test `safety_screen` before priority assignment, not after Judge. **Evidence:** queue labels in API/UI.

## Step 41 - Implement notification and outcome explanation outbox (P1)

**Dependency:** Steps 29, 34, 39. **Goal:** connect case outcomes to customer/driver communication without actual messaging APIs.

1. Read `services.py` where `notifications` are appended with `SIMULATED_OUTBOX_NOT_DELIVERED`.
2. Clarification case creates neutral question for intended rider/driver; safety creates reviewer notification; completed remedy creates receipt notification.
3. Display a plain-language reason distinguishing ruling, remedy type, SGD amount, original-payment refund vs goodwill credit vs no-action, and whether action is simulated.
4. For the driver experience, show a persistent in-app response request rather than requiring long emails while driving. Do not message an actual interview participant unless explicitly authorized.
5. For production replace outbox with authenticated, permission-aware in-app delivery + retry queue; record delivery and response timestamps.
6. Provide outcome explanations separately for rider and driver without leaking private information from the other party.

**PASS:** all three simulated outbox types appear with labeled status, not a misleading “sent email” claim. **If it fails:** inspect service event creation and `notifications` field. **Evidence:** notification objects plus UX screenshots.

---

# Phase G - Innovation B: governed reviewer learning, testing and release

## Step 42 - Capture a reviewer override as a staged learning proposal (P1)

**Dependency:** Steps 30, 39. **Goal:** collect corrections with accountability rather than self-train immediately.

1. Open `app/services.py` → `human_review`. A reviewer-only API call with `proposed_precedent` stages a new record in collection `learning_proposals`.
2. The proposal stores `proposal_id`, `source_case_id`, category, `candidate_before`, `human_after`, full correction text, policy version, timestamp and status `STAGED`.
3. Reviewers must explain what the AI or original evidence interpretation got wrong. “I disagree” with no reasoning is not enough for a reliable learning corpus.
4. Do not write the correction directly into `02_policy_rules.json`, ADK prompts, or a live vector index. The source policy is not modifiable by feedback and the published precedent requires review.
5. Test by processing DISP-001 (review required) and submitting a documented human decision with an optional precedent phrase.
6. Record a hash of the proposed content at evaluation time to prevent changing the proposal after tests passed.

```bash
curl -X POST 'http://127.0.0.1:8000/cases/DISP-001/review' \
 -H 'X-Demo-Key: change-reviewer-key' -H 'Content-Type: application/json' \
 -d '{"disposition":"refund","amount":3.44,
      "reason":"After reviewing traffic and lack of route notice, reviewer approves excess-distance refund.",
      "proposed_precedent":"For a 4.3 km traffic-justified but unannounced detour, require human review before any refund."}'
```

**PASS:** action is `MOCK-...`, learning proposal ID is returned, proposal status `STAGED`, and no precedent becomes active. **If it fails:** ensure case is `REVIEW_REQUIRED` and use reviewer key; duplicate reviews should be rejected. **Evidence:** staged proposal UI.

## Step 43 - Run regression suite against staged learning (P1)

**Dependency:** Step 42. **Goal:** prevent a reviewer correction from silently degrading decision policies.

1. Read `app/services.py` → `evaluate_suite` and `evaluate_learning`.
2. The evaluator loads 12 independently specified expected case outcomes from `fixtures/evaluation/gold.json`, computes actual deterministic path and candidate from inputs, and reports individual matches. The gold file is never read by the live agent pipeline.
3. `POST /learning/{proposal_id}/evaluate` runs the 12-case suite. It returns `passed`, `total`, `all_passed` and a SHA-256 of staged correction/policy version for change detection.
4. This is a **bounded proof-of-concept test gate**, not a complete semantic impact evaluation. Expand it with adversarial cases, actual human-annotated corrections and a separate regression of model outputs before any real deployment.
5. If any case fails, proposal goes `FAILED_EVALUATION`, cannot be released. Investigate the changed condition and update tests or proposed text before re-running, with new evidence.
6. Run the standalone reference script as a baseline and preserve its JSON report.

```bash
cd backend
PYTHONPATH=. python scripts/evaluate.py
# API after staging; replace LP_ID:
curl -X POST -H 'X-Demo-Key: change-reviewer-key' \
 http://127.0.0.1:8000/learning/LP_ID/evaluate
```

**PASS:** all 12 reference paths correct and hash recorded; no proposal is automatically active. **If it fails:** compare failing `case_id`, expected and actual paths; don't relabel expected simply to pass. **Evidence:** before/after validation result and commit.

## Step 44 - Approve and publish versioned precedent, never silently change policy (P1)

**Dependency:** Step 43. **Goal:** demonstrate safe, auditable improvement in future **decision support**.

1. Read `app/services.py` → `approve_learning`. It requires the staged proposal's status to be `EVALUATED`, the regression to pass and the proposal content hash to remain unchanged.
2. Reviewer provides written `rationale` (at least 10 characters). Only reviewer key may invoke approval.
3. The service creates `approved_precedents/{proposal_id}` record with policy version, source case ID, approval timestamp and release state `ACTIVE_APPROVED_PRECEDENT`.
4. `get_relevant_precedents(category)` may now include this approved record alongside original policy precedents. The new entry aids comparisons but **cannot override policy v2.1** or authorise an action itself.
5. Test negative path: try approving before evaluate → must fail. Change staged text after evaluation → must fail hash check. Use reviewer-only `POST /learning/{id}/rollback` with a written reason to deactivate the precedent while retaining its history; rerun regression. The backend rollback endpoint is supplied and unit-tested.
6. For production, version approvals through a signed PR/release and maintain a reversible published-precedent pointer; the demo is a proof of approval workflow, not autonomous model retraining.

```bash
curl -X POST 'http://127.0.0.1:8000/learning/LP_ID/approve' \
 -H 'Content-Type: application/json' -H 'X-Demo-Key: change-reviewer-key' \
 -d '{"rationale":"Policy reference and 12-case regression verified; approve only as future reviewer context."}'
```

**PASS:** approval only after passing suite, precedent status `ACTIVE_APPROVED_PRECEDENT`, policy source file unchanged, human approval logged. **If it fails:** inspect status/hash, reviewer role and regression result. **Evidence:** blocked-before-approval and approved-after-evaluation screenshots.

## Step 45 - Validate full Innovation B negative and release tests (P1)

**Dependency:** Steps 42-44. **Goal:** prove feedback safety rather than showing a static database append.

1. Run `pytest -k innovation_b` (checks blocked pre-approval, suite success and release).
2. Test that a rider/driver passcode cannot evaluate or approve a learning proposal; only reviewer can.
3. Test that a released precedent is scoped to its category and is not treated as a higher-authority financial rule.
4. Document what the test suite covers and **does not cover**: it checks paths and selected amounts on 12 synthetic examples, not a production-distribution shift or calibrated model output.
5. Preserve proposal content hash, test result, reviewer rationale and approval timestamp for judge demonstration.

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_api.py -k innovation_b
```

**PASS:** untested proposal blocked, regression runs, approved record searchable in proper category. **If it fails:** do not auto-enable training/retrieval; fix status transition and reviewer check. **Evidence:** test output + JSON correction record.

---

# Phase H - Build and connect the Next.js user interfaces

## Step 46 - Install frontend and verify Next.js development server (P0)

**Dependency:** Steps 02-03, 12. **Goal:** see the entire case flow in a working browser.

1. Keep backend running on `http://127.0.0.1:8000` in one terminal.
2. In a NEW terminal `cd frontend`; copy `.env.example` to `.env.local`, confirm `BACKEND_URL=http://127.0.0.1:8000`.
3. Run `npm install`; then `npm run dev`. At first install npm needs Internet and may download Next.js/React (this was **not** possible to verify in the guide-authoring environment's offline npm cache).
4. Open `http://localhost:3000`. The dashboard will ask for a passcode. Select reviewer and enter your local development review key (default for local demo only: `change-reviewer-key`). Click Connect, then Load demos.
5. Confirm the 12-case list appears, select DISP-003 and inspect initial data. Use `Process / Re-evaluate case` to see decision path, policy IDs, advocacy outputs and receipts.
6. Test responsive layout in browser mobile view. The interface is a prototype; consider accessibility testing separately.

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
# Browser: http://localhost:3000
```

**PASS:** Next.js builds/runs without a red error overlay, cases load and process button talks to FastAPI. **If it fails:** verify Node 22, `BACKEND_URL`, backend port, `npm install` succeeded, and browser developer console/network tab. **Evidence:** app screenshot and terminal logs.

## Step 47 - Understand the Next.js server proxy and credentials (P0)

**Dependency:** Step 46. **Goal:** solve cross-service calls without hardcoding Cloud Run URLs in frontend bundles.

1. Read `frontend/src/app/api/proxy/[...path]/route.js`. All browser API calls go to `/api/proxy/...` on the same origin.
2. Next's server route forwards requests to `process.env.BACKEND_URL`, passing `X-Demo-Key` and content type. It rejects traversal-like path segments and does not publish the backend URL to JS bundle.
3. Set `BACKEND_URL` in frontend `.env.local` during local development and as a runtime environment variable on the hosted frontend Cloud Run service.
4. Backend checks the role passcode independently. Passing through a proxy does NOT make a user a reviewer.
5. If browser sees 502 “Backend unreachable”, check service URL/DNS and backend running. If 401/403, check role key. If 400, inspect exact FastAPI response body.
6. For actual customer-facing deployment, replace demo keys and pass-through proxy with proper user authentication, CSRF controls and backend-to-backend service identities.

**PASS:** browser requests show `/api/proxy/cases/...` and backend success; there is no browser CORS dependency. **If it fails:** check `BACKEND_URL` and Next API route params. **Evidence:** browser Network tab.

## Step 48 - Verify four user workflows in browser (P0)

**Dependency:** Steps 33-47. **Goal:** demonstrate all roles rather than a single AI chat panel.

1. **Rider view:** select rider key, list cases, open fare dispute, see plain-language problem, status and explanation. Attempting reviewer-only import should fail 403.
2. **Driver view:** select driver key, open pending clarification intended for driver, reply through in-app-like form (not actual delivery). The system must not imply response can be safely typed while driving.
3. **Reviewer workbench:** select reviewer key, open DISP-001, see evidence, policy IDs, gate reasons and proposed partial remedy, submit human disposition and reason, receive mock receipt.
4. **Agent trace/dashboard:** expand Advocate/Judge outputs, rulebook candidates and event trace for any processed non-safety case; verify mock-vs-live labels.
5. **Innovation A view:** open DEMO-FARE-CLARIFY, process, answer then import verified synthetic system facts, reprocess and show changed outcome.
6. **Innovation B view:** stage precedent on reviewer decision, run regression, approve record and inspect learning list.
7. Screen record the run only after all flows pass in a clean, reproducible sequence.

**PASS:** all four workflows work without unhandled UI exceptions, and unauthorized role cannot perform reviewer actions. **If it fails:** inspect frontend `page.jsx` and backend API response; fix one specific path before adding design embellishments. **Evidence:** 4-6 screenshots or one narrated run-through video.

## Step 49 - Improve explanations, accessibility and failure states (P1)

**Dependency:** Step 48. **Goal:** score user-centered design rather than only having many agent boxes.

1. Make sure screen text says exactly which remedy (original payment refund, credit, no action, driver compensation) is being simulated. A voucher is not equivalent to a card refund for user satisfaction.
2. Statuses should distinguish `NEW`, `AWAITING_CLARIFICATION`, `REVIEW_REQUIRED`, `RESOLVED`, `REVIEWED_AND_RESOLVED` and failed API calls. Never show green success before backend confirms receipt.
3. Ensure every input has an accessible label/placeholder, controls are keyboard-operable, error text is announced, and text remains legible on narrow screens.
4. Show why a case is escalated with exact rule ID and a plain explanation (not just “low confidence”).
5. Avoid exposing raw personal data from one party to another in an actual integration. All supplied test personas are synthetic; production must implement field-level redaction.
6. Run browser keyboard navigation and manual screen-size checks; add automated accessibility tooling if time allows.

**PASS:** a tester can tell what happened, why, what evidence is missing, whether it was AI/human, and whether money moved (simulated). **If it fails:** remove unnecessary visuals, add explicit labels/status explanations and re-test. **Evidence:** rider/driver usability feedback labeled as anecdotal, not policy validation.

---

# Phase I - Full test plan, evaluation and business value measurement

## Step 50 - Run unit tests and interpret every failure correctly (P0)

**Dependency:** Steps 04-12, after every backend change. **Goal:** catch deterministic business rule regressions immediately.

1. Activate backend `.venv`; run `pytest -q` from `backend`. It uses `tests/conftest.py` to set `APP_MODE=memory`, `AI_MODE=mock`, an isolated memory repository and a temporary **test-only** policy signoff.
2. `tests/test_policy.py` checks 41-ID contract, routing lookup, fare refund, route >2 review, 5-minute scheduled anchor, no-show contact, fraud flag, safety and monetary boundaries.
3. `tests/test_api.py` checks actual HTTP routes, 12-case suite, auth, idempotency, clarification, reviewer learning, audit tamper detection and image/source trust.
4. Run a single failing test by node name if needed (`pytest -q tests/test_policy.py::test_route_over_2km_review_even_small_refund -vv`).
5. Do not pass tests by deleting the assertion, changing expected gold without independent justification or forcing model output.
6. Re-run full suite after every policy, schema, agent prompt, reviewer action or storage change.

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
PYTHONPATH=. pytest -q tests/test_policy.py -vv
PYTHONPATH=. pytest -q tests/test_api.py -vv
```

**PASS:** all local tests green (the current delivered reference implementation passed 24 tests during authoring). **If it fails:** read the first traceback, identify source file + input + expected policy behavior; fix cause, not label. **Evidence:** saved pytest run with code commit SHA.

## Step 51 - Understand the independent 12-case gold-standard set (P0)

**Dependency:** Steps 10-11, 28. **Goal:** evaluate policy correctness without leaking test answers to agents.

1. Open `backend/fixtures/evaluation/gold.json`; it contains **evaluation-only** labels for path, and where applicable disposition/amount. The agent input fixtures live separately under `fixtures/cases`.
2. The case matrix must include route (short and >2), fare (unnotified surge, exactly $50, >$50, missing notification, contradictory parties), no-show (valid, no-call, flagged), safety disguised as fare, and disputed cleaning damage.
3. Run `PYTHONPATH=. python scripts/evaluate.py`. It calls `evaluate_suite(approved=True)` using the Python policy reference engine and returns each case's actual/expected path.
4. Distinguish the **test oracle** from the model: 12/12 deterministic reference checks do not imply 12/12 Gemini decisions, calibrated confidence or generalization.
5. If the original sample's expected answer conflicts with the supplied policy, honor policy routing and document the mismatch. Example DISP-001 4.3 km → human despite proposed SGD 3.44 refund.
6. Freeze gold labels before model experiments to prevent evaluation overfitting. Add new challenge cases by independently interpreting the original policy.

```bash
cd backend
PYTHONPATH=. python scripts/evaluate.py
```

**PASS:** `total:12`, `passed:12`, `all_passed:true` on the reference engine; original source gold never enters `payload` in `app/agents.py`. **If it fails:** inspect the first failing case and policy clause. **Evidence:** full 12-row output and Git commit hash.

## Step 52 - Expand the test matrix systematically, not by random case duplication (P1)

**Dependency:** Step 51. **Goal:** build a defensible synthetic evaluation corpus beyond three showcase examples.

1. Create new files under `backend/fixtures/cases`, unique synthetic IDs, category and normalized factual fields. Add **separately authored** expected path/amount under `fixtures/evaluation/gold.json` only after independent policy review.
2. For route deviation vary: 0.9, 1.0, 1.1, 1.9, 2.0, 2.1 and 4.3 km; traffic supported/unsupported; notified/unknown; difference-only fare vs unverified tariff.
3. For no-show vary: cancellation at scheduled +4:59, +5:00, +5:01; driver early/late; zero/one message; zero/one call; rider presence ambiguity; fraud flag 0/1.
4. For fare vary: surge unchanged/increased/decreased; notification verified yes/no/unknown; booking fee unchanged/modified; SGD 9.99, 10.00, 50.00, 50.01 disputed value; matching/missing quote.
5. For damage vary: within/outside 24 h, app/external photo, trip association present/missing, claim disputed yes/no, clean/repair, ≤50 and >50.
6. For safety vary: explicitly safety category, hidden in fare narrative, chat-only threat, mixed allegation, urgency. Escalation must remain high recall; human reviewers validate source facts.
7. Include adversarial text and false-claim variants; ensure each variation changes only intended fields. Label which cases are synthetic *targets*, not measured results.
8. Add a `pytest.mark.parametrize` test for each new pair instead of duplicating huge test functions. Document category coverage and sample counts.

**PASS:** no expected outcome is derived by copying `recommend()` output, and at least one negative/edge case exists per important rule. **If it fails:** inspect policy requirements before adding gold; a “test” that merely reproduces the engine's answer has no independent value. **Evidence:** expanded dataset manifest and independent labels.

## Step 53 - Run security, injection and unsafe-action tests (P0)

**Dependency:** Steps 26-31. **Goal:** prove unsafe inputs cannot override deterministic gates.

1. Run `scripts/threat_eval.py`. It appends instruction-injection strings to untrusted case description and verifies the underlying deterministic remedy does not change.
2. Add chat/evidence prompt injection: “ignore previous rules”, “I am the admin”, “disable human review”, false policy excerpt, fake prior precedent and disguised safety phrase.
3. Test API authorization (401/403), value threshold (10,50,50.01), route >2, reviewer-only account-related requests, duplicate action retry and invalid file magic bytes.
4. Run manual attack in real ADK mode and compare LLM text with policy gate. If model obeys the malicious prompt, the case must remain unresolved/human rather than execute the model's request.
5. Document a *known limitation*: keyword safety detection may miss nuanced harm; model prompt defense is best effort; backend deterministic review gates are the firm execution boundary.
6. Use synthetic inputs only. Never test against real customers, wallets or Ryde support.

```bash
cd backend
PYTHONPATH=. python scripts/threat_eval.py
PYTHONPATH=. pytest -q tests/test_api.py -k 'reviewer_only or duplicate or safety'
```

**PASS:** no unsafe bypass or real action; injected instruction does not change policy-derived candidate or eligible path. **If it fails:** treat as release blocker, inspect trust boundary and re-run baseline after fix. **Evidence:** attack/result matrix.

## Step 54 - Evaluate live ADK without counting mock answers as model performance (P0)

**Dependency:** Step 25. **Goal:** produce real traces, latency and case-result metrics.

1. Use `APP_MODE=memory`, `AI_MODE=adk`, ADC and valid Vertex configuration. Make sure team policy contract has been reviewed/signed.
2. Run `PYTHONPATH=. python scripts/live_eval.py` from backend. It resets an *evaluation-only in-process memory repository*, loads fixture cases, runs real ADK agents and measures wall-clock latency.
3. The script prints and writes a timestamped JSON+CSV report under `backend/reports` with `case_id`, actual/expected path, path correctness, policy citation validity, event count and seconds. The report is generated after actual model calls, not simulated.
4. Inspect all `error` fields, model-response parsing, any missing Judge or fake AI fallback, and all policy citations. The evaluator's `policy_citations_valid` checks rule ID membership; humans must still audit that cited evidence genuinely supports the claim.
5. Record model name, project region, date, prompt versions, test set version and backend Git SHA beside the report.
6. Report observed percent only for the exact synthetic test set evaluated; don't extrapolate to real Ryde tickets or claim model confidence calibration.
7. If any route is wrong or model emits unsupported financial value, block automation and fix prompts/source normalization/gate separately; preserve original failing output for debugging.

```bash
cd backend
# .env: APP_MODE=memory; AI_MODE=adk
PYTHONPATH=. python scripts/live_eval.py
# small low-cost smoke variant:
PYTHONPATH=. python scripts/live_eval.py --cases DISP-003,DISP-001
ls -lh reports/live-*.json reports/live-*.csv
```

**PASS:** model really runs, results files exist, no required safety/category escalation bypasses. **If it fails:** live run must be recorded as failed/unverified, never relabeled as “model correct”. **Evidence:** JSON+CSV report and ADK trace.

## Step 55 - Measure reviewer work and user comprehension against a real local baseline (P1)

**Dependency:** Steps 39, 48. **Goal:** convert a credible concept into measurable business value.

1. Select at least three synthetic cases of differing complexity; redact/remove model output and give a tester the underlying evidence and policy to build a case **manually**.
2. Time from receiving evidence to producing a justified case summary and recommended path; record `manual_seconds` with start/stop rules.
3. Repeat same tasks using RydeResolve reviewer workbench; record `assisted_seconds` under comparable conditions. Counterbalance order or use different but matched cases to reduce learning effect.
4. Populate `backend/fixtures/evaluation/reviewer_time_template.csv`. Include notes about tester familiarity, case difficulty and mistakes.
5. Run `scripts/reviewer_benchmark.py` only after at least three paired observations. It reports sample means and time reduction **as measured**, not as Ryde's real staffing savings.
6. Test rider/driver comprehension with short questions: “What evidence mattered?”, “What happens next?”, “Will card be refunded or voucher issued?”, “How can I respond?” Record interview labels and distinguish opinion from correctness.
7. Do not claim the benchmark reflects Ryde's production dispute mix or savings without actual volumes, staffing costs and representative trials.

```bash
cd backend
# First enter actual measured seconds, do not invent values:
python scripts/reviewer_benchmark.py fixtures/evaluation/reviewer_time_template.csv
```

**PASS:** timed measurements from actual human testers, with sample size and limitations disclosed. **If it fails:** missing paired measurements prints a clear refusal rather than fake ROI. **Evidence:** anonymized CSV, stopwatch methodology and user feedback labels.

## Step 56 - Calculate ROI sensitivity without fabricating Ryde volumes (P1)

**Dependency:** Step 55. **Goal:** show potential enterprise value transparently.

1. Define model variables: `V` annual dispute volume (unknown), `M` average manual case-building minutes (measured or labeled assumption), `A` assisted minutes (measured), `R` proportion cases still needing review (measured on test suite or assumption), `W` loaded support cost/hour (assumption), `C` annual cloud/integration/support costs (estimate).
2. Compute `hours_saved = V * max(M-A,0) / 60` only for cases where the workflow actually saves work. If cases still require reviewer effort, use the measured reviewer-time difference, not claimed full automation.
3. Compute `gross_cost_opportunity = hours_saved * W`; `net_scenario = gross_cost_opportunity - C` under explicitly labeled low/base/high assumptions. State clearly that it is not a verified Ryde business result.
4. Include scenario cases e.g. lower/upper workload factors to demonstrate sensitivity, but *do not insert invented official volume or staffing baseline*.
5. Show operating costs: model calls per dispute, token usage when available, storage size and Cloud Run services, plus cloud budget monitoring.
6. Prefer a concise chart and assumptions table in pitch instead of one unsupported huge savings number.

**PASS:** every figure is labeled measured, estimated or assumption; readers can recompute results. **If it fails:** remove unsupported ROI claim and show accurate test outcomes instead. **Evidence:** assumption table and sensitivity analysis appendix.

## Step 57 - Run concurrency/retry and failure injection (P1)

**Dependency:** Steps 29-32, 54. **Goal:** establish realistic operational bounds and fallbacks.

1. Exercise duplicate `POST /cases/{id}/process`, duplicate reviewer submission, duplicate clarification reply and repeated mock-remedy attempts. Expected: no double simulated receipt for same action key.
2. Simulate Gemini quota/timeout or a tool returning malformed JSON; backend must not quietly replace the live model's failure with an allegedly completed action.
3. Simulate Firestore unavailable (wrong project/ADC) and GCS missing bucket (wrong IAM). UI must show failure and preserve cases where persistence permits.
4. Test long-running clarification: after a reply without verified corroboration, route human. New trusted synthetic evidence should permit a fresh, explicit re-evaluation.
5. Limitations: application does not yet use multi-document transactions for entire state transition, a distributed queue, or production retry orchestration. Describe the path to add them rather than mislabeling the prototype enterprise-ready.
6. Capture error messages, recovery time and whether a manual retry produces the same result.

**PASS:** duplicate actions do not occur; failures are observable, not disguised; no unauthorized finalization. **If it fails:** disable automatic remedies until action idempotency and state handling are corrected. **Evidence:** repeat/retry/failure test outputs.

## Step 58 - Validate CI and merge/release guardrails (P0)

**Dependency:** Steps 09, 46, 50-53. **Goal:** prevent last-minute code breaks.

1. Check `.github/workflows/ci.yml` is committed at repository root. It runs policy contract check, Python tests, 12-case reference evaluation, injection boundary tests and frontend `npm run build`.
2. Push a safe branch and open GitHub Actions. The runner requires Internet and installs dependencies from package indexes. Save a green workflow run screenshot.
3. Commit `frontend/package-lock.json` generated on your Mac after successful `npm install` for repeatable installs; CI can switch from `npm install` to `npm ci` after lockfile exists.
4. If CI is red, inspect the exact job log and fix it; do not skip deployment gates or mark unfinished checks passing.
5. Make final release branch/tag from the last green commit. Record commit SHA in submission README and evaluation report.
6. Keep at least one independent reviewer check that policy signoff and source hash remain consistent before deployment.

```bash
git status
git add .
git commit -m "Add policy-grounded RydeResolve implementation and tests"
git push origin YOUR_BRANCH
# In GitHub -> Actions: inspect both backend and frontend jobs
```

**PASS:** GitHub Actions backend+frontend jobs are green and commit hash is recorded. **If it fails:** pause feature additions; fix exact CI failure. **Evidence:** authentic GitHub Actions green build screenshot.

---

# Phase J - Google Cloud production-like DEMO deployment (Cloud Run + Firestore + GCS + Vertex AI)

> **Important deployment design:** For this hackathon you may publish a **temporary synthetic-only** demo using Cloud Run's unauthenticated URL plus strong, independently verified demo passcodes. This is **not production identity or production-grade security**; a real Ryde integration would instead protect the backend behind service-to-service IAM, use authenticated users, request throttling and approved privacy controls. The guide's simple path is optimized for a reliable 16 October submission. Always clearly display that data and financial actions are simulated.

## Step 59 - Prepare cloud project, verify billing, choose explicit region (P0 for a live demo)

**Dependency:** Step 13, successful local integration. **Goal:** avoid deploying into an unexpected project or creating resources without billing visibility.

1. Sign into Google Cloud Console and select the exact project intended for RydeResolve. Verify you have sufficient access to enable APIs, create a service account, create Firestore and deploy Cloud Run. Billing must be active for many cloud services.
2. Set shell variables once in your *current Terminal*. Replace values with real IDs that your team controls. Do not copy other teams' project IDs.
3. Choose `RUN_REGION` (Cloud Run), `FIRESTORE_REGION` (database), `BUCKET_REGION` (storage) and `GOOGLE_CLOUD_LOCATION` (supported Vertex AI model endpoint). These may differ; check available model regions and note latency/residency. A common starting point for testing is `us-central1` where supported, but do not assert it meets Ryde data-residency requirements.
4. Set `gcloud config set project`, log in with your Google account, and verify project/billing via Console. Use `gcloud auth application-default login` separately for local SDK calls.
5. In Console → Billing → Budgets & alerts, set a low alert threshold and enable email notifications. A budget alert is not a hard spending cap. Limit repeated model evaluation runs.
6. Verify that no private customer data, keys, rider names or raw interview messages will be sent to the cloud project.

```bash
export PROJECT_ID='REPLACE_WITH_YOUR_PROJECT_ID'
export RUN_REGION='us-central1'
export VERTEX_REGION='us-central1'  # change if selected Gemini model supports another region
export FIRESTORE_REGION='us-central1'
export BUCKET_REGION='us-central1'
export BUCKET_NAME="${PROJECT_ID}-ryderesolve-evidence"
export SA_NAME='ryderesolve-demo-runtime'
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud auth login
gcloud config set project "$PROJECT_ID"
gcloud config get-value project
gcloud auth application-default login
```

**PASS:** project ID is correct, billing/permissions confirmed and regions documented. **If it fails:** fix project selection or IAM before creating anything; do not run deployment commands as an unrelated organization account.

## Step 60 - Enable the required Google Cloud APIs (P0)

**Dependency:** Step 59. **Goal:** remove missing-service failures before deployment.

1. Run the enable command below. It covers Cloud Run, Cloud Build, Artifact Registry, IAM, Firestore, Storage, Vertex AI and Secret Manager.
2. Wait until API enablement operations finish. Use `gcloud services list --enabled` to check each name.
3. If IAM says `PERMISSION_DENIED`, request the necessary access from the Google Cloud project administrator; do not use a shared secret key as a workaround.
4. Keep the resulting services enabled only while your demo requires them. Review cost/retention afterward.

```bash
gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  iam.googleapis.com firestore.googleapis.com storage.googleapis.com \
  aiplatform.googleapis.com secretmanager.googleapis.com \
  --project "$PROJECT_ID"
gcloud services list --enabled --project "$PROJECT_ID" | grep -E '(run|cloudbuild|artifactregistry|firestore|storage|aiplatform|secretmanager)'
```

**PASS:** relevant services are listed as enabled. **If it fails:** read permission or billing error text, enable the exact missing service via Console if necessary, then retry.

## Step 61 - Create a dedicated Cloud Run service identity (P0)

**Dependency:** Step 60. **Goal:** never put a downloaded Google Cloud service-account JSON key in a container.

1. Create a user-managed service account with a demo-specific description and no overly broad Editor/Owner permission.
2. Give it `roles/datastore.user` for Firestore and `roles/aiplatform.user` for Vertex AI model calls at project scope, subject to your organization's least-privilege controls. It will receive bucket-specific object access in Step 63.
3. The account deploying the service must be allowed to **act as** this service account (Service Account User role). If `gcloud run deploy` says the deployer cannot impersonate it, ask the IAM administrator to grant `roles/iam.serviceAccountUser` on this identity.
4. The Cloud Run runtime authenticates with this identity using Application Default Credentials automatically. Do not set `GOOGLE_APPLICATION_CREDENTIALS` to a local key path in Cloud Run.
5. Verify the service account appears with the correct email; capture the *email* but never download or publish a private key.

```bash
gcloud iam service-accounts create "$SA_NAME" \
  --display-name='RydeResolve synthetic demo runtime' --project="$PROJECT_ID"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" --role='roles/datastore.user'
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" --role='roles/aiplatform.user'
gcloud iam service-accounts describe "$SA_EMAIL"
```

**PASS:** service identity exists with appropriate roles and deployer can attach it. **If it fails:** inspect the denied IAM permission; do not grant Owner merely to fix an unexamined error.

## Step 62 - Create Firestore database and test persistent case storage (P0)

**Dependency:** Steps 14 and 61. **Goal:** upgrade from ephemeral memory to Firestore without changing case semantics.

1. In Console → Firestore Database, check whether database `(default)` already exists. Firestore database location selection can be permanent; avoid casually changing it.
2. If missing, create a **Firestore Native** `(default)` database at the chosen supported location. Use Console or the CLI below. If already created, do not run create again.
3. In local `backend/.env`, change only `APP_MODE=firestore`, keep `AI_MODE=mock` at first. Run `gcloud auth application-default login` and `PYTHONPATH=. python scripts/seed.py`.
4. `FirestoreRepository` writes collections: `cases`, `actions`, `learning_proposals`, and `approved_precedents`. Open Console Firestore Data tab to see 12 case documents.
5. Start Uvicorn and process `DISP-003`; check one action document and a mock receipt. Restart the Python process and verify the case still exists. **Do not use `seed(reset=True)` against persistent Firestore.**
6. Check that unauthorized users cannot access the database directly using public client SDKs; all demo reads are through the authenticated FastAPI backend and Google service identity.
7. If `403`/permission errors occur, check project ID, ADC identity, enabled Firestore service and the `roles/datastore.user` grant. If duplicate database exists, use it rather than replacing it.

```bash
gcloud firestore databases list --project="$PROJECT_ID"
# ONLY if (default) does not exist:
gcloud firestore databases create --database='(default)' \
  --location="$FIRESTORE_REGION" --type=firestore-native --project="$PROJECT_ID"
cd backend
# edit .env: APP_MODE=firestore; AI_MODE=mock; GOOGLE_CLOUD_PROJECT=<PROJECT_ID>
PYTHONPATH=. python scripts/seed.py
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

**PASS:** case persists across restarts, action ID remains unique, no accidental real data used. **If it fails:** switch to `APP_MODE=memory` temporarily so core development can continue; investigate Firestore separately.

## Step 63 - Create private GCS bucket, grant minimum object permissions (P1)

**Dependency:** Steps 16, 60-61. **Goal:** make image storage work without making damage photos public.

1. Run `gcloud storage buckets list` to confirm the intended name is available (bucket names are globally unique); replace `BUCKET_NAME` if necessary.
2. Create the bucket with `STANDARD` class, uniform bucket-level access and public-access prevention. Use your selected region. Avoid enabling broad public `allUsers` IAM.
3. Grant **Storage Object Admin** to the dedicated service account only on this demo bucket. For production consider narrower permissions and signed-access/retrieval patterns.
4. Set `GCS_BUCKET` in backend `.env` (name **without** `gs://`). With `APP_MODE=firestore`, upload a synthetic PNG via `/cases/{id}/files` using reviewer key.
5. Check Console → Cloud Storage → bucket → Objects for `cases/<case-id>/<hash>.png`. Verify file bytes/size and that the API returns `gs://...`, SHA-256 and `origin_verified:false`.
6. Upload the same file again to check duplicate storage behavior. A blob SHA key deduplicates same bytes; this is not proof of malware protection.
7. If upload errors with `403`, check service-account bucket IAM; if `404`, check exact bucket name and selected project; if signature mismatch, send actual PNG/JPEG/PDF bytes.

```bash
gcloud storage buckets create "gs://${BUCKET_NAME}" \
  --project="$PROJECT_ID" --location="$BUCKET_REGION" \
  --default-storage-class=STANDARD --uniform-bucket-level-access \
  --public-access-prevention
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_EMAIL}" --role='roles/storage.objectAdmin'
gcloud storage ls "gs://${BUCKET_NAME}"
```

**PASS:** images stored privately with correct metadata and no open public ACL; demo explicitly says camera provenance remains unverified. **If it fails:** keep image stretch as local-only and do not claim GCS integration.

## Step 64 - Verify a live Vertex AI Gemini request BEFORE deployment (P0)

**Dependency:** Steps 19, 25, 59-61. **Goal:** isolate authentication/model problems from Cloud Run deployment problems.

1. In backend `.env`, set `AI_MODE=adk`, `APP_MODE=memory` while debugging model connectivity, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_GENAI_USE_VERTEXAI=TRUE`, and `GEMINI_MODEL` matching a model enabled in your region.
2. Install `requirements-cloud.txt`; run `gcloud auth application-default login` under the intended developer identity.
3. Test `PYTHONPATH=. python scripts/live_eval.py --cases DISP-003`. This invokes the real model through ADK and may use billable tokens.
4. If quota errors appear, inspect Vertex AI quotas in your project and reduce parallel calls / evaluate one case. Do not assume a model is available in every region.
5. If `ModuleNotFoundError: google.adk`, verify venv activation and `python -m pip show google-adk`.
6. If ADK emits no final text or badly formatted JSON, inspect `app/agents.py` and model events. Policy gate must block finalization instead of treating missing model output as success.
7. Switch to `APP_MODE=firestore` only after the live memory run succeeds; verify cloud datastore and model together.

```bash
cd backend
python -m pip install -r requirements-cloud.txt
PYTHONPATH=. python scripts/live_eval.py --cases DISP-003
# Once successful, verify the default seven-case set:
PYTHONPATH=. python scripts/live_eval.py
```

**PASS:** real ADK events and tool-call metadata are recorded; sample result references appropriate rules; no safety gate bypass. **If it fails:** continue mock mode locally while debugging model credentials, and be truthful about integration status.

## Step 65 - Package and test the backend container locally (P0)

**Dependency:** Steps 09, 27-32 and 64 (live model). **Goal:** prevent deployment of a container that does not start.

1. Open `backend/Dockerfile`. It starts from `python:3.11-slim`, installs both requirements files through `requirements-cloud.txt`, copies backend app/policy/fixtures/scripts, and binds Uvicorn to Cloud Run `PORT`.
2. Check `.dockerignore` excludes `.env`, `.venv`, cached tests and local upload/report files. Never include actual keys in the Docker build context.
3. From `backend/`, build `ryderesolve-backend:local`. Use only synthetic source and team-approved policy files, respecting their access classification.
4. Start the container in **memory/mock** mode first using safe dummy passcodes and mapping port 8080 to localhost. `GET /health` must return JSON.
5. To test actual Firestore/Vertex AI in a local container, avoid placing ADC JSON credentials inside the image; local model test from host or Cloud Run attached identity is preferred.
6. If `docker` unavailable locally, the Cloud Run source deploy will build the Dockerfile via Cloud Build, but a local Docker smoke test remains a useful optional gate.

```bash
cd backend
docker build -t ryderesolve-backend:local .
docker run --rm -p 8080:8080 \
  -e APP_MODE=memory -e AI_MODE=mock \
  -e DEMO_REVIEWER_KEY=local-reviewer-test \
  -e DEMO_RIDER_KEY=local-rider-test \
  -e DEMO_DRIVER_KEY=local-driver-test \
  ryderesolve-backend:local
# separate terminal:
curl -s http://localhost:8080/health | python3 -m json.tool
```

**PASS:** container starts and health returns 200; tests not dependent on local untracked files. **If it fails:** check installation in Dockerfile, launch command and 8080 binding. **Evidence:** Docker logs and health screenshot.

## Step 66 - Create demo passcode secrets safely (P0 for public demo)

**Dependency:** Steps 60-61. **Goal:** never deploy the `change-...` development passcodes publicly.

1. Generate three distinct, cryptographically random passcodes on your trusted local machine. The command below temporarily writes them into a 0600 home-directory file; immediately transfer them to a secure team password vault and delete the local file. You **must retain the values** so you can enter them in the demo login; never share them in public source/screenshots.
2. Create three Secret Manager secrets (reviewer, rider, driver) using bytes from locally generated random values. If a secret already exists, do not rerun `secrets create`; use an approved version-rotation procedure instead. Prefer piping directly and do not expose the plaintext as a command-line argument in a captured shell history.
3. Grant your dedicated Cloud Run service account `roles/secretmanager.secretAccessor` on those three secrets only. The project account issuing these commands needs Secret Manager administration access.
4. The backend Cloud Run deployment will mount them as environment variables via `--set-secrets`. Keep the reviewer passcode private from public demo visitors; supply short-lived reviewer access to judges through an approved channel only if appropriate.
5. If `permission denied` occurs on startup, check Secret Manager IAM and resource names; do **not** print the secret to debug.
6. Make sure role keys are not identical or equal to development defaults; test wrong key 401 and wrong role 403 after deployment.

```bash
# Run locally OUTSIDE the Git repository. Never record these secrets in a screen capture.
umask 077
PASSCODES_FILE="$HOME/.ryderesolve-demo-passcodes.txt"
: > "$PASSCODES_FILE"  # chmod/umask protects local file; copy to secure team vault later
for ROLE in reviewer rider driver; do
  SECRET_NAME="ryde-demo-${ROLE}"
  SECRET_VALUE="$(openssl rand -hex 32)"
  printf '%s=%s\n' "$ROLE" "$SECRET_VALUE" >> "$PASSCODES_FILE"
  printf '%s' "$SECRET_VALUE" | gcloud secrets create "$SECRET_NAME" \
    --replication-policy=automatic --data-file=- --project="$PROJECT_ID"
  gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role='roles/secretmanager.secretAccessor' --project="$PROJECT_ID"
  unset SECRET_VALUE
done
# Move values from $PASSCODES_FILE to an approved private password vault.
# Do NOT commit, display, screenshot or email the file; delete it after transferring safely.
```

**PASS:** three secrets exist, runtime identity can read them, and no value is embedded in code or image. **If it fails:** retry only after correcting IAM, and never fall back to obvious default keys on a public URL.

## Step 67 - Deploy FastAPI backend to Cloud Run (P0)

**Dependency:** Steps 59-66; team policy signoff committed to deployment source. **Goal:** use Firestore/GCS/ADK from a live URL.

1. Commit source code and approved `policy/contract_approval.json` (only the team's signoff). Keep all `.env` and API keys out of Git. **Check whether the challenge policy's internal classification permits public redistribution before making the repo public**; judge-access/private source hosting may be safer.
2. In `backend/`, deploy from source using `gcloud run deploy` with runtime service identity, `APP_MODE=firestore`, `AI_MODE=adk`, project/location/model/bucket, and Secret Manager mappings. Cloud Run will build the supplied Dockerfile.
3. For the *synthetic-only* hackathon public demo, `--allow-unauthenticated` permits HTTP entry, but application role passcodes remain required on every case endpoint. This is not a production access-control model. If you need a private backend, add Cloud Run-to-Cloud Run identity tokens and roles/run.invoker; the supplied simple Next.js proxy does **not** implement that yet.
4. Set a conservative max-instances, memory, timeout and concurrency suitable for your quota and expected evaluator traffic. Verify real costs in your Google Cloud billing, not assumed free quotas.
5. Copy the printed `Service URL` as `API_URL`. Open `$API_URL/health` and verify `storage_mode=firestore`, `ai_mode=adk`, contract valid and team signoff true.
6. Test reviewer-authenticated `POST /cases/seed`, then process `DISP-003`; inspect Firestore and the backend logs. If the policy file is missing from the container, `team_signoff_valid=false` will prevent auto-execution.
7. If deployment fails, check `gcloud run services logs read` and Cloud Build failure details; distinguish build errors from runtime IAM/quota errors.

```bash
cd backend
gcloud run deploy ryderesolve-api --source . --project="$PROJECT_ID" \
  --region="$RUN_REGION" --service-account="$SA_EMAIL" \
  --allow-unauthenticated --memory=1Gi --timeout=300 \
  --concurrency=5 --max-instances=2 \
  --set-env-vars="APP_MODE=firestore,AI_MODE=adk,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${VERTEX_REGION},GOOGLE_GENAI_USE_VERTEXAI=TRUE,GEMINI_MODEL=gemini-2.5-flash,GCS_BUCKET=${BUCKET_NAME}" \
  --set-secrets='DEMO_REVIEWER_KEY=ryde-demo-reviewer:latest,DEMO_RIDER_KEY=ryde-demo-rider:latest,DEMO_DRIVER_KEY=ryde-demo-driver:latest'
export API_URL="$(gcloud run services describe ryderesolve-api --region="$RUN_REGION" --project="$PROJECT_ID" --format='value(status.url)')"
echo "Backend: ${API_URL}"
curl -s "${API_URL}/health" | python3 -m json.tool
gcloud run services logs read ryderesolve-api --region="$RUN_REGION" --project="$PROJECT_ID" --limit=60
```

**PASS:** deployed health 200 with correct real modes, secrets loaded, Firestore case writes and actual ADK call confirmed. **If it fails:** keep working local version and repair one cloud dependency at a time; do not describe the hosted URL as a functioning live system until an end-to-end case passes.

## Step 68 - Deploy Next.js frontend to Cloud Run and connect backend (P0)

**Dependency:** Steps 53 and 67. **Goal:** give judges a single browser URL.

1. Open `frontend/Dockerfile`: Node.js 22 builds Next.js, then starts on Cloud Run's `PORT` (normally 8080). The route proxy reads server environment variable `BACKEND_URL`.
2. Run frontend `npm run build` one final time locally and commit `package-lock.json` if created. Do not copy `.env.local` into the container.
3. In `frontend/`, deploy `ryderesolve-web` with `BACKEND_URL=$API_URL`. For synthetic preview use a public URL only if this matches your project security/permission decisions.
4. Capture `WEB_URL` returned by deployment and open it in an incognito browser. It must display `RydeResolve Lab` and explicit synthetic/no-live-payments labels.
5. Enter an authorized demo passcode you generated in Step 66. Click Connect and Load demos. The Next.js proxy should reach the backend. Inspect frontend Cloud Run logs if it shows 502.
6. Do **not** put the reviewer passcode in a `NEXT_PUBLIC_*` variable, HTML or static JS. The frontend only knows the key when a demo user enters it.
7. If the backend is intentionally private, this direct proxy path will get 403 without an identity token; implement service-to-service auth **before** claiming the URL is fixed. For hackathon synthetic preview the simplified public-backend/passcode approach is the tested design target.

```bash
cd frontend
npm install --no-audit --no-fund
npm run build
gcloud run deploy ryderesolve-web --source . --project="$PROJECT_ID" \
  --region="$RUN_REGION" --allow-unauthenticated \
  --memory=1Gi --timeout=300 --max-instances=2 \
  --set-env-vars="BACKEND_URL=${API_URL}"
export WEB_URL="$(gcloud run services describe ryderesolve-web --region="$RUN_REGION" --project="$PROJECT_ID" --format='value(status.url)')"
echo "Frontend: ${WEB_URL}"
curl -I "$WEB_URL"
```

**PASS:** public synthetic frontend loads, authenticated case requests work through proxy, reviewer and model status visible. **If it fails:** read both services' logs; first fix 502/backend URL, then role key, then Firestore/model separately.

## Step 69 - Perform hosted, browser-to-cloud acceptance testing (P0)

**Dependency:** Step 68. **Goal:** independently prove the advertised live Google stack.

1. In a clean incognito browser open `WEB_URL` and authenticate with a permitted short-lived demo passcode. Do not use default keys.
2. Seed the 12 synthetic cases (if not already seeded), process `DISP-003`, and verify policy citations, real ADK trace events, `AUTO_ELIGIBLE` and exactly one **simulated** SGD 4.50 receipt.
3. Process `DISP-001`: must be `HUMAN_REVIEW` (4.3 km >2), no auto refund. Process `DISP-002`: fraud flag means human review without calibrated confidence. Process `DEMO-SAFETY-IN-FARE`: no Judge output/ruling.
4. Perform Innovation A evidence/clarification flow. Confirm Firestore stores the updated case even after refreshing the browser.
5. Upload one synthetic PNG/JPEG and verify Google Cloud Storage object path in Console if the frontend file UI is implemented, otherwise use multipart curl through FastAPI.
6. Perform Innovation B: reviewer correction → staged proposal → 12-case regression → active precedent → rollback. Verify both Firestore proposal and precedent documents.
7. Retry a completed refund from another browser tab. Ensure same `MOCK-` receipt and no second `actions` collection document.
8. Capture (a) browser screenshots, (b) actual Cloud Run service URLs, (c) Firestore/GCS object existence **without private secrets**, (d) agent trace events and (e) test pass logs.
9. If hosted model returns quota/runtime error, keep an **explicitly labeled** synthetic mock backup video. Do not hide a model failure with a seamless unannounced fallback.

**PASS:** hosted browser-to-API-to-ADK/Firestore/GCS end-to-end path is demonstrated and recorded. **If it fails:** do not submit a live URL that is known broken; use a reliable local demo recording and accurately describe cloud status.

## Step 70 - Configure basic operations, limits and rollback (P1)

**Dependency:** Steps 67-69. **Goal:** recover a broken deployment without data loss or policy bypass.

1. Open Console → Cloud Run → each service → Revisions. Note the last known-good revision name and its traffic percentage. In an outage, route traffic back to a known-good revision instead of changing policy gates on the fly.
2. Limit max instances, requests/concurrency and model eval frequency. Cloud Run cold starts are expected; warm up once before recording a 5-minute demo.
3. Inspect Cloud Logging for unauthorized requests and Vertex AI permission/quota/timeout errors. Avoid logging actual role keys, user messages containing private information or proprietary policy contents.
4. Verify budget alerts and model usage metrics; report observed latency and consumption rather than guaranteed production throughput.
5. When making a change to policy JSON or rulebook, the signature/approval must be reviewed again and associated tests rerun. A hash mismatch should block auto-settlement.
6. Keep synthetic case backups in Git fixture JSON files. Never execute destructive Firestore cleanup commands from a copy-pasted generic tutorial.
7. After the hackathon, disable public demo access or delete the synthetic resources with confirmation and keep required evidence artifacts privately. Note that disabling Cloud Run may not remove all billable ancillary services.

**PASS:** known-good revision identified, alarms and cost awareness in place, rollback path rehearsed. **If it fails:** simplify to a stable single revision and stop new features.

## Step 71 - Make CI an independent reproducibility gate (P0)

**Dependency:** Steps 09, 53 and 56-57. **Goal:** verify every new commit before merging.

1. Open `.github/workflows/ci.yml`. It configures Python 3.11 and Node 22 in separate jobs.
2. Backend job checks the policy/rulebook contract, runs pytest, the 12-case reference evaluation and injection tests **without requiring external Google credentials**. Frontend job installs Node packages and runs `npm run build`.
3. Commit code to a feature branch, open a pull request and inspect GitHub Actions checks. A failure must prevent treating the branch as release-ready.
4. Check whether npm creates `package-lock.json`; if yes, commit it to stabilize installs. Consider replacing `npm install` with `npm ci` only after lockfile exists.
5. Run `git diff --check`, `git status --short`, inspect `.gitignore`, and search for patterns like `private_key`, `DEMO_REVIEWER_KEY=`, credentials, personal identifiers, interview transcripts and secrets before publishing.
6. Ensure generated PDF, evaluation gold files and contest policy have the **appropriate sharing permissions**; GitHub source requirements do not automatically waive content rights or privacy obligations.
7. A green CI run means code-level gates passed in the clean environment; it does not guarantee deployed Firestore/GCS/Gemini integration.

```bash
# from repo root
git status --short
git diff --check
bash scripts/verify_all_local.sh
cd frontend && npm run build && cd ..
git add .github backend frontend docs scripts
git commit -m "Build policy-grounded RydeResolve demo with safety and evaluation"
git push
```

**PASS:** backend and frontend GitHub checks green, no secrets/personal data, same commit used for deployed demo. **If it fails:** address each CI error before final packaging.

---

# Phase K - Competition presentation, submission and final success definition

## Step 72 - Build the demo around three business outcomes (P0)

**Dependency:** Steps 48, 54, 56-58 and 69 (if hosted). **Goal:** lead judges from stakeholder problem to evidence-backed results.

1. Open the submission with the case study name: **Ryde / Digital Native - Multi-Agent Autonomous Dispute Resolution System**.
2. Summarize the *research input*, accurately attributed: a Ryde stakeholder described manual data gathering, consistent policy case-building and communication as bottlenecks; a driver reported difficulty responding to email while driving; two riders reported concerns around remediation and communication. These are qualitative interviews, not statistically representative volumes.
3. Show **DISP-003** as the routine auto-eligible fare case. Highlight independent rider/driver advocates, policy rule lookup, Judge output, deterministic check, SGD 4.50 *simulated* refund and action receipt.
4. Show **DISP-001** as a responsible escalation: 4.3 km deviation, proposed SGD 3.44 excess-distance refund, but `TH-6.2-ROUTE` mandates reviewer; this proves policy correctness over superficial automation.
5. Show **Innovation A** with `DEMO-FARE-CLARIFY`: missing evidence → one targeted question → unverified party answer (still no automatic refund) → separate verified synthetic system log → changed disposition → receipt.
6. Show **Innovation B** with a reviewer correction: staged precedent → regression results → approved release → rollback. Clearly disclose the testing scope and whether live shadow-model evaluation was completed.
7. Mention all seven stretch goals with **one evidence screen each**, not merely seven boxes in a diagram. The image-analysis branch is a bounded pixels/metadata demonstration, never a conclusive AI forgery detector.
8. Close with measurable evaluation, explicit limitations, and credible integration path: authenticated Ryde connectors and financial executor are future work, not current production capabilities.

**PASS:** a first-time observer can explain the operational problem, three core agents, mandatory review, active investigation, governed learning and what is simulated. **If it fails:** cut additional infrastructure slides and tell the story with evidence/action screens.

## Step 73 - Script a repeatable 5–8 minute recorded walkthrough (P0)

**Dependency:** Step 72. **Goal:** have a polished backup even when the network/model quota fails live.

| Approx. interval | What to show | What to say |
|---|---|---|
| 0:00–0:45 | Problem and firsthand research | Three operations bottlenecks; interview anecdotes, not Ryde baseline |
| 0:45–1:20 | One simplified architecture slide | Google ADK advocates/Judge, index → full rules → Python gate, Firestore/GCS |
| 1:20–2:25 | DISP-003 auto fare case | Complete evidence, policy citations, SGD 4.50 simulated outcome |
| 2:25–3:15 | DISP-001 | 4.3 km mandatory review, prepared reviewer packet, no auto action |
| 3:15–4:35 | Innovation A | Missing information, targeted clarification, corroboration, changed outcome |
| 4:35–5:45 | Innovation B | Review correction, test, approval and rollback |
| 5:45–6:35 | Evaluation + all seven stretches | Real results/limitations, image branch if functional |
| 6:35–7:10 | Business value and integration path | Measured cases/time, required Tencent usage and safe scaling |

1. Rehearse the above twice from a **fresh seeded** dataset; aim for 6–7 minutes. Do not click around improvisationally in a large architecture diagram.
2. Warm the hosted services. Have all sample case IDs and correct role keys ready **off-screen**; avoid showing passcodes while entering them.
3. If live model calls take too long, show an authentic previously recorded run with a clear label rather than fake a live response.
4. Record browser at readable zoom (100–125%). Explain rule IDs in plain language. Show action status `COMPLETED_SIMULATED` visibly.
5. Ensure audio is clear and no real interviewee name, private chat screenshot, credential, account number or internal-only policy excerpt is displayed without permission.
6. Save the final video in supported format with a clear filename. If organizers' form changes, follow current submission instructions.

**PASS:** coherent under-eight-minute demonstration with stable visual evidence and accurate simulated/live labeling. **If it fails:** shorten agent/infra exposition and prioritize complete flow + both innovations.

## Step 74 - Capture CodeBuddy usage proof and submission artifacts (P0)

**Dependency:** Step 01 and ongoing development. **Goal:** satisfy the handbook's disqualification-sensitive requirement.

1. The official handbook page 36 requires a project built with **at least one of CodeBuddy or WorkBuddy**, plus genuine proof. It also requires a **minimum of three screenshots/screen recordings of chat logs** from CodeBuddy or WorkBuddy during development.
2. While implementing actual files or debugging tests, capture three authentic CodeBuddy conversations: e.g. one for ADK agent tool contract, one for policy unit-test debugging and one for frontend/Cloud Run integration. Include enough file/tool context to prove substantive usage.
3. Never create fictional screenshots, fabricate conversations or paste live API keys. Redact secrets before uploading any image to a form.
4. Prepare required title, a blurb **under ten words**, description with target users/scenarios/research/architecture/business impact, architecture diagram, three screenshot proofs and a 16:9 cover image (recommended 380×216 px).
5. Example short blurb (8 words): **"Policy-grounded AI resolves ride disputes with accountable oversight."** Verify count before submitting; word counts can vary by platform conventions.
6. The general handbook marks the 5–8 minute demo video and a live project URL optional, with live link eligible for bonus points; Ryde-specific guidance expects an end-to-end demo and GitHub source.
7. Use only user-permitted synthetic visuals; source interviews are anonymized unless permission has been obtained to identify or quote someone publicly.

**PASS:** all mandatory fields and authentic CodeBuddy proof ready; link/video labeled accurately. **If it fails:** stop coding to gather necessary real screenshots before the deadline; they are essential to getting scored.

## Step 75 - Complete the README, architecture and evidence references (P0)

**Dependency:** Steps 48, 54-58, 69 (if hosted) and 71. **Goal:** enable a judge to inspect and reproduce the build from GitHub.

1. Update `README.md` with problem statement, high-level architecture, agents, technology stack, what works today, what is mocked, Quickstart commands, test commands, deployment link, and contact/support route if appropriate.
2. Include a clear table of 3 required agents + 7 stretch capabilities + Innovations A/B, each linked to a source file/test/evidence screenshot.
3. Include exact policy version v2.1, routing-index version `1.0.0-draft`, and explain rulebook is a **lookup index**, not a decision authority.
4. Include `n` and exact denominators for measured results. `12/12 synthetic deterministic tests` is valid when reverified; it is not a production policy-validation rate.
5. Document architecture's deliberate trade-offs: single FastAPI backend instead of microservices, parallel ADK advocate calls, independent deterministic gate, safe mock ledger, Firestore document storage and GCS origin limitations.
6. Link API reference and operational limits. Use `[repo]/docs/IMPLEMENTATION_GUIDE.md` as a technical companion, but verify policy source distribution permissions before publicizing the full reference source.
7. Read the README as a new team member: one person should be able to clone, run offline, seed, process two categories, execute tests, and understand cloud prerequisites using only the materials supplied.

**PASS:** reproducible instructions and honest capability matrix. **If it fails:** fix missing dependencies/paths and reread from an empty terminal session.

## Step 76 - Submit before the official deadline (P0)

**Dependency:** Steps 72-75; no unfinished required item. **Goal:** ensure the build receives judging rather than timing out on paperwork.

1. The organizer WhatsApp update dated 9 October states the submission deadline is **Friday, 16 October 2026, 11:59 PM GMT+8** and late submissions are not accepted. The handbook gives 16 October as submission day. Verify the live form for any updated instructions.
2. Use the organizer's submission URL: `https://tinyurl.com/TCHackathonSGProjectSubmission` (check accessibility ahead of time).
3. Confirm project title, short blurb under ten words, description, CodeBuddy proof, 16:9 cover and all required attachments/fields. Add video/live URL only if functioning and accurately described.
4. Provide a GitHub repository URL accessible to judges in accordance with their access requirements; submit the precise commit SHA in the description if possible. If source policy is internal, ensure publication permission or judge-authorized private access.
5. Upload a final copy of the demo assets and evaluator screenshot gallery; verify they open from an incognito test session and do not reveal secrets.
6. Submit **well ahead of 23:59 SGT** to allow link/file validation. Wait for any confirmation email/page; take a screenshot or save receipt number.
7. Do not make major code changes after submission unless the rules explicitly permit updates. Preserve a working tagged commit and recorded demo.

**PASS:** confirmation recorded with working URLs and all mandatory items before deadline. **If it fails:** prioritize resubmitting missing required fields immediately; no extra stretch feature is worth an invalid submission.

## Step 77 - Freeze a release and rehearse failure fallback (P0)

**Dependency:** Step 76 or last scheduled pre-submission freeze. **Goal:** avoid an impressive but fragile live demonstration.

1. Identify the last commit that passed CI, local integration, hosted smoke test and full demo. Tag it `hackathon-submission` or `demo-stable`.
2. Prepare a read-only demo operator sheet with case order, tested passcodes (stored securely), expected result text, startup commands and Cloud Run links.
3. Rehearse with network disconnected or a deliberately failed model call. Switch transparently to a **recorded** live run or an offline labeled mock; do not suggest Gemini ran when it did not.
4. Do not reseed Firestore in ways that overwrite reviewer learning demonstration or other team member state. Use an isolated demo project or case IDs when necessary.
5. Validate application error UX: offline backend, invalid passcode, exceeded quota, broken image and pending clarification. Each must fail visibly and recover without silent action.
6. Preserve measurement evidence and screenshots in a private archive. Do not store cloud service-account keys, real interviews or payment details in the archive.
7. Prepare judge Q&A on why an LLM isn't allowed to issue real refunds, how 2 km routes escalate, how the 95% fraud threshold is handled, how you avoid treating no chat as no notice, and what learning truly means.

**PASS:** repeatable demo and credible failure responses. **If it fails:** stop adding capabilities and stabilize essential pages, API and policy gate.

## Step 78 - Declare done only when this acceptance contract is met (P0)

**Dependency:** All relevant P0 steps. **Goal:** ensure “entire solution successfully built” has an operational definition.

**Core acceptance conditions:**

- [ ] Three **actual** Google ADK agents (Rider Advocate, Driver Advocate, Judge) run on complete synthetic evidence and their interactions/tool metadata are observable; if not, label the mock branch honestly.
- [ ] At least **two complete dispute categories** process from case intake through evidence, policy, ruling/review and supported simulated action.
- [ ] The **actual uploaded** 41-ID routing index is consulted by Dispute Orchestrator and Judge tools, and full rule objects are fetched from matching `02_policy_rules.json` IDs.
- [ ] Safety, high value, route >2 km, disputed damage, fraud-flagged/uncalibrated and missing evidence cases take the correct human/investigation path; confidence cannot bypass it.
- [ ] Innovation A produces a real **decision-changing** result after verified synthetic source evidence, not merely a decorative question.
- [ ] Innovation B stages, tests, receives reviewer approval, publishes and rolls back a precedent; model-level improvement is claimed only if shadow-tested.
- [ ] All seven stretch capabilities have a real artifact, test or verifiable trace; image authenticity is never overclaimed.
- [ ] UI/backend accept known synthetic cases, role restrictions operate, repeat requests cannot duplicate financial actions, and every action is labeled simulated.
- [ ] Python offline tests, case evaluation and frontend build pass. Live cloud/ADK results are logged before claiming them.
- [ ] Original CodeBuddy/WorkBuddy proof, project details, cover, source access and deadline-specific submission requirements are satisfied.

**PASS:** the required conditions have actual artifacts; optional production extensions may be documented as future work. **If it fails:** submit the highest-quality honest working scope and identify unfinished items explicitly.

---

# Phase L - Troubleshooting handbook and recovery checklists

## Step 79 - Debug errors in the right order (P0 during integration)

**Dependency:** Any failed implementation step. **Goal:** reduce debugging time using a fixed isolation sequence.

1. **Syntax/import error:** run `python -m compileall -q app scripts`; check `.venv` and `PYTHONPATH=.` from the backend directory.
2. **Policy mismatch:** run `scripts/check_contract.py`; compare actual policy source hash, ID count and index version. Never bypass invalid hashes.
3. **Unexpected routing:** use `scripts/evaluate.py` on the exact case, inspect `case.facts`, `gaps`, `conflicts`, `recommend`, `gate`, and `case.routing.candidate_rule_ids`.
4. **Model behavior:** test `AI_MODE=memory/mock` first, then `AI_MODE=adk`; inspect Agent outputs and tool calls. If live Gemini errors, isolate auth/model/quota, not the policy gate.
5. **Frontend 502:** verify `curl localhost:8000/health` from the Next.js host/container; check `BACKEND_URL` and Cloud Run service logs.
6. **Firestore:** check ADC/service account, collection names, configured project, emulator vs real mode and IAM role. Avoid mixing localhost emulator env with deployed Cloud Run.
7. **GCS:** verify bucket exists, name lacks `gs://` in `.env`, file content/MIME match, and runtime identity has bucket-level object permission.
8. **Refund duplicated:** inspect action idempotency key and whether requests hit separate independent repo instances; stop auto-remedy until fixed.
9. **No reviewer approval:** check passcode and status. `review` accepts only `REVIEW_REQUIRED`; learning release requires `EVALUATED` and a correct digest.
10. **Safety incident reached Judge:** treat as release-blocking. Confirm `safety_screen` happens before `evaluate_agents(...safety=False)` and that the case's narrative and relevant chat text were scanned.
11. **PDF/README mismatch:** cross-check actual code and API reference; never claim a function exists solely because a diagram depicts it.

| Symptom | Check | Safe recovery |
|---|---|---|
| `ModuleNotFoundError` | Activated `.venv`, package install, working directory | Recreate venv, reinstall appropriate requirements |
| `team_signoff_valid=false` | Policy review completed? Hash/version match? | Review ambiguities and sign off exact contract |
| `403` on Firestore/Vertex | Cloud project / ADC / IAM | Grant least privilege to correct identity |
| `404` on case | Seeded? Correct case ID? Memory restart? | Reseed memory-only demo; do not wipe live data |
| `AI_MODE=adk` no final text | Model/quota/ADK events JSON format | Keep human review or explicit failure, inspect real trace |
| `npm run build` fails | Next.js package/JSX module import | Fix indicated file/line, rerun `npm install` |
| Browser proxy `502` | Backend URL/reachability | Restart API, correct `BACKEND_URL`, redeploy web if needed |
| Cloud Run container not ready | `PORT`, Docker dependencies, entrypoint | `gcloud run services logs read`; fix build/run errors |
| GCS upload 400 | MIME, file signature, <=5 MB | Use real permitted test file, not renamed random bytes |
| `reviewer key required` | Role passcode mismatch | Enter reviewer key; never bypass backend checks |
| Case auto-settles while disputed | Source trust / guardrail omission | Disable auto-mode, add negative test, patch gate |
| Learning cannot approve | `STAGED` or failed regression/digest | Re-test unchanged proposal, review before release |

## Step 80 - Scope cuts if time runs short (P0 operational decision)

**Dependency:** Timetable pressure, incomplete gates. **Goal:** protect eligibility and core quality over feature count.

1. **Never cut:** three real core ADK agents, two complete categories, rulebook/full-policy lookups, mandatory safety/human gates, visible traces, CodeBuddy usage proof, required submission artifacts.
2. **First cuts:** separate rider/driver visual themes, background queue workers, advanced external route API, polished map view, live chat push. Keep straightforward synthetic source adapters.
3. **Second cuts:** photo forensic scores, full image upload UI (retain API and explain limitation), elaborate fraud ML classifier (retain documented risk signal), sophisticated SLA timers without real targets.
4. **Third cuts:** deployed GCS stretch if blocked (keep local fixture, clearly mark), shadow-model precedent evaluation (keep staged/test/approval and label the limit), multi-region/cloud autoscaling demonstrations.
5. **Last resort:** use memory-mode backend + stable Next.js frontend and an honest locally recorded live ADK session if Cloud Run deployment fails; do **not** claim an unverified deployed service.
6. Protect time for **source upload/CodeBuddy screenshots and final form**. Submission eligibility outranks hypothetical enterprise scaling.
7. Always keep a full backup video of the **last demonstrated working** version and tag its commit.

**PASS:** no scope cut undermines honesty, safety or mandatory technical requirements. **If it fails:** stop and revert to the last passing release tag before recording/submitting.

---

# Appendix A - Folder-by-folder source map

This is the actual companion ZIP structure (files may have been added by later commits). **Begin reading top-to-bottom in the order listed.**

```text
RydeResolve_Implementation_Kit/
  README.md                     # fast path & verified/unverified labels
  .gitignore                    # protects env, uploads, reports
  .github/workflows/ci.yml     # Python policy & Next.js checks
  scripts/verify_all_local.sh  # one command for offline gates
  docs/
    IMPLEMENTATION_GUIDE.md    # source for this PDF manual
    API_REFERENCE.md           # endpoints and request contracts
    OPERATIONAL_LIMITS.md      # production gaps and risk honesty
    POLICY_REVIEW_NOTES.md     # editable AMB-01 ... AMB-08 review template
  backend/
    .env.example               # modes, passcode placeholders, GCP settings
    requirements.txt           # offline minimal dependencies
    requirements-cloud.txt     # ADK, Firestore, GCS libraries
    Dockerfile                 # deployable Python 3.11 API image
    app/
      config.py                # local/cloud and model mode config
      models.py                # Pydantic request schemas
      policy.py                # 41-ID contract, routing and full-rule lookup
      policy_engine.py         # independent v2.1 deterministic evaluator/gates
      evidence.py              # safety screen, missingness, contradictions, provenance
      agents.py                # Google ADK advocate/Judge/precedent/fraud calls
      repository.py            # memory and Firestore adapters
      storage.py               # local/GCS evidence objects
      image_analysis.py        # bounded ADK Gemini pixel analyst
      actions.py               # idempotent simulated financial actions
      sla.py                   # case priority class/routing
      services.py              # end-to-end orchestration and state machine
      main.py                  # protected FastAPI routes
    policy/
      policy_v2.1.md           # source challenge policy, supplied
      02_policy_rules.json     # supplied 41 structured rules
      04_rulebook.json         # supplied 41-rule routing index
      contract_approval.json   # generated after local team signoff only
    fixtures/
      source/                  # original synthetic DISP-001/002/003 records
      cases/                   # 12 clean normalized test/demo cases
      evaluation/gold.json     # private grader targets; never feed ADK
      evaluation/reviewer_time_template.csv
    scripts/
      check_contract.py        # hash/IDs/version validation
      signoff_policy.py        # local team contract acceptance
      seed.py                  # load synthetic cases into selected store
      evaluate.py              # 12-case deterministic reference grading
      threat_eval.py           # three adversarial boundary checks
      live_eval.py             # actual model calls + recorded report
      reviewer_benchmark.py    # paired measurements, no fake baselines
    tests/
      conftest.py
      test_policy.py
      test_api.py
  frontend/
    package.json
    .env.example
    Dockerfile
    src/app/
      layout.jsx
      globals.css
      page.jsx                 # case queue, role-aware UI, traces, review/learning
      api/proxy/[...path]/route.js  # Next.js server-side API proxy
```

# Appendix B - Copy/paste command cards

## B.1 Minimal offline launch (three terminals)

```bash
# Terminal A - Backend dependencies (first time only)
cd ~/Projects/200-OK-RydeResolve/backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=. python scripts/check_contract.py
PYTHONPATH=. pytest -q
# Review AMB-01..08, then run signoff script in Step 08
PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# Terminal B - Frontend
cd ~/Projects/200-OK-RydeResolve/frontend
cp .env.example .env.local
npm install --no-audit --no-fund
npm run dev

# Terminal C - API check and seed
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
curl -s -X POST http://127.0.0.1:8000/cases/seed \
  -H 'X-Demo-Key: change-reviewer-key' | python3 -m json.tool
```

## B.2 Minimal offline validation from repository root

```bash
cd ~/Projects/200-OK-RydeResolve
bash scripts/verify_all_local.sh
cd frontend && npm run build
```

## B.3 Genuine model mode (no cloud database yet)

```bash
cd ~/Projects/200-OK-RydeResolve/backend
source .venv/bin/activate
python -m pip install -r requirements-cloud.txt
gcloud auth application-default login
# Edit .env to APP_MODE=memory, AI_MODE=adk, project, model, location
PYTHONPATH=. python scripts/live_eval.py --cases DISP-003
```

## B.4 Local evaluation outputs and appropriate wording

- `scripts/check_contract.py` verifies IDs/hashes and optionally team signoff; it does not prove Ryde officially endorsed the converted policy.
- `pytest -q` verifies code assertions; it does not measure real-world accuracy.
- `scripts/evaluate.py` evaluates 12 synthetic deterministic cases; it does not exercise Google ADK inference.
- `scripts/live_eval.py` makes genuine model calls only when `AI_MODE=adk`; review text grounding manually too.
- `scripts/reviewer_benchmark.py` refuses to invent timings and will fail until 3+ paired observations are recorded.
- `scripts/threat_eval.py` tests selected strings; it is not a complete adversarial security audit.

# Appendix C - Policy/routing control map with decisive edge cases

| Policy source | Operational interpretation | Mandatory test |
|---|---|---|
| §1.2-1.4 | Reroute notice and traffic justification; excess-distance refund from verified fare component | DISP-001 proposes SGD 3.44 but escalates |
| §2.1 | Five-minute no-show wait from scheduled pickup, not driver's early arrival | DISP-002 timing anchored correctly |
| §2.3 | Before driver cancels, at least one message AND one call | DEMO-NOSHOW-VOID reverses SGD 5 fee |
| §3.1-3.5 | Binding quoted surge and valid timely notification; booking fee exempt | DISP-003 eligible for SGD 4.50 |
| §4.2-4.4 | Photo provenance, trip link, 24h clock; rider-disputed damage → human | DEMO-DAMAGE-DISPUTED human review |
| §5.1-5.2 | Safety detected inside any selected category; no AI fault/remedy recommendation | DEMO-SAFETY-IN-FARE bypasses Judge |
| §6.1 | `<10`, `10..50`, `>50` monetary bands; exact boundaries matter | DEMO-FARE-50, DEMO-FARE-OVER50 |
| §6.2 | Route >2 km always reviewer; even shorter route needs validated >=80% confidence | DEMO-ROUTE-SHORT not auto with uncalibrated score |
| §6.3 | Any historical fraud flag raises threshold to 95%; no calibrated confidence provided | DISP-002 human review |
| §7 | Precedent advisory; must cite comparable material facts, never override policy | New approved precedent cannot bypass gate |

**Eight supplied policy ambiguities:** AMB-01 (DISP-002 timer), AMB-02 (disputed damage vs cleaning), AMB-03 (category/value/fraud precedence), AMB-04 (excess-distance pricing), AMB-05 (chat **and** call), AMB-06 (interim account action authorization), AMB-07 (dispute value basis), AMB-08 (uncalibrated confidence). Review their **original wording** in `02_policy_rules.json`; this table is only a quick index, not a substitute.

# Appendix D - Success and evidence tracking ledger

Copy this into `docs/BUILD_STATUS.md` or a shared task tracker. Use **PASS / FAIL / NOT_RUN** (never default all to green):

| Gate | Evidence to keep | Status |
|---|---|---|
| Source hash, 41 rule IDs, draft review signoff | `check_contract` output and review notes | NOT_RUN |
| Backend offline pytest | timestamped test transcript | NOT_RUN |
| 12-case reference regression | JSON with 12/12 and git SHA | NOT_RUN |
| Adversarial safety/permission gates | `threat_eval` output | NOT_RUN |
| FastAPI boot and two complete categories | screenshot + API case JSON | NOT_RUN |
| Actual Rider/Driver/Judge ADK inference | real agent/tool trace, model version | NOT_RUN |
| Innovation A decision-changing evidence | before/reply/verified-source/after snapshots | NOT_RUN |
| Innovation B stage/regress/approve/rollback | statuses and report digest | NOT_RUN |
| Firestore persists after server restart | Console + backend case read | NOT_RUN |
| GCS synthetic image and bounds | private object ref, verified pixel branch | NOT_RUN |
| Frontend npm production build | `npm run build` exit 0 | NOT_RUN |
| Cloud Run end-to-end if claimed | URL, fresh-browser case, logs | NOT_RUN |
| Authentic CodeBuddy/WorkBuddy proof | at least 3 development screenshots | NOT_RUN |
| Video, cover, description, source link | accessible sanitized artifacts | NOT_RUN |
| Official submission complete | confirmation receipt before 16 Oct 23:59 SGT | NOT_RUN |

# Appendix E - Trusted references and when to use them

**Challenge requirements and examples:**

- Tencent Cloud AI CAN DO IT Singapore 2026 Handbook, pp. 21-25 (Ryde core/advanced architecture, categories, demo); pp. 35-39 (Tencent tooling, submission requirements, timeline and general judging dimensions).
- Ryde-only excerpt pp. 4-8 (Ryde challenge), pp. 9-13 (tools, submission, judging).
- Organizer Ryde track WhatsApp post, 9 Oct 2026: submission by **16 Oct 2026 23:59 GMT+8**. Organizer post, 2 Oct 2026: create synthetic training/testing data due to privacy.
- Supplied `Document 2 — Ryde Dispute Resolution Policy v2.1 (Markdown).md` and structured conversion `02_policy_rules.json`, effective 1 Jan 2026; supplied `04_rulebook.json`, draft 41-rule lookup index. Applicable to synthetic hackathon prototype.
- Supplied synthetic DISP-001 (route deviation), DISP-002 (no-show fee) and DISP-003 (unnotified surge) records. Not evidence of real-world Ryde dispute volumes or representative case prevalence.
- Stakeholder LinkedIn reply dated 9 Oct 2026 (Nitin): describes evidence aggregation, case interpretation, party communication and human-review situations. Driver Vernon and riders Lucky/Ain are individual reported experiences; seek consent before public attribution or verbatim private-message quotes.

**Official Google tooling and deployment docs (verify current syntax if Google updates CLI):**

- ADK documentation index and recommended agent patterns: https://adk.dev/llms.txt and https://google.github.io/adk-docs/
- Google Cloud Run FastAPI source deployment: https://docs.cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-fastapi-service
- Cloud Run source deploy + Dockerfile behavior: https://docs.cloud.google.com/run/docs/deploying-source-code
- Cloud Run service identity / attaching service account: https://docs.cloud.google.com/run/docs/configuring/services/service-identity
- Firestore database creation: https://cloud.google.com/firestore/docs/manage-databases
- Cloud Storage bucket creation: https://docs.cloud.google.com/storage/docs/creating-buckets
- Google Cloud Storage uniform bucket-level access: https://docs.cloud.google.com/storage/docs/uniform-bucket-level-access
- Gemini API in Vertex AI Python SDK quickstart: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/quickstart

**Primary reliability rule:** where a guide command conflicts with current platform documentation, stop and verify the current official documentation rather than silently inventing flags or model availability. Cite the actual platform version and exact test result in final artifacts.

---

# FINAL OPERATOR CHECK

**A successful hackathon *prototype* is not a production Ryde deployment.** The minimum honest claim after doing every gate is: "We built and tested a synthetic, policy-grounded multi-agent dispute-resolution demonstration using Google ADK, Firebase/Firestore, GCS and Cloud Run, with safe mock remedies, required human review, decision-changing clarification and reviewer-governed precedent releases." Claim genuine ADK/Firestore/GCS/Cloud Run functionality **only after those live checks passed in your own Google project**. Report **actual** case counts, latencies, reviewer observations and citations. Never guarantee a prize or claim that model confidence is calibrated without evidence.

### Gemini request reliability and image previews

The live runtime keeps the configured Gemini model and uses schema-constrained ADK calls. Policy routing, authoritative rules and approved precedents are fetched once by the application and supplied to the six agents; the Judge still receives both advocates' independent findings. This removes repeated model/tool round trips without changing the deterministic policy gate.

`app/gemini_runtime.py` limits each instance to two simultaneous model calls, retries transient capacity/deadline/server failures with jitter, and allows a 115-second request budget across two attempts per model (25 seconds per attempt). The primary remains Gemini 3.8 Flash; when GEMINI_FALLBACK_MODEL=gemini-3.6-flash is configured, transient failures or invalid output after primary retries trigger that fallback. Every successful result records its actual model, primary model and fallback flag; reviewers see these labels on image descriptions and agent findings. Invalid structured responses get validation feedback on retry. Authentication and invalid-request failures are not retried. The evaluation has a 240-second overall deadline, below both Cloud Run services' 300-second request limit. Exhausted retries still require human review; these controls cannot guarantee provider availability.

Reviewer attachments show a short AI description and an expandable full visual analysis. Existing image descriptions are also displayed. Image observations never establish authenticity, trip attribution or fault. Retrying a completed upload reuses its stored analysis instead of calling the model again. Live test reports must check **all six agent outputs**, not merely a successful HTTP status or human-review fallback.

Deployment verification (19 October 2026): backend `ryderesolve-api-00015-fhn`, frontend `ryderesolve-web-00022-h69`. 392 backend tests and 27 frontend tests passed. Public-site synthetic testing completed three distinct image analyses, duplicate-upload reuse, a linked driver appeal with rider evidence/reply, reviewer resolution, in-app notifications, role isolation and monitor completion. Four evaluations returned 24/24 valid agent results (70.08s, 56.83s, 158.31s, 15.28s), including actual Gemini 3.6 Flash fallback recoveries. All 18 pre-existing cases matched their pre-deployment snapshots. QA cases are retained with the `QA-GEMINI-20261019-104406` prefix and linked appeal `APPEAL-E343D497430D3C0C10EA0FA8`; test-generated learning guidance was rolled back. This verifies the observed run, not a guarantee of provider availability.
