# RydeResolve

**Policy-grounded dispute resolution for ride-hailing.**

Live demo: **[https://ryderesolve-web-oydodesgeq-as.a.run.app](https://ryderesolve-web-oydodesgeq-as.a.run.app)**

No login or passcode needed — just open the link and explore.

---

## What is RydeResolve?

RydeResolve is a synthetic demonstration of a multi-agent dispute resolution system for ride-hailing platforms. When a rider or driver reports a problem with a trip — a fare discrepancy, a route deviation, a no-show charge, property damage, or a safety incident — RydeResolve doesn't just forward it to a human. It runs the case through a structured pipeline of AI agents and a deterministic policy engine, then presents the reviewer with a complete investigation packet and a recommended outcome.

The reviewer makes the final call. The system never lets AI authorize a financial action on its own.

All data is synthetic. No real payments, accounts, or notifications are involved.

---

## How it works

Every dispute goes through a **six-stage pipeline**:

```
1. Intake          Rider or driver files a dispute with a category and description
                   Safety screening runs immediately — safety cases skip all AI
                   
2. Routing Index   A candidate policy rule lookup matches the dispute category and
                   description against a 41-rule routing index (this is a search
                   index, not authority to rule)
                   
3. Evidence Check  The system checks for missing or conflicting evidence. If gaps
                   exist, it asks the relevant party a clarification question
                   
4. Agent Evaluation  Five independent AI agents analyze the case in parallel:
                     - Rider Advocate      — argues the rider's position
                     - Driver Advocate     — argues the driver's position
                     - Policy & Precedent  — matches applicable policy rules and prior precedents
                     - Fraud & Bad-Faith    — screens for fraud indicators
                     - Consistency Judge   — cross-checks all advocates for consistency
                     
5. Policy Gate     A deterministic Python policy engine (not an LLM) validates the
                   candidate outcome against structured policy rules. If the agents
                   disagree, if evidence is incomplete, or if the case involves safety,
                   the gate blocks automatic resolution and routes to human review
                   
6. Outcome         If the gate approves and all agents agree → auto-resolve with a
                   simulated refund/credit receipt. Otherwise → reviewer takes over.
```

**Key safety property:** AI agents can only *recommend*. The deterministic policy gate and the human reviewer are the only authorities that can authorize a financial action.

---

## The four portals

The app is organized into four role-based interfaces. All are accessible from the landing page — no passcode needed.

### /rider — Rider Portal

The rider's mobile-app-style interface. Riders can:

- **View their cases** — active and resolved disputes, with status, category, and outcome
- **Report an issue** — file a new dispute by selecting a category (fare, route, no-show, damage, safety, or "Other / I'm not sure"), choosing a past trip from their trip history, and describing the problem
- **Respond to clarification requests** — when the reviewer asks a question, the rider sees it here and can reply
- **Browse trip history** — synthetic past trips with pickup/drop-off locations, fares, and a map view
- **Create trips** — add synthetic trips to their history
- **Switch identity** — a Rider A / Rider B dropdown in the header lets you see different cases (case isolation is enforced — Rider A cannot see Rider B's cases)

### /driver — Driver Portal

The driver's mobile-app-style interface. Drivers can:

- **View cases involving them** — disputes where they are the respondent, with action-needed alerts for pending clarification requests
- **Respond to clarification requests** — same as riders, but filtered to driver-recipient questions
- **Browse trip history** — synthetic past trips from the driver's perspective
- **Create trips** — add synthetic trips
- **Switch identity** — Driver A / Driver B dropdown in the header

### /reviewer — Reviewer Workbench

The reviewer's full investigation dashboard. This is the core of the system. Reviewers can:

- **Demo cases load automatically** — backend startup seeds missing synthetic fixture cases (fare disputes, route deviations, no-shows, damage, safety, fraud)
- **View the case queue** — all cases sorted by status, with urgent cases highlighted
- **Process a case** — runs the full six-stage pipeline with a live progress display showing each step (safety screening → routing index → evidence check → agent evaluation → policy gate → outcome)
- **Investigate** — five tabs per case:
  - **Overview** — case summary, next action, recommended outcome, policy rationale
  - **Evidence** — all verified facts, their values, and provenance sources
  - **Agent Findings** — each agent's summary, recommended disposition, and detailed trace
  - **Review Decision** — the reviewer's form to issue a ruling (refund, credit, no action, reject claim), with optional proposed precedent
  - **Audit / Advanced** — tamper-evident event chain verification, review packet, learning proposals
- **Request more information** — ask the rider or driver a free-form question at any time (before or after processing)
- **Reclassify "Other" cases** — when a rider files under "Other / I'm not sure," the reviewer classifies it to a specific category before adjudication
- **Upload evidence** — add verified demo evidence (facts with provenance) or upload files
- **Manage learning** — review, evaluate, approve, or rollback learning proposals (precedents from reviewed decisions)

### /monitor — ADK Execution Monitor

A visual replay of the agent execution pipeline for any processed case. Shows:

- The workflow graph with all six stages and the agents within each
- Actual stored agent outputs and traces (not live execution — this replays recorded data)
- Node-by-node click to inspect what each agent produced, including error states
- A replay button to animate the pipeline progression

This is a technical inspection view — the same data the reviewer sees in the Agent Findings tab, but visualized as a flow graph.

---

## Dispute categories

| Category | Example | Typical outcome |
|---|---|---|
| Fare dispute | Surge applied without notification | Refund of difference if rider wasn't notified |
| Route deviation | Driver took a longer route without informing rider | Refund for excess distance if no traffic justification |
| No-show charge (rider) | Rider charged no-show fee but was present | Fee voided if rider was present |
| Driver no-show | Driver didn't arrive at pickup | Refund or credit |
| Property damage | Driver claims rider damaged vehicle | Reviewer adjudicates based on photo evidence |
| Safety incident | Rider alleges unsafe behavior | **Immediate human review — no AI ruling** |
| Other / I'm not sure | Rider isn't sure what category fits | **Manual classification required** |

---

## Architecture

```
Next.js Frontend (Cloud Run)
    │
    ▼
FastAPI Backend (Cloud Run)
    │
    ├── Policy routing index (41 rules, JSON)
    ├── Five Google ADK / Gemini agents (or offline mock mode)
    ├── Deterministic Python policy engine (the gate)
    ├── Tamper-evident audit chain (SHA-256 linked events)
    ├── Mock financial ledger (simulated receipts, no real money)
    ├── Firestore (case storage, precedents)
    └── Google Cloud Storage (file evidence)
```

**Tech stack:** Next.js, FastAPI, Google Cloud Run, Google ADK with Gemini, Firestore, GCS.

---

## Try it

1. Open **[https://ryderesolve-web-oydodesgeq-as.a.run.app](https://ryderesolve-web-oydodesgeq-as.a.run.app)**
2. Click **Reviewer Workbench** → select an automatically loaded case → click **Process**
3. Watch the pipeline run. Then explore the Evidence, Agent Findings, and Review Decision tabs.
4. Go to **Rider Portal** or **Driver Portal** — cases and trips load automatically. Switch between Rider A and Rider B to see case isolation.
5. Open **ADK Monitor** to see the agent execution graph for any processed case.

No setup, no keys, no login. Just explore.

---

## Important limitations

- All data is synthetic. No real Ryde accounts, payments, or notifications are connected.
- AI agents recommend; they do not authorize. The deterministic policy gate and human reviewer are the only authorities for financial actions.
- Safety cases cannot reach the AI ruling step — they go straight to human review.
- Model self-assessed confidence is not calibrated.
- The demo passcode system has been removed — anyone can access all roles.

Demo startup seeding is create-only: existing cases and processed results are preserved, including concurrent Cloud Run startups. The optional **Load demos** button retries the same seeding. Cloud Run uses `APP_MODE=firestore` for persistence; local `memory` mode remains ephemeral. Riders and drivers see only their assigned cases.

New driver/rider trips offer an opposite-role demo identity (A/B) or Custom (unlinked). Reports inherit that selection; the server assigns the filing identity and validates the counterpart role. Existing trips remain unlinked. Linked parties can see the case, upload supporting evidence, and answer reviewer-created clarification requests. Trip history remains browser-local; case ownership and responses persist in Firestore.
