from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from short_factory.candidate_artifacts import (
    CandidateConflictError,
    CandidateValidationError,
    append_upload_chunk,
    candidate_preview,
    candidate_source,
    create_candidate_run,
    finalize_upload,
    load_external_ai_authorization,
    load_candidate_set,
    load_run,
    prepare_analysis,
    project_candidate_run,
    publish_candidate_set,
    record_codex_selection_authorization,
    update_status,
)
from short_factory import candidate_artifacts


class CandidateArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "candidate-runs"
        self.source_bytes = b"synthetic-media-bytes" * 100

    def tearDown(self):
        self.temporary.cleanup()

    def _create(self):
        return create_candidate_run(
            self.root,
            file={
                "name": "authorized.mp4",
                "size_bytes": len(self.source_bytes),
                "content_type": "video/mp4",
                "last_modified_ms": 1234,
            },
            rights={
                "edit_analysis_confirmed": True,
                "local_processing_confirmed": True,
            },
        )

    def _upload(self, run):
        return append_upload_chunk(
            self.root,
            run["run_id"],
            index=0,
            start=0,
            end=len(self.source_bytes),
            total=len(self.source_bytes),
            data=self.source_bytes,
            chunk_sha256=hashlib.sha256(self.source_bytes).hexdigest(),
        )

    def _finalize(self, run):
        with patch(
            "short_factory.candidate_artifacts._probe_media",
            return_value={"duration_seconds": 60.0, "streams": ["audio", "video"]},
        ):
            return finalize_upload(
                self.root,
                run["run_id"],
                size_bytes=len(self.source_bytes),
                chunk_count=1,
            )

    def _candidate_document(self, run_id):
        return {
            "schema_version": 1,
            "run_id": run_id,
            "source_sha256": hashlib.sha256(self.source_bytes).hexdigest(),
            "assessment": {"mode": "straight", "reason": "単独で成立"},
            "provider": "lmstudio",
            "model": "local-model",
            "prompt_version": "candidate-map-reduce-v2",
            "candidates": [
                {
                    "candidate_id": "candidate-001",
                    "rank": 1,
                    "start": 10.0,
                    "end": 50.0,
                    "duration": 40.0,
                    "hook": "hook",
                    "setup": "setup",
                    "payoff": "payoff",
                    "summary": "summary",
                    "reason": "reason",
                    "context_dependency": "low",
                    "risk": "low",
                    "mode": "straight",
                }
            ],
        }

    def test_rights_must_be_explicit_true(self):
        with self.assertRaises(CandidateValidationError):
            create_candidate_run(
                self.root,
                file={
                    "name": "no.mp4",
                    "size_bytes": 1,
                    "content_type": "video/mp4",
                    "last_modified_ms": 0,
                },
                rights={
                    "edit_analysis_confirmed": False,
                    "local_processing_confirmed": True,
                },
            )
        self.assertEqual(list(self.root.iterdir()), [])

    def test_upload_is_sequential_idempotent_and_hash_checked(self):
        run = self._create()
        uploaded = self._upload(run)
        self.assertTrue(uploaded["upload"]["complete"])
        retried = self._upload(run)
        self.assertEqual(retried["upload"]["received_bytes"], len(self.source_bytes))
        with self.assertRaises(CandidateValidationError):
            append_upload_chunk(
                self.root,
                run["run_id"],
                index=0,
                start=0,
                end=len(self.source_bytes),
                total=len(self.source_bytes),
                data=self.source_bytes,
                chunk_sha256="0" * 64,
            )

    def test_finalize_recovers_exit_after_source_rename(self):
        run = self._create()
        uploaded = self._upload(run)
        run_dir = Path(uploaded["run_dir"])
        part = run_dir / "upload" / "source.part"
        destination = run_dir / "source" / "source.media"
        destination.parent.mkdir()
        os.replace(part, destination)
        finalized = self._finalize(run)
        self.assertEqual(
            finalized["manifest"]["source"]["sha256"],
            hashlib.sha256(self.source_bytes).hexdigest(),
        )
        self.assertTrue(finalized["source_path"].is_file())

    def test_finalize_retry_repairs_manifest_before_status_boundary(self):
        run = self._create()
        self._upload(run)
        finalized = self._finalize(run)
        run_dir = Path(finalized["run_dir"])
        update_status(
            run_dir,
            state="uploading",
            stage="upload",
            progress={"completed": len(self.source_bytes), "total": len(self.source_bytes)},
        )
        repaired = self._finalize(run)
        self.assertEqual(repaired["status"]["state"], "finalized")
        self.assertEqual(repaired["status"]["stage"], "finalized")

    def test_finalized_source_projects_range_playback_metadata_without_rehash(self):
        run = self._create()
        self._upload(run)
        finalized = self._finalize(run)
        source, path = candidate_source(self.root, run["run_id"])
        projected = project_candidate_run(self.root, run["run_id"])
        self.assertEqual(path, finalized["source_path"])
        self.assertEqual(source["size_bytes"], len(self.source_bytes))
        self.assertEqual(source["content_type"], "video/mp4")
        self.assertEqual(source["duration_seconds"], 60.0)
        self.assertEqual(projected["source_duration_seconds"], 60.0)
        self.assertEqual(
            projected["source_video_url"],
            f"/api/candidate-runs/{run['run_id']}/source/video",
        )
        path.write_bytes(b"x" * (len(self.source_bytes) - 1))
        with self.assertRaises(CandidateConflictError):
            candidate_source(self.root, run["run_id"])

    def test_finalize_rechecks_working_disk_space(self):
        run = self._create()
        self._upload(run)
        low_space = shutil._ntuple_diskusage(total=10, used=9, free=1)
        with patch(
            "short_factory.candidate_artifacts.shutil.disk_usage",
            return_value=low_space,
        ), self.assertRaisesRegex(CandidateConflictError, "disk space"):
            self._finalize(run)

    def test_prepare_analysis_is_durable_and_requires_finalized_source(self):
        run = self._create()
        with self.assertRaises(CandidateConflictError):
            prepare_analysis(self.root, run["run_id"])
        self._upload(run)
        self._finalize(run)
        queued = prepare_analysis(self.root, run["run_id"])
        self.assertEqual(queued["status"]["state"], "queued")
        self.assertEqual(load_run(self.root, run["run_id"])["status"]["state"], "queued")

    def test_codex_authorization_is_immutable_and_bound_to_source(self):
        run = self._create()
        self._upload(run)
        finalized = self._finalize(run)
        authorization = record_codex_selection_authorization(
            self.root,
            run["run_id"],
            approval_note="User approved this one source in chat.",
            rights_record="RIGHTS_AND_USAGE.md 2026-08-16",
        )
        self.assertEqual(authorization["provider"], "openai-codex")
        self.assertEqual(authorization["model"], "gpt-5.6-sol")
        self.assertEqual(
            load_external_ai_authorization(Path(finalized["run_dir"]))["content_sha256"],
            authorization["content_sha256"],
        )
        same = record_codex_selection_authorization(
            self.root,
            run["run_id"],
            approval_note="A later different note cannot overwrite the artifact.",
            rights_record="different",
        )
        self.assertEqual(same, authorization)

    def test_atomic_json_retries_transient_windows_replace_race(self):
        destination = Path(self.temporary.name) / "status.json"
        destination.write_text('{"old": true}\n', encoding="utf-8")
        real_replace = os.replace
        calls = 0

        def flaky_replace(source, target):
            nonlocal calls
            calls += 1
            if calls < 3:
                error = PermissionError("sharing race")
                error.winerror = 5
                raise error
            return real_replace(source, target)

        with patch.object(candidate_artifacts.os, "name", "nt"), patch.object(
            candidate_artifacts.os, "replace", side_effect=flaky_replace
        ), patch.object(candidate_artifacts.time, "sleep"):
            candidate_artifacts._atomic_json(destination, {"new": True})
        self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), {"new": True})
        self.assertEqual(calls, 3)

    def test_atomic_candidate_set_keeps_full_shape_and_detects_tamper(self):
        run = self._create()
        self._upload(run)
        finalized = self._finalize(run)
        run_dir = Path(finalized["run_dir"])
        preview = run_dir / "work" / "candidate-001.mp4"
        preview.parent.mkdir()
        preview.write_bytes(b"preview-bytes")
        with patch(
            "short_factory.candidate_artifacts._probe_media",
            return_value={"duration_seconds": 40.0, "streams": ["audio", "video"]},
        ):
            published = publish_candidate_set(
                run_dir,
                self._candidate_document(run["run_id"]),
                preview_sources={"candidate-001": preview},
            )
        self.assertEqual(published["prompt_version"], "candidate-map-reduce-v2")
        self.assertEqual(published["candidates"][0]["payoff"], "payoff")
        update_status(
            run_dir,
            state="complete",
            stage="complete",
            progress={"completed": 1, "total": 1},
            candidate_set_id=published["candidate_set_id"],
            candidate_count=1,
        )
        projected = project_candidate_run(self.root, run["run_id"])
        self.assertEqual(projected["status"], "complete")
        self.assertEqual(len(projected["candidates"]), 1)
        self.assertNotIn("run_dir", projected)
        self.assertNotIn("source_path", projected)
        _, served = candidate_preview(self.root, run["run_id"], "candidate-001")
        served.write_bytes(b"tampered")
        with self.assertRaises(CandidateConflictError):
            load_candidate_set(run_dir)

    def test_zero_candidates_is_a_valid_complete_result(self):
        run = self._create()
        self._upload(run)
        finalized = self._finalize(run)
        run_dir = Path(finalized["run_dir"])
        document = self._candidate_document(run["run_id"])
        document["assessment"] = {"mode": "reject", "reason": "素材不適合"}
        document["candidates"] = []
        published = publish_candidate_set(run_dir, document, preview_sources={})
        self.assertEqual(published["candidates"], [])

    def test_codex_candidate_identity_is_accepted_but_pinned(self):
        run = self._create()
        self._upload(run)
        finalized = self._finalize(run)
        document = self._candidate_document(run["run_id"])
        document.update(
            {
                "provider": "openai-codex",
                "model": "gpt-5.6-sol",
                "prompt_version": "candidate-codex-full-v1",
                "assessment": {"mode": "reject", "reason": "候補なし"},
                "candidates": [],
            }
        )
        published = publish_candidate_set(
            Path(finalized["run_dir"]), document, preview_sources={}
        )
        self.assertEqual(published["provider"], "openai-codex")


if __name__ == "__main__":
    unittest.main()
