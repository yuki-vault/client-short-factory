# Manual caption addition and timing editing verification

status: need_approval

completed_slice: version-3 manual caption addition and timing editing only

verified_at: 2026-08-13T11:05:00+09:00

## Result

The standalone local WebUI now supports the requested manual edit loop:

```text
select an explicit preview
-> seek the video
-> add a draft caption at the playhead
-> edit text plus start/end time
-> validate the draft in place
-> save one immutable caption revision
-> render that explicit revision
-> revalidate caption hash, MP4 hash, and technical QC
```

The change did not add caption deletion, split/merge commands, approval,
download, delivery, automatic upload, style/font editing, or a
`current_render.json` pointer. The Phase -1 CSV and branch remain unresolved.

## Save contract

- caption schema remains version 1; stored cue shape remains `id/start/end/text`
- an unsaved caption is sent with `id: null`
- the worker allocates a stable ID only after the global OS lock is acquired
- every existing cue ID must remain present once and in the same relative order
- unknown IDs, deletion, reorder, duplicate IDs, stale base revision, invalid
  numbers, out-of-range times, overlaps, and no-op saves are rejected
- text, timing, and additions are published together as a new immutable revision
- old caption revision files and old explicit renders are never overwritten

The save validator now uses the same minimum duration, maximum lines, maximum
characters per line, and strict non-overlap rules as the render validator. This
prevents a draft from saving successfully and then failing only at render time.

## WebUI behavior

- `＋ 字幕を追加` inserts a draft at the current playhead in chronological order
- default end is the earliest of playhead + 2 seconds, the next cue, or job end
- start and end are always visible and editable as `MM:SS.cc`
- either boundary can be set from the current playhead
- only a new unsaved row has `追加を取消`
- text, timing, addition, and order participate in deep dirty detection
- discard restores all original text/timing and removes unsaved rows
- blank text, excess lines/characters, short duration, range errors, and overlap
  are shown on the affected row
- preview rendering is disabled while the draft is dirty or invalid
- stale-save failure keeps the draft and explains how to recover

The interaction design intentionally uses one contextual add action, visible
time fields, in-place recovery messages, and explicit discard instead of hidden
autosave, auto-clamping, or automatic reordering.

## Authorized real-media acceptance

The existing scratch-only authorized pilot was used; formal `jobs/` were not
used. The earlier desired manual split was reproduced through the new UI:

- job: `real_v3_pilot_001`
- prior current caption: revision 2, 16 cues
- new current caption: revision 3, 17 cues
- revision 3 caption hash:
  `a5cf7c135efe33ffdaf5c7a4dd1660c31d68ac069b6507262ad80613edf4cbbf`
- server-issued ID: `cue-human-r000000003-0001`
- added cue: `15.00-16.20` seconds, text `そう`
- following cue: `16.26-18.76` seconds, text
  `届いてなかったみんなに声が`
- reload restored revision 3, all 17 cues, and the edited times
- cue 6 seek moved the video to exactly 15.00 seconds

Browser checks also verified timing-only dirty state, overlap error display,
disabled save/render for invalid drafts, full timing restoration on discard,
new-row cancellation returning the page to clean state, the unsaved-preview
notice, and old revision-2 renders being labeled `前版` after the save.

## Explicit revision-3 render

- render ID: `render-20260813T020041-cc49ef6905`
- fixed caption revision: 3
- fixed caption hash:
  `a5cf7c135efe33ffdaf5c7a4dd1660c31d68ac069b6507262ad80613edf4cbbf`
- recorded and actual MP4 SHA-256:
  `e81662d1d972f2b34a4644156193d62e52e62aed847efc7b493a611260cb50a9`
- ASS contains `Dialogue: 0,0:00:15.00,0:00:16.20,...,そう`
- SRT contains `00:00:15,000 --> 00:00:16,200` followed by `そう`
- technical checks: passed (13/13)
- content review: pending
- browser media ready state: 4; duration: 50.233008 seconds
- no `current_render.json`, approval, download, or delivery artifact exists

## Regression verification

- Python 3.12 full suite: 74 tests passed
- Hermes Python 3.11 full suite: 74 tests passed
- JavaScript syntax check: passed
- localhost listener: `127.0.0.1:18765`
- unauthenticated `/api/jobs`: HTTP 401
- current server stderr: empty
- Phase -1 CSV: zero data rows; SHA-256
  `84ca13f77d96e57b4002ab4fb72bc0795ff51b787af28ca13cf4aab9724f0d21`
- formal legacy `jobs/`: 70 files, 32 directories, 5,828,893,449 bytes,
  with its pre-feature latest timestamp unchanged
- C mirror: 29 files, 279,899 bytes, unchanged
- synthetic fixture: 24 files, 8,643,846 bytes; revision 4 and its three
  existing renders unchanged
- prior revision-1 and revision-2 caption files retain SHA-256
  `0c2811149ef4b1024dbbe44d3cdfc629e4d8f07ba67c067d972717ce4a1a0f92`
  and `d1adcb1e4234b9a2b613939f984e1b57cad779b53552335101a5c127479a6852`
- both prior revision-2 renders retain caption hash `c497196a...` and actual
  MP4 SHA-256 `a21b8c82...`; both are projected as stale history

Final read-only review found no remaining P0 or P1 issue. The large formal-tree
aggregate rehash timed out under local I/O load, so preservation was rechecked
with the exact file/directory counts, byte totals, latest timestamps, and the
target immutable caption/render hashes listed above.

## Remaining gate

This verifies the editing mechanism and technical output, not the creative or
semantic approval of the short. Content remains `pending`. Do not implement or
claim approval/download/delivery, decide the Phase -1 branch, or expand into
split/merge, styling, or AI editing without a new explicit scope decision.
