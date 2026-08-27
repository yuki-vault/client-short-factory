# Authorized real-media version-3 pilot verification

> Historical pilot record. Its text-only/timing limitation was superseded by
> the explicitly authorized follow-up in `verification/manual-caption-timing.md`.
> Approval, delivery, and Phase -1 stop gates remain in force.

status: need_approval

completed_slice: authorized real-media version-3 pilot only

verified_at: 2026-08-13T03:20:00+09:00

## Result

The standalone local WebUI path completed one authorized real-media pilot:

```text
authorized local source
-> new manifest version 3 job
-> machine caption revision 1
-> text-only human correction as immutable revision 2
-> explicit revision-2 immutable preview render
-> actual caption/MP4 hash and QC revalidation
-> server restart and browser recovery
```

This pilot did not alter the formal Phase -1 measurement, choose its branch, mutate any legacy job, approve content, download/deliver media, or expand product scope.

## Input and rights

- job: `real_v3_pilot_001`
- jobs root: `scratch/phase-0a-webui/jobs`
- local source: `D:\Videos\youtubeVIDEO\【VCR Rust】振り返り雑談でもしよっか。【望月ほぐの⧸ゆにれいど！】 [dfGsZY_DWVg].webm`
- source identity: 1,568,712,427 bytes; recorded size/mtime matched the earlier authorized job
- source range: 4860.44-4910.65 seconds (`01:21:00.440-01:21:50.650`), 50.21 seconds
- processing: local Codex/Hermes only; no upload, publication, approval, download, or delivery
- matching 2026-08-13 entry recorded in `RIGHTS_AND_USAGE.md`

## Measured run

- full pipeline wall time: 82.2 seconds observed by the invoking process; stage timestamps span 81.459 seconds
- explicit immutable revision render: approximately 20.745 seconds from render ID timestamp to metadata publication
- pipeline stages: acquire, audio, transcribe, subtitles, render, QC; all six completed with null errors
- bootstrap technical output: 50.233008 seconds, H.264 Main, 1080x1920, yuv420p, 30 fps, AAC 48 kHz stereo

## Caption revision

- revision 1: machine, 16 cues, caption hash `d1a8c2808996d25f80183446d7b3e3e90f3fe1aa507c4d2adfdfb51c6de6d8f2`
- revision 2: human, base revision 1, 16 cues, caption hash `c497196afe2216be31183182a0f65bb80e5271c5763cf620b013cf8d401e9c58`
- cue IDs and all start/end times remained identical; only six cue texts changed
- revision 1 remains present and byte-distinct from revision 2
- `current.json` and `recovery.json` both point to revision 2 with the same caption hash

The six compatible corrections included `でさぁ`, `ケンキさん`, `ほぐのの字`, and the final line wrapping/text cleanup. The previously hand-edited legacy ASS had added a separate 15.00-16.20 `そう` cue. That is a split/timing edit, so it was deliberately not migrated through this text-only prototype.

## Immutable preview render

- render ID: `render-20260812T181353-21529a35cb`
- fixed caption revision: 2
- output SHA-256: `a21b8c8223167e5e27215e650cb320fc090a0523d7aa5a4002f8a54956705fad`
- recorded output hash equals actual MP4 SHA-256
- render caption hash equals current revision-2 caption hash
- render MP4: 24,945,511 bytes, 50.233008 seconds
- independent ffprobe: H.264 Main, 1080x1920, yuv420p, 30 fps; AAC 48 kHz stereo
- independent full-stream FFmpeg decode: exit code 0
- technical QC: 13/13 checks passed
- content review: pending
- render ASS and SRT match revision 2

`output/short.mp4` and top-level `qc.json` are bootstrap artifacts from revision 1. The reviewed identity is only the explicit revision-2 file under `renders/render-20260812T181353-21529a35cb/`.

## Browser and restart verification

- WebUI displayed the real 50.2-second job and machine revision 1
- saving through the UI produced revision 2
- render-time caption fields and render control were disabled
- completed UI displayed `technical=passed` and `content=pending` separately
- video reached `readyState=4`, duration 50.233008 seconds
- cue 3 seek moved the player to 7.24 seconds
- after restarting the localhost server, selecting the real job restored revision 2, the same explicit render, playable media, and the separated states
- final listener: `127.0.0.1:18765`; stderr empty; unauthenticated API returned 401

## Preservation and regression verification

- Phase -1 CSV: still zero data rows; SHA-256 `84ca13f77d96e57b4002ab4fb72bc0795ff51b787af28ca13cf4aab9724f0d21`
- formal legacy `jobs/`: exact pre-pilot aggregate preserved (`aff7fb881f51a7573def117deb74979656f20271c1d52d64accf2a08e2e7fd72`)
- C: mirror: exact pre-pilot aggregate preserved (`41896cb6a946750772ab5ae7865e5f64b1bd4686f07fc386dc6dd179c6f41ef0`)
- synthetic fixture plus existing lock: exact pre-pilot aggregate preserved (`781f419c1bee5576a21f3116a57eed4b3c4e127cc730652569ed93ff9f4e42a7`)
- the new pilot is the only added scratch job sibling: 25 files, 126,315,621 bytes
- `current_render.json`: absent
- approval, download, delivery, ledger artifacts: absent
- Python 3.12.10: 57 tests passed in 10.944 seconds
- Hermes Python 3.11.15: 57 tests passed in 11.865 seconds

## Residual limits and next gate

- Content remains pending; no claim of semantic approval or delivery readiness was made.
- Caption coverage is 0.8082 and does not guarantee semantic or creative quality.
- The prototype cannot split/merge cues or change timing, which blocked exact migration of the legacy manual cue split.
- Immutable means app-published revision directories and hash-bound identities; it is not OS WORM storage.
- Synced-folder rejection and packaged-install behavior remain outside this pilot.

Stop here. Do not implement timing/split/merge, approval/full-playback/download/delivery, style/font work, AI candidate UI, or decide the Phase -1 branch without a new explicit approval.
