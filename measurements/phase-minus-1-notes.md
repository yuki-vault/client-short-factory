# Phase -1 measurement notes

## Status

- Formal measurement jobs completed: 0
- Qualitative test runs concluded: 1
- User verdict: broadly successful at the system/workflow level
- Branch decision: pending; this run is not eligible to select a branch
- Product code changes: none

## Job `phase_minus_1_001`

- Source path: `D:\Videos\youtubeVIDEO\【VCR Rust】振り返り雑談でもしよっか。【望月ほぐの⧸ゆにれいど！】 [dfGsZY_DWVg].webm`
- Matching `RIGHTS_AND_USAGE.md` entry confirmed: yes
- Range timer start signal: `2026-08-09T17:58:10.316+09:00`
- Start signal supplied by user: `PCに戻った。区間選定timer開始`
- Range timer end signal: pending
- Selected start: pending
- Selected end: pending
- Range alternatives: pending user confirmation

### Range-selection protocol change

- Range timer stopped: `2026-08-09T18:03:12.646+09:00`
- Human range selection completed: no
- `range_active_min`: invalid / not recorded
- Reason: the user clarified that watching the long source to choose a range is not acceptable active work and explicitly requested AI range selection.
- The elapsed wall time must not be used in the Phase -1 branch calculation.
- Approved exception: transcript-only AI range selection using the authorized local source; no product-code change and no frame analysis.
- Resulting job cannot establish the original human range-versus-caption branch by itself.

### Transcript-only AI range selection

- Candidate run: `scratch/candidate-runs/phase-minus-1-ai-001`
- Full-source transcription completed: yes
- Full-source transcription wall time: 1,277.7 seconds
- Transcript segments: 2,413
- Transcript validation: invalid ranges 0, backwards ordering 0, empty text 0
- Candidates compared: 5
- Candidate artifact: `scratch/candidate-runs/phase-minus-1-ai-001/candidates.json`
- Selected range: `01:21:00.440` to `01:21:50.650`
- Selected duration: 50.21 seconds
- Selection reason: the Discord mute mistake has a clear setup, self-praise, and punch line without requiring prior VCR Rust knowledge.
- Human `range_active_min`: not measured

### Initial job and AI caption pre-check

- Job ID: `phase_minus_1_001`
- Initial CLI completed: yes
- Acquire wait: 16.056 seconds
- Transcribe wait: 40.672 seconds
- Initial render wait: 28.056 seconds
- Initial technical QC: passed
- AI corrected six ASS cues before human review: `えさぁ` to `でさぁ`, punctuation, `きんきさん` to `ケンキさん`, `ジー` to `字`, and two broken end-of-clip line/cue splits.
- AI-assisted rerender wait: 23.769 seconds
- Post-edit technical QC: passed
- `captions.json`, SRT, and `subtitles/report.json` remain the automatic-generation versions by current Phase -1 design; render consumes the edited ASS.
- Caption timer start: `2026-08-09T18:48:55.630+09:00`
- Caption timer end signal: `2026-08-10T23:56:52.7663227+09:00`
- `caption_active_min` confirmed by user: 5
- Human caption edits: almost none; no exact edit count or replacement text was supplied
- Human caption-quality assessment: approximately 90% looked good and overall accuracy felt high
- Remaining concern: the user would still want to correct some fine details before treating the captions as final
- Chat latency, overnight elapsed time, metadata inspection, and unattended processing time are excluded from the five-minute active time.
- Final review: not started

### User stop decision and qualitative outcome

- Stop signal received: `2026-08-10T23:59:38.2753681+09:00`
- User decision: end this test here and treat it as broadly successful.
- System/workflow assessment: good overall.
- Caption assessment: approximately 90% looked good, with minor details still inviting manual correction.
- Remaining creative-quality work: font choice and a more visually compelling short-form editing style.
- Formal final-review timer: not started
- Formal final-review active minutes: not measured
- CSV row: not finalized; the fixed 12-step measurement was not completed
- Branch consequence: no Phase 1A / Phase 1B0 conclusion may be drawn from this run
- Approval consequence: this is a qualitative test conclusion, not delivery or publication approval
- Next product-code gate: explicit user approval is still required before Phase 0a or any later product-code change

### Public replay-metadata check

- Source URL confirmed by user: `https://www.youtube.com/watch?v=dfGsZY_DWVg`
- User authorization received: public metadata / heatmap retrieval only; no video download
- Retrieval date: `2026-08-10`
- yt-dlp version: `2026.07.04`
- Public metadata matched the local source ID, title, and approximately 8,555-second duration.
- Player clients checked across the primary and independent checks: default, web, web_safari, web_embedded, web_creator, mweb, tv, tv_simply, and android_vr
- Public heatmap points returned: 0 for every checked client
- Public chapter entries returned: 0 for every checked client
- Anonymous watch HTML also contained no `heatmapRenderer`, `markersMap`, `mostReplayed`, or `macroMarkersListRenderer` markers.
- An independent check repeated the public watch-page request under default, en-US, and ja-JP conditions; all returned HTTP 200 but no heatmap-related structures.
- A control video returned 100 heatmap points with the same yt-dlp installation, confirming that heatmap extraction was not globally broken.
- Public responses cannot distinguish between no generated heatmap and a heatmap withheld by YouTube eligibility, region, session, or experiment conditions.
- Result artifact: `scratch/candidate-runs/phase-minus-1-ai-001/replay-metadata-audit.json`
- Candidate reranking from replay data: not performed because the public heatmap is unavailable for this source.
- Existing transcript-only rank 1 remains selected: `01:21:00.440` to `01:21:50.650`.
- Metadata retrieval, command wait, and this discussion are not human active time.
- Video, subtitles, comments, and frames were not downloaded or opened by this check.
- Product code changes: none

