# RydeResolve walkthrough production record
Mode: custom autonomous, explicitly chosen by user. Target: approximately four minutes, English, 1920×1080 at 30 fps.
Source frontend: feat/three-role-frontend, commit 988bbc724cab2b5dd1a89c7389d1531a842cf505. GitHub working branch created separately: feat/three-role-video-shotcraft.
Product: synthetic dispute resolution prototype. Audience: submission judges and technical reviewers.
Requirements: stakeholder problem, six-agent architecture and independent gate, fare refund, route and safety escalation, party portals, neutral implementation comparison, measurable outcomes and deployment.
Execution decisions: shorten to focused narrative; actual browser screenshots for all existing UI; explanatory diagrams for architecture and comparison; no invented interviews, cloud runs, Tencent screens or CodeBuddy evidence. Only synthetic fixtures captured. Demo credentials remain masked; no real personal information is used.
Visual tokens from branch CSS: pink #e8336a, dark pink #c91f56, blush #faf6f8, white surfaces, ink #1a1528, secondary #534659, muted #8a7d90, borders #ece4e8, radii 14/18. Typeface: local sans-serif matching app. Calm, precise, professional motion; 21-frame eased entrances, no handheld shake. High-density text stays frontal. UI images are 2× browser captures; PageCam is the camera foundation. Video commentary uses larger editorial captions for legibility.
Selected direction: blush editorial walkthrough. Alternatives considered: dark technical monitor treatment (too distant from product); Ink Press (promo pacing too compressed for a submission explanation). Styleframe will check title, comparison, and screenshot framing before final rendering.
Shot mapping: paper-title-card for the one opening wordmark reveal (scale 1.28→1, blur 7→0, delay 4+i*4, nine-frame easing); other scenes use custom explanatory layouts and PageCam screenshot pans, not claimed replicas of Gallery demos. No row-embed usage. Library index validated and exact PaperTitleCard.tsx read. Adaptation extends the opening hold for narration while preserving reveal timing, uses app sans and pink instead of template serif/amber.
Audio: locally generated synthetic English narration, subtle transition SFX. No BGM: explanation and evidence have priority over beat-driven promo pacing. Therefore a separate no-BGM version is unnecessary. Voice model: Kokoro ONNX (Apache 2.0), af_heart. SFX attribution copied from skill.
Verified local evidence: backend tests: 302 passed with both secondary demo identities configured. DISP-003 AUTO_ELIGIBLE, mock SGD4.50 refund; DISP-001 HUMAN_REVIEW, 4.3km deviation; DEMO-SAFETY-IN-FARE IMMEDIATE_HUMAN_REVIEW, no financial action. No cloud accuracy or speed claims.
Scope: original business repository kept unchanged. Branch snapshot and video project are under /workspace/ryderesolve-video.

## Final storyboard

| Start | Duration | Scene | Source |
|---|---|---|---|
| 0:00 | 14.6s | RydeResolve | Explanatory layout |
| 0:14 | 15.3s | One trip. Three perspectives. | Explanatory layout |
| 0:29 | 13.3s | A dedicated view for each role | Browser capture: landing |
| 0:43 | 17.3s | Advocacy is not authority | Explanatory layout |
| 1:00 | 13.6s | Start with the disputed difference | Explanatory layout |
| 1:14 | 14.3s | Inspect the evidence before the outcome | Browser capture: fare-evidence |
| 1:28 | 14.8s | Make both perspectives inspectable | Browser capture: fare-agents |
| 1:43 | 14.3s | A narrow, simulated remedy | Browser capture: fare-overview |
| 1:57 | 15.4s | Trace the stored execution | Browser capture: monitor |
| 2:13 | 13.9s | A small claim can still require review | Browser capture: route |
| 2:26 | 14.7s | Safety bypasses the Judge | Browser capture: safety |
| 2:41 | 14.9s | Explain the status and next step | Browser capture: rider-detail |
| 2:56 | 16.2s | Give the driver a clear response path | Browser capture: driver-detail |
| 3:12 | 21.2s | Compare implementations on evidence | Explanatory layout |
| 3:34 | 20.8s | What this recording verifies | Explanatory layout |
| 3:54 | 20.6s | A concrete path to a hosted demo | Explanatory layout |
| 4:15 | 16.1s | Resolve with evidence. | Explanatory layout |

Narration: generated locally with Kokoro; final speech tempo adjusted 1.18× after synthesis for a concise 4:31.5 edit. Subtitles chunked to six words with sentence-proportional timing. Source WAVs and timeline.json retain editability.

## Review fixes and intentional adaptations
The initial QA required larger typography: final captions are 56px, table/body explanatory text 33px. Screenshot source text remains native UI scale; the narrated fact is also repeated in large editorial text. Persistent branding and scene-index metadata are navigation, not information the viewer must read. Calm walkthrough pacing deliberately replaces Q8’s dramatic release-party ending; final wordmark and role markers hold for narration. The paper-title reveal keeps exact nine-frame easing then a long hold; the whole opening lasts 14.6s, meeting R3 breathing time. Comparison is neutral and avoids a winner. Final duration is 4:31.5, within the chosen 4–5 minute goal. No BGM is used to preserve speech clarity.

Q11 limited exceptions: arithmetic labels are 19px but are nonessential to comprehension because the same quoted/final/difference amounts are large and identified in 56px captions. Persistent synthetic-demo disclosure and closing next-step copy are 30px (slightly below the 32px auxiliary target), high contrast and repeated in narration/captions. These were visually checked at1080p.

Workbench verification: imported and original compositions were compared at f180, f1500, f6100; all three were pixel-identical (0 differing pixels of2,073,600). Browser editor opened atlocalhost:5198 without page errors. Runtime parity helper replaced unavailable rsync with dereferencing filesystem copy and selected installed Chromium; comparison rules were unchanged. Final MP4 audio normalization target -16LUFS, true peak -1.5dBTP.

Final encoded verification: H.264,1920×1080,30fps,8,145video frames (271.5s),AAC48kHz with optional English subtitle track and17chapters. Container duration271.6s due to audio/subtitle timing. Full FFmpeg decode completed with empty warning/error log. Final measured integrated audio -16.14LUFS and true peak -1.34dBTP (AAC overshoot relative to -1.5target, still below clipping).34frames were extracted from the encoded MP4 for independent review.
