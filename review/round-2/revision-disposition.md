# Round 2 Revision Disposition

## Status

- Review loop: completed at Round 2; no Round 3.
- Source draft: `review/workflow-draft-round-1.md`
- Critic inputs: 22 findings, consolidated by the arbiter into 9 root-cause groups.
- Process health: established; 10/10 serious findings contained reproducible operation sequences, 6 conflicts were decided, and schema-invalid findings were 0.
- Product code changes in this review run: none.

## Adopted in the final workflow

1. Replace the UI-only preflight with a 0.5-day shortest-route comparison between the existing CLI/file path and Hermes.
2. Measure reuse, new work, Windows restart/install round-trips, fixtures, and fault tests before committing to the P1 estimate.
3. Split P1 into cumulative stopping points: P1a, P1b, and conditional P1c.
4. Maintain one `phase-progress.md` during implementation so interrupted work has an explicit restart point.
5. Remove `current_render.json`; use actual output hash plus caption revision as the render identity.
6. Make the `current.json` publisher participate in the same OS lock as approval and delivery handlers.
7. Preserve full playback for the initial release, prevent muted/zero-volume review, and require an explicit content confirmation bound to the same identity.
8. Add the smallest orphan-revision recovery pointer for Windows pointer-replace failures.
9. Record delivery in two stages (`prepared`, then `delivered`) with job and user-visible delivery identifiers.
10. Fold the real-job R1-to-R2 exercise into P1 as a 0.5 active-day release check.

## Removed from the current implementation scope

- Independent P2 budget of 1.5 to 2.5 days.
- Detailed P3 creative-quality design, candidate schema, holdout procedure, and current restart threshold.
- The 180-second hard boundary and its fixtures.
- `current_render.json` creation, publishing, and recovery.
- Unconditional Hermes editor implementation; P1c is performed only if P0 shows that the file/CLI route cannot reach the milestone adequately.

## Preserved despite deletion requests

- Payload-specific rights notes remain a text-only operating record because transcript, audio, frames, and public metadata can have different permissions.
- Full-playback enforcement remains in the initial release because the concrete muted-playback failure path can lead to sending an unchecked output. This decision accepts about one day of browser/player work and repeated viewing in exchange for a defensible content-review record.

## Deferred, not silently decided

- AI candidate recall.
- Productized paced multi-cut editing.
- Automatic canonical selection among multiple renders for the same caption revision.
- The supported duration beyond the observed short clip.
- Exact Hermes-versus-CLI route and the final P1 estimate, both pending P0 measurement.

## Estimate after Round 2

- P0: 0.50 person-day.
- P1, including the integrated release check: provisional 6.10 to 9.10 person-days.
- Current implementation scope: provisional 6.60 to 9.60 person-days.
- This is not a commitment. P0 replaces it with a measured Windows WBS before P1 can be approved.
