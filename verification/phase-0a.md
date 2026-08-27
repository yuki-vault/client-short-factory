# Phase 0a standalone local WebUI prototype verification

> Historical synthetic-prototype record. Manual caption addition and timing
> editing were added later under explicit approval; see
> `verification/manual-caption-timing.md`. Other stop gates remain in force.

status: need_approval

completed_phase: Phase 0a standalone-local-WebUI prototype only

verified_at: 2026-08-12T00:50:00+09:00

## Result

The approved vertical slice works on the live Windows machine:

```text
caption text edit
-> immutable caption revision
-> explicit revision-fixed immutable preview render
-> actual MP4 hash + caption hash + QC revalidation
-> technical passed / content pending shown separately
```

The chosen path is a standalone `127.0.0.1` WebUI over the existing Python/FFmpeg core. No Hermes dashboard plugin, third-party editor code, or new runtime dependency was added. This is not the superseded full Phase 0a contract and does not decide the still-pending Phase -1 branch.

## Live synthetic run

- jobs root: `scratch/phase-0a-webui/jobs`
- job: `phase0a-synthetic`
- source: programmatically generated 8.0-second video/audio fixture; no user media
- current caption: revision 4, caption hash `c864a9584f81c32430a0788725a669395244af2585e4eae9c5660796620aa89d`
- saved UI edit: first cue is `Fixture PASS.`
- published renders:
  - `render-20260811T151757-5215c9a96c`, caption revision 3, SHA-256 `ea65efe1c1b2ae26d54510837d3363e9d8622d452ea8608110295108e160e2a8`
  - `render-20260811T152013-99f7d0d89d`, caption revision 4, SHA-256 `1506b920c08c5708b7ffe098423d2ccd82dc3e10f3e64a730a83cc5f5e36071c`
  - `render-20260811T154007-6945d8e075`, caption revision 4, same deterministic SHA-256 as the other revision-4 render
- metadata SHA-256 matched the actual MP4 bytes for all three renders.
- all three renders have technical QC `true` and content review `pending`.
- two earlier render attempts with deliberately invalid overlong fixture subtitles failed before publication; no partial visible render directory remained.
- latest revision-4 render took about 4.9 seconds from render ID timestamp to metadata publication.

## Browser verification

Browser: Codex in-app browser on the live Windows desktop.

- launch token was exchanged for an HttpOnly/SameSite session cookie and removed from the visible URL.
- app restart restored job `phase0a-synthetic`, caption revision 4, and its caption text.
- video reached `readyState=4`; measured duration was exactly 8 seconds.
- clicking cue 2 moved playback from `0.0` to `2.4` seconds.
- an unsaved edit followed by in-app reload was blocked; the textarea retained `Fixture UNSAVED.` until explicit discard.
- while render was running, all three caption textareas and the render button were disabled.
- after creating a second render for caption revision 4, page reload selected no canonical render and displayed `renderを選択（字幕v4に複数あり）`.
- explicitly selecting `render-20260811T154007-6945d8e075` restored playable video and displayed `technical=passed`, `content=pending`.
- browser developer log after final restart: empty.
- final source-checkout server is listening only on `127.0.0.1:18765`; stderr is empty.

## Automated verification

```text
py -3.12 -m unittest discover -s tests -q
Ran 57 tests in 12.093s - OK

C:\Users\higes\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe -m unittest discover -s tests -q
Ran 57 tests in 12.345s - OK

py -3.12 -m compileall -q short_factory tests verification
compileall OK
```

Targeted final timings:

| Suite | Wall time |
|---|---:|
| real process-exit fault boundaries | 0.968 s |
| localhost server/API contract | 10.478 s |
| artifact integrity | 1.121 s |
| global lock boundaries | 0.924 s |

The suite covers immutable revisions, stale-base rejection, process exit after caption publication, process exit before render publication, explicit render revision capture, actual MP4/caption hash validation, contradictory QC rejection, busy locking, non-contention lock errors, lock hard-link rejection, Windows junction confinement, malformed artifact quarantine, fixed subprocess argv, bounded startup handshake, strict worker markers, Host/Origin/CSRF/session checks, byte Range/HEAD, huge Range rejection, and tampered media refusal.

## Scope and preservation checks

- `current_render.json`: 0 files
- approval/download/delivery implementation: none
- split/merge/timing editing API or UI: none; text-only save is enforced
- 180-second hard gate: not added, per Round 2 final disposition
- AI candidate selection, font/style editor, paced multi-cut editing: not added
- external package/vendor code/new dependency: none
- mutable `--rerun-from`: rejected before a workflow job directory is created
- legacy manifest version 1/2 jobs: read-only; newest file under formal `jobs/` remains `2026-08-11T11:25:52+09:00`, before this implementation
- formal Phase -1 CSV and branch decision: unchanged and pending
- C: mirror: untouched; its newest file remains `2026-08-07T10:35:25+09:00`
- test media and all browser mutations were confined to `scratch/phase-0a-webui/`

## Changed files

- `pyproject.toml`
- `README.md`
- `short_factory/artifacts.py`
- `short_factory/cli.py`
- `short_factory/mutations.py`
- `short_factory/pipeline.py`
- `short_factory/rendering.py`
- `short_factory/review_server.py`
- `short_factory/webui/index.html`
- `short_factory/webui/app.js`
- `short_factory/webui/style.css`
- `tests/test_artifacts.py`
- `tests/test_atomic_process_boundaries.py`
- `tests/test_mutations.py`
- `tests/test_pipeline_workflow.py`
- `tests/test_review_server.py`
- `tests/test_utils.py`
- `verification/create_phase0a_fixture.py`
- `verification/phase-0a.md`

## WBS classification after the prototype

| Item | Classification | Evidence / next work |
|---|---|---|
| immutable caption save + recovery pointer | run on synthetic fixture | revision 4 survives restart; process-exit test passes |
| explicit immutable preview render | run on synthetic fixture | three published renders; actual hashes verified |
| technical/content state separation | run on synthetic fixture | `passed` and `pending` displayed independently |
| standalone localhost review surface | run on synthetic fixture | edit, reload guard, seek, render, restart all exercised |
| existing FFmpeg/QC core | reused and revalidated | 8-second libx264 render and decode/QC pass |
| synchronized-folder hard reject | new, deferred P1a | current `D:\HermesWorkspace` is not a sync folder |
| authorized real-media version-3 pilot | new | not run under this prototype approval |
| packaged-install smoke test | new | source-checkout execution only |
| approval/full-playback/download/ledger | new, deferred P1b | deliberately absent |

## Residual risk and next gate

The prototype establishes that the standalone WebUI route is viable, but it is not yet a release workflow. It has not been exercised on a newly created authorized real-media version-3 job, and it cannot approve or deliver a render. Synced-folder rejection and packaged-install behavior are also unverified.

Estimated next bounded slice:

- authorized real-job pilot plus usability notes: 0.25-0.5 active day
- synchronized-folder guard and packaged-install smoke: 0.25-0.5 active day
- P1b approval/full-playback/download/ledger: separately estimated after the real-job pilot; no authorization in this phase

Stop here. Do not start the real-job pilot, playhead split/timing editing, style/font work, AI candidate work, P1b, or Phase 0a expansion without explicit approval.
