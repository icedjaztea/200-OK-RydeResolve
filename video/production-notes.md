# RydeResolve walkthrough v2 — autonomous production record

User requested an updated film from the same timeline/comparison attachments and explicitly selected custom autonomous mode. A separate branch was requested: feat/three-role-video-shotcraft-v2. This branch starts at the developer's latest frontend commit 1a6d3fa6b672e26eb41b8f7311f18c0b6a8495eb, not the first video's branch. First video remains intact.

## Product brief and requirement decisions
Audience: submission judges / product and technical reviewers. Goal: demonstrate evidence-grounded resolution across rider, driver and reviewer perspectives with an independent deterministic policy gate. English, 1080p30, approximately four minutes, narrated and captioned. Same reference structure: stakeholder needs → architecture → fare evidence/remedy → route and safety oversight → party experience → neutral comparison → measured checks and deployment.

New developer updates to show: trip history and illustrative map cards, trip-linked report intake, Other / I'm not sure classification, readable case facts, expandable policy details, perspective-oriented agent findings. Driver response and rider outcome are distinct states. Footage comes from the real updated app running locally at ports3001/8001, in memory / mock mode. No live funds, accounts, notifications or GPS are connected.

Data: only supplied synthetic fixtures and frozen synthetic trip records. Demo names are Demo Rider A / Demo Driver A; no personal or customer data is captured. Fake trip history is preloaded into the application's own localStorage before capture to prevent random/date drift. A new Other case is submitted through the real Rider UI, processed and reclassified through the real Reviewer UI. Its original category remains in the case record. Capture scripts are retained for reproducibility. No authentication credentials are shown in captured frames. Three minimal source presentation fixes were applied on the v2 branch: existing-trip dropdown matching, an incorrectly escaped apostrophe, and case-insensitive mock/live labels. Their browser checks are retained in out/correction-checks.txt.

## Evidence boundaries
346 backend tests passed with both secondary demo identities configured.18 frontend proxy tests passed. API checks: DISP-003 resolves with simulated SGD4.50 refund; DISP-001 (4.3km deviation) routes HUMAN_REVIEW; DEMO-SAFETY-IN-FARE routes IMMEDIATE_HUMAN_REVIEW; Other routes HUMAN_REVIEW with empty agent outputs and no financial action. An attempted refund on an unclassified Other case is rejected with HTTP400. Reclassification preserves original_category='other'. Driver clarification is an unverified report asking for route notification evidence, not a fabricated verified fact.

No live Gemini run, deployed cloud persistence, Tencent execution, interview record, CodeBuddy record or cloud latency is established by these local checks. Narration and comparison describe source integration paths and remaining validation, without claiming a winner. Main and putra branches were inspected by history/path diff; the updated agreed frontend branch is the film's product source. No unrelated branch is merged.

## Visual direction / design specification
Retain the updated product's restrained pink/blush system: primary #e8336a, darkpink #c91f56, background #faf6f8, white surfaces, ink #1a1528, secondary #534659, borders #ece4e8, radii14/18. Font family mirrors app's Inter/system/Arial stack; available local Arial is the fallback. Calm precise editorial motion:21-frame bezier(0,0,.2,1) entrances, no shake, no beat-driven camera pulses. Narrative scenes use diagrams; existing UI always uses real 2× screenshots and element cutouts with recorded coordinates. Dense tables remain frontal. Captions76px, editorial body33px or larger, text holds long enough for spoken explanation. Decorative scene-index metadata is smaller; native UI details are supported by large narrative callouts. Persistent synthetic-demo disclosure33px. Documentary pacing deliberately uses a restrained close instead of Q8's theatrical promo ending.

Reuse the validated v1 layout as the initial styleframe baseline, with new phone + editorial callout layout and policy cutout framing checked before full rendering. The whole opening lasts over11seconds; the brief wordmark reveal holds for the rest of the narration. No source UI is retyped or falsely presented as a new app feature.

