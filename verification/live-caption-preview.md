# Live caption preview verification

Date: 2026-08-13

## Scope

This change is limited to the approved standalone local WebUI prototype. It does
not resolve the Phase -1 branch and does not add approval, download, delivery,
autosave, or proxy/master artifact roles.

The editor now treats the slow FFmpeg render as a final-check operation:

```text
edit text or timing
-> paint an unsaved DOM caption immediately
-> save one immutable caption revision when satisfied
-> create one explicit revision-bound render for final visual review
```

## Live behavior

- Text and valid start/end edits repaint synchronously on the current frame.
- Playback uses `requestVideoFrameCallback` when available, with an animation
  frame fallback.
- Active cue semantics are `start <= mediaTime < end`.
- The existing burned-in caption band is covered while a draft is dirty, so a
  shortened cue does not leave the previous render's caption visible.
- `LIVE DRAFT` is explicitly marked as unsaved and not rendered.
- The overlay writes user text through `textContent`; it never interprets HTML.
- Timing inputs support Up/Down for 0.10 seconds and Shift+Up/Down for 0.01
  seconds. Player buttons seek backward or forward by 0.10 seconds.
- Native video fullscreen and picture-in-picture are disabled for draft review;
  the custom fullscreen control opens the complete stage so the DOM caption is
  retained.

No edit-time API request, revision publication, or FFmpeg process is added.
Saving and rendering retain the existing immutable artifact and hash checks.

## Automated verification

- `py -3.12 -m unittest discover -s tests -q`: 75 tests passed.
- Hermes Python 3.11.15 `unittest discover`: 75 tests passed.
- invalid-CSRF local HTTP response test: 10 consecutive passes after draining
  rejected bounded request bodies before responding.
- `node --check short_factory/webui/app.js`: passed.
- `py -3.12 -m compileall -q short_factory`: passed.

The static UI test also verifies that the live-caption path uses `textContent`,
contains frame-callback support, and contains no `fetch` or `apiRequest` call.

## Real-media browser acceptance

Fixture: `real_v3_pilot_001`, current caption revision 5, selected render identity
suffix `e4c603f2d3`.

1. At 16.00 seconds, changing cue 6 text from `そう` to `そう！` appeared in the
   video overlay immediately while paused.
2. Changing its end from 16.10 to 15.90 seconds hid the live caption at 16.00;
   the opaque draft mask remained, so the old burned-in caption was not visible.
3. Restoring 16.10 made the draft caption visible again.
4. Literal text `<img src=x onerror=alert(1)>` produced zero image elements and
   remained plain text.
5. The custom fullscreen control retained the live overlay.
6. The test draft was discarded without saving. Revision 5, selected render,
   output identity, render count, technical `passed`, and content `pending`
   matched the pre-test state.

## Deliberate limitation

The live DOM caption is a timing and wording preview, not pixel-identical libass
output. A dark mask is used because the current preview MP4 already contains
burned-in captions. Creating a captionless editor proxy would introduce the
separately gated proxy/master role, so final font, outline, position, and image
quality still require one explicit FFmpeg render after saving.