## Rights and source gate

Before starting each job, manually confirm that the matching entry exists in
`RIGHTS_AND_USAGE.md` and contains both:

- `edit_permission_checked: yes`
- `acquisition_method: local`, `owner-export`, or `authorized-url`

Do not infer or fill permission values on the user's behalf. Do not open
transcript, caption text, or frames in Codex/Hermes unless the entry permits the
corresponding `external_ai_use`. A shared URL is not download permission.

## Active-time rule

Active time is only time spent by the user operating, deciding, listening, or
watching. Do not include chat response latency, agent reasoning, CLI wait time,
or unattended waits longer than 30 seconds. Record human timings only from the
user's self-report or explicit start/end signals; do not estimate them.

## Fixed measurement sequence

1. Start the range timer.
2. The user reviews the source and decides start/end.
3. Stop the range timer.
4. Run the existing CLI and record unattended waits separately.
5. Start the caption timer.
6. The user compares the original audio with captions and edits the ASS file.
7. Stop the caption timer.
8. Re-render with the same input, range, and job ID plus `--rerun-from render`.
9. Start the final-review timer.
10. The user watches the finished video from beginning to end.
11. Stop the final-review timer.
12. The user confirms all active-time values before the CSV row is finalized.

If start/end was already fixed before measurement, state that in `notes` and do
not use that job to conclude the range-selection branch.

## Current CLI commands

Use only paths, ranges, and job IDs confirmed by the user.

```powershell
$hermesPython = 'C:\Users\higes\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe'
& $hermesPython -m short_factory run `
  --input '<authorized-local-source>' `
  --start '<confirmed-start>' `
  --end '<confirmed-end>' `
  --job-id '<confirmed-job-id>'
```

After the user edits `jobs/<job-id>/subtitles/captions.ass`, re-render with the
same values plus:

```powershell
  --rerun-from render
```

Current-code caveat: render consumes the manually edited `captions.ass`, but
`captions.json` and `subtitles/report.json` remain from automatic subtitle
generation. The current QC subtitle-rule section reads that old report; it does
not revalidate the human-edited ASS. Therefore technical QC alone cannot confirm
the edited captions. The user's full beginning-to-end review of the rendered MP4
is mandatory for every Phase -1 measurement job.

## Per-job worksheet

Copy this section for each measured job. Values remain blank until confirmed by
the user or measured by the relevant command.

### Job `<job_id>`

- Source path:
- Matching `RIGHTS_AND_USAGE.md` entry confirmed:
- Source duration (min):
- Selected start:
- Selected end:
- Short duration (sec):
- Range timer start signal:
- Range timer end signal:
- `range_active_min` confirmed by user:
- `range_alternatives` confirmed by user:
- Acquire wait (min):
- Transcribe wait (min):
- Caption timer start signal:
- Caption timer end signal:
- `caption_active_min` confirmed by user:
- `caption_edits` confirmed by user:
- Render wait (min):
- Final-review timer start signal:
- Final-review timer end signal:
- `final_review_active_min` confirmed by user:
- `recovery_active_min` confirmed by user:
- Notes / exceptions:
- CSV row confirmed by user:

## Branch calculation

For each job, let `C_i = caption_active_min` and `R_i = range_active_min`.

- Caption-dominant: `C_i >= 10` and `C_i >= 1.5 * R_i`
- Range-dominant: `R_i >= 10` and `R_i >= 1.5 * C_i`
- Small difference / both light: otherwise

Reservation after measurement:

- Both jobs caption-dominant: Phase 1A
- Both jobs range-dominant: Phase 1B0
- One job only, disagreement, or any small-difference result: Phase 1M

Phase 0a is next regardless of branch, but requires explicit approval before any
product-code change.

## Preflight — 2026-08-09

- Rights entry: recorded in `RIGHTS_AND_USAGE.md` from the user's explicit chat authorization.
- Planned job ID: `phase_minus_1_001`
- Authorized local source: `D:\Videos\youtubeVIDEO\【VCR Rust】振り返り雑談でもしよっか。【望月ほぐの⧸ゆにれいど！】 [dfGsZY_DWVg].webm`
- External AI use: `provider=Codex/Hermes`, `payload=transcript`
- Source metadata only: WebM/Matroska, 8,555.041 seconds, 1,568,712,427 bytes
- Video stream: AV1, 1920x1080, 30 fps
- Audio stream: Opus, 48 kHz, stereo
- Existing Hermes Python imports `faster_whisper` successfully.
- Existing yt-dlp, FFmpeg, and ffprobe paths resolve successfully.
- D: free space at preflight: 1,693.96 GiB
- Measurement CSV rows: 0
- Content inspection, range selection, transcription, caption editing, rendering, and final review have not started.
- Next gate: wait for the user's explicit range-timer start signal; do not infer `range_active_min` while the user is away from the PC.
- Product code changes: none