## Motion mapping and assets
PageCam copied from video-shotcraft is the foundation for full-page screenshot pans. Phone scenes use native app-shell cutouts with deliberate vertical framing; an illustrative explanatory panel is separate from the app. The one opening wordmark reveal adapts paper-title-card: nine-frame reveal, scale1.28→1, blur7→0, delay4+i*4 and bezier(.2,.75,.3,1), extended hold for narration. Exact recipe and demo were read in the first production and rechecked for this update; the Gallery index entry is retained in QA. Other layouts are custom explanatory scenes, not claimed Gallery replicas.

## Audio
Locally generated synthetic English narration (Kokoro ONNX af_heart, speed1.25) and restrained transition SFX. No BGM: speech intelligibility and policy explanation take priority over beat-driven promo pacing. Therefore no redundant no-BGM alternative is needed. Source WAVs, captions and a single timeline are retained; final audio is normalized toward -16LUFS and -1.5dBTP. SFX attribution and voice engine license are included.

## QA and delivery
Before full render: style/layout checks and two stills per scene. After render: extract key frames from the encoded MP4, full decode, media and loudness checks, independent review per the installed skill. Main and workbench import use the same SHOTS source. Production documents distinguish visual/technical verification from any capability to listen to audio or continuously watch every frame. User requested push work to a separate branch; video deliverables are committed only to v2.

## Final storyboard

| Start | Duration | Scene | Visual |
|---|---|---|---|
| 0:00 | 11.3s | RydeResolve | brand |
| 0:11 | 12.0s | One trip. Three perspectives. | priorities |
| 0:23 | 11.5s | Start with the trip | rider-trip-phone |
| 0:34 | 13.3s | Report it in your own words | rider-report-phone |
| 0:48 | 14.6s | Advocacy is not authority | architecture |
| 1:02 | 12.9s | Check facts before conclusions | fare-evidence |
| 1:15 | 14.5s | Read the rule behind the reference | fare-policy |
| 1:30 | 14.7s | Inspect both sides of the case | fare-agents |
| 1:44 | 13.6s | Return the disputed difference | fare-overview |
| 1:58 | 14.1s | Inspect the stored workflow | monitor |
| 2:12 | 12.0s | A small claim can require review | route |
| 2:24 | 12.1s | Safety goes straight to a person | safety |
| 2:36 | 14.5s | Unclear category? Classify first. | other-review |
| 2:51 | 11.3s | Request evidence. Hear the response. | driver-clarification-phone |
| 3:02 | 12.2s | Make the next step clear | rider-outcome-phone |
| 3:14 | 17.9s | Compare on evidence, not a winner | comparison |
| 3:32 | 15.1s | Measure what was actually checked | metrics |
| 3:47 | 16.3s | Validate the hosted path next | deployment |
| 4:03 | 11.5s | Evidence first. People in control. | closing |

Final timeline:255.37seconds,approximately4:15.

Preflight corrections: reference dropdown now matches every valid trip ID (not justTRIP-prefix IDs); Other helper apostrophe fixed; uppercaseMOCKmodeidentifiers label correctly. Browser checks verified selectedDEMO-DISP-003andfiveMockbadges. Agent screenshots were recaptured without expanded rule popovers. Tall-viewport driver capture keeps fixed navigation outside the response-card crop. Metrics footer constrained tothree lines. Captions76pxwithfive-wordchunks and explicit1680pxwidth. The reclassified case view switches atscene-localframe230; its timeline visibly preservesCategory:otherandcase-reclassified event.

Workbench comparison: original and imported compositions were pixel-identical atf1244,f2468andf6574(0differingpixels ineach2,073,600pixel frame). VideoTypeScriptcheckpassed. The new branch contains presentation-fixcommitd7f7a5f; developer baseline remains1a6d3fa.

Latest mid-render update incorporated: developer commit46d17cf(Simplify Request More Information + remove password inputs) was merged into v2 via676c8b8. The driver sequence now opens with the actual Reviewer Request More Information panel, followed by the actual Driver clarification created by Send Request. Its spoken explanation was refreshed. Backend tests rerun on this updated code:346passed. The measurements scene and narration were refreshed accordingly. Unchanged shots retain their earlier1a6d3fa captures of unchanged functionality. Core render timing remains255.37seconds.
