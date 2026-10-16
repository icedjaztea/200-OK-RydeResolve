# RydeResolve — updated submission walkthrough v2

English narrated and captioned walkthrough, approximately 4:15, 1920×1080 at 30 fps. Built from initial frontend commit `1a6d3fa` plus the subsequent `46d17cf` Request More Information update, on a separate branch, `feat/three-role-video-shotcraft-v2`.

## Deliverables

- [Final MP4](out/RydeResolve-Submission-Walkthrough-v2.mp4)
- [Editable project ZIP](out/RydeResolve-editable-project-v2.zip)
- [Spoken script](script.txt)
- [Captions](out/ryderesolve-captions.srt)
- [Independent review](out/independent-review.md)
- [Storyboard and evidence boundaries](production-notes.md)

## What changed from the first video

New browser captures show trip history, illustrative route cards, trip-linked intake, Other/manual classification, reviewer reclassification, readable facts, expanded policy rules, perspective cards, a driver clarification request and the rider outcome. All app footage is from the updated developer source. The original video branch remains intact.

Only synthetic local mock behavior is verified. No real payment, live telemetry, delivered notification, live Gemini execution or Tencent performance is represented. Interview findings and CodeBuddy proof require separate supporting records. Local evidence: 346 backend tests and 18 frontend proxy tests passed; four case paths checked; refund on an unclassified Other case rejected with HTTP 400.

## Edit / render

```sh
npm ci
npm run dev
npm run render
npm run finish
```

Node 22+ and Chromium are required. `remotion.config.ts` selects `/usr/bin/chromium`; adjust that path for your machine. The finalizer normalizes audio, adds optional English soft subtitles and chapter markers; burned captions are already in the render.

`src/timeline.json` is the single timing source. All screenshots and speech WAVs are local, so rendering does not call a live service. `src/workbench.ts` supports import into video-shotcraft Motion Workbench; titles/subtitles and shot timing are editable, and narration/SFX are separate tracks.

## Provenance and capture

Three small presentation corrections accompany the film: Rider intake selects an existing synthetic trip regardless of its ID prefix; the Other helper text renders its apostrophe correctly; Reviewer mock labels recognize uppercase mock-mode identifiers. No adjudication policy or financial behavior is changed. Capture uses the real local frontend/backend at 3001/8001 in memory/mock mode. `demo-trips.json` freezes synthetic trip data in app localStorage before capture. Reports are created through the Rider portal, then processed and reclassified through Reviewer controls. `capture.py`, `capture-finish.py`, and supporting scripts record the capture workflow; seed and start the app before running, and create the Other intake case through Rider UI if `out/other-id.txt` is not present.

Narration is synthetic Kokoro ONNX `af_heart`; generated WAVs are included. `narrate.py` is an optional regeneration helper referencing the session's separately downloaded model files; models and dependencies are not committed. PageCam and the adapted opening reveal come from [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft). See retained audio attribution and voice-engine license.

Latest mid-render update incorporated: developer commit 46d17cf (Simplify Request More Information + remove password inputs) was merged into v2 via 676c8b8. The driver sequence now opens with the actual Reviewer Request More Information panel, followed by the actual Driver clarification created by Send Request. Its spoken explanation was refreshed. Backend tests rerun on this updated code: 346 passed. The measurements scene and narration were refreshed accordingly. Unchanged shots retain their earlier 1a6d3fa captures of unchanged functionality. Core render timing remains 255.37 seconds.

The final export replaces only frames 5133–5470 (reviewer request and driver response) and 6374–6826 (updated test count) in the initial render. These ranges were rendered from the current shared composition, then the complete film was re-encoded and verified at 7,661 frames. A full render using the commands above produces the same current scene content.
