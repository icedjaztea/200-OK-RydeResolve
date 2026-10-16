#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
ffmpeg -v error -i out/ryderesolve-walkthrough.mp4 -i out/ryderesolve-captions.srt -i out/chapters.ffmeta -map 0:v -map 0:a -map 1:0 -map_metadata 2 -map_chapters 2 -c:v copy -c:a aac -b:a 192k -af 'loudnorm=I=-16:TP=-1.5:LRA=9' -ar 48000 -c:s mov_text -metadata:s:s:0 language=eng -disposition:s:0 0 -movflags +faststart -y out/RydeResolve-Submission-Walkthrough-v2.mp4
