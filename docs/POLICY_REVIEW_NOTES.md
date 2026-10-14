# Team Policy v2.1 Review Notes - REQUIRED BEFORE SIGNOFF

Use only the supplied policy/JSON/routing-index sources. Never describe this team's signoff as Ryde approval. Do not fill unreviewed decisions with assumptions.

| Source ambiguity | Exact issue | Proposed safe implementation handling | Reviewed? | Evidence / remaining question |
|---|---|---|---|---|
| AMB-01 | DISP-002 event wait clock vs policy §2.1 scheduled pickup anchor | Use scheduled pickup + five minutes; preserve dataset event separately | YES | Policy 2.1 uses five minutes from scheduled pickup. The eight-minute event in DISP-002 is sample-specific. |
| AMB-02 | Disputed damage §4.4 vs cleaning §6.2 | Disputed damage always human reviewer | YES | Policy 4.4 requires human review for disputed damage, overriding AI eligibility under S6.2. |
| AMB-03 | Low-value, category and flag confidence threshold precedence | Mandatory review gates win; uncalibrated score cannot authorize | YES | Mandatory review gates take precedence. Uncalibrated AI confidence cannot bypass them. |
| AMB-04 | Missing general tariff for excess-distance component | Only verified stored trip fare breakdown; never invent rate | YES | Policy 1.3 does not specify a standard kilometre rate. Use verified trip fare breakdowns only. |
| AMB-05 | No-show chat AND call wording | Require one of each, before cancellation | YES | Policy 2.3 requires at least one in-app message AND one call before cancellation. |
| AMB-06 | Authority for interim safety account restrictions unspecified | Reviewer only, no AI account action | YES | Policy 5.3 does not specify authorization. Account restrictions require authorized human control. |
| AMB-07 | Dispute value basis ambiguous in compound cases | Reviewer when ambiguous and financially material | YES | Policy 6.1 does not fully define dispute value for compound claims. Escalate if uncertainty affects routing. |
| AMB-08 | No source calibrated confidence formula/validation | Mark uncalibrated; never use model percentages as calibrated probabilities | YES | Policy 6.3 lacks a validated confidence formula. Treat model percentages as uncalibrated and escalate when confidence eligibility cannot be established. |

**Review result:** ACCEPTED. All eight implementation ambiguities have been reviewed. The documented conservative handling is accepted for the prototype. Unresolved evidence or policy uncertainty will trigger human review where it affects the decision. This is a team implementation decision, not official Ryde approval.
