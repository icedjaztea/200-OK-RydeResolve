# RydeResolve video project

A 4:31.5 English narrated submission walkthrough, 1920×1080 / 30fps. Synthetic demonstration only. No BGM; narration and restrained transition SFX.

## Delivered files

- [Watch or download the final video](out/RydeResolve-Submission-Walkthrough.mp4)
- [Download the editable project ZIP](out/RydeResolve-editable-project.zip)
- [Read the script](script.txt)
- [Independent review](out/independent-review.md)

## Deliverables
- out/RydeResolve-Submission-Walkthrough.mp4: final film
- out/ryderesolve-captions.srt: optional external captions (film also includes captions)
- script.txt: spoken script
- src/timeline.json: one source of truth for shot timing, captions and camera framing
- production-notes.md: storyboard, evidence and design decisions
- out/independent-review.md: independent review

## Edit and render
Requires Node.js 22+ and a Chromium browser.

```sh
npm ci
npx remotion studio src/index.tsx
npx remotion render src/index.tsx RydeResolve out/ryderesolve-walkthrough.mp4 --browser-executable=/usr/bin/chromium --concurrency=3 --crf=19
bash finish.sh
```

The retained package dependencies use Remotion 4.0.484. Rendering uses local screenshot/audio assets with no live service dependency. The copied PageCam component and adapted PaperTitleCard motion come from Vincentwei1021/video-shotcraft. See audio-attribution.md for SFX provenance. Voice: Kokoro ONNX, af_heart, Apache 2.0. The generated speech is synthetic. Check engine and asset licenses for your intended distribution.

## Evidence boundaries
Original application repository unchanged. App capture snapshot is from feat/three-role-frontend at 988bbc724cab2b5dd1a89c7389d1531a842cf505. Source files needed for the film are retained separately under app/ in the workspace, outside the small editable export. Local backend tests passed 302/302 with second demo identity keys set. No live Gemini execution, Tencent run, stakeholder interview, CodeBuddy development evidence or cloud latency was invented.

The Motion Workbench manifest is src/workbench.ts. Import into video-shotcraft/workbench to edit shot titles, subtitles and timing; captions remain inside the Scene component, generated from timeline.json. Audio is on separate tracks.
