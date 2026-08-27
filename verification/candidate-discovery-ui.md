# Candidate discovery WebUI verification

Date: 2026-08-14 (Asia/Tokyo)

## Scope and gate

The user explicitly requested the next workflow experiment: drop a local video into the independent localhost WebUI and receive up to five short-form candidates. This is a narrow product-code override for candidate discovery. It does not decide the pending Phase -1 branch and does not authorize approval, download, delivery, publication, or candidate-to-job adoption.

The system returns `0..5`, not exactly five. Zero is a valid result for silent, shorter-than-30-second, unsuitable, or weak-evidence material. Fabricating weak candidates to fill five slots is prohibited.

## Implemented flow

1. The user drops one local video or chooses it with the file picker.
2. The UI requires explicit edit/analysis permission and consent to local Whisper + LM Studio processing.
3. The browser streams 8 MiB chunks to an isolated candidate run. Every chunk is SHA-256 checked and already committed chunks are re-sent and revalidated after file re-selection.
4. Finalization computes a full source SHA-256, verifies video and audio streams with ffprobe, checks free space, and publishes an immutable source manifest.
5. A disk-reporting worker extracts 16 kHz mono audio and transcribes resumable 900-second chunks with `faster-whisper small / CPU / int8`.
6. A fail-closed map/reduce selector calls only the literal loopback LM Studio endpoint `127.0.0.1:1234`, using `qwen3.5-9b-uncensored-hauhaucs-aggressive.gguf` and a strict JSON schema.
7. Valid non-overlapping 30-to-60-second candidates are preview-encoded with libx264/AAC. A complete 0-to-5 candidate set is published atomically only after every preview validates.
8. The WebUI shows progress, cancellation/recovery, candidate cards, and a Range-capable local preview. It offers no adoption, approval, download, delivery, or external upload action.

Durable runs live below the configured jobs root at `.candidate-runs/<run-id>/`; normal jobs and candidate runs use separate locks and artifact namespaces.

## Automated verification

Final regression on 2026-08-14:

- Python 3.12.10: `108 tests` passed.
- Hermes Python 3.11.15: `108 tests` passed.
- `node --check short_factory/webui/app.js`: passed.
- `py -3.12 -m compileall -q short_factory tests`: passed.
- Synthetic HTTP integration passed create, hashed upload, finalize, subprocess handoff, analysis, atomic publish, HEAD preview, byte Range `206`, and ETag validation.
- Silent and shorter-than-30-second inputs complete normally with `reject / 0 candidates` and do not call LM Studio.

Security and integrity coverage includes exact loopback Host/session/Origin/CSRF checks, bounded raw request bodies, sequential/idempotent upload, filename-as-metadata-only behavior, path confinement, source/preview hash revalidation, corrupt transcript-cache rejection, per-run OS locking, durable interruption recovery, strict candidate schema, and no partial candidate-set publication.

## Authorized real-media pilot

The UI was exercised with a 60.233-second local clip derived from the already authorized source. Run `candidate-20260813T231543-6d56ee458c` completed and published one candidate:

- source SHA-256: `833a6c2e379a86167a79f2f30065cc5aadcaa4cdf9e343a0ec3dc50b50b1e71e`
- candidate: `00:07.32` to `01:00.21` (52.89 seconds)
- preview duration: 52.921016 seconds
- preview SHA-256: `d221e51963adc3b6c71c16b1af45adff3995719fafb3f4aa3e92bc5e297e94e5`
- provider/model: local LM Studio / `qwen3.5-9b-uncensored-hauhaucs-aggressive.gguf`
- prompt version: `candidate-map-reduce-v3`

The browser loaded the published preview successfully. Reload restored the disk-backed completed run rather than starting a new analysis.

## Quality finding

The workflow and artifact contracts are working, but candidate quality is not production-proven. The real 60-second pilot found the intended mute-forgotten story, yet its card misread the ASR phrase about handwriting as a phrase about voice. An independent first-900-second probe of the full source also returned zero and missed a previously identified candidate. Therefore:

- candidate cards are navigation aids, not authoritative summaries;
- the user must judge hook and payoff from the preview;
- the present local Qwen 9B selector cannot be claimed to have reliable top-five recall;
- the next quality experiment should compare a stronger local selector and/or higher-accuracy ASR before adding more editing UI.

## Preserved boundaries

- Phase -1 CSV remains unfinalized and the branch decision remains pending.
- No formal legacy job was rerun or migrated.
- Candidate analysis did not modify caption revisions, renders, approval state, download state, or delivery records.
- No transcript was sent to an external provider.
- No YouTube/publication/delivery action was added.
