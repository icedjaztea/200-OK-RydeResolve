# Judge walkthrough

**Follow the evidence, compare the perspectives, and inspect the decision.**

[Open RydeResolve](https://ryderesolve-web-oydodesgeq-as.a.run.app) · [Product overview](../readme.md) · [Architecture](OPERATIONAL_LIMITS.md)

This guide follows the application on `feat/three-role-frontend`. The hosted demonstration uses synthetic trips, open role selection, and simulated financial actions.

## Start with a resolved case

Open the **Reviewer Workbench** and select **DISP-003** in the case queue. Its original facts are a SGD 12.00 quote, a SGD 16.50 final fare, and a surge increase without notification.

Inspect these checkpoints:

| View | What to inspect |
|---|---|
| Overview | The SGD 4.50 differential, resolution path, and simulated action receipt. |
| Evidence | Recorded fare and notification facts, with their provenance. |
| Agent Findings | The six core agent outputs, including both advocates and the Judge. |
| Audit / Advanced | The review packet and internal event-chain verification. |
| ADK Monitor | Stored workflow outputs, model metadata, and execution replay. |

If the case is new, select **Process**. If it is already resolved, inspect the saved result. Agent failures or a Judge-policy mismatch route a new run to review; a deterministic candidate alone does not authorize automatic resolution.

**What this demonstrates:** the system connects a specific remedy to evidence and policy, with separate recommendation and execution controls.

## Follow a clarification across roles

1. Select **DEMO-FARE-CLARIFY** in the reviewer queue.
2. Inspect the missing notification facts. Process a new case to generate the targeted question; an existing pending request can be used directly.
3. Open the **Rider Portal** and select **Rider A**. Open the same case and respond to the pending question.
4. Return to the reviewer, refresh the case, and inspect the response.
5. Review or add corroborating evidence before continuing the decision workflow.

A party's answer remains a party account. It does not automatically overwrite a verified fact. The reviewer can also request further information from a linked rider or driver.

If the shared case has already completed this stage, inspect its recorded clarification and timeline. To explore a fresh exchange, file a new report from a linked trip and use the reviewer's information-request control.

**What this demonstrates:** the investigation involves both parties and preserves the distinction between statements and evidence.

## Inspect safety routing

Select **DEMO-SAFETY-IN-FARE**. The report is categorized as a fare dispute, but its narrative contains a threat allegation.

Look for **Immediate Human Review**, the safety policy references, and the absence of a Judge ruling. Advisory agents may summarize the record under a restricted safety contract; fault and remedy remain with the human reviewer.

**What this demonstrates:** safety screening applies across intake categories, so a fare label does not bypass the safety workflow.

## File a driver report with evidence

1. Open the **Driver Portal** and select a demo identity.
2. Choose a trip with a linked rider, or create a synthetic trip linked to Rider A or Rider B.
3. Choose **Report an issue**, describe the dispute, and attach PNG, JPEG, or PDF evidence.
4. Submit the report. Each attachment has its own upload result; failed attachments can be retried without creating another report.
5. Open the case in the reviewer workbench. Inspect file evidence and any available Gemini image observations.

Files are limited to 5 MB each. Image analysis describes visible content; provenance, trip attribution, and policy eligibility are evaluated separately. Riders can also add attachments to open cases.

**What this demonstrates:** both parties can initiate a dispute, and evidence submission has a recoverable workflow.

## Follow an appeal

1. In the Rider or Driver Portal, open a resolved case linked to that identity.
2. Use the appeal panel to explain the reason for reconsideration.
3. Open the new linked appeal case. It retains the original decision, context, and evidence.
4. Switch to the linked counterparty and respond to the appeal's clarification request. Add supporting files if useful.
5. Return to the reviewer to reconsider the case once the response is complete.

Appeals require human review. A repeated submission for the same decision and party returns the existing appeal. Where the shared demo already has an appeal, follow that record and its original-case link.

**What this demonstrates:** a decision has a structured route for challenge, evidence, and accountability.

## Inspect how reviewed outcomes become guidance

Open a case resolved by a reviewer and inspect **Learning from this review**. Eligible cases can publish a case-specific example after source-decision and deterministic policy-regression checks.

The example records the decision and rationale under the policy version. Authoritative policy continues to take precedence. Reviewers can roll back released guidance, and guidance sourced from appealed decisions is excluded from agent retrieval.

**What this demonstrates:** operational experience can inform future reviews without changing policy rules or model weights.

## Shared-demo behavior

The backend adds missing fixture cases at startup and preserves existing decisions. **Load demos** repeats this create-only operation; it does not reset cases. Case ownership, responses, decisions, and in-app updates persist in Firestore. Trip history is stored in the current browser.

For a fresh fixture set, follow the [local setup](DEVELOPMENT.md) using memory mode and restart that local backend. The [ADK Monitor](https://ryderesolve-web-oydodesgeq-as.a.run.app/monitor) is an execution replay, so completed examples can be inspected without running another model workflow.
